"""The reveal over a fabricated three-generation experiment with known-correct answers.

Five held-out tasks, four generations (H2 an identity), every artifact checked against
hand-computed values — the matrix, the transitions, the retention curve, the endpoint —
plus every refusal that keeps a half-true reveal from happening.
"""

from __future__ import annotations

import csv
import json
import subprocess

import pytest
import yaml

from tau_adapter import heldout, records, reveal
from tau_adapter.lock import Lock

TASKS = ["task_101", "task_102", "task_103", "task_104", "task_105"]

#: The freeze every synthetic round claims to have run under; the snapshot pins the same.
FINGERPRINT = "sha256:test-freeze"

#: task → solved, per measured generation. H2 is an identity generation (no measurement).
MEASURED = {
    0: {"task_101": 1.0, "task_102": 0.0, "task_103": 0.0, "task_104": 1.0, "task_105": 0.0},
    1: {"task_101": 1.0, "task_102": 1.0, "task_103": 0.0, "task_104": 0.0, "task_105": 0.0},
    3: {"task_101": 1.0, "task_102": 1.0, "task_103": 1.0, "task_104": 1.0, "task_105": 0.0},
}


def _lock() -> Lock:
    return Lock(
        raw={
            "experiment": {"seq": 2, "name": "exp-b"},
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


def _manifest() -> dict:
    return {"version": 2, "batches": {"batch_01": ["task_900"]}, "held_out": list(TASKS)}


def _record(source: int, outcome: str) -> dict:
    accepted = outcome == "accepted"
    return {
        "transition": {"from_generation": source, "to_generation": source + 1},
        "experiment": "002_exp-b",
        "outcome": outcome,
        "batch": {"name": f"batch_{source + 1:02d}", "task_ids": ["task_900"]},
        "evidence": {"conversation_ids": ["conv_x"], "summary": "batch inspection"},
        "signals": [{"description": "signal", "prevalence": "1/3"}],
        "counterevidence": "none found",
        "hypothesis": "reformulate on empty hits",
        "owning_layer": "prompt",
        "proposed_change": "one instruction line",
        "mutation": {
            "branch": "gen/x",
            "pr_url": "https://example.com",
            "source_commit": f"sha{source}",
            "candidate_commit": f"sha{source + 1}" if accepted else None,
        },
        "expected_effect": "better retrieval" if accepted else "",
        "human_approval": {"approved_by": "user", "date": "2026-08-13"},
        "held_out_result": None,
    }


def _graded_payload(rewards: dict[str, float]) -> dict:
    return {
        "simulations": [
            {"task_id": task, "reward_info": {"reward": reward}} for task, reward in rewards.items()
        ]
    }


@pytest.fixture
def experiment(tmp_path):
    """Vault + records + results root + a scratch repo carrying the final tag."""
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (
        ["init", "-q"],
        ["config", "user.email", "t@example.com"],
        ["config", "user.name", "t"],
        ["commit", "-q", "--allow-empty", "-m", "x"],
        ["tag", "exp2-g003"],
    ):
        subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=repo,
            check=True,
            capture_output=True,
            timeout=30,
        )
    vault = tmp_path / "vault"
    for generation, rewards in MEASURED.items():
        generation_dir = vault / "experiment_002_exp-b" / f"generation_{generation:03d}"
        graded = generation_dir / heldout.GRADED_DIR
        graded.mkdir(parents=True)
        (graded / heldout.GRADED_RESULTS).write_text(
            json.dumps(_graded_payload(rewards)), encoding="utf-8"
        )
        (generation_dir / "run_metadata.json").write_text(
            json.dumps({"freeze_fingerprint": FINGERPRINT}), encoding="utf-8"
        )
    results_root = tmp_path / "results"
    (results_root / "experiment_002_exp-b").mkdir(parents=True)
    (results_root / "experiment_002_exp-b" / "experiment.yaml").write_text(
        yaml.safe_dump({"id": "002_exp-b", "fingerprint": FINGERPRINT}), encoding="utf-8"
    )
    records_dir = results_root / "experiment_002_exp-b" / records.RECORDS_DIRNAME
    records_dir.mkdir(parents=True)
    for source, outcome in ((0, "accepted"), (1, "rejected"), (2, "accepted")):
        path = records_dir / records.record_name(source)
        path.write_text(
            "# scaffold header comment\n" + yaml.safe_dump(_record(source, outcome)),
            encoding="utf-8",
        )
    return {"repo": repo, "vault": vault, "results_root": results_root}


def _reveal(experiment):
    return reveal.reveal(
        _lock(),
        results_root=experiment["results_root"],
        vault_root=experiment["vault"],
        repo_root=experiment["repo"],
        manifest=_manifest(),
    )


def test_reveal_computes_the_known_progression(experiment):
    experiment_dir = _reveal(experiment)
    rows = list(
        csv.DictReader((experiment_dir / "held_out" / reveal.RESULTS_BY_GENERATION_CSV).open())
    )
    assert [(r["generation"], r["passed"], r["basis"]) for r in rows] == [
        ("H0", "2", "measured"),
        ("H1", "2", "measured"),
        ("H2", "2", "carried"),
        ("H3", "4", "measured"),
    ]


def test_reveal_writes_the_known_matrix(experiment):
    experiment_dir = _reveal(experiment)
    rows = list(
        csv.DictReader((experiment_dir / "held_out" / reveal.TASK_GENERATION_MATRIX_CSV).open())
    )
    by_task = {row["task_id"]: (row["H0"], row["H1"], row["H2"], row["H3"]) for row in rows}
    assert by_task["task_101"] == ("1", "1", "1", "1")
    assert by_task["task_102"] == ("0", "1", "1", "1")
    assert by_task["task_103"] == ("0", "0", "0", "1")
    assert by_task["task_104"] == ("1", "0", "0", "1")
    assert by_task["task_105"] == ("0", "0", "0", "0")


def test_transitions_and_retention_match_hand_computation(experiment):
    _reveal(experiment)
    results = [
        reveal.GenerationResult(0, {t: bool(v) for t, v in MEASURED[0].items()}, False),
        reveal.GenerationResult(1, {t: bool(v) for t, v in MEASURED[1].items()}, False),
        reveal.GenerationResult(2, {t: bool(v) for t, v in MEASURED[1].items()}, True),
        reveal.GenerationResult(3, {t: bool(v) for t, v in MEASURED[3].items()}, False),
    ]
    moves = reveal.transitions(results)
    assert moves[0] == {
        "transition": "H0→H1",
        "gains": 1,
        "retained": 1,
        "regressions": 1,
        "unresolved": 2,
        "net": 0,
        "identity": False,
    }
    assert moves[1]["identity"] and moves[1]["gains"] == 0 and moves[1]["regressions"] == 0
    assert moves[2] == {
        "transition": "H2→H3",
        "gains": 2,
        "retained": 2,
        "regressions": 0,
        "unresolved": 1,
        "net": 2,
        "identity": False,
    }
    kept = reveal.retention(results)
    assert [(row["currently"], row["ever"]) for row in kept] == [(2, 2), (2, 3), (2, 3), (4, 4)]


def test_reveal_writes_transitions_and_retention_csvs(experiment):
    experiment_dir = _reveal(experiment)
    held = experiment_dir / "held_out"
    moves = list(csv.DictReader((held / reveal.TRANSITIONS_CSV).open()))
    assert [
        (r["transition"], r["gains"], r["regressions"], r["net"], r["identity"]) for r in moves
    ] == [
        ("H0→H1", "1", "1", "0", "false"),
        ("H1→H2", "0", "0", "0", "true"),
        ("H2→H3", "2", "0", "2", "false"),
    ]
    kept = list(csv.DictReader((held / reveal.RETENTION_CSV).open()))
    assert [
        (r["generation"], r["currently_solved"], r["ever_solved"], r["total"]) for r in kept
    ] == [
        ("H0", "2", "2", "5"),
        ("H1", "2", "3", "5"),
        ("H2", "2", "3", "5"),
        ("H3", "4", "4", "5"),
    ]


def test_summary_states_the_endpoint_against_the_noise_band(experiment):
    experiment_dir = _reveal(experiment)
    summary = (experiment_dir / reveal.SUMMARY_NAME).read_text(encoding="utf-8")
    assert "R_T(H3) - R_T(H0) = +2 task(s) (+40.0 pp)" in summary
    assert "±22 pp" in summary  # one binomial s.e. at p=0.5, T=5
    assert "outside the noise band" in summary
    assert "carried (identity)" in summary
    assert "pass^k is never used" in summary


def test_reveal_copies_measured_rounds_and_stamps_records(experiment):
    experiment_dir = _reveal(experiment)
    held = experiment_dir / "held_out"
    assert (held / "generation_000" / heldout.GRADED_DIR / heldout.GRADED_RESULTS).exists()
    assert not (held / "generation_002").exists()  # identity: nothing was measured
    stamped = (experiment_dir / records.RECORDS_DIRNAME / records.record_name(1)).read_text(
        encoding="utf-8"
    )
    assert "# scaffold header comment" in stamped  # the rest of the file is untouched
    parsed = yaml.safe_load(stamped)
    assert parsed["held_out_result"] == {"passed": 2, "total": 5, "carried": True}
    first = yaml.safe_load(
        (experiment_dir / records.RECORDS_DIRNAME / records.record_name(0)).read_text()
    )
    assert first["held_out_result"] == {"passed": 2, "total": 5, "carried": False}


def test_reveal_refuses_before_the_final_tag(experiment):
    subprocess.run(
        ["git", "tag", "-d", "exp2-g003"],  # noqa: S607
        cwd=experiment["repo"],
        check=True,
        capture_output=True,
        timeout=30,
    )
    with pytest.raises(reveal.RevealError, match=r"final generation tag.*Nothing was read"):
        _reveal(experiment)


def test_reveal_happens_once(experiment):
    _reveal(experiment)
    with pytest.raises(reveal.RevealError, match="a reveal happens once"):
        _reveal(experiment)


def test_reveal_refuses_a_broken_evidence_chain(experiment):
    records_dir = experiment["results_root"] / "experiment_002_exp-b" / records.RECORDS_DIRNAME
    (records_dir / records.record_name(1)).unlink()
    with pytest.raises(reveal.RevealError, match="evidence chain is incomplete"):
        _reveal(experiment)


def test_reveal_refuses_an_unmeasured_generation(experiment):
    graded = experiment["vault"] / "experiment_002_exp-b" / "generation_003" / heldout.GRADED_DIR
    (graded / heldout.GRADED_RESULTS).unlink()
    with pytest.raises(reveal.RevealError, match="no graded round for generation_003"):
        _reveal(experiment)


def test_reveal_refuses_a_measurement_for_an_identity_generation(experiment):
    graded = experiment["vault"] / "experiment_002_exp-b" / "generation_002" / heldout.GRADED_DIR
    graded.mkdir(parents=True)
    (graded / heldout.GRADED_RESULTS).write_text(
        json.dumps(_graded_payload(MEASURED[1])), encoding="utf-8"
    )
    with pytest.raises(reveal.RevealError, match="should never have run"):
        _reveal(experiment)


def test_reveal_refuses_the_wrong_task_set(experiment):
    graded = (
        experiment["vault"]
        / "experiment_002_exp-b"
        / "generation_000"
        / heldout.GRADED_DIR
        / heldout.GRADED_RESULTS
    )
    rewards = dict(MEASURED[0])
    rewards["task_999"] = rewards.pop("task_105")
    graded.write_text(json.dumps(_graded_payload(rewards)), encoding="utf-8")
    with pytest.raises(reveal.RevealError, match=r"not measured on the frozen held-out set"):
        _reveal(experiment)


def test_reveal_refuses_a_measurement_under_a_different_freeze(experiment):
    meta = experiment["vault"] / "experiment_002_exp-b" / "generation_001" / "run_metadata.json"
    meta.write_text(json.dumps({"freeze_fingerprint": "sha256:other"}), encoding="utf-8")
    with pytest.raises(reveal.RevealError, match="cannot mix"):
        _reveal(experiment)


def test_reveal_refuses_without_the_freeze_snapshot(experiment):
    (experiment["results_root"] / "experiment_002_exp-b" / "experiment.yaml").unlink()
    with pytest.raises(reveal.RevealError, match="PROVISIONAL"):
        _reveal(experiment)


def test_two_trials_for_one_task_are_refused(tmp_path):
    graded = tmp_path / heldout.GRADED_DIR
    graded.mkdir()
    payload = {
        "simulations": [
            {"task_id": "task_101", "reward_info": {"reward": 1.0}},
            {"task_id": "task_101", "reward_info": {"reward": 0.0}},
        ]
    }
    (graded / heldout.GRADED_RESULTS).write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(reveal.RevealError, match="single-trial"):
        reveal.load_measured(tmp_path)


def test_partial_reward_is_not_a_pass(tmp_path):
    graded = tmp_path / heldout.GRADED_DIR
    graded.mkdir()
    payload = _graded_payload({"task_101": 0.5, "task_102": 1.0})
    (graded / heldout.GRADED_RESULTS).write_text(json.dumps(payload), encoding="utf-8")
    assert reveal.load_measured(tmp_path) == {"task_101": False, "task_102": True}


# ------------------------------------------------ the pre-registered trend test (D11)


def _fixture_results() -> list[reveal.GenerationResult]:
    """The experiment fixture's curve as GenerationResults, H2 carrying H1's draws."""
    return [
        reveal.GenerationResult(0, {t: bool(v) for t, v in MEASURED[0].items()}, False),
        reveal.GenerationResult(1, {t: bool(v) for t, v in MEASURED[1].items()}, False),
        reveal.GenerationResult(2, {t: bool(v) for t, v in MEASURED[1].items()}, True),
        reveal.GenerationResult(3, {t: bool(v) for t, v in MEASURED[3].items()}, False),
    ]


def test_trend_statistic_matches_hand_computation():
    # Measured generations 0, 1, 3: centered coefficients (-4/3, -1/3, 5/3).
    # S = 4/3 (task_102) + 5/3 (task_103) + 1/3 (task_104) = 10/3; Var = 3 * 14/9 = 14/3;
    # z = (10/3)/sqrt(14/3) = 1.5430, one-sided p = 0.0614.
    trend = reveal.trend_test(_fixture_results())
    assert trend["statistic"] == pytest.approx(10 / 3)
    assert trend["z"] == pytest.approx(1.5430, abs=1e-4)
    assert trend["p_value"] == pytest.approx(0.0614, abs=1e-4)
    assert not trend["significant"]


def test_trend_excludes_identity_generations():
    trend = reveal.trend_test(_fixture_results())
    assert trend["measured_generations"] == ["H0", "H1", "H3"]
    assert trend["excluded_identity"] == ["H2"]


def test_trend_single_flip_over_two_generations():
    # One task 0 -> 1 across two measured generations: z = 1 exactly, p = Phi(-1).
    results = [
        reveal.GenerationResult(0, {"task_a": False}, False),
        reveal.GenerationResult(1, {"task_a": True}, False),
    ]
    trend = reveal.trend_test(results)
    assert trend["z"] == pytest.approx(1.0)
    assert trend["p_value"] == pytest.approx(0.15866, abs=1e-4)
    assert not trend["significant"]


def test_trend_is_one_sided_so_decline_yields_high_p():
    results = [
        reveal.GenerationResult(0, {"task_a": True}, False),
        reveal.GenerationResult(1, {"task_a": False}, False),
    ]
    trend = reveal.trend_test(results)
    assert trend["z"] == pytest.approx(-1.0)
    assert trend["p_value"] == pytest.approx(0.84134, abs=1e-4)
    assert not trend["significant"]


def test_trend_without_discordance_reports_no_evidence():
    constant = {"task_a": True, "task_b": False}
    results = [
        reveal.GenerationResult(generation, dict(constant), False) for generation in range(4)
    ]
    trend = reveal.trend_test(results)
    assert trend["statistic"] == 0.0
    assert trend["p_value"] == 1.0
    assert not trend["significant"]


def test_trend_with_a_single_measured_generation_is_no_evidence():
    results = [
        reveal.GenerationResult(0, {"task_a": True}, False),
        reveal.GenerationResult(1, {"task_a": True}, True),
    ]
    trend = reveal.trend_test(results)
    assert trend["p_value"] == 1.0
    assert not trend["significant"]


def test_summary_states_the_preregistered_trend_verdict(experiment):
    experiment_dir = _reveal(experiment)
    summary = (experiment_dir / reveal.SUMMARY_NAME).read_text(encoding="utf-8")
    assert "Pre-registered primary (D11)" in summary
    assert "z = 1.54, p = 0.061 — not significant at alpha = 0.05" in summary
    assert "Identity generations (H2) carry their predecessor's draws" in summary


def test_reveal_writes_the_trend_verdict_json(experiment):
    experiment_dir = _reveal(experiment)
    verdict = json.loads(
        (experiment_dir / "held_out" / reveal.TREND_TEST_JSON).read_text(encoding="utf-8")
    )
    assert verdict["alpha"] == 0.05
    assert verdict["measured_generations"] == ["H0", "H1", "H3"]
    assert verdict["excluded_identity"] == ["H2"]
    assert verdict["significant"] is False
    assert verdict["p_value"] == pytest.approx(0.0614, abs=1e-4)
