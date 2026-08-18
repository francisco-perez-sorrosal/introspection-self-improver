#!/usr/bin/env python3
"""Phase 0: how much better could ANY harness be? (plan D36)

Four experiments asked "did the score go up" against an unknown maximum, so four nulls left
"the loop failed" and "there was nothing to find" equally alive. This script turns the
unknown maximum into a measurement.

It compares graded rounds of the SAME tasks under different harnesses — at minimum an H0
and an H-EXPERT (hand-built with full access to the batch tasks and unlimited effort, never
shipped, never part of the loop, existing only to bound the range) — and reports:

  HEADROOM       H_expert - H0, aggregate and per task. The number the loop is playing for.
  GAP-CLOSURE    the denominator for every later claim: "the loop closed X% of the reachable
                 gap" is meaningful where "+4 pp against an unknown ceiling" is not.
  REACHABILITY   per task, an EMPIRICAL verdict. A task H-expert passes is provably
                 harness-reachable; one it never passes is walled or beyond harness. This
                 replaces trajectory-reading-and-guessing as the screen, and it is what makes
                 a batch larger than the marginal band safe to compose.

WHY NOT JUST TAKE THE BEST ROUND. Seq 10's best per-task result across its nine rounds sums
to 32/36 = 88.9% against an H0 of 55.6% — an apparent 33-point ceiling that is almost
entirely artifact: a task that truly succeeds half the time shows 3/3 in at least one of
nine rounds about 70% of the time. Best-of statistics measure noise. H-expert must be a
harness someone actually built.

Computes no reward: every outcome comes from `tau2 evaluate-trajs` via scripts/grade.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter.lock import REPO_ROOT

#: A task is called reachable when the expert harness passes it at least this often.
REACHABLE_MIN_PASSES = 1


def rates(round_dir: Path) -> dict[str, tuple[int, int]]:
    """{task_id: (passes, trials)} from one graded round."""
    graded = round_dir / "graded" / "updated_results.json"
    if not graded.is_file():
        raise SystemExit(f"no graded results at {graded}")
    out: dict[str, list[int]] = {}
    for sim in json.loads(graded.read_text())["simulations"]:
        reward = (sim.get("reward_info") or {}).get("reward")
        entry = out.setdefault(sim["task_id"], [0, 0])
        entry[0] += 1 if (reward or 0) > 0 else 0
        entry[1] += 1
    return {task: (passes, trials) for task, (passes, trials) in out.items()}


def rate(pair: tuple[int, int]) -> float:
    passes, trials = pair
    return passes / trials if trials else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--h0", required=True, help="graded round dir for the H0 harness")
    ap.add_argument("--expert", required=True, help="graded round dir for the expert harness")
    ap.add_argument("--label", default="", help="a note for the verdict, e.g. the retrieval backend")
    ap.add_argument("--write", help="write the verdict JSON here")
    args = ap.parse_args()

    def resolve(p: str) -> Path:
        path = Path(p)
        return path if path.is_absolute() else (REPO_ROOT / path)

    h0 = rates(resolve(args.h0))
    expert = rates(resolve(args.expert))
    shared = sorted(set(h0) & set(expert), key=lambda t: int(t.split("_")[1]))
    if not shared:
        raise SystemExit("the two rounds share no tasks")

    reachable, walled, rows = [], [], []
    for task in shared:
        h0_rate, ex_rate = rate(h0[task]), rate(expert[task])
        is_reachable = expert[task][0] >= REACHABLE_MIN_PASSES
        (reachable if is_reachable else walled).append(task)
        rows.append(
            {
                "task": task,
                "h0": f"{h0[task][0]}/{h0[task][1]}",
                "expert": f"{expert[task][0]}/{expert[task][1]}",
                "delta_pp": round(100 * (ex_rate - h0_rate), 1),
                "reachable": is_reachable,
            }
        )

    h0_mean = sum(rate(h0[t]) for t in shared) / len(shared)
    ex_mean = sum(rate(expert[t]) for t in shared) / len(shared)
    headroom = ex_mean - h0_mean

    verdict = {
        "label": args.label,
        "tasks": len(shared),
        "h0_round": args.h0,
        "expert_round": args.expert,
        "h0_mean_rate": round(h0_mean, 4),
        "expert_mean_rate": round(ex_mean, 4),
        "headroom_pp": round(100 * headroom, 1),
        "reachable_tasks": reachable,
        "walled_tasks": walled,
        "reachable_count": len(reachable),
        "per_task": rows,
    }

    print(f"── headroom{(' — ' + args.label) if args.label else ''}: {len(shared)} tasks")
    print(f"   H0     {h0_mean:.1%}")
    print(f"   expert {ex_mean:.1%}")
    print(f"   HEADROOM {100 * headroom:+.1f} pp   "
          f"reachable {len(reachable)}/{len(shared)}, walled {len(walled)}")
    if headroom <= 0.05:
        print("   ⚠ headroom is at or below 5 pp — on this evidence the objective offers")
        print("     little for any harness to win, and running a loop against it would")
        print("     reproduce the prior nulls without being able to explain them.")
    if walled:
        print(f"   walled: {', '.join(walled)}")
    if args.write:
        out = resolve(args.write)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
        print(f"   → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
