#!/usr/bin/env python3
"""The primary's power envelope, computed at freeze — never discovered at closure.

The pre-registered primary (scripts/batch_curve.py) is a one-sided exact paired sign-flip
test on per-task rate deltas: its best case for m same-signed non-zero deltas is
p = 2^-m, so alpha = 0.05 needs m >= 5 movers. Movers can only come from tasks that CAN
move — anchors are at ceiling by construction, and domain-walled headroom will not move
under any mutation the invariants allow — so the attainable p is a property of the
frozen composition, computable before the first episode. Seq 8 froze a composition whose
envelope (five movers needed, three walled tasks) was discovered at closure; protocol.md
§ 0 makes this computation a freeze step, and an UNREACHABLE verdict means fixing the
composition or the test before freezing.

Computation-only: reads the lock and the split manifest (strata/walled when present),
runs no episodes. Default prints; --write commits the verdict to
results/experiment_<id>/gates/power_envelope.json at freeze time.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod
from tau_adapter import split as splitmod
from tau_adapter.lock import REPO_ROOT

#: The primary's pre-registered alpha (scripts/batch_curve.py ALPHA) — restated here so
#: the envelope and the test cannot drift apart silently; test_power_envelope asserts
#: the two are equal.
ALPHA = 0.05


def movers_needed(alpha: float = ALPHA) -> int:
    """Smallest m with 2^-m <= alpha: the sign-flip test's minimum all-positive movers."""
    return math.ceil(-math.log2(alpha))


def episode_envelope(
    batch_size: int,
    num_trials: int,
    baseline_rounds: int = 2,
    alpha: float = ALPHA,
    headroom_pp: float | None = None,
) -> dict:
    """The seq-12+ envelope: what the EPISODE-level primary can detect (plan D36).

    scripts/endpoint_test.py compares episode outcomes stratified by task, so its resolution
    is set by episode counts rather than by how many task-level signs happen to align. At
    p = 0.5 the standard error of the endpoint difference is

        SE = 0.5 * sqrt(1/(B*trials*baseline_rounds) + 1/(B*trials))

    from which two numbers follow: the smallest effect reaching alpha one-sided (1.645*SE),
    and the effect needed for 80% power (2.487*SE). `baseline_rounds` is 2 when a
    generation-1 identity round pools the baseline — which is why registering the identity
    round at generation 1 is a POWER decision and not only a noise-floor one.

    REACHABILITY IS JUDGED AGAINST MEASURED HEADROOM when Phase 0 supplies it: an experiment
    whose smallest detectable effect exceeds the room any harness has to move in cannot win
    however good the loop is, and that is knowable before the first generation is spent.
    """
    baseline_episodes = batch_size * num_trials * baseline_rounds
    endpoint_episodes = batch_size * num_trials
    se = 0.5 * math.sqrt(1 / baseline_episodes + 1 / endpoint_episodes)
    detectable = 1.645 * se
    powered = 2.487 * se
    result = {
        "test": "within-task permutation on episode outcomes (scripts/endpoint_test.py)",
        "alpha": alpha,
        "batch_size": batch_size,
        "num_trials": num_trials,
        "baseline_rounds": baseline_rounds,
        "baseline_episodes": baseline_episodes,
        "endpoint_episodes": endpoint_episodes,
        "se_pp": round(100 * se, 2),
        "detectable_at_alpha_pp": round(100 * detectable, 1),
        "effect_for_80pc_power_pp": round(100 * powered, 1),
    }
    if headroom_pp is not None:
        result["measured_headroom_pp"] = headroom_pp
        result["reachable"] = headroom_pp > 100 * detectable
        result["headroom_verdict"] = (
            "REACHABLE — the smallest detectable effect is inside the measured headroom"
            if headroom_pp > 100 * detectable
            else "UNREACHABLE — the smallest detectable effect exceeds the headroom any "
            "harness has to move in; fix the composition, the trials or the objective"
        )
    return result


def print_episode_envelope(result: dict) -> None:
    print(f"   EPISODE-LEVEL primary (seq 12+, plan D36): B={result['batch_size']}, "
          f"trials={result['num_trials']}, baseline pooled over "
          f"{result['baseline_rounds']} round(s)")
    print(f"     {result['baseline_episodes']} baseline vs {result['endpoint_episodes']} "
          f"endpoint episodes -> SE {result['se_pp']} pp")
    print(f"     detectable at alpha: {result['detectable_at_alpha_pp']} pp   "
          f"80% power needs: {result['effect_for_80pc_power_pp']} pp")
    if "headroom_verdict" in result:
        print(f"     measured headroom {result['measured_headroom_pp']} pp — "
              f"{result['headroom_verdict']}")


def envelope(
    batch_size: int,
    anchors: int,
    walled: int,
    alpha: float = ALPHA,
) -> dict:
    """The frozen composition's attainable significance, closed-form."""
    movable = batch_size - anchors - walled
    needed = movers_needed(alpha)
    best_case_p = 2.0**-movable if movable > 0 else 1.0
    return {
        "test": "one-sided exact paired sign-flip permutation on per-task rate deltas",
        "alpha": alpha,
        "batch_size": batch_size,
        "anchors": anchors,
        "walled": walled,
        "movable_tasks": movable,
        "movers_needed": needed,
        "attainable_best_case_p": best_case_p,
        "verdict": "REACHABLE" if movable >= needed else "UNREACHABLE",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-root", type=Path, default=REPO_ROOT / "results", help="results directory"
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="commit the verdict to results/experiment_<id>/gates/power_envelope.json "
        "(freeze time only — never rewrite a closed experiment's gates)",
    )
    parser.add_argument(
        "--headroom-pp",
        type=float,
        default=None,
        help="measured harness headroom from Phase 0 (scripts/headroom.py). When given, the "
        "episode-level envelope is judged REACHABLE only if the smallest detectable effect "
        "is inside it — an experiment that cannot resolve anything smaller than the room "
        "available cannot win however good the loop is.",
    )
    args = parser.parse_args()

    lock = lockmod.load_lock()
    manifest = splitmod.load_manifest()
    lists = splitmod.partition_lists(manifest)
    batch_tasks = sorted(
        set(next(iter(ids for name, ids in lists.items() if name != splitmod.HELD_OUT), []))
    )
    strata = dict(manifest.get("strata") or {})
    walled = sorted(set(manifest.get("walled") or []))
    anchors = sorted(t for t in batch_tasks if strata.get(t) == "anchor")

    verdict = envelope(len(batch_tasks), len(anchors), len(walled))
    verdict["experiment"] = lock.experiment_id
    verdict["computed_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    verdict["anchor_tasks"] = anchors
    verdict["walled_tasks"] = walled
    if not strata:
        verdict["caveat"] = (
            "no strata mapping in the split manifest — the envelope assumes every batch "
            "task movable, which overstates attainable power"
        )

    print(f"── power envelope: {lock.experiment_id}")
    print(
        f"   B={verdict['batch_size']}, anchors={verdict['anchors']}, "
        f"walled={verdict['walled']} → movable={verdict['movable_tasks']}"
    )
    print(
        f"   sign-flip primary needs {verdict['movers_needed']} movers at "
        f"alpha={verdict['alpha']}; attainable best-case p = "
        f"{verdict['attainable_best_case_p']:.4g} — {verdict['verdict']}"
    )
    if "caveat" in verdict:
        print(f"   caveat: {verdict['caveat']}")

    # The seq-12+ primary. The sign-flip numbers above stay printed because seq <= 10's gates
    # recorded them and must keep reproducing; from seq 12 the EPISODE-level envelope is the
    # one the freeze is judged on, and the exit status follows it.
    episode = episode_envelope(
        len(batch_tasks),
        lock.num_trials,
        baseline_rounds=2 if lock.protocol.identity_generations[:1] == (1,) else 1,
        headroom_pp=args.headroom_pp,
    )
    verdict["episode_level"] = episode
    print_episode_envelope(episode)
    if args.headroom_pp is None:
        print("     (no --headroom-pp given: reachability against measured headroom not judged")
        print("      — Phase 0's scripts/headroom.py supplies it, plan D36)")

    if args.write:
        out_path = (
            args.results_root / f"experiment_{lock.experiment_id}" / "gates" / "power_envelope.json"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
        print(f"   → {out_path}")
    if args.headroom_pp is not None:
        return 0 if episode.get("reachable") else 1
    return 0 if verdict["verdict"] == "REACHABLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
