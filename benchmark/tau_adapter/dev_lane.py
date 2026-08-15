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

import atexit
import contextlib
import json
import os
import secrets
import signal
import subprocess
import threading
import time
from pathlib import Path

from loguru import logger

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
    Naming the attachment also keeps two concurrent runs on one machine from claiming each
    other's default (username-derived) dev target.
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
        # The attachment holds the Runtime's single dev slot (dev_slot_conflict), and its
        # own session means it survives this process unless someone reclaims it — a caller
        # that crashes between here and its finally would block the next run's attach for
        # minutes. Reclamation therefore cannot depend on the caller: register the backstop
        # the moment the child exists. stop() is idempotent, so the normal-path stop and
        # this exit-time one never conflict.
        atexit.register(self.stop)
        threading.Thread(target=self._read, daemon=True).start()

        for _ in range(int(timeout * 4)):
            if self._proc.poll() is not None:
                raise DevLaneError(
                    f"`{CLI} dev` exited during startup ({self._proc.returncode}):\n{self.log[-1500:]}"
                )
            if any(READY_MARKER in line for line in self._lines):
                self.dev_target = self._resolve_dev_target()
                logger.info(f"development lane attached; dev target {self.dev_target!r}")
                return
            time.sleep(0.25)
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


def attachment_name() -> str:
    """A nonce'd dev-target name for this run's attachment.

    Two concurrent runs on one machine must not claim each other's dev target — the
    platform's default (username, then machine id) would collide; a per-run nonce cannot.
    """
    return f"tau-{secrets.token_hex(2)}"
