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
