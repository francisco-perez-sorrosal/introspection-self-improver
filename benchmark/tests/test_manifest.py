"""Episode-manifest rows: the (task, trial) → conversation join, stated once and testable.

The manifest is what `operate` receives, so the joins and flags here are load-bearing: a row
that silently mis-joins would send a diagnosis to the wrong conversation, which is worse
than no join at all.
"""

from __future__ import annotations

import json

from tau_adapter.manifest import (
    EpisodeIncidents,
    RoundContext,
    build_rows,
    read_manifest,
    write_manifest,
)


def _payload() -> dict:
    return {
        "simulations": [
            {
                "task_id": "task_001",
                "trial": 0,
                "seed": 111,
                "termination_reason": "TerminationReason.USER_STOP",
                "reward_info": {"reward": 1.0},
                "duration": 45.2,
                "agent_cost": 0.11,
                "user_cost": float("nan"),
                "messages": [
                    {"role": "assistant", "raw_data": {"pi_session_ref": "conv-aaa"}},
                    {"role": "user"},
                ],
            },
            {
                # τ's infrastructure-error placeholder: no messages, no session ref.
                "task_id": "task_002",
                "trial": 1,
                "seed": 222,
                "termination_reason": "TerminationReason.INFRASTRUCTURE_ERROR",
                "reward_info": None,
                "messages": [],
                "info": {
                    "error": "litellm.APIConnectionError: peer closed connection " + "x" * 600,
                    "error_type": "APIConnectionError",
                    "error_traceback": "Traceback (most recent call last): ...",
                    "failed_after_attempts": 4,
                },
            },
        ]
    }


def _context(**overrides) -> RoundContext:
    fields = dict(
        experiment_id="001_bm25-sonnet46",
        transport="platform",
        generation="generation_000",
        arm_sha="abc123",
        accounting={
            "conv-aaa": {
                "cost": {"usd": 0.25},
                "usage": {"total_tokens": 1000},
                "metrics": {"span_count": 40},
                "recipe_git_commit_sha": "abc123",
                "evidence_complete": True,
            }
        },
        incidents_by_ref={"conv-aaa": {"stall_warnings": 2, "prompt_409": 0}},
        labels_by_ref={
            "conv-aaa": (
                "[exp_001:bm25-sonnet46] τ²-bench banking task_001 trial 0 gen_000"
                " - Wanted to change the email address on their account"
            )
        },
    )
    fields.update(overrides)
    return RoundContext(**fields)


def test_rows_join_accounting_incidents_and_labels_by_session_ref():
    rows = build_rows(_payload(), _context())
    joined = next(r for r in rows if r["tau_task_id"] == "task_001")
    assert joined["introspection_task_id"] == "conv-aaa"
    assert joined["recipe_git_commit_sha"] == "abc123"
    assert joined["arm_sha_ok"] is True
    assert joined["cost_usd"] == 0.25
    assert joined["total_tokens"] == 1000
    assert joined["evidence_complete"] is True
    assert joined["stall_warnings"] == 2
    assert joined["label"].startswith("[exp_001:bm25-sonnet46]")
    assert joined["completed"] is True
    assert joined["seed"] == 111


def test_infrastructure_placeholder_row_is_counted_but_joins_nothing():
    rows = build_rows(_payload(), _context())
    placeholder = next(r for r in rows if r["tau_task_id"] == "task_002")
    assert placeholder["completed"] is False
    assert placeholder["introspection_task_id"] is None
    assert placeholder["recipe_git_commit_sha"] is None
    assert placeholder["arm_sha_ok"] is None
    assert placeholder["reward"] is None


def test_failed_row_carries_the_root_cause_tau_recorded():
    rows = build_rows(_payload(), _context())
    placeholder = next(r for r in rows if r["tau_task_id"] == "task_002")
    failure = placeholder["failure"]
    assert failure["error_type"] == "APIConnectionError"
    assert failure["failed_after_attempts"] == 4
    assert failure["error"].startswith("litellm.APIConnectionError")
    assert len(failure["error"]) <= 500  # bounded; the full traceback stays in results.json
    assert "error_traceback" not in failure
    completed = next(r for r in rows if r["tau_task_id"] == "task_001")
    assert completed["failure"] is None


def test_arm_sha_mismatch_and_dirty_tree_mark_rows_not_ok():
    mismatched = _context(arm_sha="different")
    row = next(r for r in build_rows(_payload(), mismatched) if r["tau_task_id"] == "task_001")
    assert row["arm_sha_ok"] is False

    dirty = _context(arm_dirty=True)
    row = next(r for r in build_rows(_payload(), dirty) if r["tau_task_id"] == "task_001")
    assert row["arm_sha_ok"] is False


def test_local_rows_carry_session_ref_but_no_conversation_identity():
    rows = build_rows(_payload(), _context(transport="local", accounting={}))
    row = next(r for r in rows if r["tau_task_id"] == "task_001")
    assert row["introspection_task_id"] is None
    assert row["pi_session_ref"] == "conv-aaa"
    assert row["arm_sha_ok"] is None


def test_manifest_round_trips_as_strict_jsonl(tmp_path):
    rows = build_rows(_payload(), _context())
    path = write_manifest(tmp_path, rows)
    # NaN user_cost must have been cleaned: strict parsers reject bare NaN tokens.
    for line in path.read_text(encoding="utf-8").splitlines():
        json.loads(line)
    read_back = read_manifest(tmp_path)
    assert [r["tau_task_id"] for r in read_back] == ["task_001", "task_002"]
    assert read_back[0]["user_cost"] is None


def test_incident_sink_counts_and_reports():
    sink = EpisodeIncidents()
    assert not sink.any()
    sink.count_stall()
    sink.prompt_409 += 1
    assert sink.any()
    assert sink.as_dict()["stall_warnings"] == 1
    assert sink.as_dict()["prompt_409"] == 1


def test_sandbox_tool_failures_counts_what_only_the_conversation_shows():
    """A call the sandbox's MCP daemon answers itself never reaches the bridge.

    τ records no turn for it, the bridge refuses nothing (it received nothing), and the
    episode ends normally — so without reading the platform conversation the round reports
    itself healthy while the agent was denied its tools. These counters are the detector.
    """
    from tau_adapter.run import _sandbox_tool_failures

    items = [
        {
            "attributes": {
                "gen_ai": {"operation": {"name": "execute_tool"}},
                "error": {"type": "tool_error"},
            }
        },
        {
            "attributes": {"gen_ai": {"operation": {"name": "execute_tool"}}},
            "response": "MCP daemon: Error POSTing to endpoint: "
            '{"detail":"local MCP \'tau\' is disconnected"}',
        },
        {"attributes": {"gen_ai": {"operation": {"name": "chat"}}}},
    ]
    items.append(
        {"response": 'MCP daemon: Error POSTing to endpoint: {"detail":"mcp upstream timed out"}'}
    )
    counts = _sandbox_tool_failures(items)
    assert counts["sandbox_tool_errors"] == 1
    # The two classes are counted apart: unreachable bridge vs bridge that answered too late.
    # They mean opposite things and are fixed in different places, so lumping them would
    # have hidden exactly the regression that motivated this detector.
    assert counts["sandbox_seam_disconnects"] == 1
    assert counts["sandbox_seam_timeouts"] == 1

    # A healthy conversation must score zero on all three, or the signal is noise.
    healthy = [{"attributes": {"gen_ai": {"operation": {"name": "execute_tool"}}}}] * 5
    assert _sandbox_tool_failures(healthy) == {
        "sandbox_tool_errors": 0,
        "sandbox_seam_disconnects": 0,
        "sandbox_seam_timeouts": 0,
    }
