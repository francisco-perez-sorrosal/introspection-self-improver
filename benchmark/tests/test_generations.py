"""H0 restore mechanics and generation tag naming, in a scratch repository.

The scratch repo mirrors the anchored surface's shape — recipe tree, runtime manifest,
machine-local binding, gitignored runtime state — because the restore's whole point is
what it touches and what it must never touch.
"""

from __future__ import annotations

import subprocess

import pytest

from tau_adapter.generations import (
    H0_TAG,
    GenerationError,
    assert_heldout_measures_a_generation,
    final_generation_tag,
    generation_tag,
    restore_h0,
    tag_exists,
    verify_h0,
)
from tau_adapter.lock import Lock


def _git(repo, *args):
    subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "target-agent" / "agents").mkdir(parents=True)
    (root / "target-agent" / ".pi").mkdir()
    (root / ".introspection").mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / ".gitignore").write_text("target-agent/.pi/mcp.local.json\n", encoding="utf-8")
    (root / "target-agent" / "SYSTEM.md").write_text("baseline prompt\n", encoding="utf-8")
    (root / "target-agent" / "agents" / "agent.yaml").write_text("model: m\n", encoding="utf-8")
    (root / ".introspection" / "target-agent.yaml").write_text("runtime: h0\n", encoding="utf-8")
    (root / ".introspection" / "local.json").write_text('{"binding": "old"}', encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "h0")
    _git(root, "tag", "-a", H0_TAG, "-m", "H0 anchor")
    return root


def _mutate(repo):
    (repo / "target-agent" / "SYSTEM.md").write_text("mutated prompt\n", encoding="utf-8")
    (repo / "target-agent" / "added.md").write_text("new capability\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "mutation")
    (repo / "target-agent" / ".pi" / "mcp.local.json").write_text("{}", encoding="utf-8")
    (repo / ".introspection" / "local.json").write_text('{"binding": "new"}', encoding="utf-8")


def test_restore_replaces_rather_than_merges(repo):
    _mutate(repo)
    restore_h0(repo)
    assert (repo / "target-agent" / "SYSTEM.md").read_text(encoding="utf-8") == "baseline prompt\n"
    # The case a plain path checkout misses: a file committed after the tag must go.
    assert not (repo / "target-agent" / "added.md").exists()
    # Ignored runtime state went with the tree; bootstrap regrows it.
    assert not (repo / "target-agent" / ".pi" / "mcp.local.json").exists()
    assert verify_h0(repo) == []


def test_restore_preserves_the_machine_local_binding(repo):
    _mutate(repo)
    restore_h0(repo)
    binding = (repo / ".introspection" / "local.json").read_text(encoding="utf-8")
    assert binding == '{"binding": "new"}'


def test_restore_stages_the_difference_for_commit(repo):
    _mutate(repo)
    restore_h0(repo)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],  # noqa: S607
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout
    assert "M\ttarget-agent/SYSTEM.md" in staged
    assert "D\ttarget-agent/added.md" in staged


def test_verify_reports_drift_and_untracked_files(repo):
    (repo / "target-agent" / "SYSTEM.md").write_text("drifted\n", encoding="utf-8")
    problems = "\n".join(verify_h0(repo))
    assert "differs from h0-baseline" in problems
    restore_h0(repo)
    (repo / "target-agent" / "stray.txt").write_text("x", encoding="utf-8")
    problems = "\n".join(verify_h0(repo))
    assert "untracked files under the anchored surface" in problems
    assert "stray.txt" in problems


def test_restore_without_the_anchor_tag_is_refused(tmp_path):
    root = tmp_path / "bare"
    root.mkdir()
    _git(root, "init", "-q")
    with pytest.raises(GenerationError, match="no defined H0 to restore"):
        restore_h0(root)


def test_restore_is_idempotent(repo):
    _mutate(repo)
    restore_h0(repo)
    restore_h0(repo)
    assert verify_h0(repo) == []


def test_generation_tag_naming():
    assert generation_tag(2, 1) == "exp2-g001"
    assert generation_tag(3, 12) == "exp3-g012"


def test_final_generation_tag_reads_the_protocol():
    lock = Lock(
        raw={
            "experiment": {"seq": 2, "name": "x"},
            "protocol": {
                "generations": 3,
                "improvement_tasks_per_generation": 3,
                "held_out_tasks": 5,
                "allow_within_batch_verification": False,
                "holdout_visibility": {
                    "expose_tasks_to_orchestrator": False,
                    "expose_traces_to_orchestrator": False,
                    "expose_per_task_results_to_orchestrator": False,
                    "expose_aggregate_score_to_orchestrator": False,
                },
                "require_human_approval": True,
            },
        }
    )
    assert final_generation_tag(lock) == "exp2-g003"


def test_tag_exists_is_exact(repo):
    assert tag_exists(H0_TAG, repo)
    assert not tag_exists("exp2-g003", repo)


def test_a_heldout_round_verifies_h0_against_its_anchor(repo):
    assert assert_heldout_measures_a_generation(2, "generation_000", repo) == H0_TAG


def test_a_heldout_round_accepts_the_tagged_generation(repo):
    _git(repo, "tag", "exp2-g001")
    assert assert_heldout_measures_a_generation(2, "generation_001", repo) == "exp2-g001"


def test_a_heldout_round_requires_the_generation_tag(repo):
    with pytest.raises(GenerationError, match="does not exist"):
        assert_heldout_measures_a_generation(2, "generation_001", repo)


def test_a_heldout_round_refuses_a_drifted_recipe(repo):
    _git(repo, "tag", "exp2-g001")
    (repo / "target-agent" / "SYSTEM.md").write_text("drifted\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "drift")
    with pytest.raises(GenerationError, match="byte-identical"):
        assert_heldout_measures_a_generation(2, "generation_001", repo)
