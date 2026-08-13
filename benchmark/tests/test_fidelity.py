"""The lane fidelity checker.

Two of these tests exist because the first version of the checker failed on healthy runs. In this
domain both participants hold tools: the agent has the 15 locked banking tools, reached through
our bridge, and the user simulator has `apply_for_credit_card`, which never touches the bridge and
is deliberately absent from the locked catalogue. Treating the two surfaces as one produced false
alarms on exactly the *successful* episodes — the ones where the user applies — which is the worst
possible place for a gate to cry wolf.
"""

from __future__ import annotations

import json

from fidelity.lane_report import build_report, check_invariants

LOCKED = {"KB_search", "get_user_information_by_id", "log_verification"}


def write_results(tmp_path, messages: list[dict], reward=1.0, termination="user_stop"):
    payload = {
        "simulations": [
            {
                "task_id": "task_001",
                "termination_reason": termination,
                "messages": messages,
                "reward_info": {"reward": reward},
            }
        ]
    }
    path = tmp_path / "results.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def agent_call(call_id: str, name: str = "KB_search") -> dict:
    return {"role": "assistant", "tool_calls": [{"id": call_id, "name": name}]}


def tool_result(call_id: str) -> dict:
    return {"role": "tool", "id": call_id, "content": "..."}


def verdicts(report) -> dict[str, bool]:
    return {f.check: f.ok for f in check_invariants(report)}


def test_a_healthy_episode_passes_every_invariant(tmp_path) -> None:
    report = build_report(
        write_results(
            tmp_path,
            [
                {"role": "assistant", "content": "Hi"},
                {"role": "user", "content": "hello"},
                agent_call("c1"),
                tool_result("c1"),
                {"role": "assistant", "content": "here you go"},
                {"role": "user", "content": "thanks ###STOP###"},
            ],
        ),
        lane="local",
        locked_tools=LOCKED,
    )
    assert all(verdicts(report).values())
    assert report.agent_invocations == 1
    assert report.shape == "A U A* t A U"


def test_the_user_simulators_own_tool_is_not_an_adapter_fault(tmp_path) -> None:
    """`apply_for_credit_card` is the user's tool: not in the agent's catalogue, and correct.

    It is also the tool whose presence marks a *winning* episode in this domain, so flagging it
    would fail the gate precisely when the harness did well.
    """
    report = build_report(
        write_results(
            tmp_path,
            [
                {"role": "assistant", "content": "Hi"},
                {"role": "user", "content": "hello"},
                agent_call("c1"),
                tool_result("c1"),
                {"role": "assistant", "content": "the Gold card has no annual fee"},
                {
                    "role": "user",
                    "content": "applying now",
                    "tool_calls": [{"id": "u1", "name": "apply_for_credit_card"}],
                },
                tool_result("u1"),
                {"role": "user", "content": "done ###STOP###"},
            ],
        ),
        lane="platform",
        locked_tools=LOCKED,
    )
    assert all(verdicts(report).values())
    assert report.user_tool_names == ["apply_for_credit_card"]
    assert report.agent_tool_names == ["KB_search"]
    # The user's result must not read as an orphan just because the agent did not make the call.
    assert report.results_without_calls == []


def test_a_mangled_tool_name_reaching_tau_is_a_failure(tmp_path) -> None:
    """If the reverse name map leaks, the graded action is not the action the agent took."""
    report = build_report(
        write_results(
            tmp_path,
            [
                {"role": "user", "content": "hello"},
                agent_call("c1", "mcp_tau_KB_search_77c5623a9f"),
                tool_result("c1"),
            ],
        ),
        lane="local",
        locked_tools=LOCKED,
    )
    assert verdicts(report)["the agent's tool names are τ's own"] is False
    assert report.unmapped_tool_names == ["mcp_tau_KB_search_77c5623a9f"]


def test_an_unanswered_tool_call_is_a_failure(tmp_path) -> None:
    """The signature of a broken rendezvous — and it can coexist with a perfect reward."""
    report = build_report(
        write_results(
            tmp_path,
            [
                {"role": "user", "content": "hello"},
                agent_call("c1"),
                tool_result("c1"),
                agent_call("c2"),  # parked, never answered
                {"role": "assistant", "content": "answering anyway"},
                {"role": "user", "content": "###STOP###"},
            ],
            reward=1.0,
        ),
        lane="platform",
        locked_tools=LOCKED,
    )
    assert verdicts(report)["every tool call was answered"] is False
    assert report.calls_without_results == ["c2"]
    # The reward is untouched: that is the danger this check exists to catch.
    assert report.reward == 1.0


def test_an_infrastructure_error_is_not_a_graded_outcome(tmp_path) -> None:
    report = build_report(
        write_results(tmp_path, [], reward=None, termination="infrastructure_error"),
        lane="platform",
        locked_tools=LOCKED,
    )
    assert verdicts(report)["episode ended normally"] is False


def test_an_ungraded_episode_is_reported_as_such(tmp_path) -> None:
    path = tmp_path / "results.json"
    path.write_text(
        json.dumps(
            {"simulations": [{"task_id": "t", "termination_reason": "user_stop", "messages": []}]}
        ),
        encoding="utf-8",
    )
    report = build_report(path, lane="local", locked_tools=LOCKED)
    assert verdicts(report)["reward came from τ"] is False


def test_agent_invocations_count_answers_to_the_user_not_continuations(tmp_path) -> None:
    """The count that distinguishes a one-turn success from a truncated episode.

    A winning episode here is often a *single* agent invocation: the answer satisfies the user, who
    applies with their own tool and stops. Counting every assistant message instead would make that
    look like nine turns and hide the distinction.
    """
    report = build_report(
        write_results(
            tmp_path,
            [
                {"role": "user", "content": "q1"},
                agent_call("c1"),
                tool_result("c1"),
                agent_call("c2"),
                tool_result("c2"),
                {"role": "assistant", "content": "answer"},
                {"role": "user", "content": "q2"},
                {"role": "assistant", "content": "answer 2"},
                {"role": "user", "content": "###STOP###"},
            ],
        ),
        lane="local",
        locked_tools=LOCKED,
    )
    assert report.agent_invocations == 2
