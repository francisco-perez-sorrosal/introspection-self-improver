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

    if args.write:
        out_path = (
            args.results_root / f"experiment_{lock.experiment_id}" / "gates" / "power_envelope.json"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
        print(f"   → {out_path}")
    return 0 if verdict["verdict"] == "REACHABLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
