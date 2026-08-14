"""Episode channels: the rendezvous, and the episode identity results must not cross.

The bridge serves every episode from one server, so episode identity lives in the URL:
each channel is its own `/mcp/<token>` path with its own mailbox. These tests pin the
property the whole experiment rests on — a result posted for one episode can never
answer another episode's call, even when both call the same tool with identical
arguments — plus the lifecycle rules that keep that true across τ's retries.
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

    def __init__(self, token: str) -> None:
        self.path_params = {"token": token}


class _StubCtx:
    def __init__(self, token: str) -> None:
        self.request = _StubRequest(token)


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


def test_a_replaced_run_channel_discards_results_posted_for_abandoned_calls() -> None:
    """A stale result must not answer the next episode's identical call.

    The development lane serves every episode from one pinned URL, and τ retries an
    episode of the same task with the same tool name and arguments after an
    infrastructure error. Without the replacement, a result posted after its handler
    gave up would satisfy the retry's first call instantly and shift every later
    pairing by one — silent cross-episode contamination.
    """
    bridge = ToolBridge(tau_tools=[])
    first = bridge.open_run_channel()
    first.post_result("KB_search", {"query": "gold card"}, "stale", is_error=False)
    second = bridge.open_run_channel()
    with pytest.raises(ToolResultTimeout):
        second.wait("KB_search", {"query": "gold card"}, timeout=0.05)


def test_a_closed_channels_stale_result_cannot_answer_a_new_episode() -> None:
    """The local lane's variant of the same rule: fresh token, fresh mailbox."""
    bridge = ToolBridge(tau_tools=[])
    first = bridge.open_channel()
    first.post_result("KB_search", {"query": "gold card"}, "stale", is_error=False)
    first.close()
    second = bridge.open_channel()
    with pytest.raises(ToolResultTimeout):
        second.wait("KB_search", {"query": "gold card"}, timeout=0.05)


def test_the_run_channel_keeps_its_url_across_episodes() -> None:
    """`introspection dev` is handed one URL for the whole run; episodes must not move it."""
    bridge = ToolBridge(tau_tools=[])
    first = bridge.open_run_channel()
    second = bridge.open_run_channel()
    assert first.token == second.token == bridge.token


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


def test_a_late_close_of_a_replaced_run_channel_does_not_evict_its_successor() -> None:
    """τ's teardown of a failed attempt may close its channel after the retry opened one."""
    bridge = ToolBridge(tau_tools=[_FakeTauTool()])
    first = bridge.open_run_channel()
    second = bridge.open_run_channel()
    first.close()
    second.post_result("KB_search", {"query": "gold card"}, "for the retry", is_error=False)
    answered = asyncio.run(bridge._on_call_tool(_StubCtx(bridge.token), _call_params()))
    assert not answered.is_error
    assert answered.content[0].text == "for the retry"
