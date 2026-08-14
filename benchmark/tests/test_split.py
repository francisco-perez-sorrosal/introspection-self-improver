"""Partition proposal and verification: determinism, stratification, frozen-manifest checks.

Synthetic rows only — the vendored checkout is gitignored, so nothing here may read it.
The synthetic population mirrors the locked domain's shape (88 DB / 9 ACTION tasks) because
the proportional ACTION floors depend on that shape.
"""

from __future__ import annotations

import pytest
import yaml

from tau_adapter.split import (
    HELD_OUT,
    MANIFEST_VERSION,
    TaskRow,
    _dominant_category,
    _label_sequence,
    exclude_rows,
    partition_sizes,
    propose,
    render_manifest,
    verify,
)

_CATEGORIES = ["credit_cards", "bank_accounts", "checking_accounts", "savings_accounts"]

#: The protocol's default full experiment: (5*10)+47 = 97, the whole pool.
FULL = partition_sizes(5, 10, 47)
#: The protocol's debug configuration: (3*3)+5 = 14 of 97.
DEBUG = partition_sizes(3, 3, 5)


def _rows(n_db: int = 88, n_action: int = 9) -> list[TaskRow]:
    rows = [
        TaskRow(f"task_{i:03d}", ("DB",), _CATEGORIES[i % 4], 1 + (i % 30)) for i in range(n_db)
    ]
    rows += [
        TaskRow(f"task_{900 + j}", ("ACTION",), _CATEGORIES[j % 2], 2 + j) for j in range(n_action)
    ]
    return rows


def _action_ids(rows: list[TaskRow]) -> set[str]:
    return {row.task_id for row in rows if row.reward_basis == ("ACTION",)}


def _manifest(assignment: dict[str, list[str]]) -> dict:
    return {
        "version": MANIFEST_VERSION,
        "domain": "banking_knowledge",
        "batches": {name: ids for name, ids in assignment.items() if name != HELD_OUT},
        HELD_OUT: assignment[HELD_OUT],
    }


def _move_action_tasks(
    assignment: dict[str, list[str]], rows: list[TaskRow], into: str
) -> dict[str, list[str]]:
    """Swap every ACTION task outside ``into`` with a DB task inside it, sizes preserved."""
    action = _action_ids(rows)
    moved = {name: set(ids) for name, ids in assignment.items()}
    db_inside = sorted(moved[into] - action)
    for name, ids in moved.items():
        if name == into:
            continue
        for task_id in sorted(ids & action):
            swap = db_inside.pop()
            ids.discard(task_id)
            ids.add(swap)
            moved[into].discard(swap)
            moved[into].add(task_id)
    return {name: sorted(ids) for name, ids in moved.items()}


def test_dominant_category_takes_two_tokens_after_doc_prefix():
    docs = ["doc_credit_cards_gold_001", "doc_credit_cards_silver_001", "doc_bank_accounts_a_1"]
    assert _dominant_category(docs) == "credit_cards"
    assert _dominant_category([]) == "none"


def test_partition_sizes_names_batches_and_held_out():
    assert DEBUG == {"batch_01": 3, "batch_02": 3, "batch_03": 3, HELD_OUT: 5}


def test_label_sequence_counts_match_quotas():
    sequence = _label_sequence(97, FULL)
    assert len(sequence) == 97
    for name, quota in FULL.items():
        assert sequence.count(name) == quota
    assert sequence.count("unused") == 97 - sum(FULL.values())


def test_label_sequence_spreads_labels_over_contiguous_strata():
    sequence = _label_sequence(97, FULL)
    for start in range(len(sequence) - 8):
        window = set(sequence[start : start + 9])
        assert len(window) >= 2, f"window at {start} is a single label"


def test_propose_sizes_disjoint_and_deterministic():
    rows = _rows()
    first = propose(rows, FULL, seed=7)
    second = propose(rows, FULL, seed=7)
    assert first == second
    all_ids: list[str] = []
    for name, quota in FULL.items():
        assert len(first[name]) == quota
        all_ids.extend(first[name])
    assert len(all_ids) == len(set(all_ids))


def test_excluded_tasks_never_enter_any_partition():
    rows = _rows()
    survivors = exclude_rows(rows, ["task_000", "task_901"])
    assert len(survivors) == len(rows) - 2
    assignment = propose(survivors, DEBUG)
    assigned = {task_id for ids in assignment.values() for task_id in ids}
    assert "task_000" not in assigned and "task_901" not in assigned


def test_excluding_an_unknown_task_id_is_refused():
    with pytest.raises(ValueError, match="task_999"):
        exclude_rows(_rows(), ["task_999"])


def test_propose_enforces_the_task_budget():
    with pytest.raises(ValueError, match=r"\(G\*B\)\+T"):
        propose(_rows(), partition_sizes(5, 10, 48))


def test_propose_gives_each_side_its_action_share():
    # 9 ACTION tasks over 97: held-out's share is ⌊9*47/97⌋ = 4, the batches' joint
    # share ⌊9*50/97⌋ = 4.
    rows = _rows()
    assignment = propose(rows, FULL)
    action = _action_ids(rows)
    held = len(action & set(assignment[HELD_OUT]))
    batched = sum(len(action & set(ids)) for name, ids in assignment.items() if name != HELD_OUT)
    assert held >= 4
    assert batched >= 4
    assert held + batched == 9


def test_debug_partition_proposes_and_verifies():
    rows = _rows()
    assignment = propose(rows, DEBUG)
    assert sum(len(ids) for ids in assignment.values()) == 14
    assert verify(_manifest(assignment), rows, "banking_knowledge", DEBUG) == []


def test_verify_accepts_a_full_proposal():
    rows = _rows()
    assert verify(_manifest(propose(rows, FULL)), rows, "banking_knowledge", FULL) == []


def test_verify_flags_domain_mismatch_empty_and_unknown():
    rows = _rows()
    manifest = _manifest(propose(rows, FULL))
    manifest["domain"] = "mock"
    manifest["batches"]["batch_02"] = []
    manifest[HELD_OUT] = [*manifest[HELD_OUT][:-1], "task_nonexistent"]
    problems = "\n".join(verify(manifest, rows, "banking_knowledge", FULL))
    assert "domain" in problems
    assert "batch_02 is empty" in problems
    assert "unknown tasks" in problems


def test_verify_flags_overlap_and_size():
    rows = _rows()
    manifest = _manifest(propose(rows, FULL))
    manifest[HELD_OUT] = [*manifest[HELD_OUT][:-1], manifest["batches"]["batch_01"][0]]
    problems = "\n".join(verify(manifest, rows, "banking_knowledge", FULL))
    assert "appears in multiple partitions" in problems

    short = _manifest(propose(rows, FULL))
    short["batches"]["batch_03"] = short["batches"]["batch_03"][:-2]
    problems = "\n".join(verify(short, rows, "banking_knowledge", FULL))
    assert "holds 8 ids, expected 10" in problems


def test_verify_flags_a_batch_set_disagreeing_with_the_config():
    rows = _rows()
    manifest = _manifest(propose(rows, DEBUG))
    problems = "\n".join(verify(manifest, rows, "banking_knowledge", FULL))
    assert "expects [batch_01, batch_02, batch_03, batch_04, batch_05]" in problems


def test_verify_flags_a_config_exceeding_the_pool():
    rows = _rows()
    manifest = _manifest(propose(rows, FULL))
    oversized = partition_sizes(5, 10, 48)
    problems = "\n".join(verify(manifest, rows, "banking_knowledge", oversized))
    assert "(G*B)+T = 98 exceeds the 97 available tasks" in problems


def test_verify_flags_held_out_stripped_of_action():
    rows = _rows()
    concentrated = _move_action_tasks(propose(rows, FULL), rows, into="batch_01")
    problems = "\n".join(verify(_manifest(concentrated), rows, "banking_knowledge", FULL))
    assert "held_out holds 0 ACTION-basis tasks" in problems


def test_verify_flags_batches_stripped_of_action():
    rows = _rows()
    concentrated = _move_action_tasks(propose(rows, FULL), rows, into=HELD_OUT)
    problems = "\n".join(verify(_manifest(concentrated), rows, "banking_knowledge", FULL))
    assert "batches jointly hold 0 ACTION-basis tasks" in problems


def test_verify_refuses_the_legacy_three_way_manifest():
    # The committed manifest of closed experiment 001 must never verify as a partition —
    # loudly, and before any other check confuses the matter.
    rows = _rows()
    legacy = {
        "version": 1,
        "domain": "banking_knowledge",
        "discovery": ["task_001"],
        "validation": ["task_002"],
        "test": ["task_003"],
    }
    problems = verify(legacy, rows, "banking_knowledge", FULL)
    assert len(problems) == 1
    assert "retired three-way split" in problems[0]
    versioned_only = {"version": 1, "domain": "banking_knowledge"}
    assert "retired three-way split" in verify(versioned_only, rows, "banking_knowledge", FULL)[0]


def test_render_manifest_round_trips_through_yaml():
    rows = _rows()
    assignment = propose(rows, DEBUG)
    rendered = render_manifest(assignment, "banking_knowledge", "base", seed=7, note="note line")
    parsed = yaml.safe_load(rendered)
    assert parsed["version"] == MANIFEST_VERSION
    assert parsed["domain"] == "banking_knowledge"
    assert parsed["task_split_name"] == "base"
    assert parsed["batches"] == {name: ids for name, ids in assignment.items() if name != HELD_OUT}
    assert parsed[HELD_OUT] == assignment[HELD_OUT]
    assert "# note line" in rendered


def test_rendered_manifest_verifies_as_written():
    rows = _rows()
    rendered = render_manifest(propose(rows, FULL), "banking_knowledge", "base", seed=7)
    assert verify(yaml.safe_load(rendered), rows, "banking_knowledge", FULL) == []
