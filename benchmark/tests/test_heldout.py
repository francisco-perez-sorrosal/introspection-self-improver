"""The muted held-out wrapper: vault layout, idempotent stages, reward-free terminal.

The central assertion is the firewall's: whatever the children print — and the fakes here
print graded figures on purpose — the wrapper's own stdout carries counts and paths only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tau_adapter import heldout
from tau_adapter.experiment import COMPLETION_SENTINEL
from tau_adapter.lock import Lock
from tau_adapter.manifest import write_manifest
from tau_adapter.split import HELD_OUT

_HELD_IDS = ["task_001", "task_002", "task_003", "task_004", "task_005"]


def _lock(num_trials: int = 1) -> Lock:
    return Lock(
        raw={
            "experiment": {"seq": 2, "name": "exp-b"},
            "frozen": {"num_trials": num_trials},
        }
    )


def _partition() -> dict:
    return {"version": 2, "batches": {"batch_01": ["task_900"]}, HELD_OUT: list(_HELD_IDS)}


def _rows(completed: int, total: int = 5) -> list[dict]:
    # Rewards present on purpose: the report must not repeat them.
    return [
        {
            "tau_task_id": f"task_{i:03d}",
            "trial": 0,
            "reward": 1.0 if i % 2 else 0.0,
            "completed": i < completed,
        }
        for i in range(total)
    ]


def _assert_reward_free(text: str) -> None:
    assert not re.search(r"reward", text, re.IGNORECASE), text
    assert "avg" not in text.lower(), text
    assert "1.0" not in text and "0.0" not in text, text


def _fake_child(rows_completed: int = 5):
    """A run_child that behaves like the real stages: artifacts in the vault, spam on the log."""

    def child(argv: list[str], console) -> int:
        console.write("Simulation done  reward=1.0\navg_reward: 0.5  pass^1: 0.5\n")
        target = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
        if target is not None:  # the runner stage
            (target / "results.json").write_text("{}", encoding="utf-8")
            # Realistic metadata: graded values elsewhere in the file, counters projected out.
            metadata = {
                "incidents": {"totals": {"stream_reattaches": 2, "stall_warnings": 0}},
                "episodes": [{"task_id": "task_001", "reward": 1.0}],
            }
            (target / COMPLETION_SENTINEL).write_text(json.dumps(metadata), encoding="utf-8")
            write_manifest(target, _rows(rows_completed))
        else:  # the grading stage
            graded = Path(argv[argv.index("--output-dir") + 1])
            graded.mkdir(parents=True, exist_ok=True)
            (graded / heldout.GRADED_RESULTS).write_text("{}", encoding="utf-8")
        return 0

    return child


def test_vault_root_honours_the_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv(heldout.VAULT_ENV, str(tmp_path / "vault"))
    assert heldout.vault_root() == tmp_path / "vault"
    monkeypatch.delenv(heldout.VAULT_ENV)
    assert heldout.vault_root() == heldout.DEFAULT_VAULT


def test_round_dir_layout_is_experiment_then_generation(tmp_path):
    path = heldout.round_dir_for(_lock(), "generation_003", root=tmp_path)
    assert path == tmp_path / "experiment_002_exp-b" / "generation_003"


def test_run_round_seals_child_output_and_prints_counts_only(tmp_path, capsys):
    rc = heldout.run_round(
        _lock(), "generation_000", root=tmp_path, manifest=_partition(), run_child=_fake_child()
    )
    out = capsys.readouterr().out
    assert rc == 0
    _assert_reward_free(out)
    assert "5/5 completed" in out
    assert "5 task(s) x 1 trial(s)" in out
    assert "5 row(s)" in out
    assert "incidents     stream_reattaches=2 — seam counters, not graded outcomes" in out
    assert "graded/updated_results.json — persisted, not shown" in out
    assert "read at reveal" in out
    console = (tmp_path / "experiment_002_exp-b" / "generation_000" / "console.log").read_text(
        encoding="utf-8"
    )
    assert "reward=1.0" in console  # the spam went to the vault, not the terminal
    assert "run.py" in console and "grade.py" in console  # both stages logged their argv


def test_run_round_never_reruns_a_measured_round(tmp_path, capsys):
    round_dir = heldout.round_dir_for(_lock(), "generation_000", root=tmp_path)
    round_dir.mkdir(parents=True)
    (round_dir / "results.json").write_text("{}", encoding="utf-8")
    (round_dir / COMPLETION_SENTINEL).write_text("{}", encoding="utf-8")
    write_manifest(round_dir, _rows(5))
    graded = round_dir / heldout.GRADED_DIR
    graded.mkdir()
    (graded / heldout.GRADED_RESULTS).write_text("{}", encoding="utf-8")

    def forbidden(argv, console):
        raise AssertionError(f"no stage may run for a measured round: {argv}")

    rc = heldout.run_round(
        _lock(), "generation_000", root=tmp_path, manifest=_partition(), run_child=forbidden
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "already measured (one measurement per generation)" in out
    _assert_reward_free(out)


def test_run_round_grades_a_run_that_crashed_before_grading(tmp_path, capsys):
    # Sentinel present, graded/ missing: only the grading stage runs.
    round_dir = heldout.round_dir_for(_lock(), "generation_000", root=tmp_path)
    round_dir.mkdir(parents=True)
    (round_dir / "results.json").write_text("{}", encoding="utf-8")
    (round_dir / COMPLETION_SENTINEL).write_text("{}", encoding="utf-8")
    write_manifest(round_dir, _rows(5))
    stages: list[str] = []

    def child(argv, console):
        stages.append("run" if "--out" in argv else "grade")
        graded = Path(argv[argv.index("--output-dir") + 1])
        graded.mkdir(parents=True, exist_ok=True)
        (graded / heldout.GRADED_RESULTS).write_text("{}", encoding="utf-8")
        return 0

    rc = heldout.run_round(
        _lock(), "generation_000", root=tmp_path, manifest=_partition(), run_child=child
    )
    assert rc == 0
    assert stages == ["grade"]
    _assert_reward_free(capsys.readouterr().out)


def test_incomplete_round_reports_and_exits_nonzero(tmp_path, capsys):
    rc = heldout.run_round(
        _lock(), "generation_000", root=tmp_path, manifest=_partition(), run_child=_fake_child(3)
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "3/5 completed" in out and "INCOMPLETE" in out
    assert "Rerun `make heldout GEN=generation_000` to resume" in out
    _assert_reward_free(out)


def test_runner_failure_keeps_the_terminal_sealed(tmp_path, capsys):
    def failing(argv, console):
        console.write("boom with reward=0.0\n")
        return 3

    rc = heldout.run_round(
        _lock(), "generation_000", root=tmp_path, manifest=_partition(), run_child=failing
    )
    out = capsys.readouterr().out
    assert rc == 3
    assert "the runner exited 3" in out
    assert "prefer resuming over reading it" in out
    _assert_reward_free(out)


def test_missing_held_out_list_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="no held_out list"):
        heldout.run_round(_lock(), "generation_000", root=tmp_path, manifest={"version": 2})


def test_a_non_generation_name_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="not a generation directory name"):
        heldout.run_round(_lock(), "gen0", root=tmp_path, manifest=_partition())


def test_runner_argv_is_the_muted_runner_invocation(tmp_path):
    argv = heldout._runner_argv(tmp_path)
    assert "--heldout" in argv and "--out" in argv
    assert not any(flag in argv for flag in ("--overwrite", "--transport"))


def test_grade_argv_is_quiet_and_persisted(tmp_path):
    argv = heldout._grade_argv(tmp_path)
    assert "--quiet" in argv
    assert str(tmp_path / "graded") in argv
