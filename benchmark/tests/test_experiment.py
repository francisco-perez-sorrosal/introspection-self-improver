"""The experiment level of results/: path derivation and the freeze snapshot.

One experiment is one freeze. These guards stop the two ways that could silently break:
a run landing in another experiment's directory, and a frozen value changing under an
experiment that already holds results.
"""

from __future__ import annotations

import pytest
import yaml

from tau_adapter.experiment import (
    ExperimentError,
    enforce_snapshot,
    enforce_snapshot_for_experiment,
    experiment_dir_for,
    freeze_fingerprint,
)
from tau_adapter.lock import Lock


def _lock(experiment_name: str = "exp-a", status: str = "FROZEN", **frozen_overrides) -> Lock:
    frozen = {
        "status": status,
        "agent_model": "anthropic/claude-sonnet-4-6",
        "user_llm": "anthropic/claude-sonnet-4-5",
        "num_trials": 1,
        "seed": 300,
    }
    frozen.update(frozen_overrides)
    return Lock(
        raw={
            "experiment": {"seq": 1, "name": experiment_name},
            "benchmark": {
                "domain": "banking_knowledge",
                "retrieval_config": "bm25",
                "commit": "abc123",
                "task_set_name": "banking_knowledge",
                "task_split_name": "base",
            },
            "frozen": frozen,
        }
    )


def _split_manifest(tmp_path, content: dict | None = None):
    path = tmp_path / "split_manifest.yaml"
    default = {"version": 2, "batches": {"batch_01": ["task_001"]}, "held_out": ["task_002"]}
    path.write_text(yaml.safe_dump(content or default), encoding="utf-8")
    return path


def test_paths_outside_results_are_left_alone(tmp_path) -> None:
    out = tmp_path / "elsewhere" / "run"
    assert experiment_dir_for(out, _lock(), results_root=tmp_path / "results") is None


def test_a_path_in_the_wrong_experiment_is_refused(tmp_path) -> None:
    results = tmp_path / "results"
    out = results / "experiment_other" / "generation_000" / "task_001"
    with pytest.raises(ExperimentError, match="experiment_001_exp-a"):
        experiment_dir_for(out, _lock(), results_root=results)


def test_the_pre_experiment_layout_is_refused(tmp_path) -> None:
    # results/<generation>/ without an experiment level was the old layout; nothing may
    # write there any more.
    results = tmp_path / "results"
    out = results / "generation_000" / "task_001"
    with pytest.raises(ExperimentError, match="experiment_001_exp-a"):
        experiment_dir_for(out, _lock(), results_root=results)


def test_fingerprint_tracks_values_not_bytes(tmp_path) -> None:
    split = _split_manifest(tmp_path)
    original = freeze_fingerprint(_lock(), split_manifest_path=split)
    split.write_text("# a comment changes nothing\n" + split.read_text(encoding="utf-8"))
    assert freeze_fingerprint(_lock(), split_manifest_path=split) == original
    assert freeze_fingerprint(_lock(num_trials=2), split_manifest_path=split) != original


def test_first_frozen_run_writes_the_snapshot(tmp_path) -> None:
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    out = results / "experiment_001_exp-a" / "generation_000" / "task_001"
    status = enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)
    assert status is not None and "created" in status
    assert (results / "experiment_001_exp-a" / "experiment.yaml").exists()


def test_a_matching_snapshot_verifies(tmp_path) -> None:
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    out = results / "experiment_001_exp-a" / "generation_000" / "task_001"
    enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)
    status = enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)
    assert status is not None and "verified" in status


def test_freeze_drift_refuses_the_run(tmp_path) -> None:
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    out = results / "experiment_001_exp-a" / "generation_000" / "task_001"
    enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)
    with pytest.raises(ExperimentError, match=r"bump experiment\.seq"):
        enforce_snapshot(_lock(num_trials=2), out, results_root=results, split_manifest_path=split)


def test_the_fingerprint_ignores_operational_defaults(tmp_path) -> None:
    # The operational block is a recorded default, not part of the freeze: changing it
    # mid-experiment must not read as freeze drift.
    split = _split_manifest(tmp_path)
    original = freeze_fingerprint(_lock(), split_manifest_path=split)
    raw = dict(_lock().raw)
    raw["operational"] = {"max_concurrency": 4}
    assert freeze_fingerprint(Lock(raw=raw), split_manifest_path=split) == original


def test_heldout_rounds_anchor_to_the_in_tree_snapshot(tmp_path) -> None:
    # Held-out output lives outside results/ by design, so the snapshot is enforced by
    # experiment id: the H0 round creates it, and later freeze drift refuses the round.
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    status = enforce_snapshot_for_experiment(
        _lock(), results_root=results, split_manifest_path=split
    )
    assert "created" in status
    assert (results / "experiment_001_exp-a" / "experiment.yaml").exists()
    with pytest.raises(ExperimentError, match=r"bump experiment\.seq"):
        enforce_snapshot_for_experiment(
            _lock(num_trials=2), results_root=results, split_manifest_path=split
        )


def test_the_snapshot_writes_value_copies_of_lock_and_partition(tmp_path) -> None:
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    enforce_snapshot_for_experiment(_lock(), results_root=results, split_manifest_path=split)
    exp = results / "experiment_001_exp-a"
    assert yaml.safe_load((exp / "benchmark_lock.yaml").read_text(encoding="utf-8")) == _lock().raw
    split_copy = yaml.safe_load((exp / "split_manifest.yaml").read_text(encoding="utf-8"))
    assert split_copy["held_out"] == ["task_002"]


def test_fingerprint_drifts_on_partition_change(tmp_path) -> None:
    # Moving one task between a batch and the held-out set is a different experiment,
    # even though every list keeps its size.
    split = _split_manifest(tmp_path)
    original = freeze_fingerprint(_lock(), split_manifest_path=split)
    swapped = {"version": 2, "batches": {"batch_01": ["task_002"]}, "held_out": ["task_001"]}
    _split_manifest(tmp_path, swapped)
    assert freeze_fingerprint(_lock(), split_manifest_path=split) != original


def test_a_split_manifest_change_is_freeze_drift(tmp_path) -> None:
    # The partition is part of the freeze: re-cutting batches or held_out under an
    # experiment that already holds results would invalidate every held-out claim.
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    out = results / "experiment_001_exp-a" / "generation_000" / "task_001"
    enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)
    grown = {"version": 2, "batches": {"batch_01": ["task_001", "task_003"]}, "held_out": []}
    _split_manifest(tmp_path, grown)
    with pytest.raises(ExperimentError, match="split-manifest"):
        enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)


def test_a_provisional_lock_writes_no_snapshot(tmp_path) -> None:
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    out = results / "experiment_001_exp-a" / "generation_000" / "task_001"
    status = enforce_snapshot(
        _lock(status="PROVISIONAL"), out, results_root=results, split_manifest_path=split
    )
    assert status is not None and "PROVISIONAL" in status
    assert not (results / "experiment_001_exp-a" / "experiment.yaml").exists()


def test_a_frozen_experiment_cannot_be_reentered_as_provisional(tmp_path) -> None:
    # Flipping the lock back to PROVISIONAL is itself a freeze change; the snapshot, once
    # written, is checked by every run regardless of the lock's current status.
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    out = results / "experiment_001_exp-a" / "generation_000" / "task_001"
    enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)
    with pytest.raises(ExperimentError):
        enforce_snapshot(
            _lock(status="PROVISIONAL"), out, results_root=results, split_manifest_path=split
        )
