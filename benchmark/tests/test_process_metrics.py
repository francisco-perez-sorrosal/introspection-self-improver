"""Process metrics derived from revealed grading records: counting rules and CSVs.

The metrics are diagnostic descriptive statistics beside the progression curve; the
tests pin the counting rules that make them trustworthy — the DB denominator excludes
non-DB-basis tasks, the discoverable-op counter measures the agent-side surface (never
the simulated user's own calls), and carried generations simply have no rows.
"""

from __future__ import annotations

import csv
import io
import json

from tau_adapter import process_metrics as pm


def _payload() -> dict:
    return {
        "tasks": [
            {"id": "task_a", "evaluation_criteria": {"reward_basis": ["DB"]}},
            {"id": "task_b", "evaluation_criteria": {"reward_basis": ["ACTION"]}},
        ],
        "simulations": [
            {
                "task_id": "task_a",
                "duration": 120.0,
                "agent_cost": 0.2,
                "user_cost": 0.1,
                "reward_info": {
                    "reward": 1.0,
                    "db_check": {"db_match": True, "db_reward": 1.0},
                    "action_checks": [
                        {"action_match": True, "action_reward": 1.0, "tool_type": "write"},
                        {"action_match": False, "action_reward": 0.0, "tool_type": "write"},
                        {"action_match": True, "action_reward": 1.0, "tool_type": "read"},
                    ],
                },
                "messages": [
                    {"role": "assistant", "tool_calls": [{"name": "KB_search"}]},
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {"name": "unlock_discoverable_agent_tool"},
                            {"name": "call_discoverable_agent_tool"},
                        ],
                    },
                    # The simulated user's own tool call: never a harness signal.
                    {"role": "user", "tool_calls": [{"name": "call_discoverable_user_tool"}]},
                    {"role": "assistant", "tool_calls": [{"name": "transfer_to_human_agents"}]},
                ],
            },
            {
                "task_id": "task_b",
                "duration": 60.0,
                "agent_cost": 0.1,
                "user_cost": 0.0,
                "reward_info": {
                    "reward": 0.0,
                    # db_check present but ACTION-basis: must not enter the DB aggregate.
                    "db_check": {"db_match": True, "db_reward": 1.0},
                    "action_checks": [
                        {"action_match": False, "action_reward": 0.5, "tool_type": "write"},
                    ],
                },
                "messages": [
                    {"role": "assistant", "tool_calls": [{"name": "KB_search"}]},
                    {"role": "assistant", "tool_calls": [{"name": "KB_search"}]},
                ],
            },
        ],
    }


def test_task_rows_pin_the_counting_rules():
    rows = pm.derive_task_rows(_payload(), "generation_000")
    by_id = {row["task_id"]: row for row in rows}
    a, b = by_id["task_a"], by_id["task_b"]
    assert a["passed"] is True and a["db_match"] is True
    assert a["actions_matched"] == 2 and a["actions_total"] == 3
    assert a["writes_matched"] == 1 and a["writes_total"] == 2
    assert a["kb_search_calls"] == 1
    assert a["discoverable_ops"] == 2  # the user's own call is not counted
    assert a["transfers"] == 1
    assert a["messages"] == 4
    assert abs(a["cost_usd"] - 0.3) < 1e-9
    assert b["db_match"] is None  # ACTION basis: excluded from the DB aggregate
    assert b["partial_action_reward"] == 0.5


def test_generation_aggregate_math():
    rows = pm.derive_task_rows(_payload(), "generation_000")
    agg = pm.aggregate_generation(rows)
    assert agg["tasks"] == 2 and agg["passed"] == 1
    assert agg["db_matched"] == 1 and agg["db_basis_tasks"] == 1
    assert agg["actions_matched"] == 2 and agg["actions_total"] == 4
    assert abs(agg["action_match_pct"] - 50.0) < 1e-9
    assert agg["writes_matched"] == 1 and agg["writes_total"] == 3
    assert agg["kb_search_calls"] == 3
    assert agg["transfers"] == 1
    # mean of per-task partial rewards: (2/3 + 0.5) / 2
    assert abs(agg["partial_action_reward_pct"] - 100 * (2 / 3 + 0.5) / 2) < 1e-6


def test_derivation_walks_only_measured_generations(tmp_path):
    held = tmp_path / "held_out"
    for gen in ("generation_000", "generation_002"):  # 001 carried: no directory
        graded = held / gen / "graded"
        graded.mkdir(parents=True)
        (graded / "updated_results.json").write_text(json.dumps(_payload()), encoding="utf-8")
    written = pm.write_process_metrics(held)
    assert all(path.exists() for path in written)
    with (held / pm.PROCESS_BY_GENERATION_CSV).open(newline="") as handle:
        gens = [row["generation"] for row in csv.DictReader(handle)]
    assert gens == ["generation_000", "generation_002"]
    with (held / pm.PROCESS_BY_TASK_CSV).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert {row["generation"] for row in rows} == {"generation_000", "generation_002"}
    # ACTION-basis rows leave db_match empty rather than false.
    assert [r["db_match"] for r in rows if r["task_id"] == "task_b"] == ["", ""]


def test_csvs_are_reparseable_numbers():
    rows = pm.derive_task_rows(_payload(), "generation_000")
    text = pm.by_generation_csv([pm.aggregate_generation(rows)])
    parsed = next(csv.DictReader(io.StringIO(text)))
    assert float(parsed["action_match_pct"]) == 50.0
    assert int(parsed["kb_search_calls"]) == 3


# ----------------------------------------- batch rounds + lock-sourced tool classes (D25)


def _graded_payload(tool_name: str) -> dict:
    return {
        "tasks": [{"id": "task_x", "evaluation_criteria": {"reward_basis": ["DB"]}}],
        "simulations": [
            {
                "task_id": "task_x",
                "reward_info": {"reward": 0.0, "action_checks": [], "db_check": {}},
                "messages": [
                    {"role": "assistant", "tool_calls": [{"name": tool_name}]},
                ],
            }
        ],
    }


def test_batch_rounds_derive_under_any_mode(tmp_path):
    import json as jsonmod

    round_dir = tmp_path / "generation_000" / "batch_01" / "graded"
    round_dir.mkdir(parents=True)
    (round_dir / "updated_results.json").write_text(
        jsonmod.dumps(_graded_payload("KB_search")), encoding="utf-8"
    )
    task_rows, round_rows = pm.derive_from_batch_rounds(tmp_path)
    assert [r["generation"] for r in round_rows] == ["batch_01"]
    assert task_rows[0]["kb_search_calls"] == 1
    paths = pm.write_batch_process_metrics(tmp_path)
    assert all(p.exists() for p in paths)


def test_tool_classes_come_from_the_lock_operational_block():
    from tau_adapter.lock import Lock

    lock = Lock(
        raw={
            "operational": {
                "process_metric_tools": {
                    "search": "find_docs",
                    "transfer": "escalate",
                    "discoverable": ["unlock_thing"],
                }
            }
        }
    )
    classes = pm.tool_classes_from_lock(lock)
    assert classes.search == "find_docs"
    assert classes.transfer == "escalate"
    assert classes.discoverable == frozenset({"unlock_thing"})
    rows = pm.derive_task_rows(_graded_payload("escalate"), "batch_01", classes)
    assert rows[0]["transfers"] == 1
    assert rows[0]["kb_search_calls"] == 0


def test_tool_classes_default_when_lock_has_no_block():
    from tau_adapter.lock import Lock

    classes = pm.tool_classes_from_lock(Lock(raw={}))
    assert classes == pm.DEFAULT_TOOL_CLASSES
