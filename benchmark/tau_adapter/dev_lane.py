"""Own the `introspection dev` attachment for the length of a run.

`dev` is the bridge between a cloud sandbox and the τ environment on this machine: it serves the
Recipe from the git work-tree and routes the Recipe's declared `tau` MCP server to a local URL.
It is expensive to start (~15s) and there is exactly one of it, so its lifetime is the *run*,
not the episode — which is also why the tool bridge had to become run-scoped.

Two things about `--mcp` were established by experiment rather than from the documentation, and
both are load-bearing:

  * `--mcp tau=<url>` conveys the transport and nothing else. It carries no credentials, which
    is why the bridge puts its token in the URL path.
  * A *connected* MCP binding **overrides** the `--mcp` route with the binding's own URL.
    Binding URLs must be `https` or `host.docker.internal`, neither of which reaches this
    machine from a cloud sandbox, so a connected `tau` binding turns every episode into a
    5-second catalog-discovery timeout. The development lane therefore requires the `tau`
    binding to stay disconnected, and `assert_no_connected_binding` refuses to start otherwise.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import signal
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from tau_adapter.tool_bridge import ToolBridge

CLI = "introspection"
READY_MARKER = "Development ready"
DEV_TARGET_MARKER = "INTROSPECTION_DEV_TARGET="


class DevLaneError(RuntimeError):
    pass


def _cli_json(
    args: list[str],
    cwd: Path,
    timeout: float = 120,
    extra_env: dict[str, str] | None = None,
) -> object:
    proc = subprocess.run(  # noqa: S603
        [CLI, *args, "-o", "json"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, **extra_env} if extra_env else None,
        check=False,
    )
    if proc.returncode != 0:
        raise DevLaneError(
            f"`{CLI} {' '.join(args)}` failed ({proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:400]}"
        )
    return json.loads(proc.stdout)


def resolve_runtime_id(runtime_name: str, repo_root: Path) -> str:
    """Look the Runtime id up by name instead of hardcoding it.

    A Runtime id is per-project and changes when the first version is re-created, so committing
    one would be a value that silently goes stale. `TAU_RUNTIME_ID` overrides for the case where
    several versions share a name and a specific one is wanted.
    """
    override = os.environ.get("TAU_RUNTIME_ID")
    if override:
        return override

    rows = _cli_json(["runtimes", "list"], cwd=repo_root)
    if isinstance(rows, dict):
        rows = rows.get("runtimes") or rows.get("items") or []
    matches = [
        r for r in rows if isinstance(r, dict) and r.get("name") == runtime_name and r.get("id")
    ]
    if not matches:
        available = sorted({r.get("name") for r in rows if isinstance(r, dict)})
        raise DevLaneError(
            f"no Runtime named {runtime_name!r} in this project (have: {available}). "
            "Create one with `introspection runtimes create` from a clean, pushed main branch."
        )
    if len(matches) > 1:
        logger.warning(
            f"{len(matches)} Runtime versions named {runtime_name!r}; using the first. "
            "Set TAU_RUNTIME_ID to pin one."
        )
    return str(matches[0]["id"])


def assert_no_connected_binding(runtime_id: str, environment: str, repo_root: Path) -> None:
    """Refuse to run while a `tau` MCP binding is connected. See the module docstring."""
    rows = _cli_json(
        ["bindings", "mcp", "list", "--runtime-id", runtime_id, "-e", environment],
        cwd=repo_root,
    )
    if isinstance(rows, dict):
        rows = rows.get("servers") or rows.get("items") or []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("mcp_server_id") == "tau" and row.get("connected"):
            raise DevLaneError(
                "the `tau` MCP binding is connected, which overrides `--mcp` with the binding's "
                "own URL and makes every episode fail catalog discovery. Disconnect it:\n"
                f"  {CLI} bindings mcp disconnect --endpoint {row.get('endpoint_id')} -y"
            )


def warm_runtime(
    runtime_id: str,
    environment: str,
    repo_root: Path,
    dev_target: str | None = None,
    attempts: int = 3,
) -> str | None:
    """Spend one throwaway task so no graded episode pays for the cold start.

    The first task created after `dev` attaches comes back `Task sandbox is not ready` often
    enough to matter. τ absorbs it — as an infrastructure error, by discarding the episode and
    retrying — so the cost is a whole episode's tokens and wall clock, and on a sweep it is one
    episode per run. Paying it here instead costs about two cents against a prompt that needs no
    tool and no policy.

    Deliberately not a retry inside the transport: an episode that is already producing messages
    must never be silently restarted, because the adapter would then be deciding what counts as a
    run. A warm-up before the first episode decides nothing.

    Returns the warm-up task id if one completed, else None. Failure is not fatal: the worst case
    is the behaviour we have today.
    """
    for attempt in range(1, attempts + 1):
        try:
            created = _cli_json(
                [
                    "tasks",
                    "create",
                    "--runtime-id",
                    runtime_id,
                    "--environment",
                    environment,
                    "--idle-timeout",
                    "0",
                    "--prompt",
                    "Reply with the single word READY and nothing else.",
                ],
                cwd=repo_root,
                timeout=300,
                extra_env={"INTROSPECTION_DEV_TARGET": dev_target} if dev_target else None,
            )
        except DevLaneError as exc:
            logger.warning(f"warm-up attempt {attempt}/{attempts} could not create a task: {exc}")
            continue

        task_id = str((created or {}).get("task", {}).get("id"))
        settled = _stream_to_completion(task_id, repo_root, timeout=240)
        # Tear the sandbox down immediately; `--idle-timeout 0` asks for the same thing, and the
        # delete keeps the conversation while releasing the slot.
        with contextlib.suppress(DevLaneError):
            _cli_json(["tasks", "delete", task_id, "-y"], cwd=repo_root, timeout=120)
        if settled:
            logger.info(f"runtime warm after task {task_id}")
            return task_id
        logger.warning(f"warm-up attempt {attempt}/{attempts} did not settle ({task_id})")
    logger.warning("runtime never warmed; the first episode may absorb a cold start")
    return None


def _stream_to_completion(task_id: str, repo_root: Path, timeout: float) -> bool:
    """True when the run reached RUN_FINISHED, False on RUN_ERROR or a silent stream."""
    proc = subprocess.run(  # noqa: S603
        [CLI, "tasks", "stream", task_id, "--run", "current", "--since", "0"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    finished = False
    for line in proc.stdout.splitlines():
        try:
            event = (json.loads(line) or {}).get("event") or {}
        except json.JSONDecodeError:
            continue
        if event.get("type") == "RUN_FINISHED":
            finished = True
        elif event.get("type") == "RUN_ERROR":
            logger.debug(f"warm-up run error: {event.get('message')}")
            return False
    return finished


class DevAttachment:
    """`introspection dev`, held open for the run.

    `as_name` names the attachment (`dev --as`): tasks created with
    `INTROSPECTION_DEV_TARGET=<as_name>` route to this attachment and no other, fail-closed.
    Naming every attachment — including a pool of one — also keeps two concurrent runs on
    one machine from claiming each other's default (username-derived) dev target.
    """

    def __init__(
        self,
        mcp_url: str,
        repo_root: Path,
        runtime_name: str | None = None,
        as_name: str | None = None,
    ) -> None:
        self._mcp_url = mcp_url
        self._repo_root = Path(repo_root)
        self._runtime_name = runtime_name
        self._as_name = as_name
        self._proc: subprocess.Popen[str] | None = None
        self._lines: list[str] = []
        self.dev_target: str | None = None

    @property
    def alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def argv(self) -> list[str]:
        """The launch vector. Public so a run can record exactly what served its episodes."""
        argv = [CLI, "dev", "--non-interactive", "--mcp", f"tau={self._mcp_url}"]
        if self._as_name:
            argv += ["--as", self._as_name]
        if self._runtime_name:
            argv += ["--runtime", self._runtime_name]
        return argv

    def start(self, timeout: float = 180.0) -> None:
        argv = self.argv()
        # start_new_session: `dev` runs a platform binary which runs further children, so
        # teardown has to reclaim the group rather than the direct child.
        self._proc = subprocess.Popen(  # noqa: S603
            argv,
            cwd=self._repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        threading.Thread(target=self._read, daemon=True).start()

        ready = threading.Event()
        for _ in range(int(timeout * 4)):
            if self._proc.poll() is not None:
                raise DevLaneError(
                    f"`{CLI} dev` exited during startup ({self._proc.returncode}):\n{self.log[-1500:]}"
                )
            if any(READY_MARKER in line for line in self._lines):
                self.dev_target = self._resolve_dev_target()
                logger.info(f"development lane attached; dev target {self.dev_target!r}")
                return
            ready.wait(0.25)
        raise DevLaneError(f"`{CLI} dev` never reported {READY_MARKER!r}:\n{self.log[-1500:]}")

    def stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)

    @property
    def log(self) -> str:
        return "".join(self._lines)

    def _read(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        for line in self._proc.stdout:
            self._lines.append(line)

    def _parse_dev_target(self) -> str | None:
        """`dev` prints the value an app must set to route tasks to this attachment."""
        for line in self._lines:
            if DEV_TARGET_MARKER in line:
                return line.split(DEV_TARGET_MARKER, 1)[1].strip().rstrip("│").strip() or None
        return None

    def _resolve_dev_target(self) -> str | None:
        """The dev target this attachment actually serves, validated against `--as`.

        The banner is the source of truth; when a name was requested, the two must agree —
        episode routing is fail-closed on this exact string, so a mismatch would strand
        every task aimed at the requested name. Refused at startup, not discovered
        episode-by-episode.
        """
        parsed = self._parse_dev_target()
        if self._as_name is not None and parsed != self._as_name:
            self.stop()
            raise DevLaneError(
                f"`dev --as {self._as_name}` reported dev target {parsed!r}; tasks routed "
                f"to {self._as_name!r} would fail closed. Not serving episodes on a "
                "misnamed attachment."
            )
        return parsed


@dataclass
class AttachmentSlot:
    """One `dev` attachment plus the pinned bridge token whose URL it carries."""

    name: str
    channel_token: str
    attachment: DevAttachment
    dev_target: str | None = None
    #: Guarded by the pool's lock. True while exactly one episode owns this slot.
    leased: bool = False


class AttachmentPool:
    """N named `dev` attachments, leased to episodes one at a time.

    τ's worker pool never tells the agent factory which worker it is, so the episode ↔
    attachment binding happens here: an episode leases a slot for its lifetime and its
    transport releases it at close. A slot queued twice would mean two episodes sharing one
    attachment — and therefore one rendezvous channel, the exact crossing the channels
    forbid — so release is state-guarded and can never re-queue a slot that is not leased.
    A slot whose attachment died is refused loudly at lease and retired rather than
    recycled: τ books the episode as an infrastructure error and the incident stays
    visible, instead of every later episode on that slot hanging quietly.
    """

    def __init__(self, slots: list[AttachmentSlot]) -> None:
        if not slots:
            raise ValueError("an attachment pool needs at least one slot")
        self._slots = list(slots)
        self._lock = threading.Lock()
        self._available = threading.Condition(self._lock)
        self._free: deque[AttachmentSlot] = deque(self._slots)

    @property
    def slots(self) -> list[AttachmentSlot]:
        return list(self._slots)

    def lease(self, timeout: float = 60.0) -> AttachmentSlot:
        deadline = time.monotonic() + timeout
        with self._available:
            while not self._free:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not self._available.wait(timeout=remaining):
                    states = ", ".join(
                        f"{s.name}={'leased' if s.leased else 'retired'}" for s in self._slots
                    )
                    raise DevLaneError(
                        f"no attachment slot became free within {timeout:.0f}s ({states}). "
                        "Either every worker is mid-episode far longer than expected, or "
                        "slots were retired after their attachments died."
                    )
            slot = self._free.popleft()
            slot.leased = True
        if not slot.attachment.alive:
            # Retired: `leased` stays True so the slot can never re-enter the free queue.
            raise DevLaneError(
                f"attachment {slot.name} has exited; refusing to serve an episode on a dead "
                "attachment. τ will book this episode as an infrastructure error."
            )
        return slot

    def release(self, slot: AttachmentSlot) -> None:
        with self._available:
            if not slot.leased:
                return  # double release must never re-queue a slot
            slot.leased = False
            self._free.append(slot)
            self._available.notify()

    def stop(self) -> None:
        for slot in self._slots:
            slot.attachment.stop()


def start_attachment_pool(
    *,
    bridge: ToolBridge,
    size: int,
    repo_root: Path,
    runtime_name: str | None = None,
) -> AttachmentPool:
    """Start `size` named attachments concurrently, one pinned bridge slot each.

    Slot 0 rides the bridge's own run token, so a pool of one serves episodes at exactly
    the URL a single attachment always got. Names carry a per-run nonce so two concurrent
    runs on one machine cannot claim each other's dev target. Any startup failure stops
    every attachment that did start — a partial pool would serve some episodes and strand
    others, which is worse than failing the run before money is spent.
    """
    nonce = secrets.token_hex(2)
    slots: list[AttachmentSlot] = []
    for index in range(size):
        token = bridge.token if index == 0 else bridge.mint_pinned_token()
        name = f"tau-w{index:02d}-{nonce}"
        slots.append(
            AttachmentSlot(
                name=name,
                channel_token=token,
                attachment=DevAttachment(
                    mcp_url=bridge.url_for(token),
                    repo_root=repo_root,
                    runtime_name=runtime_name,
                    as_name=name,
                ),
            )
        )

    failures: list[str] = []

    def _start(slot: AttachmentSlot) -> None:
        try:
            slot.attachment.start()
            slot.dev_target = slot.attachment.dev_target
        except Exception as exc:  # noqa: BLE001 - collected and re-raised jointly below
            failures.append(f"{slot.name}: {exc}")

    threads = [threading.Thread(target=_start, args=(slot,), daemon=True) for slot in slots]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if failures:
        for slot in slots:
            with contextlib.suppress(Exception):
                slot.attachment.stop()
        raise DevLaneError(
            "attachment pool startup failed; every attachment was stopped:\n  "
            + "\n  ".join(failures)
        )
    return AttachmentPool(slots)
