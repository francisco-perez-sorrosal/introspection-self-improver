"""Drive a Recipe as an Introspection task in the development environment.

The expensive lane, and the only one that produces platform evidence: each episode is a real
task, so it leaves a conversation, traces, spans, cost and usage, and `recipe_git_commit_sha`
lineage behind. The agent runs in a cloud sandbox; the τ environment stays on this machine and
is reached back through `introspection dev --mcp tau=<url>`.

The rendezvous is unchanged, because it is driven by the MCP bridge rather than by the
transport. What differs is only how a turn is delivered and observed:

    send_user_text  →  `tasks prompt <task> --prompt <text>`   (one run per user turn)
    next_turn       →  `tasks stream <task> --run <run>`       (AG-UI events, JSONL)

One run can contain several assistant messages. The sandbox calls a τ tool, our bridge parks,
the call surfaces here as `TOOL_CALL_END`, τ executes it, `PiRecipeAgent` posts the result to
the bridge, the parked handler returns, and the *same* run keeps streaming. So the stream stays
open across the rendezvous and turns are queued as they complete — the same shape the local
transport uses for Pi's `message_end`.

CLI startup is this lane's latency tax. Every `introspection` invocation pays ~5.5s of process
startup (node → platform binary) before it does anything, and the stream subprocess is the only
path by which τ learns a tool call exists — while the sandbox's MCP daemon gives that parked
call only ~30s. Paying the prompt's startup and then the stream's startup serially was eating a
third of that budget before τ could see anything, so the stream for a turn is spawned *before*
its `tasks prompt` and the two startups overlap. The envelope's own `run_id` plus a single
reattach make the early attach safe; see `send_user_text` and `_StreamSession`.

The AG-UI vocabulary below is documented nowhere; it was read off a live run. See
`tests/test_transport_platform.py` for the captured shapes this parser is pinned to.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loguru import logger

from tau_adapter.transport import (
    AssistantTurn,
    PiToolCall,
    TransportFailure,
    TurnItem,
)

CLI = "introspection"

# How long to wait for the current run to finish before sending the next user turn. Generous:
# the ceiling only matters once something has already gone wrong, and prompting early is the
# very thing this gate exists to prevent.
SETTLE_GRACE_SECONDS = 300.0


class StreamAssembler:
    """Turn AG-UI events into τ-shaped assistant turns.

    Emits one turn per completed text message and one per completed tool call. Deliberately not
    merged: τ's protocol expects a message to carry either narration or tool calls, and the
    platform streams them as separate event groups, so merging them would be the adapter
    inventing a message shape the host never produced.

    Fed each event exactly once. Arguments arrive as `TOOL_CALL_ARGS` deltas and are
    concatenated in arrival order; re-feeding an event would corrupt them, and a corrupted
    argument set does not fail loudly — it deadlocks the rendezvous, because the result would be
    posted under a key no parked handler is waiting on.
    """

    def __init__(self) -> None:
        self._text: dict[str, list[str]] = {}
        self._call_name: dict[str, str] = {}
        self._call_args: dict[str, list[str]] = {}
        self.finished = False

    def feed(self, envelope: Mapping[str, Any]) -> list[TurnItem]:
        event = envelope.get("event") or {}
        kind = event.get("type")

        if kind == "TEXT_MESSAGE_START":
            self._text[str(event.get("messageId"))] = []
        elif kind == "TEXT_MESSAGE_CONTENT":
            self._text.setdefault(str(event.get("messageId")), []).append(event.get("delta") or "")
        elif kind == "TEXT_MESSAGE_END":
            text = "".join(self._text.pop(str(event.get("messageId")), [])).strip()
            # An empty text message is not a turn. τ would record a contentless assistant
            # message and hand the floor to the user simulator with nothing said.
            if text:
                return [AssistantTurn(text=text, tool_calls=())]

        elif kind == "TOOL_CALL_START":
            call_id = str(event.get("toolCallId"))
            self._call_name[call_id] = str(event.get("toolCallName") or "")
            self._call_args[call_id] = []
        elif kind == "TOOL_CALL_ARGS":
            self._call_args.setdefault(str(event.get("toolCallId")), []).append(
                event.get("delta") or ""
            )
        elif kind == "TOOL_CALL_END":
            return self._finish_tool_call(str(event.get("toolCallId")))

        elif kind == "RUN_ERROR":
            return [TransportFailure(reason=f"run error: {event.get('message') or 'unknown'}")]
        elif kind == "RUN_FINISHED":
            self.finished = True

        # Ignored on purpose:
        #   REASONING_* — τ's AssistantMessage has no reasoning field, so the local lane drops
        #     Pi's `thinking` blocks for the same reason. Dropping them here keeps the lanes
        #     comparable rather than giving the platform lane a channel τ cannot grade.
        #   TOOL_CALL_RESULT — the platform echoing the result *we* posted through the bridge.
        #     Treating it as input would double-count τ's own tool execution.
        #   CUSTOM (run_lifecycle), RUN_STARTED, and untyped heartbeats — no turn content.
        return []

    def _finish_tool_call(self, call_id: str) -> list[TurnItem]:
        raw = "".join(self._call_args.pop(call_id, []))
        pi_name = self._call_name.pop(call_id, "")
        try:
            arguments = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as exc:
            # Loud, because the alternative is silent: posting a result under mis-parsed
            # arguments leaves the sandbox's MCP call parked until its daemon times out.
            return [
                TransportFailure(
                    reason=(
                        f"could not reassemble arguments for {pi_name} ({exc}); "
                        f"raw delta stream was {raw[:200]!r}"
                    )
                )
            ]
        if not isinstance(arguments, dict):
            return [
                TransportFailure(
                    reason=f"{pi_name} arguments reassembled to {type(arguments).__name__}, not an object"
                )
            ]
        return [
            AssistantTurn(
                text=None,
                tool_calls=(PiToolCall(id=call_id, pi_name=pi_name, arguments=arguments),),
            )
        ]


class _StreamSession:
    """One `tasks stream` subprocess, its reader state, and the rules it was attached under.

    `drop_run_id` names the previous, already-consumed run. An overlapped attach may reach the
    platform before the new run exists, in which case `--run current` resolves to that previous
    run and replays it — events this transport has already turned into τ messages. Filtering by
    the envelope's own run id keeps a lost race from double-feeding the episode.

    `emitted` counts turn items queued from this stream. A reattach replays from event 0 with a
    fresh assembler, so it is only safe while nothing was emitted — one duplicated turn would
    desynchronise τ from the agent for the rest of the episode.
    """

    def __init__(
        self,
        proc: subprocess.Popen[str] | None,
        assembler: StreamAssembler,
        drop_run_id: str | None,
        reattaches_left: int,
    ) -> None:
        self.proc = proc
        self.assembler = assembler
        self.drop_run_id = drop_run_id
        self.reattaches_left = reattaches_left
        self.emitted = 0
        self.dropped = 0
        self.thread: threading.Thread | None = None


class PlatformTransport:
    """One Introspection task per episode, one run per user turn."""

    def __init__(
        self,
        runtime_id: str,
        repo_root: Path,
        agent_name: str = "agent",
        environment: str = "development",
        idle_timeout_seconds: int = 600,
        dev_target: str | None = None,
        episode_label: str | None = None,
    ) -> None:
        self._runtime_id = runtime_id
        self._repo_root = Path(repo_root)
        self._agent_name = agent_name
        self._environment = environment
        self._idle_timeout = idle_timeout_seconds
        self._dev_target = dev_target
        # Becomes the task's title at episode end. The dashboard's conversation list shows the
        # task's title as the conversation's summary line, so this is what a row reads as.
        self._episode_label = episode_label

        self._task_id: str | None = None
        self._run_id: str | None = None
        # Set once the in-flight turn's run id is known. The reader thread needs it to recover
        # an overlapped attach that lost its race with `tasks prompt` — see _on_stream_end.
        self._run_id_known = threading.Event()
        self._session: _StreamSession | None = None
        self._session_lock = threading.Lock()
        self._turns: queue.SimpleQueue[TurnItem] = queue.SimpleQueue()
        # Set while no run is in flight. τ hands the floor to its user simulator as soon as it has
        # an assistant message, but the platform run can still be streaming — and prompting a task
        # mid-run is refused with 409 `Task is already processing`, which τ records as an
        # infrastructure error and retries the episode over. The local transport gates the same
        # way, on Pi's `agent_settled`.
        self._settled = threading.Event()
        self._settled.set()
        self._closed = False

    # ------------------------------------------------------------------ lifecycle

    def start(self, env: Mapping[str, str]) -> None:
        """Note that the episode may begin. `env` is the bridge binding, unused in this lane.

        No task is created here, deliberately. A task created empty and prompted afterwards races
        its own sandbox: the prompt lands before the sandbox is warm, comes back as
        `RUN_ERROR: Task sandbox is not ready`, and τ discards the whole episode as an
        infrastructure error and starts over — measured at 3 retries in 4 attempts. Creating the
        task *with* τ's first user turn as `--prompt` is the platform's own documented path, and
        it does not race, so creation waits for that turn.

        The sandbox never reads our environment: it reaches the bridge through the
        `introspection dev` attachment, which was handed the URL when it started.
        """
        del env

    def close(self) -> None:
        """Stop streaming, then retitle and archive the task — never delete it.

        The first design deleted the task here, and that was verified evidence-safe for the
        *export*: the task 404s while its conversation still returns full spans, cost and
        usage. What deletion does destroy is presentation — the dashboard's conversation list
        shows the task's `title` as the conversation's summary line, so a deleted task demotes
        its conversation to a bare id in the UI. The task row is cheap and joins the
        conversation to a readable name; keep it.

        Archiving hides the finished row from the default `tasks list` (a 97-episode sweep
        would otherwise bury it), and it also settles the task: an archived episode came back
        `status: cancelled` with `completed_at` stamped at archive time rather than after the
        idle timeout, so the sandbox is released immediately and nothing trails against the
        organization's concurrency limit. The inactivity timeout remains as the backstop for
        an episode that crashes before reaching this method.

        Both calls are best effort and independent: a failure here must not mask the episode's
        outcome, and a task that cannot be archived still completes on its own.
        """
        if self._closed:
            return
        self._closed = True
        self._stop_stream()
        if self._task_id is None:
            return
        if self._episode_label:
            try:
                self._cli(
                    ["tasks", "update", self._task_id, "--title", self._episode_label],
                    timeout=60,
                )
            except (RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
                logger.debug(f"could not retitle task {self._task_id}: {exc}")
        try:
            self._cli(["tasks", "archive", self._task_id, "-y"], timeout=120)
        except (RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            logger.debug(f"could not archive task {self._task_id}: {exc}")

    @property
    def session_ref(self) -> str | None:
        """The task id, which is also the conversation id — the anchor for platform evidence."""
        return self._task_id

    @property
    def stderr_tail(self) -> str:
        return ""

    # ------------------------------------------------------------------- driving

    def send_user_text(self, text: str) -> None:
        if not self._settled.wait(timeout=SETTLE_GRACE_SECONDS):
            logger.warning(
                f"run {self._run_id} had not settled after {SETTLE_GRACE_SECONDS:.0f}s; "
                "prompting anyway, which the platform may refuse as already-processing"
            )
        self._settled.clear()
        self._stop_stream()
        if self._task_id is None:
            # The first turn cannot overlap: the stream needs a task id, which creation returns.
            created = self._cli(
                [
                    "tasks",
                    "create",
                    "--runtime-id",
                    self._runtime_id,
                    "--environment",
                    self._environment,
                    "--agent",
                    self._agent_name,
                    "--idle-timeout",
                    str(int(self._idle_timeout)),
                    "--prompt",
                    text,
                ],
                timeout=300,
            )
            self._task_id = str(created["task"]["id"])
            self._set_run_id(self._run_id_of(created))
            logger.info(
                f"platform task {self._task_id} on runtime {self._runtime_id} "
                f"(conversation id is the same value)"
            )
            self._spawn_stream(
                run_ref=self._run_id or "current", drop_run_id=None, reattaches_left=1
            )
        else:
            # Overlap the stream attach with the prompt, so their CLI startups run concurrently
            # instead of serially — see the module docstring for why serial startup was eating
            # the sandbox's per-call MCP budget. `current` may resolve before the new run
            # exists; the previous run's replay is filtered by run id, and a fully lost race is
            # recovered by one reattach under the explicit id once `tasks prompt` returns it.
            prior_run = self._run_id
            self._clear_run_id()
            self._spawn_stream(run_ref="current", drop_run_id=prior_run, reattaches_left=1)
            try:
                started = self._cli(
                    ["tasks", "prompt", self._task_id, "--prompt", text], timeout=300
                )
            except Exception:
                # No run started, so nothing will ever settle: reap the orphaned stream and
                # reopen the gate before surfacing the real failure.
                self._stop_stream()
                self._settled.set()
                raise
            self._set_run_id(self._run_id_of(started))

    def next_turn(self, timeout: float) -> TurnItem:
        try:
            return self._turns.get(timeout=timeout)
        except queue.Empty:
            return TransportFailure(
                reason=(
                    f"no assistant turn from task {self._task_id} within {timeout:.0f}s "
                    f"(run {self._run_id})"
                )
            )

    def request_session_ref(self) -> None:
        """No-op: the task id is known at creation, unlike Pi's session id."""

    # ------------------------------------------------------------------ internals

    def _cli(self, args: list[str], timeout: float) -> dict:
        env = dict(os.environ)
        if self._dev_target:
            # Routes the task to this machine's `introspection dev` attachment.
            env["INTROSPECTION_DEV_TARGET"] = self._dev_target
        proc = subprocess.run(  # noqa: S603
            [CLI, *args, "-o", "json"],
            cwd=self._repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"`{CLI} {' '.join(args[:2])}` failed ({proc.returncode}): "
                f"{(proc.stderr or proc.stdout).strip()[:500]}"
            )
        return json.loads(proc.stdout)

    @staticmethod
    def _run_id_of(payload: dict) -> str:
        """`tasks create` nests the run; `tasks prompt` may return it either way."""
        run = payload.get("run")
        if isinstance(run, dict) and run.get("id"):
            return str(run["id"])
        if payload.get("id"):
            return str(payload["id"])
        raise RuntimeError(f"no run id in CLI response: {json.dumps(payload)[:300]}")

    def _set_run_id(self, run_id: str) -> None:
        self._run_id = run_id
        self._run_id_known.set()

    def _clear_run_id(self) -> None:
        self._run_id_known.clear()
        self._run_id = None

    def _spawn_stream(self, run_ref: str, drop_run_id: str | None, reattaches_left: int) -> None:
        proc = subprocess.Popen(  # noqa: S603
            [
                CLI,
                "tasks",
                "stream",
                str(self._task_id),
                "--run",
                run_ref,
                "--since",
                "0",
            ],
            cwd=self._repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        session = _StreamSession(
            proc=proc,
            assembler=StreamAssembler(),
            drop_run_id=drop_run_id,
            reattaches_left=reattaches_left,
        )
        session.thread = threading.Thread(target=self._read_stream, args=(session,), daemon=True)
        with self._session_lock:
            self._session = session
        session.thread.start()

    def _read_stream(self, session: _StreamSession) -> None:
        proc = session.proc
        assert proc is not None and proc.stdout is not None
        for line in proc.stdout:
            self._ingest_line(session, line)
        self._on_stream_end(session)

    def _ingest_line(self, session: _StreamSession, line: str) -> None:
        line = line.strip()
        if not line:
            return
        try:
            envelope = json.loads(line)
        except json.JSONDecodeError:
            return
        if session.drop_run_id is not None and envelope.get("run_id") == session.drop_run_id:
            # A replay of the previous, already-consumed run. See _StreamSession.
            session.dropped += 1
            return
        items = session.assembler.feed(envelope)
        if not items and not session.assembler.finished:
            return
        if not self._is_current(session):
            # Replaced or torn down mid-drain. Nothing visible may escape a superseded stream:
            # a buffered line arriving after the old run's RUN_FINISHED would otherwise re-open
            # the settle gate while the *next* run is already streaming — an early prompt the
            # platform refuses with 409, which τ books as an infrastructure error.
            return
        for item in items:
            session.emitted += 1
            self._turns.put(item)
        if session.assembler.finished:
            self._settled.set()

    def _on_stream_end(self, session: _StreamSession) -> None:
        """Decide what a stream's exit means: the run settled, a lost race, or a failure."""
        if not self._is_current(session):
            return
        if session.assembler.finished:
            self._settled.set()
            return
        if session.emitted == 0 and session.reattaches_left > 0:
            # The overlapped attach lost its race: `current` resolved before the new run
            # existed, so nothing from it was seen and an attach by explicit run id replays it
            # from event 0 with nothing double-fed. The run id arrives with `tasks prompt`'s
            # response, which shares the CLI's 300s ceiling.
            run_known = self._run_id_known.wait(timeout=SETTLE_GRACE_SECONDS)
            if run_known and self._run_id and self._is_current(session):
                logger.info(
                    f"stream attach raced run creation (dropped {session.dropped} stale "
                    f"event(s)); reattaching to run {self._run_id}"
                )
                self._spawn_stream(
                    run_ref=self._run_id,
                    drop_run_id=None,
                    reattaches_left=session.reattaches_left - 1,
                )
                return
        if not self._is_current(session):
            return
        stderr = ""
        if session.proc is not None and session.proc.stderr is not None:
            stderr = session.proc.stderr.read() or ""
        self._turns.put(
            TransportFailure(
                reason=(
                    f"event stream for run {self._run_id} ended without RUN_FINISHED. "
                    f"stderr: {stderr.strip()[:300] or '(empty)'}"
                )
            )
        )
        self._settled.set()

    def _is_current(self, session: _StreamSession) -> bool:
        with self._session_lock:
            return self._session is session and not self._closed

    def _stop_stream(self) -> None:
        with self._session_lock:
            session, self._session = self._session, None
        if session is None:
            return
        proc = session.proc
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        thread = session.thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5)
