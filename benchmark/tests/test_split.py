"""Split proposal and verification: determinism, stratification, frozen-manifest checks.

Synthetic rows only — the vendored checkout is gitignored, so nothing here may read it.
The synthetic population mirrors the locked domain's shape (88 DB / 9 ACTION tasks) because
the ACTION-spread guarantee is the one property that depends on that shape.
"""

from __future__ import annotations

import yaml

from tau_adapter.split import (
    SPLIT_SIZES,
    TaskRow,
    _dominant_category,
    _label_sequence,
    fidelity_task_set,
    propose,
    render_manifest,
    verify,
)

_CATEGORIES = ["credit_cards", "bank_accounts", "checking_accounts", "savings_accounts"]


def _rows(n_db: int = 88, n_action: int = 9) -> list[TaskRow]:
    rows = [
        TaskRow(f"task_{i:03d}", ("DB",), _CATEGORIES[i % 4], 1 + (i % 30)) for i in range(n_db)
    ]
    rows += [
        TaskRow(f"task_{900 + j}", ("ACTION",), _CATEGORIES[j % 2], 2 + j) for j in range(n_action)
    ]
    return rows


def _manifest(assignment: dict[str, list[str]]) -> dict:
    return {"domain": "banking_knowledge", **assignment}


def test_dominant_category_takes_two_tokens_after_doc_prefix():
    docs = ["doc_credit_cards_gold_001", "doc_credit_cards_silver_001", "doc_bank_accounts_a_1"]
    assert _dominant_category(docs) == "credit_cards"
    assert _dominant_category([]) == "none"


def test_label_sequence_counts_match_quotas():
    sequence = _label_sequence(97, SPLIT_SIZES)
    assert len(sequence) == 97
    for name, quota in SPLIT_SIZES.items():
        assert sequence.count(name) == quota
    assert sequence.count("unused") == 97 - sum(SPLIT_SIZES.values())


def test_label_sequence_spreads_labels_over_contiguous_strata():
    sequence = _label_sequence(97, SPLIT_SIZES)
    for start in range(len(sequence) - 8):
        window = set(sequence[start : start + 9])
        assert len(window) >= 2, f"window at {start} is a single label"


def test_propose_sizes_disjoint_and_deterministic():
    rows = _rows()
    first = propose(rows, seed=7)
    second = propose(rows, seed=7)
    assert first == second
    all_ids: list[str] = []
    for name, quota in SPLIT_SIZES.items():
        assert len(first[name]) == quota
        all_ids.extend(first[name])
    assert len(all_ids) == len(set(all_ids))


def test_propose_spreads_action_tasks_across_splits():
    rows = _rows()
    assignment = propose(rows)
    action_ids = {row.task_id for row in rows if row.reward_basis == ("ACTION",)}
    holding = [name for name, ids in assignment.items() if action_ids & set(ids)]
    assert len(holding) >= 2


def test_verify_accepts_a_proposal():
    rows = _rows()
    assert verify(_manifest(propose(rows)), rows, "banking_knowledge") == []


def test_verify_flags_domain_mismatch_empty_and_unknown():
    rows = _rows()
    manifest = _manifest(propose(rows))
    manifest["domain"] = "mock"
    manifest["validation"] = []
    manifest["test"] = manifest["test"][:-1] + ["task_nonexistent"]
    problems = "\n".join(verify(manifest, rows, "banking_knowledge"))
    assert "domain" in problems
    assert "validation is empty" in problems
    assert "unknown tasks" in problems


def test_verify_flags_overlap_and_size():
    rows = _rows()
    manifest = _manifest(propose(rows))
    manifest["validation"] = manifest["validation"][:-1] + [manifest["discovery"][0]]
    problems = "\n".join(verify(manifest, rows, "banking_knowledge"))
    assert "overlap" in problems

    short = _manifest(propose(rows))
    short["discovery"] = short["discovery"][:-2]
    problems = "\n".join(verify(short, rows, "banking_knowledge"))
    assert "expected 30" in problems


def test_verify_flags_action_concentration():
    rows = _rows()
    assignment = propose(rows)
    action_ids = {row.task_id for row in rows if row.reward_basis == ("ACTION",)}
    stripped = {
        name: [task_id for task_id in ids if task_id not in action_ids]
        for name, ids in assignment.items()
    }
    # Rebuild to the expected sizes with every ACTION task concentrated in discovery.
    db_pool = [
        row.task_id
        for row in rows
        if row.task_id not in action_ids
        and all(row.task_id not in ids for ids in stripped.values())
    ]
    concentrated = {}
    for name, quota in SPLIT_SIZES.items():
        ids = list(stripped[name])
        if name == "discovery":
            ids = (ids + sorted(action_ids))[:quota]
        while len(ids) < quota:
            ids.append(db_pool.pop())
        concentrated[name] = ids
    problems = "\n".join(verify(_manifest(concentrated), rows, "banking_knowledge"))
    assert "ACTION" in problems


def test_fidelity_task_set_is_deterministic_and_covers_both_bases():
    rows = _rows()
    manifest = _manifest(propose(rows))
    chosen = fidelity_task_set(manifest, rows)
    assert chosen == fidelity_task_set(manifest, rows)
    assert len(chosen) == 3
    basis = {row.task_id: row.reward_basis for row in rows}
    assert sum(1 for t in chosen if basis[t] == ("ACTION",)) == 1
    assert all(t in manifest["discovery"] for t in chosen)


def test_fidelity_task_set_degrades_without_action_tasks():
    rows = _rows(n_action=0)
    manifest = {"domain": "banking_knowledge", **propose(rows)}
    chosen = fidelity_task_set(manifest, rows)
    assert len(chosen) == 3  # all DB — still a valid gate set, just single-basis


def test_render_manifest_round_trips_through_yaml():
    rows = _rows()
    assignment = propose(rows)
    rendered = render_manifest(assignment, "banking_knowledge", "base", seed=7, note="note line")
    parsed = yaml.safe_load(rendered)
    assert parsed["domain"] == "banking_knowledge"
    assert parsed["task_split_name"] == "base"
    for name in SPLIT_SIZES:
        assert parsed[name] == assignment[name]
    assert "# note line" in rendered
