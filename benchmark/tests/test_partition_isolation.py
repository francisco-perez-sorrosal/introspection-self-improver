"""Cross-experiment partition isolation.

The within-experiment checks (`propose_split.py --verify`) cannot see whether a task was
already spent, diagnosed, or revealed under an EARLIER experiment. That axis decides what a
capability claim is worth, and it lived in prose until this checker existed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_partition_isolation as iso


def _write_experiment(root: Path, name: str, batch, held, *, revealed=False, spent=False):
    exp = root / f"experiment_{name}"
    exp.mkdir(parents=True)
    (exp / "split_manifest.yaml").write_text(
        yaml.safe_dump({"batches": {"batch_01": list(batch)}, "held_out": list(held)}),
        encoding="utf-8",
    )
    if revealed:
        (exp / "held_out").mkdir()
    if spent:
        run = exp / "generation_000" / "batch_01"
        run.mkdir(parents=True)
        (run / "results.json").write_text("{}", encoding="utf-8")
    return exp


def test_overlap_kinds_are_classified_by_what_the_orchestrator_could_have_learned():
    current = ({"t1", "t2"}, {"t3", "t4"})
    prior = ({"t2", "t3"}, {"t4", "t5"})
    found = iso.overlaps(current, prior)
    assert found["held_out_from_held_out"] == ["t4"]
    assert found["held_out_from_batch"] == ["t3"]
    assert found["batch_from_batch"] == ["t2"]
    assert found["batch_from_held_out"] == []


def test_a_partition_that_was_planned_but_never_spent_is_not_exposure(tmp_path):
    """Seq 1 froze a partition and died at H0 before any generation ran. Those tasks were
    named, never looked at — demanding a declaration for them trains the operator to wave
    the check through, which is worse than having no check."""
    _write_experiment(tmp_path, "001_void", ["t1"], ["t2"], revealed=False, spent=False)
    priors = iso.prior_experiments(tmp_path)
    assert priors[0][2] is False, "not revealed"
    assert priors[0][3] is False, "no batch round ran"


def test_a_spent_and_revealed_partition_is_flagged(tmp_path):
    _write_experiment(tmp_path, "004_prior", ["t1"], ["t2"], revealed=True, spent=True)
    priors = iso.prior_experiments(tmp_path)
    assert priors[0][2] is True and priors[0][3] is True


def test_a_declaration_without_a_reason_does_not_silence_the_check(tmp_path):
    """Silencing must cost the same keystrokes as explaining, or it becomes the default."""
    path = tmp_path / "reuse.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "declarations": [
                    {
                        "experiment": "005",
                        "reuses_from": "004",
                        "kinds": ["held_out_from_held_out"],
                    },
                    {
                        "experiment": "005",
                        "reuses_from": "002",
                        "kinds": ["held_out_from_batch"],
                        "reason": "pool exhausted; stated wherever a number appears",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    declared = iso.load_declarations(path, "005")
    assert "004" not in declared, "a reasonless declaration is a silencer, not a record"
    assert declared["002"] == {"held_out_from_batch": None}


def test_a_pinned_count_bounds_what_the_declaration_acknowledges(tmp_path):
    """A declaration made for 28 tasks must not silently cover a partition that later
    drifts to overlap more — the pin makes drift re-trip the gate."""
    path = tmp_path / "reuse.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "declarations": [
                    {
                        "experiment": "005",
                        "reuses_from": "004",
                        "kinds": ["held_out_from_held_out"],
                        "count": 28,
                        "reason": "pool exhausted",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    declared = iso.load_declarations(path, "005")
    assert declared["004"] == {"held_out_from_held_out": 28}


def test_an_experiment_without_a_manifest_is_reported_as_a_blind_spot(tmp_path):
    """Calibration pilots and probes spend tasks outside any batch round; an experiment
    directory holding episodes but no committed partition is invisible to the overlap
    analysis and must be named rather than silently treated as clean."""
    blind = tmp_path / "experiment_003_pilot" / "generation_000" / "calibration_pilot"
    blind.mkdir(parents=True)
    (blind / "results.json").write_text("{}", encoding="utf-8")
    _write_experiment(tmp_path, "004_prior", ["t1"], ["t2"])
    assert iso.undocumented_experiments(tmp_path) == ["003_pilot"]


def test_the_live_repo_partition_is_declared(monkeypatch):
    """The real check the commit gate runs: seq 5's reuse of seq 4's held-out set is
    sanctioned (plan D19) and must be declared, not merely commented."""
    monkeypatch.setattr(sys, "argv", ["check_partition_isolation.py"])
    assert iso.main() == 0
