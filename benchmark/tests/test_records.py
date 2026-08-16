"""Improvement-record validation: the schema contract plus the D5 rules.

The committed schema file is loaded once and reused — these tests hold records to the
real contract, not to a fixture copy that could drift from it.
"""

from __future__ import annotations

import pytest
import yaml

from tau_adapter import records
from tau_adapter.lock import Lock

SCHEMA = records.load_schema()


def _lock() -> Lock:
    return Lock(raw={"experiment": {"seq": 2, "name": "exp-b"}})


def _record(**overrides) -> dict:
    base = {
        "transition": {"from_generation": 0, "to_generation": 1},
        "experiment": "002_exp-b",
        "outcome": "accepted",
        "batch": {"name": "batch_01", "task_ids": ["task_001", "task_002"]},
        "evidence": {"conversation_ids": ["conv_abc"], "summary": "read the tool calls"},
        "signals": [{"description": "query never reformulated", "prevalence": "2/3"}],
        "counterevidence": "none found",
        "hypothesis": "reformulating on empty KB hits recovers the document",
        "owning_layer": "retrieval usage (system prompt)",
        "proposed_change": "add a reformulate-once instruction",
        "mutation": {
            "branch": "gen-001/reformulate",
            "pr_url": "https://example.com/pr/1",
            "source_commit": "aaa111",
            "candidate_commit": "bbb222",
        },
        "expected_effect": "fewer empty retrievals on doc-lookup tasks",
        "human_approval": {"approved_by": "user", "date": "2026-08-13"},
        "held_out_result": None,
    }
    base.update(overrides)
    return base


def _problems(record: dict, filename: str | None = None, revealed: bool = False) -> str:
    return "\n".join(records.validate(record, filename=filename, revealed=revealed, schema=SCHEMA))


def test_a_complete_accepted_record_holds():
    assert _problems(_record(), filename="gen_000_to_001.yaml") == ""


def test_missing_required_fields_are_named():
    record = _record()
    del record["hypothesis"], record["evidence"]
    problems = _problems(record)
    assert "missing required field: hypothesis" in problems
    assert "missing required field: evidence" in problems


def test_unknown_fields_are_refused():
    assert "unknown fields: reward" in _problems(_record(reward=1.0))


def test_unknown_outcome_is_refused():
    assert "not one of" in _problems(_record(outcome="maybe"))


def test_transition_must_advance_exactly_one_generation():
    record = _record(transition={"from_generation": 0, "to_generation": 2})
    assert "must advance exactly one generation" in _problems(record)


def test_filename_must_match_the_transition():
    assert "does not match transition" in _problems(_record(), filename="gen_001_to_002.yaml")


def test_accepted_requires_a_distinct_candidate_commit():
    same = _record()
    same["mutation"]["candidate_commit"] = same["mutation"]["source_commit"]
    assert "distinct from" in _problems(same)
    missing = _record()
    missing["mutation"]["candidate_commit"] = None
    assert "distinct from" in _problems(missing)


@pytest.mark.parametrize("outcome", ["rejected", "identity"])
def test_non_accepted_outcomes_pin_the_generation(outcome):
    # H_(g+1) = H_g (D5): a rejected or identity transition cannot smuggle in a new commit.
    record = _record(outcome=outcome)
    assert "pins the next generation" in _problems(record)
    record["mutation"]["candidate_commit"] = None
    assert _problems(record, filename="gen_000_to_001.yaml") == ""


def test_scaffold_todo_placeholders_are_refused():
    assert "TODO placeholder" in _problems(_record(hypothesis="TODO"))


def test_placeholder_conversation_ids_are_refused():
    record = _record(
        evidence={"conversation_ids": ["TODO: conv_..."], "summary": "read the tool calls"}
    )
    assert "TODO placeholder" in _problems(record)


def test_every_record_cites_at_least_one_conversation():
    record = _record(evidence={"conversation_ids": [], "summary": "s"})
    assert "cites the executions" in _problems(record)


def test_prose_may_be_terse_only_for_identity():
    identity = _record(outcome="identity", hypothesis="", proposed_change="")
    identity["mutation"]["candidate_commit"] = None
    assert _problems(identity, filename="gen_000_to_001.yaml") == ""
    rejected = _record(outcome="rejected", hypothesis="")
    rejected["mutation"]["candidate_commit"] = None
    assert "hypothesis must not be empty" in _problems(rejected)


def test_held_out_result_stays_empty_until_reveal():
    filled = _record(held_out_result={"passed": 3, "total": 5})
    assert "written by `make reveal`" in _problems(filled)
    assert _problems(filled, revealed=True, filename="gen_000_to_001.yaml") == ""


def test_scaffold_round_trips_and_names_its_own_gaps():
    text = records.scaffold(
        _lock(),
        from_generation=0,
        batch_name="batch_01",
        batch_task_ids=["task_001"],
        source_commit="aaa111",
        date="2026-08-13",
    )
    parsed = yaml.safe_load(text)
    assert parsed["experiment"] == "002_exp-b"
    assert parsed["batch"] == {"name": "batch_01", "task_ids": ["task_001"]}
    assert parsed["mutation"]["source_commit"] == "aaa111"
    assert parsed["held_out_result"] is None
    # The scaffold is deliberately not yet valid: the TODOs are the work.
    assert "TODO" in text
    assert records.validate(parsed, schema=SCHEMA)


def test_record_name_is_zero_padded():
    assert records.record_name(0) == "gen_000_to_001.yaml"
    assert records.record_name(4) == "gen_004_to_005.yaml"


def test_record_evidence_must_come_from_this_experiments_own_rounds(tmp_path, monkeypatch):
    """Experiments are isolated: a record may not cite another experiment's conversation.

    The failure this prevents is silent — an id borrowed from a prior experiment looks
    exactly like a real one, and nothing downstream ever resolves it. A prior experiment is
    legitimate context in prose, never a cited execution.
    """
    from tau_adapter import records

    manifest_dir = tmp_path / "results" / "experiment_009_x" / "generation_000" / "batch_01"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "episode_manifest.jsonl").write_text(
        '{"conversation_id": "conv-own-1"}\n{"conversation_id": "conv-own-2"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(records, "REPO_ROOT", tmp_path)

    own = {"experiment_id": "009_x", "evidence": {"conversation_ids": ["conv-own-1"]}}
    assert records._evidence_problems(own) == []

    borrowed = {
        "experiment_id": "009_x",
        "evidence": {"conversation_ids": ["conv-own-1", "conv-from-a-prior-experiment"]},
    }
    problems = records._evidence_problems(borrowed)
    assert len(problems) == 1
    assert "conv-from-a-prior-experiment" in problems[0]

    # A record scaffolded before its round has written manifests must not be refused for
    # evidence that exists but is not on disk yet.
    unknown = {"experiment_id": "999_none", "evidence": {"conversation_ids": ["conv-x"]}}
    assert records._evidence_problems(unknown) == []
