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
