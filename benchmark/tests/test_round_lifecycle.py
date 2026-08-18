"""Round-directory lifecycle and arm state: resume-vs-refuse told apart by the sentinel."""

from __future__ import annotations

import json
import subprocess

import pytest

from tau_adapter.experiment import (
    COMPLETION_SENTINEL,
    ExperimentError,
    generation_of,
    prepare_round_dir,
    repo_arm_state,
    round_measured,
)


def test_fresh_directory_returns_no_status(tmp_path):
    out = tmp_path / "round"
    assert prepare_round_dir(out, overwrite=False) is None
    assert out.is_dir()


def test_a_console_log_alone_is_not_prior_results(tmp_path):
    # The held-out wrapper creates console.log before the runner starts (it is the redirect
    # target); a fresh round must not read as "resuming" — that lie would land in
    # run_metadata.json as resumed=true and stay in the record.
    out = tmp_path / "round"
    out.mkdir()
    (out / "console.log").write_text("===== stage header\n", encoding="utf-8")
    assert prepare_round_dir(out, overwrite=False) is None


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
    subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


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


def _round_with_rows(out, rows, *, sentinel=True):
    """A round directory holding `rows` manifest rows, optionally already sentinelled."""
    out.mkdir(exist_ok=True)
    (out / "results.json").write_text("{}", encoding="utf-8")
    (out / "episode_manifest.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    if sentinel:
        (out / COMPLETION_SENTINEL).write_text("{}", encoding="utf-8")
    return out


def test_sentinelled_but_incomplete_round_resumes_instead_of_refusing(tmp_path):
    # The case that cost a baseline round: tau's runner returned, but one episode died an
    # infrastructure_error past its retry budget (provider weather on the FROZEN user-sim
    # surface). The sentinel says "runner returned", never "measured" — so the round must
    # resume, not demand --overwrite and re-spend every healthy episode in it.
    out = _round_with_rows(
        tmp_path / "round",
        [{"completed": True}, {"completed": False}, {"completed": True}],
    )
    (out / "graded").mkdir()
    (out / "graded" / "updated_results.json").write_text("{}", encoding="utf-8")

    status = prepare_round_dir(out, overwrite=False, expected_episodes=3)

    assert status is not None
    assert "INCOMPLETE" in status and "2/3" in status
    # The sentinel and the grading derived from non-measurements are gone, so the runner's
    # own documented interrupted-run path takes over.
    assert not (out / COMPLETION_SENTINEL).exists()
    assert not (out / "graded").exists()
    # And the completed episodes survive untouched — resuming must never re-spend them.
    assert (out / "episode_manifest.jsonl").exists()


def test_measured_round_still_refuses_even_with_expected_episodes(tmp_path):
    # The guard's purpose is unchanged for a round that really did measure everything.
    out = _round_with_rows(tmp_path / "round", [{"completed": True}, {"completed": True}])
    with pytest.raises(ExperimentError):
        prepare_round_dir(out, overwrite=False, expected_episodes=2)
    assert (out / COMPLETION_SENTINEL).exists()


def test_unknown_episode_count_refuses_a_sentinelled_round(tmp_path):
    # Without an expected count the sentinel is taken at face value — the safe direction.
    out = _round_with_rows(tmp_path / "round", [{"completed": True}])
    with pytest.raises(ExperimentError):
        prepare_round_dir(out, overwrite=False, expected_episodes=None)
    assert (out / COMPLETION_SENTINEL).exists()


def test_round_measured_counts_completed_rows_only(tmp_path):
    out = _round_with_rows(
        tmp_path / "round",
        [{"completed": True}, {"completed": False}, {"completed": None}],
        sentinel=False,
    )
    assert round_measured(out, 1) is True
    assert round_measured(out, 2) is False
