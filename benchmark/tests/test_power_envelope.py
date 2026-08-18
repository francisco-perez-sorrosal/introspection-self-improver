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


# ── the episode-level envelope (plan D36) ───────────────────────────────────────────────


def test_episode_envelope_reproduces_the_seq10_futility_number():
    # Seq 10 ran B=12 at 3 trials with a generation-1 identity pooling the baseline. Its
    # endpoint needed ~17 pp to reach alpha, which is why the primary was arithmetically
    # unreachable after batch_07 at +8.3 pp. The envelope must say so from the sizes alone.
    from power_envelope import episode_envelope

    result = episode_envelope(batch_size=12, num_trials=3, baseline_rounds=2)
    assert result["baseline_episodes"] == 72
    assert result["endpoint_episodes"] == 36
    assert 16.0 < result["detectable_at_alpha_pp"] < 17.5


def test_episode_envelope_improves_with_batch_size():
    from power_envelope import episode_envelope

    smaller = episode_envelope(batch_size=12, num_trials=3, baseline_rounds=2)
    larger = episode_envelope(batch_size=30, num_trials=3, baseline_rounds=2)
    assert larger["detectable_at_alpha_pp"] < smaller["detectable_at_alpha_pp"]
    # B=30 is the size seq 12 freezes because it brings the detectable effect under the
    # ~11 pp that seq 10's batch actually moved.
    assert larger["detectable_at_alpha_pp"] < 11.0


def test_pooling_the_baseline_buys_power():
    # Registering the identity round at generation 1 is a POWER decision, not only a
    # noise-floor one: it doubles the baseline episodes.
    from power_envelope import episode_envelope

    pooled = episode_envelope(batch_size=30, num_trials=3, baseline_rounds=2)
    single = episode_envelope(batch_size=30, num_trials=3, baseline_rounds=1)
    assert pooled["detectable_at_alpha_pp"] < single["detectable_at_alpha_pp"]


def test_reachability_is_judged_against_measured_headroom():
    from power_envelope import episode_envelope

    roomy = episode_envelope(batch_size=30, num_trials=3, baseline_rounds=2, headroom_pp=15.0)
    cramped = episode_envelope(batch_size=30, num_trials=3, baseline_rounds=2, headroom_pp=8.0)
    assert roomy["reachable"] is True
    assert cramped["reachable"] is False
    # The point of the gate: an experiment that cannot resolve anything smaller than the
    # room available cannot win however good the loop is, and that is knowable at freeze.
    assert "UNREACHABLE" in cramped["headroom_verdict"]
