"""Episode channels: the rendezvous, and the episode identity results must not cross.

One bridge serves every episode; each episode's channel is its own mailbox, found by the
channel's `/mcp/<token>` URL locally and by the sandbox-session binding through the
development tunnel. These tests pin the property the whole experiment rests on — a result
posted for one episode can never answer another episode's call, even when both call the
same tool with identical arguments — plus the lifecycle rules that keep that true across
τ's retries and concurrent workers.
"""

from __future__ import annotations

import asyncio
import threading
from typing import ClassVar

import mcp.types as mcp_types
import pytest

from tau_adapter.tool_bridge import ToolBridge, ToolResultTimeout


class _FakeTauTool:
    """The minimal τ tool surface the bridge reads: a name and an openai schema."""

    name = "KB_search"
    openai_schema: ClassVar[dict] = {
        "function": {
            "name": "KB_search",
            "description": "search the knowledge base",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
        }
    }


class _StubRequest:
    """What the handler reads off the transport-attached HTTP request."""

    def __init__(self, token: str, session: str | None = None) -> None:
        self.path_params = {"token": token}
        self.headers = {"x-introspection-session-id": session} if session else {}


class _StubCtx:
    def __init__(self, token: str, session: str | None = None) -> None:
        self.request = _StubRequest(token, session)


def _call_params(query: str = "gold card") -> mcp_types.CallToolRequestParams:
    return mcp_types.CallToolRequestParams(name="KB_search", arguments={"query": query})


def test_results_do_not_cross_between_concurrent_channels_with_identical_calls() -> None:
    """Two in-flight episodes, same tool, same arguments — each gets its own answer.

    This is the failure mode concurrency introduces: with one shared mailbox the first
    parked handler would take whichever result posted first, and both episodes would
    still "work" — graded contamination with no error anywhere. Channels remove the
    shared keyspace entirely.
    """
    bridge = ToolBridge(tau_tools=[])
    channel_a = bridge.open_channel()
    channel_b = bridge.open_channel()

    # B's answer arrives first. A, parked on the same (tool, args) key, must not take it.
    channel_b.post_result("KB_search", {"query": "gold card"}, "answer-for-B", is_error=False)
    with pytest.raises(ToolResultTimeout):
        channel_a.wait("KB_search", {"query": "gold card"}, timeout=0.05)

    channel_a.post_result("KB_search", {"query": "gold card"}, "answer-for-A", is_error=False)
    assert channel_a.wait("KB_search", {"query": "gold card"}, timeout=1.0) == (
        "answer-for-A",
        False,
    )
    assert channel_b.wait("KB_search", {"query": "gold card"}, timeout=1.0) == (
        "answer-for-B",
        False,
    )


def test_the_live_server_routes_concurrent_identical_calls_by_episode_url() -> None:
    """End to end through HTTP: two MCP clients on their channel URLs, identical calls.

    The mailbox-level test above proves the state model; this proves the routing —
    the token in the request path is what resolves a parked handler to its episode.
    """
    bridge = ToolBridge(tau_tools=[_FakeTauTool()])
    bridge.start()
    try:
        channel_a = bridge.open_channel()
        channel_b = bridge.open_channel()

        def post_both() -> None:
            channel_b.post_result(
                "KB_search", {"query": "gold card"}, "answer-for-B", is_error=False
            )
            channel_a.post_result(
                "KB_search", {"query": "gold card"}, "answer-for-A", is_error=False
            )

        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async def call(url: str) -> str:
            async with (
                streamable_http_client(url) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                result = await session.call_tool("KB_search", {"query": "gold card"})
                return result.content[0].text

        async def both() -> tuple[str, str]:
            poster = threading.Timer(0.3, post_both)
            poster.start()
            try:
                return await asyncio.gather(call(channel_a.url), call(channel_b.url))
            finally:
                poster.cancel()

        got_a, got_b = asyncio.run(both())
        assert got_a == "answer-for-A"
        assert got_b == "answer-for-B"
    finally:
        bridge.stop()


def test_a_posted_result_pairs_with_the_matching_wait() -> None:
    bridge = ToolBridge(tau_tools=[])
    channel = bridge.open_channel()
    channel.post_result("KB_search", {"query": "gold card"}, "the document", is_error=False)
    assert channel.wait("KB_search", {"query": "gold card"}, timeout=1.0) == (
        "the document",
        False,
    )


def test_calls_route_by_session_binding_before_path_token() -> None:
    """A tunneled request names its sandbox session; that identity outranks the path.

    Every development-lane request arrives at the one URL `dev` was handed, so the path
    token alone cannot separate N concurrent platform episodes — the
    `x-introspection-session-id` header is what does, once the transport binds its
    episode's channel to the session `tasks get` reports as `metadata.agent_session_id`.
    """
    bridge = ToolBridge(tau_tools=[])
    channel_a = bridge.open_channel()
    channel_b = bridge.open_channel()
    channel_a.bind("sess-A")
    channel_b.bind("sess-B")

    assert bridge.channel_for_request("sess-A", bridge.token, grace=0.0) is channel_a
    assert bridge.channel_for_request("sess-B", bridge.token, grace=0.0) is channel_b
    # A local-lane request has no session header and routes by its own path token.
    assert bridge.channel_for_request(None, channel_a.token, grace=0.0) is channel_a


def test_results_do_not_cross_between_session_bound_channels_with_identical_calls() -> None:
    """Two concurrent platform episodes, same tool, same arguments — no crossing."""
    bridge = ToolBridge(tau_tools=[])
    channel_a = bridge.open_channel()
    channel_b = bridge.open_channel()
    channel_a.bind("sess-A")
    channel_b.bind("sess-B")

    channel_b.post_result("KB_search", {"query": "gold card"}, "answer-for-B", is_error=False)
    with pytest.raises(ToolResultTimeout):
        channel_a.wait("KB_search", {"query": "gold card"}, timeout=0.05)
    channel_a.post_result("KB_search", {"query": "gold card"}, "answer-for-A", is_error=False)
    assert channel_a.wait("KB_search", {"query": "gold card"}, timeout=1.0) == (
        "answer-for-A",
        False,
    )
    assert channel_b.wait("KB_search", {"query": "gold card"}, timeout=1.0) == (
        "answer-for-B",
        False,
    )


def test_an_unbound_session_waits_for_its_binding_then_routes() -> None:
    """The sandbox's first tool call may race the transport's `tasks get` binding poll;
    the handler waits out the race instead of failing the call."""
    bridge = ToolBridge(tau_tools=[])
    channel = bridge.open_channel()
    threading.Timer(0.2, lambda: channel.bind("sess-late")).start()
    resolved = bridge.channel_for_request("sess-late", bridge.token, grace=2.0)
    assert resolved is channel


def test_a_session_that_never_binds_is_refused_after_the_grace() -> None:
    bridge = ToolBridge(tau_tools=[])
    assert bridge.channel_for_request("sess-ghost", "no-such-token", grace=0.05) is None


def test_a_closed_channel_releases_its_session_binding_and_token() -> None:
    bridge = ToolBridge(tau_tools=[])
    channel = bridge.open_channel()
    channel.bind("sess-A")
    channel.close()
    assert bridge.channel_for_request("sess-A", channel.token, grace=0.0) is None


def test_a_session_key_cannot_be_bound_to_two_live_channels() -> None:
    """Session ids are unique per task attempt; a double bind is a wiring bug and must
    fail loudly rather than silently hand one episode's calls to another."""
    bridge = ToolBridge(tau_tools=[])
    first = bridge.open_channel()
    second = bridge.open_channel()
    first.bind("sess-A")
    with pytest.raises(RuntimeError, match="already bound"):
        second.bind("sess-A")
    # After the first episode closes, the key is free again (a fresh attempt could
    # legitimately reuse it only if the platform ever reissued it).
    first.close()
    second.bind("sess-A")
    assert bridge.channel_for_request("sess-A", bridge.token, grace=0.0) is second


def test_a_closed_channels_stale_result_cannot_answer_a_new_episode() -> None:
    """The local lane's variant of the same rule: fresh token, fresh mailbox."""
    bridge = ToolBridge(tau_tools=[])
    first = bridge.open_channel()
    first.post_result("KB_search", {"query": "gold card"}, "stale", is_error=False)
    first.close()
    second = bridge.open_channel()
    with pytest.raises(ToolResultTimeout):
        second.wait("KB_search", {"query": "gold card"}, timeout=0.05)


def test_fresh_channels_get_distinct_tokens_and_urls() -> None:
    bridge = ToolBridge(tau_tools=[])
    tokens = {bridge.open_channel().token for _ in range(8)}
    assert len(tokens) == 8
    assert bridge.token not in tokens


def test_a_stall_is_attributed_to_the_channel_that_stalled() -> None:
    """Stall warnings feed the episode manifest; they must land on their own episode."""
    stalls_a: list[int] = []
    stalls_b: list[int] = []
    bridge = ToolBridge(tau_tools=[])
    channel_a = bridge.open_channel(on_stall=lambda: stalls_a.append(1))
    bridge.open_channel(on_stall=lambda: stalls_b.append(1))
    with pytest.raises(ToolResultTimeout):
        channel_a.wait("KB_search", {"query": "gold card"}, timeout=0.05)
    assert stalls_a == [1]
    assert stalls_b == []


def test_a_call_for_an_unknown_or_closed_token_is_refused_loudly() -> None:
    """A stale URL fails as an error result, not a 300s park against nothing."""
    bridge = ToolBridge(tau_tools=[_FakeTauTool()])
    refused = asyncio.run(bridge._on_call_tool(_StubCtx("no-such-token"), _call_params()))
    assert refused.is_error
    assert "no live episode channel" in refused.content[0].text

    channel = bridge.open_channel()
    channel.close()
    refused = asyncio.run(bridge._on_call_tool(_StubCtx(channel.token), _call_params()))
    assert refused.is_error


def test_channels_stay_isolated_under_a_worker_pool_of_episodes() -> None:
    """The shape τ's runner drives at max_concurrency N: concurrent create/rendezvous/close.

    Every worker runs episodes back to back — open a channel, post and await a result under
    the SAME (tool, arguments) key every other worker is using, close — while the registry
    is mutated from all sides. Any crossing or lost result is an error; τ retrying an
    episode mid-flight is just one more worker doing exactly this.
    """
    bridge = ToolBridge(tau_tools=[])
    errors: list[str] = []

    def worker(worker_id: int) -> None:
        for episode in range(25):
            channel = bridge.open_channel()
            expected = f"answer-{worker_id}-{episode}"
            channel.post_result("KB_search", {"query": "gold card"}, expected, is_error=False)
            try:
                got, _ = channel.wait("KB_search", {"query": "gold card"}, timeout=1.0)
            except ToolResultTimeout:
                errors.append(f"worker {worker_id} episode {episode}: result never arrived")
            else:
                if got != expected:
                    errors.append(
                        f"worker {worker_id} episode {episode}: got {got!r}, "
                        f"expected {expected!r} — a result crossed episodes"
                    )
            channel.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert not errors, errors


def test_a_late_close_of_a_previous_attempts_channel_does_not_evict_the_retry() -> None:
    """τ's teardown of a failed attempt may close its channel after the retry opened one.

    Sessions make this structural — each attempt binds its own session id — but the
    routing must still hold when a stale close arrives after the retry is live.
    """
    bridge = ToolBridge(tau_tools=[_FakeTauTool()])
    first = bridge.open_channel()
    first.bind("sess-attempt-1")
    second = bridge.open_channel()
    second.bind("sess-attempt-2")
    first.close()
    second.post_result("KB_search", {"query": "gold card"}, "for the retry", is_error=False)
    answered = asyncio.run(
        bridge._on_call_tool(_StubCtx("ignored-path", session="sess-attempt-2"), _call_params())
    )
    assert not answered.is_error
    assert answered.content[0].text == "for the retry"


def test_a_bind_arriving_after_close_cannot_resurrect_the_channel() -> None:
    """The transport's binding poll can lose a race with the episode's teardown (a τ
    retry closes the failed attempt while `tasks get` is in flight); a late bind must
    not re-register the dead channel in the routing table."""
    bridge = ToolBridge(tau_tools=[])
    channel = bridge.open_channel()
    channel.close()
    channel.bind("sess-late-after-close")
    assert bridge.channel_for_request("sess-late-after-close", channel.token, grace=0.0) is None
