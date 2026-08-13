"""The rendezvous mailbox, and the episode boundary its state must not leak across."""

from __future__ import annotations

import pytest

from tau_adapter.tool_bridge import ToolBridge, ToolResultTimeout, _Key


def test_a_posted_result_pairs_with_the_matching_wait() -> None:
    bridge = ToolBridge(tau_tools=[])
    bridge.post_result("KB_search", {"query": "gold card"}, "the document", is_error=False)
    content, is_error = bridge._mailbox.wait(
        _Key.of("KB_search", {"query": "gold card"}), timeout=1.0
    )
    assert (content, is_error) == ("the document", False)


def test_an_episode_reset_discards_results_posted_for_abandoned_calls() -> None:
    """A stale result must not answer the next episode's identical call.

    τ retries an episode of the same task after an infrastructure error, and the retry asks
    with the same tool name and arguments. Without the reset, a result posted after its
    handler gave up would satisfy the retry's first call instantly and shift every later
    pairing by one — silent cross-episode contamination.
    """
    bridge = ToolBridge(tau_tools=[])
    bridge.post_result("KB_search", {"query": "gold card"}, "stale", is_error=False)
    bridge.reset_for_episode()
    with pytest.raises(ToolResultTimeout):
        bridge._mailbox.wait(_Key.of("KB_search", {"query": "gold card"}), timeout=0.05)
