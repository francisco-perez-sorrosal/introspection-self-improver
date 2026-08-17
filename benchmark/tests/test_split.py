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


# ---------------------------------------------------------------- fixed batch mode


#: Fixed-mode sizes: G+1 batch rounds (the extra one is H_G's endpoint measurement).
FIXED = partition_sizes(5, 8, 28, "fixed")


def _fixed_manifest(batch_ids=None, held_ids=None) -> dict:
    rows = _rows()
    batch_ids = batch_ids or sorted(r.task_id for r in rows[:8])
    # 26 DB + 2 ACTION rows: the held-out side must hold its proportional ACTION share
    # (floor = 9 * 28 // 97 = 2), exactly as a real frozen manifest must.
    held_ids = held_ids or sorted(r.task_id for r in rows[10:36]) + sorted(
        r.task_id for r in rows[-2:]
    )
    return {
        "version": MANIFEST_VERSION,
        "domain": "banking_knowledge",
        "batch_mode": "fixed",
        "batches": {name: list(batch_ids) for name in FIXED if name != HELD_OUT},
        HELD_OUT: list(held_ids),
    }


def test_fixed_sizes_add_the_endpoint_batch_round() -> None:
    names = sorted(name for name in FIXED if name != HELD_OUT)
    assert names == [f"batch_{n:02d}" for n in range(1, 7)]
    assert all(FIXED[name] == 8 for name in names)


def test_fixed_manifest_with_identical_batches_verifies() -> None:
    rows = _rows()
    assert verify(_fixed_manifest(), rows, "banking_knowledge", FIXED, "fixed") == []


def test_fixed_mode_flags_batches_that_differ() -> None:
    rows = _rows()
    manifest = _fixed_manifest()
    manifest["batches"]["batch_03"] = list(manifest["batches"]["batch_03"])
    manifest["batches"]["batch_03"][0] = rows[40].task_id
    problems = verify(manifest, rows, "banking_knowledge", FIXED, "fixed")
    assert any("batch_03 differs" in problem for problem in problems)


def test_fixed_mode_still_enforces_batch_held_out_disjointness() -> None:
    rows = _rows()
    held = sorted(r.task_id for r in rows[10:38])
    batch = sorted(r.task_id for r in rows[:7]) + [held[0]]
    manifest = _fixed_manifest(batch_ids=batch)
    problems = verify(manifest, rows, "banking_knowledge", FIXED, "fixed")
    assert any("multiple partitions" in problem for problem in problems)


def test_fixed_mode_budget_counts_distinct_tasks_not_rounds() -> None:
    """B+T = 36 distinct tasks must fit a 40-task pool even though 6 rounds x 8 = 48."""
    rows = _rows(n_db=36, n_action=4)
    manifest = {
        "version": MANIFEST_VERSION,
        "domain": "banking_knowledge",
        "batch_mode": "fixed",
        "batches": {
            name: sorted(r.task_id for r in rows[:8]) for name in FIXED if name != HELD_OUT
        },
        HELD_OUT: sorted(r.task_id for r in rows[8:36]),
    }
    problems = verify(manifest, rows, "banking_knowledge", FIXED, "fixed")
    assert not any("exceeds" in problem for problem in problems)


def test_manifest_mode_must_agree_with_the_lock() -> None:
    rows = _rows()
    manifest = _fixed_manifest()
    manifest["batch_mode"] = "fresh"
    problems = verify(manifest, rows, "banking_knowledge", FIXED, "fixed")
    assert any("batch_mode" in problem for problem in problems)


def test_explicit_assignment_replicates_the_batch_list() -> None:
    from tau_adapter.split import explicit_assignment

    assignment = explicit_assignment(["task_002", "task_001"], ["task_010"], FIXED)
    batch_names = [name for name in FIXED if name != HELD_OUT]
    assert all(assignment[name] == ["task_001", "task_002"] for name in batch_names)
    assert assignment[HELD_OUT] == ["task_010"]


def test_fixed_rendered_manifest_verifies_as_written() -> None:
    from tau_adapter.split import explicit_assignment

    rows = _rows()
    assignment = explicit_assignment(
        [r.task_id for r in rows[:8]],
        [r.task_id for r in rows[10:36]] + [r.task_id for r in rows[-2:]],
        FIXED,
    )
    rendered = render_manifest(
        assignment, "banking_knowledge", "base", 1, "fixed-mode test", "fixed"
    )
    manifest = yaml.safe_load(rendered)
    assert manifest["batch_mode"] == "fixed"
    assert verify(manifest, rows, "banking_knowledge", FIXED, "fixed") == []



def _strata_for(batch_ids: list[str]) -> dict[str, str]:
    """2 anchors + 3 marginals + 3 headroom over an 8-task fixed batch, in id order."""
    tiers = ["anchor"] * 2 + ["marginal"] * 3 + ["headroom"] * 3
    return dict(zip(sorted(batch_ids), tiers, strict=True))


def test_fixed_manifest_with_complete_strata_verifies() -> None:
    manifest = _fixed_manifest()
    batch_ids = manifest["batches"]["batch_01"]
    manifest["strata"] = _strata_for(batch_ids)
    manifest["walled"] = [t for t, s in manifest["strata"].items() if s == "headroom"][:1]
    assert verify(manifest, _rows(), "banking_knowledge", FIXED, "fixed") == []


def test_strata_flag_missing_extra_and_bad_values() -> None:
    manifest = _fixed_manifest()
    batch_ids = manifest["batches"]["batch_01"]
    strata = _strata_for(batch_ids)
    dropped = sorted(strata)[0]
    del strata[dropped]
    strata["task_999"] = "anchor"
    strata[sorted(strata)[1]] = "bedrock"
    manifest["strata"] = strata
    problems = "\n".join(verify(manifest, _rows(), "banking_knowledge", FIXED, "fixed"))
    assert f"missing a stratum: {dropped}" in problems
    assert "non-batch tasks: task_999" in problems
    assert "must be one of anchor/marginal/headroom" in problems


def test_walled_must_be_headroom_batch_tasks() -> None:
    manifest = _fixed_manifest()
    batch_ids = manifest["batches"]["batch_01"]
    manifest["strata"] = _strata_for(batch_ids)
    anchor = next(t for t, s in manifest["strata"].items() if s == "anchor")
    manifest["walled"] = [anchor]
    problems = "\n".join(verify(manifest, _rows(), "banking_knowledge", FIXED, "fixed"))
    assert "walled tasks must be headroom" in problems


def test_walled_without_strata_is_flagged() -> None:
    manifest = _fixed_manifest()
    manifest["walled"] = ["task_001"]
    problems = "\n".join(verify(manifest, _rows(), "banking_knowledge", FIXED, "fixed"))
    assert "no strata mapping" in problems


def test_strata_on_a_fresh_manifest_are_flagged() -> None:
    rows = _rows()
    assignment = propose(rows, DEBUG)
    manifest = _manifest(assignment)
    manifest["strata"] = {assignment["batch_01"][0]: "anchor"}
    problems = "\n".join(verify(manifest, rows, "banking_knowledge", DEBUG, "fresh"))
    assert "strata describe a fixed batch" in problems


def test_render_manifest_with_strata_round_trips() -> None:
    from tau_adapter.split import explicit_assignment

    rows = _rows()
    batch_ids = [r.task_id for r in rows[:8]]
    held_ids = [r.task_id for r in rows[10:36]] + [r.task_id for r in rows[-2:]]
    strata = _strata_for(batch_ids)
    walled = [t for t, s in strata.items() if s == "headroom"][:2]
    rendered = render_manifest(
        explicit_assignment(batch_ids, held_ids, FIXED),
        "banking_knowledge",
        "base",
        1,
        "strata round-trip",
        "fixed",
        strata=strata,
        walled=walled,
    )
    manifest = yaml.safe_load(rendered)
    assert manifest["strata"] == strata
    assert manifest["walled"] == sorted(walled)
    assert verify(manifest, rows, "banking_knowledge", FIXED, "fixed") == []
