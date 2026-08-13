"""Round-directory lifecycle and arm state: resume-vs-refuse told apart by the sentinel."""

from __future__ import annotations

import subprocess

import pytest

from tau_adapter.experiment import (
    COMPLETION_SENTINEL,
    ExperimentError,
    generation_of,
    prepare_round_dir,
    repo_arm_state,
)


def test_fresh_directory_returns_no_status(tmp_path):
    out = tmp_path / "round"
    assert prepare_round_dir(out, overwrite=False) is None
    assert out.is_dir()


def test_completed_round_refuses_without_overwrite(tmp_path):
    out = tmp_path / "round"
    out.mkdir()
    (out / "results.json").write_text("{}", encoding="utf-8")
    (out / COMPLETION_SENTINEL).write_text("{}", encoding="utf-8")
    with pytest.raises(ExperimentError):
        prepare_round_dir(out, overwrite=False)


def test_interrupted_round_resumes(tmp_path):
    out = tmp_path / "round"
    out.mkdir()
    (out / "results.json").write_text("{}", encoding="utf-8")
    status = prepare_round_dir(out, overwrite=False)
    assert status is not None and "resum" in status
    assert (out / "results.json").exists()  # kept: τ's checkpoint resume reads it


def test_overwrite_clears_even_a_completed_round(tmp_path):
    out = tmp_path / "round"
    out.mkdir()
    (out / "results.json").write_text("{}", encoding="utf-8")
    (out / COMPLETION_SENTINEL).write_text("{}", encoding="utf-8")
    status = prepare_round_dir(out, overwrite=True)
    assert status is not None and "overwr" in status
    assert not (out / "results.json").exists()


def test_generation_of_reads_the_path_component(tmp_path):
    assert generation_of(tmp_path / "experiment_x" / "generation_007" / "round") == "generation_007"
    assert generation_of(tmp_path / "elsewhere") is None


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True, timeout=30)


def test_repo_arm_state_reports_head_and_served_surface_dirt_only(tmp_path):
    repo = tmp_path / "repo"
    (repo / "target-agent").mkdir(parents=True)
    (repo / ".introspection").mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "target-agent" / "SYSTEM.md").write_text("x", encoding="utf-8")
    (repo / ".introspection" / "m.yaml").write_text("y", encoding="utf-8")
    (repo / "unrelated.txt").write_text("z", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")

    head, dirty = repo_arm_state(repo)
    assert len(head) == 40 and not dirty

    # Dirt outside the served surface is not arm dirt; dirt on it is.
    (repo / "unrelated.txt").write_text("changed", encoding="utf-8")
    _, dirty = repo_arm_state(repo)
    assert not dirty
    (repo / "target-agent" / "SYSTEM.md").write_text("changed", encoding="utf-8")
    _, dirty = repo_arm_state(repo)
    assert dirty and "SYSTEM.md" in dirty[0]
