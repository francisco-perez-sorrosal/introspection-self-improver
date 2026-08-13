"""The A.0b gate's statistics and multi-episode reporting.

Small-N honesty is the design constraint: at gate scale the interval must not collapse to
zero width on unanimous outcomes (the normal approximation does; Wilson does not), and
"within noise" must stay a defined, recorded claim rather than an impression.
"""

from __future__ import annotations

import json

from fidelity.lane_report import (
    LaneAggregate,
    aggregate,
    build_reports,
    within_noise,
    wilson_interval,
)


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


def test_wilson_interval_is_nondegenerate_on_unanimous_outcomes():
    low, high = wilson_interval(0, 12)
    assert low == 0.0 or low < 0.01
    assert high > 0.2  # 0/12 still admits a real success rate — the interval must say so
    low, high = wilson_interval(12, 12)
    assert low < 0.8
    assert wilson_interval(0, 0) is None


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


def _lane(successes, n):
    return LaneAggregate(
        lane="x",
        episodes=n,
        graded=n,
        successes=successes,
        pass1=successes / n,
        interval=wilson_interval(successes, n),
        mean_messages=None,
    )


def test_within_noise_overlap_and_clear_divergence():
    assert within_noise(_lane(6, 12), _lane(8, 12)) is True
    # 0/40 against 40/40 is beyond any trial-noise story even for Wilson at this N.
    assert within_noise(_lane(0, 40), _lane(40, 40)) is False
    empty = LaneAggregate("x", 0, 0, 0, None, None, None)
    assert within_noise(_lane(6, 12), empty) is None
