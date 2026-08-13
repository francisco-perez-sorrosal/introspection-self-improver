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
    experiment_dir_for,
    freeze_fingerprint,
)
from tau_adapter.lock import Lock


def _lock(experiment_id: str = "exp_a", status: str = "FROZEN", **frozen_overrides) -> Lock:
    frozen = {
        "status": status,
        "agent_model": "anthropic/claude-sonnet-4-6",
        "user_llm": "anthropic/claude-sonnet-4-5",
        "num_trials": 4,
        "seed": 300,
    }
    frozen.update(frozen_overrides)
    return Lock(
        raw={
            "experiment": {"id": experiment_id},
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
    path.write_text(
        yaml.safe_dump(content or {"discovery": [], "validation": [], "test": []}),
        encoding="utf-8",
    )
    return path


def test_paths_outside_results_are_left_alone(tmp_path) -> None:
    out = tmp_path / "elsewhere" / "run"
    assert experiment_dir_for(out, _lock(), results_root=tmp_path / "results") is None


def test_a_path_in_the_wrong_experiment_is_refused(tmp_path) -> None:
    results = tmp_path / "results"
    out = results / "experiment_other" / "generation_000" / "task_001"
    with pytest.raises(ExperimentError, match="experiment_exp_a"):
        experiment_dir_for(out, _lock(), results_root=results)


def test_the_pre_experiment_layout_is_refused(tmp_path) -> None:
    # results/<generation>/ without an experiment level was the old layout; nothing may
    # write there any more.
    results = tmp_path / "results"
    out = results / "generation_000" / "task_001"
    with pytest.raises(ExperimentError, match="experiment_exp_a"):
        experiment_dir_for(out, _lock(), results_root=results)


def test_fingerprint_tracks_values_not_bytes(tmp_path) -> None:
    split = _split_manifest(tmp_path)
    original = freeze_fingerprint(_lock(), split_manifest_path=split)
    split.write_text("# a comment changes nothing\n" + split.read_text(encoding="utf-8"))
    assert freeze_fingerprint(_lock(), split_manifest_path=split) == original
    assert freeze_fingerprint(_lock(num_trials=1), split_manifest_path=split) != original


def test_first_frozen_run_writes_the_snapshot(tmp_path) -> None:
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    out = results / "experiment_exp_a" / "generation_000" / "task_001"
    status = enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)
    assert status is not None and "created" in status
    assert (results / "experiment_exp_a" / "experiment.yaml").exists()


def test_a_matching_snapshot_verifies(tmp_path) -> None:
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    out = results / "experiment_exp_a" / "generation_000" / "task_001"
    enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)
    status = enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)
    assert status is not None and "verified" in status


def test_freeze_drift_refuses_the_run(tmp_path) -> None:
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    out = results / "experiment_exp_a" / "generation_000" / "task_001"
    enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)
    with pytest.raises(ExperimentError, match="new experiment"):
        enforce_snapshot(_lock(num_trials=1), out, results_root=results, split_manifest_path=split)


def test_a_split_manifest_change_is_freeze_drift(tmp_path) -> None:
    # The split is part of the freeze: re-cutting discovery/validation/test under an
    # experiment that already holds results would invalidate every held-out claim.
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    out = results / "experiment_exp_a" / "generation_000" / "task_001"
    enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)
    _split_manifest(tmp_path, {"discovery": ["task_001"], "validation": [], "test": []})
    with pytest.raises(ExperimentError, match="split-manifest"):
        enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)


def test_a_provisional_lock_writes_no_snapshot(tmp_path) -> None:
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    out = results / "experiment_exp_a" / "generation_000" / "task_001"
    status = enforce_snapshot(
        _lock(status="PROVISIONAL"), out, results_root=results, split_manifest_path=split
    )
    assert status is not None and "PROVISIONAL" in status
    assert not (results / "experiment_exp_a" / "experiment.yaml").exists()


def test_a_frozen_experiment_cannot_be_reentered_as_provisional(tmp_path) -> None:
    # Flipping the lock back to PROVISIONAL is itself a freeze change; the snapshot, once
    # written, is checked by every run regardless of the lock's current status.
    results, split = tmp_path / "results", _split_manifest(tmp_path)
    out = results / "experiment_exp_a" / "generation_000" / "task_001"
    enforce_snapshot(_lock(), out, results_root=results, split_manifest_path=split)
    with pytest.raises(ExperimentError):
        enforce_snapshot(
            _lock(status="PROVISIONAL"), out, results_root=results, split_manifest_path=split
        )
