"""The D24 seam semantics: Pi-local tool calls are suppressed from τ, evidenced in full.

Covers the registry (`pi_local.py`), the turn-level pump in `PiRecipeAgent`, the
invalid-call passthrough that must survive suppression, the runaway cap, and the
manifest's derived `pi_local_calls` counter. The local-lane assembly
(`transport_local._assistant_turn`) and `_assemble_tau_message` had no coverage before
this file; these tests are the A.0a floor for any future seam change.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tau2.data_model.message import UserMessage

from tau_adapter import manifest as manifestmod
from tau_adapter.pi_agent import MAX_SUPPRESSED_TURNS_PER_STEP, PiAgentState, PiRecipeAgent
from tau_adapter.pi_local import pi_local_tool_names
from tau_adapter.transport import AssistantTurn, PiToolCall

# ------------------------------------------------------------------------- registry


def _write_recipe(tmp_path: Path, tools: list[str], subagents: list[str]) -> Path:
    agents = tmp_path / "agents"
    agents.mkdir(parents=True)
    lines = ["name: agent", f"tools: [{', '.join(tools)}]", f"subagents: [{', '.join(subagents)}]"]
    (agents / "agent.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


def test_registry_is_tools_allowlist(tmp_path: Path) -> None:
    recipe = _write_recipe(tmp_path, tools=["probe_note", "sum_charges"], subagents=[])
    assert pi_local_tool_names(recipe) == frozenset({"probe_note", "sum_charges"})


def test_registry_empty_for_bare_recipe(tmp_path: Path) -> None:
    recipe = _write_recipe(tmp_path, tools=[], subagents=[])
    assert pi_local_tool_names(recipe) == frozenset()


def test_registry_adds_agent_tool_only_with_subagents(tmp_path: Path) -> None:
    recipe = _write_recipe(tmp_path, tools=[], subagents=["helper"])
    assert pi_local_tool_names(recipe) == frozenset({"agent"})


# ------------------------------------------------------------------------- fixtures


class FakeChannel:
    """The slice of EpisodeChannel the stepping path touches."""

    def __init__(self, name_map: dict[str, str]) -> None:
        self.name_map = name_map
        self.posted: list[dict] = []

    def post_result(self, **kwargs) -> None:
        self.posted.append(kwargs)


class FakeTransport:
    """Scripted turns; records what the agent asked of it."""

    def __init__(self, turns: list[AssistantTurn]) -> None:
        self._turns = list(turns)
        self.sent_user_texts: list[str] = []
        self.session_ref = "fake-session"

    def send_user_text(self, text: str) -> None:
        self.sent_user_texts.append(text)

    def next_turn(self, timeout: float) -> AssistantTurn:
        if not self._turns:
            raise AssertionError("transport pumped past its script")
        return self._turns.pop(0)


def _agent(turns: list[AssistantTurn], pi_local: frozenset[str]) -> PiRecipeAgent:
    agent = PiRecipeAgent.__new__(PiRecipeAgent)
    agent._transport = FakeTransport(turns)
    agent._channel = FakeChannel({"mcp_tau_lookup_ab12": "lookup"})
    agent._pi_local_tools = pi_local
    return agent


def _call(pi_name: str, call_id: str = "c1") -> PiToolCall:
    return PiToolCall(id=call_id, pi_name=pi_name, arguments={"q": call_id})


def _step(agent: PiRecipeAgent, state: PiAgentState | None = None):
    state = state or PiAgentState()
    message, state = agent.generate_next_message(UserMessage(role="user", content="hi"), state)
    return message, state


# ---------------------------------------------------------------------- suppression


def test_local_only_turn_is_pumped_and_next_turn_forwards() -> None:
    turns = [
        AssistantTurn(tool_calls=(_call("probe_note", "a"),), cost=0.01),
        AssistantTurn(tool_calls=(_call("mcp_tau_lookup_ab12", "b"),), cost=0.02),
    ]
    message, state = _step(_agent(turns, frozenset({"probe_note"})))
    assert [tc.name for tc in message.tool_calls] == ["lookup"]
    assert state.pending == {"b": ("lookup", {"q": "b"})}
    assert state.assistant_turns == 2
    assert message.raw_data["pi_tool_names"] == ["probe_note", "mcp_tau_lookup_ab12"]
    assert message.raw_data["pi_suppressed_tool_names"] == ["probe_note"]
    assert message.cost == pytest.approx(0.03)


def test_mixed_turn_forwards_tau_call_and_suppresses_local_sibling() -> None:
    turns = [
        AssistantTurn(
            text="checking",
            tool_calls=(_call("probe_note", "a"), _call("mcp_tau_lookup_ab12", "b")),
        )
    ]
    message, state = _step(_agent(turns, frozenset({"probe_note"})))
    assert [tc.name for tc in message.tool_calls] == ["lookup"]
    assert message.content == "checking"
    assert message.raw_data["pi_suppressed_tool_names"] == ["probe_note"]
    assert "a" not in state.pending


def test_held_narration_rides_with_the_next_forwardable_turn() -> None:
    turns = [
        AssistantTurn(text="thinking aloud", tool_calls=(_call("probe_note", "a"),)),
        AssistantTurn(text="the answer", tool_calls=()),
    ]
    message, _ = _step(_agent(turns, frozenset({"probe_note"})))
    assert message.content == "thinking aloud\n\nthe answer"
    assert message.tool_calls is None


def test_unowned_name_still_forwards_as_invalid_call() -> None:
    turns = [AssistantTurn(tool_calls=(_call("no_such_tool", "a"),))]
    message, state = _step(_agent(turns, frozenset({"probe_note"})))
    assert [tc.name for tc in message.tool_calls] == ["no_such_tool"]
    assert state.pending["a"] == ("no_such_tool", {"q": "a"})
    assert message.raw_data["pi_suppressed_tool_names"] == []


def test_pure_text_turn_is_untouched() -> None:
    turns = [AssistantTurn(text="hello there")]
    message, state = _step(_agent(turns, frozenset({"probe_note"})))
    assert message.content == "hello there"
    assert message.tool_calls is None
    assert state.assistant_turns == 1


def test_suppression_disabled_when_registry_empty() -> None:
    turns = [AssistantTurn(tool_calls=(_call("probe_note", "a"),))]
    message, _ = _step(_agent(turns, frozenset()))
    assert [tc.name for tc in message.tool_calls] == ["probe_note"]


def test_runaway_cap_resumes_unfiltered_forwarding() -> None:
    local = [
        AssistantTurn(tool_calls=(_call("probe_note", f"c{i}"),))
        for i in range(MAX_SUPPRESSED_TURNS_PER_STEP)
    ]
    overflow = AssistantTurn(tool_calls=(_call("probe_note", "overflow"),))
    message, state = _step(_agent([*local, overflow], frozenset({"probe_note"})))
    # The cap-crossing call forwards under its Pi name: the runaway is graded, not hidden.
    assert [tc.name for tc in message.tool_calls] == ["probe_note"]
    assert len(message.raw_data["pi_suppressed_tool_names"]) == MAX_SUPPRESSED_TURNS_PER_STEP
    assert state.assistant_turns == MAX_SUPPRESSED_TURNS_PER_STEP + 1


def test_usage_merges_numerically_across_pumped_turns() -> None:
    turns = [
        AssistantTurn(tool_calls=(_call("probe_note", "a"),), usage={"total_tokens": 10}),
        AssistantTurn(text="done", usage={"total_tokens": 5, "model": "x"}),
    ]
    message, _ = _step(_agent(turns, frozenset({"probe_note"})))
    assert message.usage == {"total_tokens": 15, "model": "x"}


# ------------------------------------------------------------------------- manifest


def test_manifest_derives_pi_local_calls_from_raw_data() -> None:
    payload = {
        "simulations": [
            {
                "task_id": "task_x",
                "trial": 0,
                "termination_reason": "user_stop",
                "reward_info": {"reward": 1.0},
                "messages": [
                    {"role": "assistant", "raw_data": {"pi_suppressed_tool_names": ["a", "b"]}},
                    {"role": "assistant", "raw_data": {"pi_suppressed_tool_names": []}},
                    {"role": "assistant"},
                ],
            }
        ]
    }
    context = manifestmod.RoundContext(experiment_id="exp", transport="local")
    rows = manifestmod.build_rows(payload, context)
    assert rows[0]["pi_local_calls"] == 2


def test_manifest_pi_local_calls_zero_without_suppression() -> None:
    payload = {
        "simulations": [
            {
                "task_id": "task_x",
                "trial": 0,
                "termination_reason": "user_stop",
                "reward_info": {"reward": 1.0},
                "messages": [{"role": "assistant", "raw_data": {"pi_tool_names": ["lookup"]}}],
            }
        ]
    }
    context = manifestmod.RoundContext(experiment_id="exp", transport="local")
    rows = manifestmod.build_rows(payload, context)
    assert rows[0]["pi_local_calls"] == 0
