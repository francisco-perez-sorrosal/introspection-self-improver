"""The freeze-time power envelope, held to the sign-flip primary's closed form."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import batch_curve
from power_envelope import ALPHA, envelope, movers_needed


def test_alpha_matches_the_preregistered_primary():
    # The envelope's whole point is describing batch_curve's test; a drifted alpha would
    # certify a composition against a test nobody runs.
    assert ALPHA == batch_curve.ALPHA


def test_movers_needed_is_five_at_the_frozen_alpha():
    assert movers_needed(0.05) == 5  # 2^-5 = 0.03125 <= 0.05 < 0.0625 = 2^-4
    assert movers_needed(0.0625) == 4


def test_boundary_composition_is_reachable_at_five_movable():
    verdict = envelope(10, anchors=2, walled=3)
    assert verdict["movable_tasks"] == 5
    assert verdict["verdict"] == "REACHABLE"
    assert verdict["attainable_best_case_p"] == pytest.approx(1 / 32)


def test_four_movable_is_unreachable():
    verdict = envelope(8, anchors=2, walled=2)
    assert verdict["movable_tasks"] == 4
    assert verdict["attainable_best_case_p"] == pytest.approx(1 / 16)
    assert verdict["verdict"] == "UNREACHABLE"


def test_walled_subtracts_from_movable_like_anchors():
    # The seq-8 shape read back through the envelope: B=8, 2 anchors, 3 walled headroom
    # leaves 3 movable tasks — the composition could never have reached alpha.
    verdict = envelope(8, anchors=2, walled=3)
    assert verdict["movable_tasks"] == 3
    assert verdict["verdict"] == "UNREACHABLE"


def test_zero_movable_caps_best_case_p_at_one():
    assert envelope(2, anchors=2, walled=0)["attainable_best_case_p"] == 1.0
