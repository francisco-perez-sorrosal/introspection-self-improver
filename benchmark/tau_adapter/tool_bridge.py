"""Serve τ's tool surface to Pi over MCP, and rendezvous on the results.

τ and Pi have opposite control flow. τ's orchestrator executes the agent's tool calls itself
and hands back a `ToolMessage`; a Pi agent executes its own tools and returns text. This
bridge reconciles them without either side giving up authority:

    Pi calls an MCP tool
      → the handler parks, and the call surfaces to τ as an ordinary tool_calls message
      → τ's orchestrator executes it against the environment  (τ stays authoritative)
      → the resulting ToolMessage is posted here
      → the parked handler returns it as the MCP tool's value, and Pi continues

Nothing about the trajectory is reconstructed: τ builds it, counts the steps, and grades it.
The bridge never touches the environment, so it cannot become a second implementation of the
benchmark's semantics.

Episodes rendezvous on **channels**. One bridge serves the whole run, but every episode
opens its own `EpisodeChannel` — its own mailbox — so a result posted for one episode
cannot answer another's call even when both name the same tool with identical arguments.
τ runs its episodes from a worker pool (`max_concurrency`); the channel registry is what
makes N in-flight episodes safe, and one at a time is the degenerate case of the same
mechanism. What differs per lane is only how a request finds its channel:

  * Local lane: episode identity is the URL. Each Pi subprocess is handed its channel's
    `/mcp/<token>` path through its environment, and the path routes the call.
  * Development lane: every sandbox reaches the bridge through the single URL its `dev`
    attachment was handed, but the tunnel stamps each forwarded request with the
    sandbox's session (`x-introspection-session-id` — observed 2026-08-13, matching the
    task's `metadata.agent_session_id` from `tasks get`). The transport binds its
    episode's channel to that session id, and the header routes the call. N concurrent
    tasks therefore share one attachment without sharing any rendezvous state.
"""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import functools
import hashlib
import json
import os
import queue
import secrets
import socket
import sys
import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import mcp.types as mcp_types
import uvicorn
from loguru import logger
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server as LowLevelServer

from tau_adapter.names import build_name_map

DEFAULT_SERVER_ID = "tau"

# Ceiling on how long a parked handler waits for τ to execute its call. τ tool execution is
# local and fast; this exists so a seam bug fails loudly instead of hanging an episode. It is
# harness plumbing, unrelated to τ's own --max-steps-seconds budget.
RESULT_WAIT_SECONDS = 300.0

# How long a wait may run before it is reported as a stall, rather than only at the ceiling.
#
# This exists because of an asymmetry that hides real failures. In the development lane the
# sandbox's own MCP daemon abandons a call after about 30s, so if τ has not posted by then the
# agent sees a tool error and carries on — while this handler is still waiting, quietly, for
# another four and a half minutes. The episode can then be graded 1.0 on the answers that did
# work, with a broken rendezvous recorded nowhere. Observed once, intermittently: a `tools/call`
# span of 30090ms against `mcp upstream timed out`. Warning at the shorter horizon means the
# next occurrence names itself.
STALL_WARN_SECONDS = 25.0

# How long a call from a not-yet-bound sandbox session may wait for its binding. The
# transport learns its task's session id by polling `tasks get` after creation; the
# sandbox's first tool call can only arrive after the sandbox booted and the agent
# processed its first turn, so in practice the binding wins this race by many seconds —
# the grace exists so the loser of a pathological race parks briefly instead of failing
# the call.
UNBOUND_SESSION_GRACE_SECONDS = 30.0

# How many worker threads the bridge's OWN executor gets per concurrent episode.
#
# Every `tools/call` parks TWO threads in sequence — `channel_for_request` (up to
# UNBOUND_SESSION_GRACE_SECONDS) and then `channel.wait` (up to RESULT_WAIT_SECONDS) — and
# the bridge is run-scoped, so every concurrent episode draws from the same pool. Two per
# episode is the worst case; four is that with headroom for the overlap while one call
# resolves its channel and another is still parked.
#
# This exists because the pool was previously asyncio's DEFAULT executor, sized
# `min(32, os.cpu_count() + 4)` — 16 on a 12-core machine. That is an accident of the host,
# not a designed capacity, and at 2 threads per episode it silently capped the seam at ~8
# concurrent episodes: past that, new MCP calls queued behind parked ones and surfaced as
# rendezvous stalls indistinguishable from a hung agent. Observed 2026-08-15 at
# --max-concurrency 8 (one 300s stall on a 24-episode batch round). Sizing the pool
# explicitly puts the ceiling back where it belongs — on max_concurrency, provider rate
# limits and sandbox provisioning — instead of on the CPU count of whoever runs it.
BRIDGE_THREADS_PER_EPISODE = 4

# Floor for that pool. A serial run still wants room for a retry's late call arriving while
# the replacement episode is already talking.
MIN_BRIDGE_WORKERS = 32

#: Refused-call counter keys. A refusal means a request resolved to no live channel, so
#: there is no episode to attribute it to — the counters are run-level, and the runner
#: folds them into the round's incident totals. Split by cause because they read
#: differently: a session the transport never bound is the platform lane's starvation
#: mode (the episode fails every call while the seam would otherwise look healthy); a
#: stale or unknown endpoint token is a late call after its episode ended.
REFUSAL_UNBOUND_SESSION = "tool_refusals_unbound_session"
REFUSAL_STALE_ENDPOINT = "tool_refusals_stale_endpoint"

#: Set TAU_ADAPTER_TRACE=1 to print every rendezvous pairing to stderr. The rendezvous is the
#: highest-risk part of the seam and its failure mode is a hang, which leaves no evidence
#: behind; a mismatched await/post pair is obvious in this trace and invisible without it.
TRACE = bool(os.environ.get("TAU_ADAPTER_TRACE"))

#: Set TAU_BRIDGE_TRACE_HEADERS=1 to log every inbound MCP request's HTTP headers. This is
#: how transport-level identity questions get answered from evidence instead of assumption —
#: e.g. whether the development lane's tunnel stamps forwarded requests with the task they
#: belong to. Loopback-only traffic whose credentials are this run's own; still off by
#: default because headers are noise on every healthy run.
TRACE_HEADERS = bool(os.environ.get("TAU_BRIDGE_TRACE_HEADERS"))


def _trace(message: str) -> None:
    logger.debug(message)
    if TRACE:
        print(f"[bridge] {message}", file=sys.stderr, flush=True)


class ToolResultTimeout(RuntimeError):
    pass


@dataclass(frozen=True)
class _Key:
    """Identifies one tool invocation within a turn.

    Keyed on τ's own tool name, which is what a `tools/call` carries. Recipes' `mcp_<server>_
    <tool>_<hash>` rewrite is client-side presentation only: the model sees the mangled name,
    but the MCP request that reaches this server names the tool the server advertised. Keying
    on the mangled name is what deadlocked the first working version of the rendezvous.
    """

    tool_name: str
    arguments: str

    @staticmethod
    def of(tool_name: str, arguments: dict | None) -> _Key:
        return _Key(
            tool_name=tool_name,
            arguments=json.dumps(
                arguments or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ),
        )


class _Mailbox:
    """Per-invocation result slots.

    Keyed by name plus canonicalised arguments rather than by position, so a turn carrying
    several tool calls pairs correctly no matter what order the host executes them in.
    Repeated identical calls queue behind each other.

    `on_stall` fires once per wait that crosses STALL_WARN_SECONDS, so a rendezvous
    regression lands in the episode's incident counters instead of only in a log line.
    """

    def __init__(self, on_stall: Callable[[], None] | None = None) -> None:
        self._lock = threading.Lock()
        self._slots: dict[_Key, queue.SimpleQueue[tuple[str, bool]]] = {}
        self._on_stall = on_stall
        self.posted: list[_Key] = []
        self.awaited: list[_Key] = []

    def _slot(self, key: _Key) -> queue.SimpleQueue[tuple[str, bool]]:
        with self._lock:
            return self._slots.setdefault(key, queue.SimpleQueue())

    def post(self, key: _Key, content: str, is_error: bool) -> None:
        with self._lock:
            self.posted.append(key)
        _trace(f"post   {key.tool_name} args={key.arguments}")
        self._slot(key).put((content, is_error))

    def wait(self, key: _Key, timeout: float) -> tuple[str, bool]:
        with self._lock:
            self.awaited.append(key)
        _trace(f"await  {key.tool_name} args={key.arguments}")
        slot = self._slot(key)
        # Two-stage wait: report the stall at the horizon where the caller has probably already
        # given up, then keep waiting to the ceiling in case the result is merely slow.
        with contextlib.suppress(queue.Empty):
            return slot.get(timeout=min(STALL_WARN_SECONDS, timeout))
        if self._on_stall is not None:
            self._on_stall()
        logger.warning(
            f"rendezvous stalled: no result for {key.tool_name} after "
            f"{STALL_WARN_SECONDS:.0f}s. The caller's MCP daemon has likely abandoned this call "
            f"already, so the agent will see a tool error even if the result arrives.\n"
            f"  awaited: {key.arguments[:200]}\n"
            f"  posted so far: {[(k.tool_name, k.arguments[:60]) for k in self.posted][-5:]}"
        )
        try:
            return slot.get(timeout=max(timeout - STALL_WARN_SECONDS, 0.0))
        except queue.Empty as exc:
            raise ToolResultTimeout(
                f"no result for {key.tool_name} within {timeout:.0f}s.\n"
                f"  awaited: {key.arguments[:200]}\n"
                f"  posted keys this episode: "
                f"{[(k.tool_name, k.arguments[:80]) for k in self.posted][-5:]}"
            ) from exc


class EpisodeChannel:
    """One episode's rendezvous surface: its own mailbox, reachable by token or binding.

    A parked handler can only ever be answered by a result posted to the same episode's
    channel — the keyspace two concurrent episodes could collide in no longer exists.
    Local episodes are routed by the channel's URL token; a development-lane episode is
    additionally `bind()`-ed to its sandbox's session id once the transport learns it.
    `on_stall` is bound at open, which is what attributes a stalled rendezvous to the one
    episode (and manifest row) it belongs to.
    """

    def __init__(self, bridge: ToolBridge, token: str, on_stall: Callable[[], None] | None) -> None:
        self._bridge = bridge
        self.token = token
        #: Calls that resolved to this channel, incremented on arrival. Zero after the
        #: episode has been running for a while is the signature of a dead tunnel — the
        #: sandbox daemon answering calls itself, invisible to every bridge-side counter —
        #: so the transport reads this to tell "agent thinking" apart from "agent unreachable".
        self.calls_received = 0
        #: The sandbox session this channel answers for, once bound; see `bind`.
        self.bound_key: str | None = None
        #: Set at close, under the bridge lock. A closed channel refuses new bindings —
        #: the transport's binding poll can race the episode's teardown, and a late bind
        #: would re-register a dead channel in the routing table.
        self.closed = False
        self._mailbox = _Mailbox(on_stall=on_stall)

    def bind(self, key: str) -> None:
        """Also answer for `key` — the episode's sandbox session id on the platform lane.

        Raises rather than stealing if another live channel already answers for it: session
        ids are unique per task attempt, so a collision is a wiring bug, and silently
        re-binding would hand one episode's calls to another.
        """
        self._bridge._bind(self, key)

    @property
    def url(self) -> str:
        return self._bridge.url_for(self.token)

    @property
    def name_map(self) -> dict[str, str]:
        """pi name -> τ name; the tool surface is bridge-level and frozen for the run."""
        return self._bridge.name_map

    @property
    def tau_tool_names(self) -> list[str]:
        return self._bridge.tau_tool_names

    def env(self) -> dict[str, str]:
        """What binds this episode's host to the Recipe's declared `tau` server.

        One variable, because the URL carries both endpoint and credential in its path.
        See `ToolBridge.path`.
        """
        return {f"{self._bridge.server_id.upper()}_MCP_URL": self.url}

    def post_result(
        self, tool_name: str, arguments: dict | None, content: str, is_error: bool
    ) -> None:
        """Hand τ's ToolMessage to whichever parked handler on this episode asked for it.

        `tool_name` is τ's name, matching what the MCP request carried — not the mangled
        name the model saw.
        """
        self._mailbox.post(_Key.of(tool_name, arguments), content, is_error)

    def wait(self, tool_name: str, arguments: dict | None, timeout: float) -> tuple[str, bool]:
        """Park until τ posts this invocation's result. The server's call handler ends here."""
        return self._mailbox.wait(_Key.of(tool_name, arguments), timeout)

    def close(self) -> None:
        """Retire the channel: later calls to its URL are refused rather than parked.

        Any handler still parked on this mailbox times out on its own ceiling; nothing can
        legitimately outlive its episode.
        """
        self._bridge._release(self)


class ToolBridge:
    """An MCP server over a fixed τ tool set, listening on an ephemeral loopback port."""

    def __init__(
        self,
        tau_tools: Iterable[Any],
        server_id: str = DEFAULT_SERVER_ID,
        token: str | None = None,
        port: int = 0,
        max_concurrency: int = 1,
    ) -> None:
        self._tau_tools = list(tau_tools)
        # Sizes the bridge's own thread pool (see BRIDGE_THREADS_PER_EPISODE). Passed by the
        # runner from the round's effective concurrency so the seam is never the binding
        # constraint. Since the post-seq-5 fix-forward, `start()` creates this pool and the
        # two parking hops in `_on_call_tool` draw from it explicitly — no event-loop
        # surgery involved, so uvicorn's own run path stays untouched.
        self.executor_workers = max(
            MIN_BRIDGE_WORKERS, BRIDGE_THREADS_PER_EPISODE * max(1, int(max_concurrency))
        )
        self._executor: ThreadPoolExecutor | None = None
        # Per-call observations, appended by `_on_call_tool` and drained by the runner into
        # `bridge_calls.jsonl` at round end. Observation only — nothing in the call path
        # reads it — so the seam's semantics cannot depend on it. It exists because the
        # bridge is the only vantage that sees every call's arrival, park duration and
        # outcome, which is what a latency diagnosis or a cross-talk audit needs.
        self._call_log: list[dict[str, Any]] = []
        self._call_log_lock = threading.Lock()
        self.server_id = server_id
        self.token = token or secrets.token_urlsafe(24)
        # 0 asks the OS for an ephemeral port, which is right for the local lane: the URL reaches
        # the Pi subprocess through its environment, so nothing has to predict it. Pinning matters
        # only when `introspection dev --mcp tau=<url>` is started by hand, before the run.
        self.requested_port = port
        self.tau_tool_names = [t.name for t in self._tau_tools]
        # pi name -> τ name. Built forwards; raises on a collision.
        self.name_map = build_name_map(server_id, self.tau_tool_names)
        self._mcp_tools = [_as_mcp_tool(t, server_id) for t in self._tau_tools]
        # key -> live channel, where a key is a channel's URL token or a bound sandbox
        # session id (UUIDs and minted tokens cannot collide). Guarded: τ's workers open,
        # bind and close channels concurrently while the server's event loop resolves
        # inbound calls against the same registry; the condition lets an unbound session's
        # call wait for its binding instead of failing the race.
        self._channels: dict[str, EpisodeChannel] = {}
        self._channels_lock = threading.Lock()
        self._channel_bound = threading.Condition(self._channels_lock)
        # Refused calls by cause (see the REFUSAL_* keys). Guarded by the channels lock:
        # increments come from the server's event loop, the runner reads the totals after
        # the run.
        self._refusals: dict[str, int] = dict.fromkeys(
            (REFUSAL_UNBOUND_SESSION, REFUSAL_STALE_ENDPOINT), 0
        )

        self._socket: socket.socket | None = None
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self._port: int | None = None

    # ------------------------------------------------------------------ lifecycle

    def start(self) -> str:
        """Bind, serve in a background thread, and return the MCP endpoint URL."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", self.requested_port))
        self._port = self._socket.getsockname()[1]

        low = LowLevelServer(
            name=f"tau-{self.server_id}",
            version="0.1.0",
            on_list_tools=self._on_list_tools,
            on_call_tool=self._on_call_tool,
        )
        # One parameterized route serves every channel: the token in the request path is
        # what `_on_call_tool` resolves an episode by.
        app = low.streamable_http_app(streamable_http_path="/mcp/{token}")
        config = uvicorn.Config(app, log_level="warning", lifespan="on", access_log=False)
        self._server = uvicorn.Server(config)

        # uvicorn's own run path, kept after the 2026-08-15 regression scare: a hand-built
        # loop (see _serve, retained for the bisect) coincided with sandbox-side
        # "local MCP 'tau' is disconnected" failures on 3/10 platform episodes. Causality
        # was never established (constraints.md § The disconnect regression) and 72
        # post-revert batch episodes ran with zero disconnects, so the loop stays uvicorn's.
        # The thread ceiling the hand-built loop tried to fix is solved differently now:
        # `_in_bridge_pool` gives the two parking hops their own executor, created here —
        # no loop surgery, sized by `executor_workers`, recorded per round.
        self._executor = ThreadPoolExecutor(
            max_workers=self.executor_workers, thread_name_prefix="tau-bridge"
        )
        self._thread = threading.Thread(
            target=self._server.run, kwargs={"sockets": [self._socket]}, daemon=True
        )
        self._thread.start()

        for _ in range(600):  # up to ~30s
            if self._server.started:
                break
            time.sleep(0.05)
        if not self._server.started:
            raise RuntimeError("tool bridge failed to start")
        return self.url

    @property
    def effective_executor_workers(self) -> int:
        """Workers in the pool the two parking hops actually draw from this run.

        Since the post-seq-5 fix-forward the hops draw from the bridge's OWN pool
        (`_in_bridge_pool`), so the effective capacity IS the designed sizing — the
        host-derived `min(32, cpu_count + 4)` ceiling this property existed to report
        honestly is gone. The property survives because run_metadata.json records it, and
        the contract stands: it must always report the pool in use, never an intent.
        """
        return self.executor_workers

    async def _in_bridge_pool(self, func: Callable[..., Any], /, *args: Any) -> Any:
        """`asyncio.to_thread`, with the bridge's own executor named instead of the loop's.

        CPython's `to_thread` is exactly these three lines with `None` as the executor —
        contextvar propagation and error semantics are identical. Naming the pool is what
        removes the silent host-derived capacity ceiling (`min(32, cpu_count + 4)` shared
        with whatever else the loop runs) without touching how the serving loop is built —
        the lesson of the 2026-08-15 regression scare being that the loop lifecycle is
        uvicorn's to own.
        """
        loop = asyncio.get_running_loop()
        ctx = contextvars.copy_context()
        return await loop.run_in_executor(self._executor, functools.partial(ctx.run, func, *args))

    def _serve(self) -> None:
        """SUPERSEDED, retained only as the bisect arm for the 2026-08-15 disconnect question.

        The capacity problem this solved is now solved by `_in_bridge_pool` without owning
        the loop. Re-enabling this path (point `start()`'s thread at it) reproduces the
        hand-built-loop configuration for a B-prime discriminator run — nothing else should
        ever use it, and it must not be combined with `start()`'s executor creation.

        Original intent — uvicorn's own `Server.run`, with one addition: this loop's default executor.

        `Server.run` builds a loop from the config's loop factory and runs `serve()` on it, so
        the loop it builds carries asyncio's default executor — the host-sized pool the two
        `asyncio.to_thread` hops in `_on_call_tool` draw from. Building the loop here instead
        lets the pool be sized for the round (see BRIDGE_THREADS_PER_EPISODE) before a single
        request lands. `set_default_executor` keeps both call sites untouched, so
        `to_thread`'s contextvar propagation and error semantics are exactly as before — only
        the capacity changes. The loop is this thread's alone, so nothing else in the process
        (τ's runner included) sees a different executor.

        The factory is uvicorn's own (`get_loop_factory`, which replaced `setup_event_loop` in
        uvicorn 0.36) so a configured uvloop is still honoured; `None` means the stdlib loop.
        """
        factory = self._server.config.get_loop_factory()
        loop = factory() if factory is not None else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._executor = ThreadPoolExecutor(
            max_workers=self.executor_workers, thread_name_prefix="tau-bridge"
        )
        loop.set_default_executor(self._executor)
        try:
            loop.run_until_complete(self._server.serve(sockets=[self._socket]))
        finally:
            # The teardown `asyncio.run` would have done, since this builds the loop by hand:
            # cancel what the ASGI stack left pending (sse_starlette parks a shutdown watcher)
            # and close async generators, or closing the loop warns and leaks them.
            try:
                pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                # wait=False, and deliberately NOT loop.shutdown_default_executor(): a handler
                # parked in `channel.wait` returns on its own bounded timeout, and a run's
                # teardown must not block for RESULT_WAIT_SECONDS behind one of them.
                self._executor.shutdown(wait=False, cancel_futures=True)
                asyncio.set_event_loop(None)
                loop.close()

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=10)
        if self._executor is not None:
            # wait=False: a handler still parked in `channel.wait` returns on its own
            # bounded timeout, and a run's teardown must not block behind one of them.
            self._executor.shutdown(wait=False, cancel_futures=True)
        if self._socket is not None:
            with contextlib.suppress(OSError):
                self._socket.close()

    @property
    def url(self) -> str:
        """The run-pinned URL — what `introspection dev --mcp tau=<url>` is handed.

        A `dev` attachment can carry exactly one URL: `--mcp` conveys a URL and nothing
        else — no credentials, no per-task override — and a *connected* MCP binding (the
        documented place for headers) replaces the URL with its own, which cannot reach
        this machine from a cloud sandbox. The run token therefore rides in the path.
        Tunneled requests arriving here carry their sandbox's session header, which is
        what routes them to an episode's channel; local-lane episodes mint their own
        per-episode paths instead.
        """
        return self.url_for(self.token)

    def url_for(self, token: str) -> str:
        if self._port is None:
            raise RuntimeError("tool bridge not started")
        return f"http://127.0.0.1:{self._port}/mcp/{token}"

    # ------------------------------------------------------------------- channels

    def open_channel(self, on_stall: Callable[[], None] | None = None) -> EpisodeChannel:
        """Open a fresh episode channel at its own minted `/mcp/<token>` path.

        The local lane's per-episode entry: the URL reaches that episode's Pi subprocess
        through its environment, so every in-flight episode rendezvouses in isolation.
        `on_stall` attributes the episode's stall warnings to its caller's incident sink,
        which is how a stalled rendezvous reaches the episode manifest.
        """
        with self._channels_lock:
            token = secrets.token_urlsafe(24)
            while token in self._channels or token == self.token:  # pragma: no cover
                token = secrets.token_urlsafe(24)
            channel = EpisodeChannel(self, token, on_stall)
            self._channels[token] = channel
            return channel

    def _bind(self, channel: EpisodeChannel, key: str) -> None:
        with self._channel_bound:
            if channel.closed:
                # The transport's binding poll lost a race with the episode's teardown
                # (τ retried, or the run ended). Registering a dead channel would leak it
                # into the routing table; the episode it served is over either way.
                logger.debug(f"bind of {key!r} arrived after channel close; ignored")
                return
            existing = self._channels.get(key)
            if existing is not None and existing is not channel:
                raise RuntimeError(
                    f"session {key!r} is already bound to a live channel: session ids are "
                    "unique per task attempt, so this is a wiring bug, and re-binding "
                    "would hand one episode's calls to another"
                )
            self._channels[key] = channel
            channel.bound_key = key
            self._channel_bound.notify_all()

    def _release(self, channel: EpisodeChannel) -> None:
        # Identity-guarded per key: a late close of a failed attempt's channel (τ tearing
        # it down after the retry already opened and bound its own) must not evict the
        # successor from either the token or the session namespace.
        with self._channels_lock:
            channel.closed = True
            for key in (channel.token, channel.bound_key):
                if key is not None and self._channels.get(key) is channel:
                    del self._channels[key]

    def _channel_for(self, key: str | None) -> EpisodeChannel | None:
        if key is None:
            return None
        with self._channels_lock:
            return self._channels.get(key)

    def channel_for_request(
        self, session_key: str | None, path_token: str | None, grace: float
    ) -> EpisodeChannel | None:
        """Resolve the channel a request belongs to: session binding first, then the path.

        A tunneled request names its sandbox session, which outranks the path — every
        development-lane request arrives at the one URL its `dev` attachment was handed,
        so the path cannot separate N concurrent platform episodes. An unknown session
        waits up to `grace` for the transport's binding poll to catch up before the
        path fallback and, failing both, refusal.
        """
        if session_key is not None:
            with self._channel_bound:
                channel = self._channels.get(session_key)
                if channel is None and grace > 0:
                    deadline = time.monotonic() + grace
                    while channel is None:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0 or not self._channel_bound.wait(timeout=remaining):
                            break
                        channel = self._channels.get(session_key)
                if channel is not None:
                    return channel
        return self._channel_for(path_token)

    def count_refusal(self, session_key: str | None) -> str:
        """Count a refused call by cause; returns the counter key it landed in."""
        reason = REFUSAL_UNBOUND_SESSION if session_key else REFUSAL_STALE_ENDPOINT
        with self._channels_lock:
            self._refusals[reason] += 1
        return reason

    def refusal_counters(self) -> dict[str, int]:
        """Refused-call totals by cause — run-level, since a refusal has no episode."""
        with self._channels_lock:
            return dict(self._refusals)

    # ------------------------------------------------------------------- handlers

    async def _on_list_tools(
        self, ctx: ServerRequestContext, params: mcp_types.PaginatedRequestParams | None
    ) -> mcp_types.ListToolsResult:
        _trace_headers(ctx, "tools/list")
        return mcp_types.ListToolsResult(tools=list(self._mcp_tools))

    async def _on_call_tool(
        self, ctx: ServerRequestContext, params: mcp_types.CallToolRequestParams
    ) -> mcp_types.CallToolResult:
        _trace_headers(ctx, f"tools/call:{params.name}")
        session_key = _session_of(ctx)
        arrived = time.time()
        channel = await self._in_bridge_pool(
            self.channel_for_request,
            session_key,
            _token_of(ctx),
            UNBOUND_SESSION_GRACE_SECONDS if session_key else 0.0,
        )
        if channel is None:
            # A closed or never-opened token: the episode this URL belonged to is over (or
            # the URL is stale). Refusing immediately beats parking a handler for 300s
            # against a mailbox nothing will ever post to — and the refusal is counted,
            # because an episode whose session never binds fails every call exactly here,
            # and a round whose seam refused calls must say so instead of reporting itself
            # healthy (the failure class this bridge exists to make loud).
            reason = self.count_refusal(session_key)
            token = _token_of(ctx) or ""
            self._log_call(None, params.name, arrived, outcome=f"refused:{reason}")
            logger.warning(
                f"refused {params.name}: no live episode channel "
                f"(session={session_key!r}, token={token[:8]}…) — counted as {reason}"
            )
            return mcp_types.CallToolResult(
                content=[
                    mcp_types.TextContent(
                        type="text",
                        text=(
                            f"no live episode channel at this endpoint for {params.name}: "
                            "the episode has ended, or the URL is stale"
                        ),
                    )
                ],
                is_error=True,
            )
        channel.calls_received += 1
        try:
            content, is_error = await self._in_bridge_pool(
                channel.wait, params.name, params.arguments, RESULT_WAIT_SECONDS
            )
        except ToolResultTimeout as exc:
            self._log_call(channel, params.name, arrived, outcome="timeout")
            # Surfaced to the agent as a failed tool call rather than raised, so the episode
            # ends through τ's own error accounting instead of an adapter traceback.
            return mcp_types.CallToolResult(
                content=[mcp_types.TextContent(type="text", text=str(exc))], is_error=True
            )
        self._log_call(
            channel, params.name, arrived, outcome="error" if is_error else "ok", content=content
        )
        return mcp_types.CallToolResult(
            content=[mcp_types.TextContent(type="text", text=content)], is_error=is_error
        )

    def _log_call(
        self,
        channel: EpisodeChannel | None,
        tool_name: str,
        arrived: float,
        *,
        outcome: str,
        content: str | None = None,
    ) -> None:
        """One observation per handled call: arrival, park duration, outcome, result digest.

        The digest lets a later integrity audit compare what the bridge returned against
        what the conversation export says the agent received — payload corruption in
        transit currently grades as agent behaviour, and this is the bridge-side half of
        the evidence.
        """
        entry = {
            "token": channel.token if channel is not None else None,
            "session": channel.bound_key if channel is not None else None,
            "tool": tool_name,
            "arrived_unix": round(arrived, 3),
            "duration_seconds": round(time.time() - arrived, 3),
            "outcome": outcome,
            "result_sha256_16": (
                hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
                if content is not None
                else None
            ),
        }
        with self._call_log_lock:
            self._call_log.append(entry)

    def call_log(self) -> list[dict[str, Any]]:
        """A copy of every per-call observation so far; the runner persists it per round."""
        with self._call_log_lock:
            return list(self._call_log)


def _trace_headers(ctx: ServerRequestContext, method: str) -> None:
    # Raw stderr, not loguru: τ's per-task log context filters loguru during simulations,
    # which is precisely when these requests arrive. Same rationale as _trace above.
    if not TRACE_HEADERS:
        return
    request = getattr(ctx, "request", None)
    if request is None:
        print(f"[headers] {method}: no HTTP request attached", file=sys.stderr, flush=True)
        return
    headers = dict(getattr(request, "headers", None) or {})
    path = getattr(getattr(request, "url", None), "path", "?")
    print(
        f"[headers] {method} path={path} headers={json.dumps(headers, sort_keys=True)}",
        file=sys.stderr,
        flush=True,
    )


def _token_of(ctx: ServerRequestContext) -> str | None:
    """The channel token named by the request's URL path.

    The streamable-HTTP transport attaches the live HTTP request to every inbound message,
    and the parameterized route puts the path's token segment in its `path_params` — so the
    token is read per request, never inferred from session state.
    """
    request = getattr(ctx, "request", None)
    if request is None:
        return None
    return (getattr(request, "path_params", None) or {}).get("token")


def _session_of(ctx: ServerRequestContext) -> str | None:
    """The sandbox session the development lane's tunnel stamps on forwarded requests.

    Absent on local-lane requests (Pi connects directly), present on every tunneled one —
    and equal to the task's `metadata.agent_session_id`, which is how the transport binds
    an episode's channel to it. Observed live 2026-08-13; recorded in
    `contract/constraints.md` § Platform-lane concurrency.
    """
    request = getattr(ctx, "request", None)
    if request is None:
        return None
    headers = getattr(request, "headers", None)
    if headers is None:
        return None
    return headers.get("x-introspection-session-id")


def _as_mcp_tool(tau_tool: Any, server_id: str) -> mcp_types.Tool:
    """Publish a τ tool unchanged: same name, same description, same JSON Schema.

    τ's `openai_schema` already carries exactly what MCP needs, so nothing is rewritten and
    the model sees the tool documentation the benchmark wrote.
    """
    schema = tau_tool.openai_schema["function"]
    return mcp_types.Tool(
        name=schema["name"],
        description=schema.get("description") or "",
        input_schema=schema.get("parameters") or {"type": "object", "properties": {}},
    )
