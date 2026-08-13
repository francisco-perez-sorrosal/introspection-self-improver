"""Multi-episode reporting for the cross-lane diagnostic: coverage and τ's grading
conventions (infrastructure errors excluded from the denominator, counts stated as facts)."""

from __future__ import annotations

import json

from fidelity.lane_report import aggregate, build_reports


def _write_results(tmp_path, sims):
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"simulations": sims}), encoding="utf-8")
    return path


def _sim(task_id, trial, reward, termination="user_stop"):
    return {
        "task_id": task_id,
        "trial": trial,
        "termination_reason": termination,
        "reward_info": {"reward": reward},
        "messages": [],
    }


def test_build_reports_covers_every_simulation(tmp_path):
    path = _write_results(
        tmp_path, [_sim("task_001", 0, 1.0), _sim("task_001", 1, 0.0), _sim("task_002", 0, 1.0)]
    )
    reports = build_reports(path, lane="local", locked_tools=set())
    assert [(r.task_id, r.trial) for r in reports] == [
        ("task_001", 0),
        ("task_001", 1),
        ("task_002", 0),
    ]


def test_aggregate_excludes_infrastructure_errors_from_the_denominator(tmp_path):
    path = _write_results(
        tmp_path,
        [
            _sim("task_001", 0, 1.0),
            _sim("task_001", 1, None, termination="TerminationReason.INFRASTRUCTURE_ERROR"),
            _sim("task_002", 0, 0.0),
        ],
    )
    summary = aggregate(build_reports(path, lane="local", locked_tools=set()))
    assert summary.episodes == 3
    assert summary.graded == 2
    assert summary.successes == 1
    assert summary.pass1 == 0.5
