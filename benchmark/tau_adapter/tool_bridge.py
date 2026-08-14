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
opens an `EpisodeChannel` — its own mailbox at its own `/mcp/<token>` path — so episode
identity is the URL itself, and a result posted for one episode cannot answer another's
call even when both name the same tool with identical arguments. τ runs its episodes from
a worker pool (`max_concurrency`), and the channel registry is what makes N in-flight
episodes safe; one episode at a time is simply the degenerate case of the same mechanism.
The development lane, whose `dev` attachment is handed a single URL for the whole run,
reuses one pinned token sequentially (`open_run_channel`) — same mechanism, same rules.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import queue
import secrets
import socket
import sys
import threading
from collections.abc import Callable, Iterable
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

#: Set TAU_ADAPTER_TRACE=1 to print every rendezvous pairing to stderr. The rendezvous is the
#: highest-risk part of the seam and its failure mode is a hang, which leaves no evidence
#: behind; a mismatched await/post pair is obvious in this trace and invisible without it.
TRACE = bool(os.environ.get("TAU_ADAPTER_TRACE"))


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
    """One episode's rendezvous surface: its own mailbox, served at its own URL path.

    Episode identity is the URL. Every MCP request carries the channel token in its path,
    so a parked handler can only ever be answered by a result posted to the same episode's
    channel — the keyspace two concurrent episodes could collide in no longer exists.
    `on_stall` is bound at open, which is what attributes a stalled rendezvous to the one
    episode (and manifest row) it belongs to.
    """

    def __init__(self, bridge: ToolBridge, token: str, on_stall: Callable[[], None] | None) -> None:
        self._bridge = bridge
        self.token = token
        self._mailbox = _Mailbox(on_stall=on_stall)
        self.calls_served = 0

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
    ) -> None:
        self._tau_tools = list(tau_tools)
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
        # token -> live channel. Guarded: τ's workers open and close channels concurrently
        # while the server's event loop resolves inbound calls against the same registry.
        self._channels: dict[str, EpisodeChannel] = {}
        self._channels_lock = threading.Lock()
        # Pinned slot tokens: paths whose URL outlives episodes because a `dev` attachment
        # was handed it for the whole run. Slot 0 is the run token itself; the attachment
        # pool mints one more per additional worker. Membership is what open_pinned_channel
        # checks, so a typo'd token cannot silently create a rogue pinned path.
        self._pinned: set[str] = {self.token}

        self._socket: socket.socket | None = None
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self._port: int | None = None
        self.calls_served = 0

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

        self._thread = threading.Thread(
            target=self._server.run, kwargs={"sockets": [self._socket]}, daemon=True
        )
        self._thread.start()

        deadline = threading.Event()
        for _ in range(600):  # up to ~30s
            if self._server.started:
                break
            deadline.wait(0.05)
        if not self._server.started:
            raise RuntimeError("tool bridge failed to start")
        return self.url

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=10)
        if self._socket is not None:
            with contextlib.suppress(OSError):
                self._socket.close()

    @property
    def path(self) -> str:
        """The run-pinned endpoint path, with its token as the last segment.

        This is the one URL the development lane can carry: `introspection dev --mcp
        tau=<url>` conveys a URL and nothing else — no credentials, no per-task override —
        and a *connected* MCP binding (the documented place for headers) replaces the URL
        with its own, which cannot reach this machine from a cloud sandbox. The token
        therefore rides in the path, and this pinned path is the platform lane's channel
        for every episode (`open_run_channel`). Local-lane episodes mint their own paths.
        """
        return f"/mcp/{self.token}"

    @property
    def url(self) -> str:
        """The run-pinned URL — what `introspection dev` is handed for the whole run."""
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

    def mint_pinned_token(self) -> str:
        """Register one more pinned slot — a path whose URL a `dev` attachment holds all run."""
        with self._channels_lock:
            token = secrets.token_urlsafe(24)
            while token in self._pinned or token in self._channels:  # pragma: no cover
                token = secrets.token_urlsafe(24)
            self._pinned.add(token)
            return token

    def open_pinned_channel(
        self, token: str, on_stall: Callable[[], None] | None = None
    ) -> EpisodeChannel:
        """Open this episode's channel at a pinned slot path, replacing any predecessor.

        The development lane's entry: a `dev` attachment holds one URL for the whole run,
        so that slot's episodes share its token *sequentially* — the attachment pool leases
        a slot to exactly one episode at a time. Replacement is the episode boundary: a
        result posted for a call whose handler had already given up stays queued in the
        predecessor's mailbox, and a τ infrastructure retry re-asks the *same task* with
        identical arguments — against the old mailbox it would receive the stale result
        instantly and shift every later pairing by one, silently. The fresh mailbox makes
        that impossible, and any handler still parked on the old one times out on its own
        ceiling.
        """
        with self._channels_lock:
            if token not in self._pinned:
                raise ValueError(
                    f"{token[:8]}… is not a registered pinned token: pinned channels exist "
                    "only at the run token or a slot minted by mint_pinned_token"
                )
            channel = EpisodeChannel(self, token, on_stall)
            self._channels[token] = channel
            return channel

    def open_run_channel(self, on_stall: Callable[[], None] | None = None) -> EpisodeChannel:
        """Slot 0's opener: the run-pinned path. Alias for the single-attachment case."""
        return self.open_pinned_channel(self.token, on_stall)

    def _release(self, channel: EpisodeChannel) -> None:
        # Identity-guarded: a late close of a replaced run channel (τ tearing down a failed
        # attempt after the retry already opened its own) must not evict the successor.
        with self._channels_lock:
            if self._channels.get(channel.token) is channel:
                del self._channels[channel.token]

    def _channel_for(self, token: str | None) -> EpisodeChannel | None:
        if token is None:
            return None
        with self._channels_lock:
            return self._channels.get(token)

    # ------------------------------------------------------------------- handlers

    async def _on_list_tools(
        self, ctx: ServerRequestContext, params: mcp_types.PaginatedRequestParams | None
    ) -> mcp_types.ListToolsResult:
        return mcp_types.ListToolsResult(tools=list(self._mcp_tools))

    async def _on_call_tool(
        self, ctx: ServerRequestContext, params: mcp_types.CallToolRequestParams
    ) -> mcp_types.CallToolResult:
        channel = self._channel_for(_token_of(ctx))
        if channel is None:
            # A closed or never-opened token: the episode this URL belonged to is over (or
            # the URL is stale). Refusing immediately beats parking a handler for 300s
            # against a mailbox nothing will ever post to.
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
        self.calls_served += 1
        channel.calls_served += 1
        try:
            content, is_error = await asyncio.to_thread(
                channel.wait, params.name, params.arguments, RESULT_WAIT_SECONDS
            )
        except ToolResultTimeout as exc:
            # Surfaced to the agent as a failed tool call rather than raised, so the episode
            # ends through τ's own error accounting instead of an adapter traceback.
            return mcp_types.CallToolResult(
                content=[mcp_types.TextContent(type="text", text=str(exc))], is_error=True
            )
        return mcp_types.CallToolResult(
            content=[mcp_types.TextContent(type="text", text=content)], is_error=is_error
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
