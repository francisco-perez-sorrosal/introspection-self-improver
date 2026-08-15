#!/usr/bin/env python3
"""The fixed-batch saturation curve and its pre-registered paired endpoint test (seq 5).

Meaningful only under `protocol.batch_mode: fixed`, where every batch round measures the
SAME task set, so per-task rates are paired across generations and the curve asks the
loop-reliability question directly: can the improvement loop fix what it stares at?

Batch evidence is fully observable by design (SIA_EVALUATION_PLAN.md D1), so unlike the
held-out reveal this is runnable at any time — but the PRIMARY statistic is pre-registered
at the freeze and computed over the endpoint pair only:

    One-sided exact paired permutation test on per-task rate deltas between the LAST
    batch round (run by H_G — the endpoint measurement round) and the FIRST (run by H_0),
    alpha 0.05. Under the null each task's two rates are exchangeable, so each delta's
    sign flips with probability 1/2: with 8 tasks the reference distribution is the 2^8
    sign-flip enumeration of sum(deltas) — exact, no approximation. Interim invocations
    while the experiment runs are DESCRIPTIVE diagnosis only; the primary is the endpoint
    pair, fixed n, no interim looks (same discipline as the reveal's trend test).

Writes results/experiment_<id>/batch_curve.json and prints the table. Reads only graded
batch artifacts already in tree; never touches the vault.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import heldout as heldoutmod
from tau_adapter import lock as lockmod
from tau_adapter.lock import BATCH_MODE_FIXED, REPO_ROOT
from tau_adapter.reveal import PASS_THRESHOLD, fmt_count

ALPHA = 0.05
OUTPUT_NAME = "batch_curve.json"


def load_batch_round(round_dir: Path) -> dict[str, tuple[int, int]] | None:
    """{task_id: (passed_trials, trials)} from a graded batch round; None if absent."""
    graded = round_dir / heldoutmod.GRADED_DIR / heldoutmod.GRADED_RESULTS
    if not graded.exists():
        return None
    payload = json.loads(graded.read_text(encoding="utf-8"))
    stats: dict[str, list[int]] = {}
    for sim in payload.get("simulations") or []:
        task_id = str(sim.get("task_id"))
        reward = (sim.get("reward_info") or {}).get("reward")
        entry = stats.setdefault(task_id, [0, 0])
        entry[0] += int(reward is not None and float(reward) >= PASS_THRESHOLD)
        entry[1] += 1
    return {task_id: (c, n) for task_id, (c, n) in stats.items()}


def paired_endpoint_test(
    first: dict[str, tuple[int, int]], last: dict[str, tuple[int, int]]
) -> dict:
    """One-sided exact sign-flip permutation test on paired per-task rate deltas.

    Exact because the tasks are few by design: the reference distribution enumerates all
    2^n sign assignments of the observed deltas. p = P(sum >= observed) under the null;
    ties count for the tail (conservative). Zero deltas contribute nothing either way.
    """
    tasks = sorted(first)
    deltas = [last[t][0] / last[t][1] - first[t][0] / first[t][1] for t in tasks]
    observed = sum(deltas)
    n = len(deltas)
    at_least = sum(
        1
        for signs in itertools.product((1, -1), repeat=n)
        if sum(s * d for s, d in zip(signs, deltas, strict=True)) >= observed - 1e-12
    )
    p_value = at_least / (2**n)
    return {
        "test": "one-sided exact paired sign-flip permutation on per-task rate deltas",
        "alpha": ALPHA,
        "tasks": n,
        "observed_delta_sum": round(observed, 6),
        "per_task_deltas": {t: round(d, 6) for t, d in zip(tasks, deltas, strict=True)},
        "p_value": p_value,  # exact — rounding is display's job, not the statistic's
        "significant": p_value < ALPHA,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-root", type=Path, default=REPO_ROOT / "results", help="results directory"
    )
    args = parser.parse_args()

    lock = lockmod.load_lock()
    if lock.protocol.batch_mode != BATCH_MODE_FIXED:
        print(
            "✗ batch_curve is a fixed-batch-mode instrument: under batch_mode fresh the "
            "batches are disjoint task sets and a cross-generation batch curve compares "
            "different tasks — diagnosis evidence, never a curve. Nothing was computed.",
            file=sys.stderr,
        )
        return 1
    experiment_dir = args.results_root / f"experiment_{lock.experiment_id}"
    generations = lock.protocol.generations

    rounds: list[dict] = []
    for g in range(generations + 1):  # batch_0(g+1) is run by H_g; the last is H_G's endpoint
        round_dir = experiment_dir / f"generation_{g:03d}" / f"batch_{g + 1:02d}"
        stats = load_batch_round(round_dir)
        rounds.append(
            {
                "harness": f"H{g}",
                "round": f"batch_{g + 1:02d}",
                "measured": stats is not None,
                "stats": {t: list(v) for t, v in (stats or {}).items()},
            }
        )

    measured = [r for r in rounds if r["measured"]]
    print(f"── batch curve: {lock.experiment_id} (batch_mode fixed)")
    for r in rounds:
        if not r["measured"]:
            print(f"   {r['harness']:>3} {r['round']}   — not measured yet")
            continue
        stats = {t: tuple(v) for t, v in r["stats"].items()}
        expected = sum(c / n for c, n in stats.values())
        print(
            f"   {r['harness']:>3} {r['round']}   mean rate "
            f"{100 * expected / len(stats):5.1f}%   expected {fmt_count(expected)}/{len(stats)}"
        )

    payload: dict = {
        "experiment": lock.experiment_id,
        "computed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "batch_mode": lock.protocol.batch_mode,
        "rounds": rounds,
        "endpoint_test": None,
        "endpoint_status": "descriptive — endpoint pair incomplete",
    }
    first_round, last_round = rounds[0], rounds[-1]
    if first_round["measured"] and last_round["measured"]:
        first = {t: tuple(v) for t, v in first_round["stats"].items()}
        last = {t: tuple(v) for t, v in last_round["stats"].items()}
        if sorted(first) == sorted(last):
            payload["endpoint_test"] = paired_endpoint_test(first, last)
            payload["endpoint_status"] = (
                f"primary — {first_round['harness']} vs {last_round['harness']} on the fixed batch"
            )
            verdict = payload["endpoint_test"]
            print(
                f"   endpoint {last_round['harness']} vs {first_round['harness']}: "
                f"Σ rate deltas = {verdict['observed_delta_sum']:+.3f}, exact one-sided "
                f"p = {verdict['p_value']:.4f} — "
                + ("significant" if verdict["significant"] else "not significant")
                + f" at alpha = {verdict['alpha']}"
            )
        else:
            payload["endpoint_status"] = "task sets differ — not a paired endpoint"
    else:
        print("   endpoint test: pending — needs the first and last batch rounds graded")

    out_path = experiment_dir / OUTPUT_NAME
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"   → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
