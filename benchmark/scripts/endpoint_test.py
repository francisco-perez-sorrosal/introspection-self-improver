#!/usr/bin/env python3
"""The endpoint test on EPISODES, stratified by task — the seq-12 primary (plan D36).

WHY THIS REPLACES THE SIGN TEST. Through seq 10 the pre-registered primary collapsed each
task's `num_trials` episodes into one better/worse/flat verdict and counted verdicts, then
required ~5 of them to align. Two things went wrong with that. It discarded most of the
data — 36 episode outcomes compressed to 12 votes — and it demanded a pattern that
per-task noise makes nearly unreachable: seq 10's identity round measured 6 of 12 task
rates moving by a cell on a byte-identical harness. Seq 10's batch rose 55.6% -> 66.7%,
an 11.1 pp move, and the sign test returned p = 0.1836.

The same movement under this test, by batch size (SE of the endpoint difference at
num_trials 3, baseline pooled over two rounds):

    B = 12  SE 10.2 pp   p = 0.14
    B = 24  SE  7.2 pp   p = 0.063
    B = 30  SE  6.5 pp   p = 0.044   <- the size seq 12 freezes

THE TEST. Per task the baseline holds n_b episodes (pooled over the identity pair) and the
endpoint n_e; the statistic is the sum over tasks of (endpoint rate - baseline rate). The
null distribution comes from permuting, WITHIN EACH TASK, which of that task's episodes are
labelled endpoint — an exact conditional test given each task's own total, so between-task
difficulty cancels by construction rather than by assumption. Reported alongside is the
Cochran-Mantel-Haenszel statistic over the same 2x2xK tables, which is the closed-form
analogue and a check that the permutation implementation is not lying.

Reads graded rounds only. Computes no reward: every outcome here comes from
`tau2 evaluate-trajs` output via scripts/grade.py, unchanged.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter.lock import REPO_ROOT

ALPHA = 0.05
DEFAULT_PERMUTATIONS = 100_000


def episode_outcomes(round_dir: Path) -> dict[str, list[int]]:
    """{task_id: [0/1 per episode]} from one graded round."""
    graded = round_dir / "graded" / "updated_results.json"
    if not graded.is_file():
        raise SystemExit(f"no graded results at {graded}")
    out: dict[str, list[int]] = {}
    for sim in json.loads(graded.read_text())["simulations"]:
        reward = (sim.get("reward_info") or {}).get("reward")
        out.setdefault(sim["task_id"], []).append(1 if (reward or 0) > 0 else 0)
    return out


def statistic(baseline: dict[str, list[int]], endpoint: dict[str, list[int]]) -> float:
    """Sum over tasks of (endpoint rate - baseline rate)."""
    total = 0.0
    for task, ep in endpoint.items():
        base = baseline.get(task)
        if not base or not ep:
            continue
        total += sum(ep) / len(ep) - sum(base) / len(base)
    return total


def permutation_p(
    baseline: dict[str, list[int]],
    endpoint: dict[str, list[int]],
    permutations: int,
    seed: int,
) -> tuple[float, float, int]:
    """One-sided P(T >= observed) under within-task relabelling. Returns (p, observed, n)."""
    rng = random.Random(seed)
    observed = statistic(baseline, endpoint)
    pooled = []
    for task in sorted(endpoint):
        if task not in baseline:
            continue
        pooled.append((baseline[task] + endpoint[task], len(baseline[task]), len(endpoint[task])))
    if not pooled:
        raise SystemExit("no tasks shared between the two rounds")

    at_least = 0
    for _ in range(permutations):
        total = 0.0
        for episodes, n_base, n_end in pooled:
            shuffled = episodes[:]
            rng.shuffle(shuffled)
            base_sum = sum(shuffled[:n_base])
            end_sum = sum(shuffled[n_base : n_base + n_end])
            total += end_sum / n_end - base_sum / n_base
        if total >= observed - 1e-12:
            at_least += 1
    # +1 correction: the observed labelling is itself one of the permutations.
    return (at_least + 1) / (permutations + 1), observed, len(pooled)


def cmh(baseline: dict[str, list[int]], endpoint: dict[str, list[int]]) -> dict:
    """Cochran-Mantel-Haenszel over the same 2x2xK tables — the closed-form cross-check."""
    num = 0.0
    var = 0.0
    for task in sorted(endpoint):
        base = baseline.get(task)
        ep = endpoint.get(task)
        if not base or not ep:
            continue
        n1, n2 = len(ep), len(base)
        n = n1 + n2
        passes = sum(ep) + sum(base)
        num += sum(ep) - n1 * passes / n
        if n > 1:
            var += (n1 * n2 * passes * (n - passes)) / (n * n * (n - 1))
    if var <= 0:
        return {"z": 0.0, "p_value": 1.0, "note": "no within-task variation"}
    z = num / math.sqrt(var)
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return {"z": z, "p_value": p}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", nargs="+", required=True, help="baseline round dir(s), pooled")
    ap.add_argument("--endpoint", required=True, help="endpoint round dir")
    ap.add_argument("--permutations", type=int, default=DEFAULT_PERMUTATIONS)
    ap.add_argument("--seed", type=int, default=300)
    ap.add_argument("--write", help="write the verdict JSON here")
    args = ap.parse_args()

    def resolve(p: str) -> Path:
        path = Path(p)
        return path if path.is_absolute() else (REPO_ROOT / path)

    baseline: dict[str, list[int]] = {}
    for round_path in args.baseline:
        for task, outcomes in episode_outcomes(resolve(round_path)).items():
            baseline.setdefault(task, []).extend(outcomes)
    endpoint = episode_outcomes(resolve(args.endpoint))

    p_value, observed, tasks = permutation_p(baseline, endpoint, args.permutations, args.seed)
    closed = cmh(baseline, endpoint)
    base_rate = sum(sum(v) for v in baseline.values()) / sum(len(v) for v in baseline.values())
    end_rate = sum(sum(v) for v in endpoint.values()) / sum(len(v) for v in endpoint.values())

    verdict = {
        "test": "within-task permutation on episode outcomes, stratified by task",
        "alpha": ALPHA,
        "tasks": tasks,
        "baseline_rounds": list(args.baseline),
        "endpoint_round": args.endpoint,
        "baseline_episodes": sum(len(v) for v in baseline.values()),
        "endpoint_episodes": sum(len(v) for v in endpoint.values()),
        "baseline_rate": round(base_rate, 4),
        "endpoint_rate": round(end_rate, 4),
        "statistic_sum_rate_deltas": round(observed, 4),
        "permutations": args.permutations,
        "p_value": round(p_value, 5),
        "significant": p_value < ALPHA,
        "cmh_crosscheck": {k: (round(v, 5) if isinstance(v, float) else v) for k, v in closed.items()},
    }
    print(f"── endpoint test: {tasks} tasks, "
          f"{verdict['baseline_episodes']} baseline vs {verdict['endpoint_episodes']} endpoint episodes")
    print(f"   rate {base_rate:.1%} → {end_rate:.1%}   Σ rate deltas {observed:+.3f}")
    print(f"   permutation one-sided p = {p_value:.4f}"
          f" — {'SIGNIFICANT' if p_value < ALPHA else 'not significant'} at alpha = {ALPHA}")
    print(f"   CMH cross-check z = {closed.get('z', 0):.3f}, p = {closed.get('p_value', 1):.4f}")
    if args.write:
        out = resolve(args.write)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
        print(f"   → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
