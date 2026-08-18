"""The platform seam-canary gate and the seam-integrity audit.

The local A.0a gate structurally cannot exercise the tunnel — the 2026-08-15 disconnect
regression passed the whole suite and a mock smoke while denying platform agents their
tools. These tests pin the two mechanisms built from that lesson: the canary's verdict
logic, the batch round's refusal to start against a missing or stale verdict, and the
bridge-vs-τ record audit.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gate_seam_canary as canary
from fidelity import seam_integrity
from tau_adapter import run as runmod
from tau_adapter.lock import REPO_ROOT


def _clean_row(**overrides):
    row = {
        "trial": 0,
        "completed": True,
        "evidence_complete": True,
        "sandbox_seam_disconnects": 0,
        "sandbox_seam_timeouts": 0,
        "sandbox_seam_unclassified": 0,
        "sandbox_tool_errors": 0,
    }
    row.update(overrides)
    return row


def test_canary_passes_on_clean_verifiable_episodes():
    passed, findings = canary.judge([_clean_row(), _clean_row(trial=1)])
    assert passed and findings == []


def test_canary_fails_on_any_seam_counter():
    passed, findings = canary.judge([_clean_row(sandbox_seam_disconnects=2)])
    assert not passed
    assert "sandbox_seam_disconnects=2" in findings[0]


def test_canary_fails_when_nothing_is_verifiable():
    """An infra-stormed run that produced no complete conversation attests nothing —
    'could not check' must never grade as 'checked and clean'."""
    infra = _clean_row(completed=False, evidence_complete=None)
    passed, findings = canary.judge([infra])
    assert not passed
    assert any("nothing attests" in finding for finding in findings)


def test_canary_fails_on_a_completed_but_unverifiable_episode():
    passed, findings = canary.judge([_clean_row(), _clean_row(trial=1, evidence_complete=None)])
    assert not passed
    assert any("unverifiable" in finding for finding in findings)


def _simulations(*tool_names):
    return [
        {
            "messages": [
                {"role": "assistant", "turn_idx": idx, "tool_calls": [{"name": name}]}
                for idx, name in enumerate(tool_names)
            ]
        }
    ]


def test_suppression_passes_when_engaged_and_absent_from_trajectory():
    """The suppressing path attests only when the model called the registered tool AND τ
    never saw it — engagement without a leak."""
    rows = [_clean_row(pi_local_calls=2)]
    passed, findings = canary.suppression_judge(rows, _simulations("KB_search"), "probe_note")
    assert passed and findings == []


def test_suppression_fails_when_the_path_never_engaged():
    """pi_local_calls = 0 means the model never called the tool: 'could not check' must
    never grade as 'checked and clean' (seq 8 ran an entire experiment pump-path-only)."""
    rows = [_clean_row(pi_local_calls=0)]
    passed, findings = canary.suppression_judge(rows, _simulations("KB_search"), "probe_note")
    assert not passed
    assert any("never engaged" in finding for finding in findings)


def test_suppression_fails_when_the_tool_leaks_into_the_graded_trajectory():
    rows = [_clean_row(pi_local_calls=1)]
    passed, findings = canary.suppression_judge(
        rows, _simulations("KB_search", "probe_note"), "probe_note"
    )
    assert not passed
    assert any("suppression leaked" in finding for finding in findings)
    assert any("probe_note" in finding for finding in findings)


def test_suppression_still_fails_on_seam_counters():
    """Suppression success on a sick seam is not a PASS — the base seam-health findings
    carry through."""
    rows = [_clean_row(pi_local_calls=1, sandbox_seam_timeouts=1)]
    passed, findings = canary.suppression_judge(rows, _simulations("KB_search"), "probe_note")
    assert not passed
    assert any("sandbox_seam_timeouts=1" in finding for finding in findings)


def test_batch_refuses_without_a_seam_canary_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr(runmod, "RESULTS_ROOT", tmp_path)
    problem = runmod._seam_canary_problem("099_test")
    assert problem is not None and "gate_seam" in problem


def test_batch_refuses_a_failed_or_stale_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr(runmod, "RESULTS_ROOT", tmp_path)
    gates = tmp_path / "experiment_099_test" / "gates"
    gates.mkdir(parents=True)

    (gates / "seam_canary.json").write_text(json.dumps({"passed": False}), encoding="utf-8")
    assert "FAILED" in (runmod._seam_canary_problem("099_test") or "")

    # A PASS at the current HEAD is current by definition: no tau_adapter diff since.
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    (gates / "seam_canary.json").write_text(
        json.dumps({"passed": True, "adapter_sha": head}), encoding="utf-8"
    )
    assert runmod._seam_canary_problem("099_test") is None

    # An unresolvable sha reads as stale — fail-closed, the canary is the cheap side.
    (gates / "seam_canary.json").write_text(
        json.dumps({"passed": True, "adapter_sha": "0" * 40}), encoding="utf-8"
    )
    assert runmod._seam_canary_problem("099_test") is not None


def test_seam_integrity_flags_count_drift_and_skips_unjoined_lanes():
    calls = [
        {"token": "t1", "episode": "task-A", "duration_seconds": 1.0, "outcome": "ok"},
        {"token": "t1", "episode": "task-A", "duration_seconds": 1.0, "outcome": "ok"},
    ]
    rows = [
        {
            "pi_session_ref": "task-A",
            "tau_task_id": "task_001",
            "trial": 0,
            "transport": "platform",
            "tool_messages": 3,
        }
    ]
    findings = seam_integrity.audit(rows, calls, park_warn=20.0)
    assert any("count drift" in finding for finding in findings)

    # A run with no joined episode (the local lane) must not fabricate drift findings.
    unjoined = [{"token": "x", "episode": None, "duration_seconds": 1.0, "outcome": "ok"}]
    findings = seam_integrity.audit(rows, unjoined, park_warn=20.0)
    assert all(f.startswith("info:") for f in findings)


def test_seam_integrity_flags_daemon_patience_parks():
    calls = [{"token": "t1", "episode": "task-A", "duration_seconds": 45.0, "outcome": "ok"}]
    rows = [
        {
            "pi_session_ref": "task-A",
            "tau_task_id": "task_001",
            "trial": 0,
            "transport": "platform",
            "tool_messages": 1,
        }
    ]
    findings = seam_integrity.audit(rows, calls, park_warn=20.0)
    assert any("daemon-patience" in finding for finding in findings)


def _cadence_lock(heldout_generations=None):
    """A minimal lock for the cadence gates.

    Carries a protocol block because the gates read `protocol.heldout_generations` (plan
    D36) — in production that block is mandatory, so a fixture without one was testing a
    lock shape that cannot exist. `heldout_generations` left None keeps the pre-D36
    contract: every non-identity generation is measured.
    """
    from tau_adapter.lock import Lock

    protocol = {
        "generations": 3,
        "improvement_tasks_per_generation": 4,
        "held_out_tasks": 8,
        "allow_within_batch_verification": True,
        "require_human_approval": False,
        "holdout_visibility": {
            "expose_tasks_to_orchestrator": False,
            "expose_traces_to_orchestrator": False,
            "expose_per_task_results_to_orchestrator": False,
            "expose_aggregate_score_to_orchestrator": False,
        },
        "batch_mode": "fixed",
    }
    if heldout_generations is not None:
        protocol["heldout_generations"] = heldout_generations
    return Lock(raw={"experiment": {"seq": 9, "name": "t"}, "protocol": protocol})


@pytest.fixture
def cadence(tmp_path, monkeypatch):
    """A tmp results tree + vault, with the git identity checks stubbed green."""
    monkeypatch.setattr(runmod, "RESULTS_ROOT", tmp_path / "results")
    monkeypatch.setenv("SIA_VAULT_DIR", str(tmp_path / "vault"))
    monkeypatch.setattr(runmod.gensmod, "tag_exists", lambda tag, *a, **k: True)
    monkeypatch.setattr(runmod.gensmod, "verify_against_tag", lambda tag, *a, **k: [])
    return tmp_path


def _grade_vault_round(root, generation_name):
    from tau_adapter import heldout

    graded = root / "vault" / "experiment_009_t" / generation_name / heldout.GRADED_DIR
    graded.mkdir(parents=True)
    (graded / heldout.GRADED_RESULTS).write_text("{}", encoding="utf-8")


def test_batch_refuses_before_the_baseline_is_measured(cadence):
    """Measure, then learn: batch_01 must not spend evidence before H0's held-out round
    exists — a baseline skipped now becomes unmeasurable once the next merge moves the
    recipe."""
    problem = runmod._batch_cadence_problem(_cadence_lock(), 1)
    assert problem is not None and "make heldout GEN=generation_000" in problem


def test_batch_proceeds_once_its_generation_is_measured(cadence):
    _grade_vault_round(cadence, "generation_000")
    assert runmod._batch_cadence_problem(_cadence_lock(), 1) is None


def test_batch_cadence_resolves_identity_chains(cadence):
    """H2 pinned to H1 by an identity transition: batch_03 is satisfied by H1's
    measurement and never demands a round for a harness that does not exist."""
    records_dir = cadence / "results" / "experiment_009_t" / "improvement_records"
    records_dir.mkdir(parents=True)
    (records_dir / "gen_001_to_002.yaml").write_text("outcome: identity\n", encoding="utf-8")

    problem = runmod._batch_cadence_problem(_cadence_lock(), 3)
    assert problem is not None and "generation_001" in problem and "carries forward" in problem

    _grade_vault_round(cadence, "generation_001")
    assert runmod._batch_cadence_problem(_cadence_lock(), 3) is None


def test_batch_refuses_a_recipe_that_is_not_its_generation(cadence, monkeypatch):
    """A mutation merged early would silently attribute H_(g+1) behaviour to H_g's round."""
    _grade_vault_round(cadence, "generation_000")
    monkeypatch.setattr(
        runmod.gensmod, "verify_against_tag", lambda tag, *a, **k: ["SYSTEM.md differs"]
    )
    problem = runmod._batch_cadence_problem(_cadence_lock(), 1)
    assert problem is not None and "byte-identical" in problem


def test_heldout_baseline_needs_no_batch(cadence):
    """generation_000 precedes any batch by definition — the baseline is always the
    experiment's first measurement."""
    assert runmod._heldout_cadence_problem(_cadence_lock(), "generation_000") is None


def test_heldout_refuses_before_the_learning_batch_is_graded(cadence):
    """H_(g+1) is the product of batch_(g+1)'s learnings: without this refusal a skipped
    batch would be invisible — merge, tag and measure while citing older evidence."""
    records_dir = cadence / "results" / "experiment_009_t" / "improvement_records"
    records_dir.mkdir(parents=True)

    problem = runmod._heldout_cadence_problem(_cadence_lock(), "generation_001")
    assert problem is not None and "no transition record" in problem

    (records_dir / "gen_000_to_001.yaml").write_text("outcome: accepted\n", encoding="utf-8")
    problem = runmod._heldout_cadence_problem(_cadence_lock(), "generation_001")
    assert problem is not None and "make batch B=1" in problem

    from tau_adapter import heldout

    graded = (
        cadence
        / "results"
        / "experiment_009_t"
        / "generation_000"
        / "batch_01"
        / heldout.GRADED_DIR
    )
    graded.mkdir(parents=True)
    (graded / heldout.GRADED_RESULTS).write_text("{}", encoding="utf-8")
    assert runmod._heldout_cadence_problem(_cadence_lock(), "generation_001") is None


def test_heldout_refuses_identity_generations_before_the_spend(cadence):
    """H_g = H_(g-1) carries forward (D5); reveal refuses the measurement anyway, but
    refusing here saves the whole round."""
    records_dir = cadence / "results" / "experiment_009_t" / "improvement_records"
    records_dir.mkdir(parents=True)
    (records_dir / "gen_000_to_001.yaml").write_text("outcome: identity\n", encoding="utf-8")
    problem = runmod._heldout_cadence_problem(_cadence_lock(), "generation_001")
    assert problem is not None and "carries" in problem


# ── sparse held-out schedules (plan D36) ────────────────────────────────────────────────
# Through seq 10 the held-out set was measured once per generation and consumed roughly two
# thirds of the episode budget to produce one flat line. A frozen schedule makes measurement
# sparse WITHOUT making it optional: the generations it omits are carried exactly as identity
# generations are, and a batch still cannot run while any scheduled measurement is missing.


def test_sparse_schedule_still_refuses_a_batch_whose_baseline_is_unmeasured(cadence):
    lock = _cadence_lock(heldout_generations=[0, 2, 3])
    problem = runmod._batch_cadence_problem(lock, 1)
    assert problem is not None and "make heldout GEN=generation_000" in problem


def test_sparse_schedule_lets_a_batch_run_past_an_unscheduled_generation(cadence):
    # H1 is not on the schedule, so batch_02 (run by H1) needs H0's measurement and no more.
    _grade_vault_round(cadence, "generation_000")
    lock = _cadence_lock(heldout_generations=[0, 2, 3])
    assert runmod._batch_cadence_problem(lock, 2) is None


def test_sparse_schedule_refuses_a_batch_when_an_EARLIER_scheduled_round_is_missing(cadence):
    # The gate walks every scheduled measurement at or before the generation, not just the
    # latest — otherwise a sparse schedule would let a skipped baseline through.
    _grade_vault_round(cadence, "generation_002")
    lock = _cadence_lock(heldout_generations=[0, 2, 3])
    problem = runmod._batch_cadence_problem(lock, 3)
    assert problem is not None and "generation_000" in problem


def test_heldout_refuses_an_unscheduled_generation_before_the_spend(cadence):
    lock = _cadence_lock(heldout_generations=[0, 2, 3])
    problem = runmod._heldout_cadence_problem(lock, "generation_001")
    assert problem is not None
    assert "not on this experiment's frozen held-out schedule" in problem


def test_schedule_must_include_the_baseline_and_the_final_generation():
    from tau_adapter.lock import LockError

    with pytest.raises(LockError, match="must include 0"):
        _cadence_lock(heldout_generations=[1, 3]).protocol
    with pytest.raises(LockError, match="must include 3"):
        _cadence_lock(heldout_generations=[0, 2]).protocol


def test_schedule_may_not_name_an_identity_generation():
    from tau_adapter.lock import Lock, LockError

    protocol = dict(_cadence_lock(heldout_generations=[0, 1, 3]).raw["protocol"])
    protocol["identity_generations"] = [1]
    lock = Lock(raw={"experiment": {"seq": 9, "name": "t"}, "protocol": protocol})
    with pytest.raises(LockError, match="carry their predecessor"):
        lock.protocol


def test_absent_schedule_reproduces_the_pre_D36_contract():
    # The default must be byte-for-byte the old behaviour: every generation is due.
    from tau_adapter import generations as gensmod

    assert gensmod.heldout_scheduled(2, None) is True
    assert gensmod.heldout_due_before(2, None) == [2]
    assert gensmod.heldout_scheduled(1, (0, 2, 3)) is False
    assert gensmod.heldout_due_before(3, (0, 2, 3)) == [0, 2, 3]
