"""Drive a Recipe locally in Pi's RPC mode.

The cheap lane: no login, no runtime, no cloud. It produces no Introspection task and
therefore no conversation — Pi's own session file is the only record. Use it for bring-up
and as a fast regression gate; use the development-lane transport when platform evidence is
the point.

Two launchers reach the same Pi RPC protocol:

  pi             `pi --recipe <dir> --agent <a> --mode rpc …`
                 The default. One process, median 1.8s to first event.
  introspection  `introspection local --work-dir <ws> --agent <a> -- --mode rpc …`
                 The sanctioned interface: resolves the Recipe through the `.introspection/`
                 Runtime manifest — the same resolution the development lane uses — and
                 validates it before launch. Median 7.3s to first event, so it costs about
                 5.5s per episode, or ~9 minutes on a 97-task sweep.

`pi` is the default because that 5.5s buys a guarantee the repository already has elsewhere:
the Recipe is validated by `make check` in `.githooks/pre-commit` and in CI, an agent-authored
change reaches the Recipe only through a pull request that runs it, and the runner re-validates
once per run. Paying for the same check on every episode is the wrong place to spend it.

`introspection local` passes everything after `--` to Pi unchanged and keeps its own banner
on stderr, so stdout stays the pure JSONL stream the reader below depends on. Verified
equivalent: `get_state` under both launchers agrees on model, provider, base URL and
thinking level, differing only in the session id.
"""

from __future__ import annotations

import contextlib
import json
import os
import queue
import signal
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

LAUNCHER_CLI = "introspection"
LAUNCHER_PI = "pi"
LAUNCHERS = (LAUNCHER_CLI, LAUNCHER_PI)

# Pi's RPC framing is strict JSONL with LF as the only record delimiter.
_LF = b"\n"

# How long to let a settled-agent check wait before sending a user turn anyway. τ hands the
# turn to its user simulator (an LLM call) between assistant messages, so in practice Pi has
# long since settled; this only guards a pathological overlap.
_SETTLE_GRACE_SECONDS = 30.0


class LocalPiTransport:
    """One Pi subprocess per episode."""

    def __init__(
        self,
        recipe_dir: Path,
        agent_name: str = "agent",
        session_dir: Path | None = None,
        launcher: str = LAUNCHER_PI,
        workspace_dir: Path | None = None,
    ) -> None:
        if launcher not in LAUNCHERS:
            raise ValueError(f"launcher must be one of {LAUNCHERS}, got {launcher!r}")
        self._recipe_dir = Path(recipe_dir).resolve()
        self._agent_name = agent_name
        self._session_dir = Path(session_dir).resolve() if session_dir else None
        self._launcher = launcher
        # The CLI discovers the Runtime manifest by walking up from here, so it must be the
        # directory holding `.introspection/` — the repo root, or the materialised workspace a
        # diagnostic run builds. Defaults to the Recipe's parent, which is that layout.
        self._workspace_dir = (
            Path(workspace_dir).resolve() if workspace_dir else self._recipe_dir.parent
        )

        self._proc: subprocess.Popen[bytes] | None = None
        self._turns: queue.SimpleQueue[TurnItem] = queue.SimpleQueue()
        self._settled = threading.Event()
        self._reader: threading.Thread | None = None
        self._stderr_reader: threading.Thread | None = None
        self._stderr_tail: list[str] = []
        self._session_ref: str | None = None
        self._closed = False

    # ------------------------------------------------------------------ lifecycle

    def argv(self) -> list[str]:
        """The launch vector. Public so a run can record exactly what produced its episodes."""
        pi_args = ["--mode", "rpc"]
        if self._session_dir is not None:
            pi_args += ["--session-dir", str(self._session_dir)]
        else:
            pi_args += ["--no-session"]

        if self._launcher == LAUNCHER_CLI:
            return [
                LAUNCHER_CLI,
                "local",
                "--work-dir",
                str(self._workspace_dir),
                "--agent",
                self._agent_name,
                "--",
                *pi_args,
            ]
        return [
            LAUNCHER_PI,
            "--recipe",
            str(self._recipe_dir),
            "--agent",
            self._agent_name,
            *pi_args,
        ]

    def start(self, env: Mapping[str, str]) -> None:
        if self._session_dir is not None:
            self._session_dir.mkdir(parents=True, exist_ok=True)

        # S603 is suppressed because argv is a fixed vector: an executable name plus paths
        # resolved from the lock and the recipe. No shell, and no caller-supplied string.
        #
        # start_new_session puts the launch in its own process group. Under the CLI launcher Pi
        # is a grandchild (node → platform binary → pi), so killing the direct child alone
        # leaves the rest reparented to init, holding our stdout pipe open — a hang at teardown
        # rather than a clean episode end. Verified: killpg reclaims the whole tree.
        self._proc = subprocess.Popen(  # noqa: S603
            self.argv(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(env),
            cwd=str(self._workspace_dir),
            bufsize=0,
            start_new_session=True,
        )
        self._settled.set()
        self._reader = threading.Thread(target=self._read_events, daemon=True)
        self._reader.start()
        self._stderr_reader = threading.Thread(target=self._read_stderr, daemon=True)
        self._stderr_reader.start()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        proc = self._proc
        if proc is None:
            return
        try:
            if proc.poll() is None:
                self._write({"type": "abort"})
                proc.stdin.close()  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001 - teardown must not mask the real failure
            logger.debug(f"transport close: abort not delivered ({exc})")
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._kill_group(proc)

    @staticmethod
    def _kill_group(proc: subprocess.Popen[bytes]) -> None:
        """SIGKILL the whole process group, then the direct child as a fallback."""
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError) as exc:
            logger.debug(f"transport close: process group already gone ({exc})")
            proc.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)

    @property
    def session_ref(self) -> str | None:
        return self._session_ref

    @property
    def stderr_tail(self) -> str:
        return "".join(self._stderr_tail[-40:])

    # ------------------------------------------------------------------- driving

    def send_user_text(self, text: str) -> None:
        # A `prompt` sent while the agent is still streaming is rejected unless it declares a
        # steering behaviour, and steering would change turn semantics. Wait instead.
        self._settled.wait(timeout=_SETTLE_GRACE_SECONDS)
        self._settled.clear()
        self._write({"type": "prompt", "message": text})

    def next_turn(self, timeout: float) -> TurnItem:
        try:
            return self._turns.get(timeout=timeout)
        except queue.Empty:
            return TransportFailure(
                reason=(
                    f"no assistant turn from Pi within {timeout:.0f}s. "
                    f"stderr tail: {self.stderr_tail[-500:] or '(empty)'}"
                )
            )

    # ------------------------------------------------------------------ internals

    def _write(self, command: dict[str, Any]) -> None:
        proc = self._proc
        if proc is None or proc.stdin is None:
            raise RuntimeError("transport not started")
        proc.stdin.write(json.dumps(command).encode("utf-8") + _LF)
        proc.stdin.flush()

    def _read_stderr(self) -> None:
        proc = self._proc
        if proc is None or proc.stderr is None:
            return
        for raw in iter(proc.stderr.readline, b""):
            self._stderr_tail.append(raw.decode("utf-8", "replace"))

    def _read_events(self) -> None:
        """Split stdout on LF only, per Pi's documented framing."""
        proc = self._proc
        assert proc is not None and proc.stdout is not None
        buffer = b""
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            buffer += chunk
            while _LF in buffer:
                line, buffer = buffer.split(_LF, 1)
                if line.endswith(b"\r"):
                    line = line[:-1]
                if line.strip():
                    self._handle_line(line)
        # Pi exited. Unblock anyone waiting, so a crash surfaces as a failure rather than a
        # timeout that looks like a slow model.
        self._settled.set()
        code = proc.poll()
        self._turns.put(
            TransportFailure(
                reason=f"Pi exited (code {code}). stderr tail: {self.stderr_tail[-500:] or '(empty)'}"
            )
        )

    def _handle_line(self, line: bytes) -> None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return
        kind = event.get("type")

        if kind == "agent_start":
            self._settled.clear()
        elif kind == "agent_settled":
            self._settled.set()
        elif kind == "message_end":
            message = event.get("message") or {}
            if message.get("role") == "assistant":
                self._turns.put(_assistant_turn(message))
        elif kind == "response" and event.get("command") == "get_state":
            data = event.get("data") or {}
            self._session_ref = data.get("sessionId") or data.get("sessionFile")
        elif kind == "extension_ui_request":
            self._answer_ui_request(event)

    def _answer_ui_request(self, event: dict[str, Any]) -> None:
        """Cancel any blocking dialog.

        `notify` and friends are fire-and-forget, but `select`/`confirm`/`input`/`editor`
        block the agent until answered. Nothing in this Recipe should raise one; cancelling
        unconditionally means a surprise cannot deadlock an episode.
        """
        if event.get("method") not in ("select", "confirm", "input", "editor"):
            return
        try:
            self._write(
                {
                    "type": "extension_ui_response",
                    "id": event.get("id"),
                    "cancelled": True,
                }
            )
        except Exception as exc:  # noqa: BLE001 - a cancel we cannot send is not fatal
            logger.debug(f"transport: could not cancel extension dialog ({exc})")

    def request_session_ref(self) -> None:
        """Ask Pi for its session identity; answered asynchronously into `session_ref`."""
        try:
            self._write({"type": "get_state"})
        except Exception as exc:  # noqa: BLE001 - session_ref is evidence metadata, not control
            logger.debug(f"transport: could not request session state ({exc})")


def _assistant_turn(message: dict[str, Any]) -> TurnItem:
    """Translate one Pi assistant message into a transport turn, losing nothing graded."""
    stop_reason = message.get("stopReason")
    if stop_reason == "error":
        return TransportFailure(
            reason=f"Pi assistant message errored: {message.get('errorMessage') or 'unknown'}"
        )

    texts: list[str] = []
    calls: list[PiToolCall] = []
    for block in message.get("content") or []:
        block_type = block.get("type")
        if block_type == "text":
            texts.append(block.get("text") or "")
        elif block_type == "toolCall":
            calls.append(
                PiToolCall(
                    id=str(block.get("id") or ""),
                    pi_name=str(block.get("name") or ""),
                    arguments=block.get("arguments") or {},
                )
            )
        # `thinking` is intentionally dropped: τ has nowhere to put it.

    text = "".join(texts).strip() or None
    usage = message.get("usage") or None
    cost = None
    if isinstance(usage, dict):
        cost_block = usage.get("cost")
        if isinstance(cost_block, dict):
            cost = cost_block.get("total")

    return AssistantTurn(
        text=text,
        tool_calls=tuple(calls),
        model=message.get("model"),
        usage=usage if isinstance(usage, dict) else None,
        cost=cost,
    )
