"""The fixed-batch paired endpoint test, held to hand-computed exact values."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from batch_curve import paired_endpoint_test


def test_all_positive_deltas_give_the_smallest_exact_p():
    """8 tasks all rising: only the all-positive sign assignment reaches the observed sum,
    so p = 1/256 exactly."""
    first = {f"t{i}": (0, 3) for i in range(8)}
    last = {f"t{i}": (3, 3) for i in range(8)}
    verdict = paired_endpoint_test(first, last)
    assert verdict["observed_delta_sum"] == pytest.approx(8.0)
    assert verdict["p_value"] == pytest.approx(1 / 256)
    assert verdict["significant"]


def test_single_rising_task_is_never_significant_at_n_8():
    """One task rises, seven unchanged: zero deltas flip sign to themselves, so all 2^8
    assignments tie at >= observed through the zeros — p = 128/256 = 0.5."""
    first = {f"t{i}": (0, 3) for i in range(8)}
    last = dict(first, t0=(3, 3))
    verdict = paired_endpoint_test(first, last)
    assert verdict["p_value"] == pytest.approx(0.5)
    assert not verdict["significant"]


def test_balanced_moves_sit_at_the_null_center():
    """One up, one down by the same amount, six unchanged: observed sum 0 — every sign
    assignment reaches >= 0 - tie tolerance in half the flips of the two live deltas."""
    first = {f"t{i}": (1, 3) for i in range(8)}
    last = dict(first, t0=(2, 3), t1=(0, 3))
    verdict = paired_endpoint_test(first, last)
    assert verdict["observed_delta_sum"] == pytest.approx(0.0)
    assert verdict["p_value"] >= 0.5
    assert not verdict["significant"]


def test_decline_yields_high_p_one_sided():
    first = {f"t{i}": (3, 3) for i in range(8)}
    last = {f"t{i}": (0, 3) for i in range(8)}
    verdict = paired_endpoint_test(first, last)
    assert verdict["p_value"] == pytest.approx(1.0)
    assert not verdict["significant"]


def test_six_of_eight_rising_matches_enumeration():
    """6 rise by 1, 2 unchanged: sum = 6. Sign assignments reaching >= 6: all six live
    deltas positive (1 way) x zeros free (4 ways) = 4 of 256."""
    first = {f"t{i}": (0, 1) for i in range(8)}
    last = {f"t{i}": (1, 1) for i in range(6)} | {f"t{i}": (0, 1) for i in range(6, 8)}
    verdict = paired_endpoint_test(first, last)
    assert verdict["p_value"] == pytest.approx(4 / 256)
    assert verdict["significant"]


from batch_curve import (  # noqa: E402  - after the sys.path insert, like the import above
    baseline_round_indices,
    batch_trend,
    noise_floor_entries,
    pool_rounds,
    strata_summary,
)


def _round(name: str, harness: str, stats: dict, measured: bool = True) -> dict:
    return {
        "round": name,
        "harness": harness,
        "measured": measured,
        "stats": {t: list(v) for t, v in stats.items()},
    }


def test_pool_rounds_sums_passed_and_trials():
    assert pool_rounds([{"a": (1, 3)}, {"a": (2, 3)}]) == {"a": (3, 6)}


def test_baseline_pools_only_a_leading_identity_chain():
    assert baseline_round_indices(()) == [0]
    assert baseline_round_indices((1,)) == [0, 1]
    assert baseline_round_indices((1, 2)) == [0, 1, 2]
    # A mid-experiment identity gets a noise_floor entry, never baseline membership.
    assert baseline_round_indices((3,)) == [0]


def test_noise_floor_counts_moved_cells_on_the_identity_pair():
    rounds = [
        _round("batch_01", "H0", {"a": (3, 3), "b": (1, 3)}),
        _round("batch_02", "H1", {"a": (2, 3), "b": (0, 3)}),
    ]
    (entry,) = noise_floor_entries(rounds, (1,))
    assert entry["rounds"] == ["batch_01", "batch_02"]
    assert entry["cells_moved"] == 2
    assert entry["pp_moved"] == pytest.approx(33.3)
    assert entry["net_cells"] == -2
    assert entry["per_task_cell_deltas"] == {"a": -1, "b": -1}


def test_strata_summary_rates_and_reachable_harvest():
    strata = {"a": "anchor", "b": "marginal", "c": "headroom"}
    rounds = [
        _round("batch_01", "H0", {"a": (3, 3), "b": (0, 3), "c": (0, 3)}),
        _round("batch_02", "H1", {"a": (3, 3), "b": (3, 3), "c": (0, 3)}),
    ]
    summary = strata_summary(rounds, strata, walled={"c"})
    assert summary["per_round"][0]["strata"]["anchor"]["rate"] == 1.0
    assert summary["per_round"][0]["strata"]["marginal"]["rate"] == 0.0
    # Harvest reads non-walled cells only: baseline 3/6, endpoint 6/6.
    assert summary["reachable_harvest"]["baseline"] == pytest.approx(0.5)
    assert summary["reachable_harvest"]["endpoint"] == pytest.approx(1.0)
    assert summary["walled"] == ["c"]


def test_batch_trend_excludes_identity_rounds_like_the_reveal():
    rounds = [
        _round("batch_01", "H0", {"a": (0, 3), "b": (0, 3)}),
        _round("batch_02", "H1", {"a": (1, 3), "b": (0, 3)}),
        _round("batch_03", "H2", {"a": (3, 3), "b": (2, 3)}),
    ]
    verdict = batch_trend(rounds, (1,))
    assert verdict["measured_generations"] == ["H0", "H2"]
    assert verdict["excluded_identity"] == ["H1"]
    assert verdict["status"].startswith("diagnostic")


def test_batch_trend_refuses_mismatched_task_sets():
    rounds = [
        _round("batch_01", "H0", {"a": (0, 3)}),
        _round("batch_02", "H1", {"b": (1, 3)}),
    ]
    assert batch_trend(rounds, ()) is None
