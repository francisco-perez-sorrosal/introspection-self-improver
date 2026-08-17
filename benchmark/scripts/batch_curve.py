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
from tau_adapter import process_metrics
from tau_adapter import split as splitmod
from tau_adapter.lock import BATCH_MODE_FIXED, REPO_ROOT
from tau_adapter.reveal import PASS_THRESHOLD, GenerationResult, fmt_count, trend_test

ALPHA = 0.05
OUTPUT_NAME = "batch_curve.json"

STRATUM_VALUES = ("anchor", "marginal", "headroom")


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


def pool_rounds(
    rounds_stats: list[dict[str, tuple[int, int]]],
) -> dict[str, tuple[int, int]]:
    """Sum (passed, trials) per task across rounds of one behaviourally-identical harness."""
    pooled: dict[str, list[int]] = {}
    for stats in rounds_stats:
        for task_id, (passed, trials) in stats.items():
            entry = pooled.setdefault(task_id, [0, 0])
            entry[0] += passed
            entry[1] += trials
    return {task_id: (c, n) for task_id, (c, n) in pooled.items()}


def baseline_round_indices(identity_generations: tuple[int, ...]) -> list[int]:
    """Indices into the rounds list that the primary's H0 side pools.

    A pre-registered gen-1 identity means H1 ≡ H0, so batch_01 (run by H0, index 0) and
    batch_02 (run by H1, index 1) are draws of the SAME harness — pooling them doubles
    the baseline's trials at zero cost (protocol.md § 0). Only a leading identity chain
    from generation 1 keeps pooled rounds at H0; a mid-experiment identity still gets its
    noise_floor entry but never joins the baseline.
    """
    indices = [0]
    generation = 1
    while generation in identity_generations:
        indices.append(generation)  # batch_(g+1) sits at index g, run by H_g
        generation += 1
    return indices


def noise_floor_entries(rounds: list[dict], identity_generations: tuple[int, ...]) -> list[dict]:
    """Per pre-registered identity generation k: batch_k vs batch_(k+1) — the same harness
    measured twice on the same tasks, so every moved cell is measured noise."""
    entries: list[dict] = []
    for k in identity_generations:
        before, after = rounds[k - 1], rounds[k]
        if not (before["measured"] and after["measured"]):
            continue
        b = {t: tuple(v) for t, v in before["stats"].items()}
        a = {t: tuple(v) for t, v in after["stats"].items()}
        if sorted(b) != sorted(a):
            continue
        per_task = {t: a[t][0] - b[t][0] for t in sorted(b) if a[t][0] != b[t][0]}
        episodes = sum(n for _, n in b.values())
        cells = sum(abs(d) for d in per_task.values())
        entries.append(
            {
                "identity_generation": k,
                "rounds": [before["round"], after["round"]],
                "cells_moved": cells,
                "pp_moved": round(100 * cells / episodes, 1) if episodes else 0.0,
                "net_cells": sum(per_task.values()),
                "per_task_cell_deltas": per_task,
            }
        )
    return entries


def strata_summary(rounds: list[dict], strata: dict[str, str], walled: set[str]) -> dict | None:
    """Per-stratum rates per round, plus the reachable-harvest co-metric.

    Harvest — the fraction of non-walled batch cells passed — is the pre-registered
    disambiguator between loop failure and headroom exhaustion (protocol.md § 0): a flat
    primary with high harvest says the objective's reachable range is spent, not that
    the loop found nothing.
    """
    measured = [r for r in rounds if r["measured"]]
    if not measured:
        return None

    def cells(round_entry: dict, tasks: list[str]) -> tuple[int, int]:
        stats = {t: tuple(v) for t, v in round_entry["stats"].items()}
        chosen = [t for t in tasks if t in stats]
        return sum(stats[t][0] for t in chosen), sum(stats[t][1] for t in chosen)

    per_round = []
    for r in measured:
        by_stratum = {}
        for stratum in STRATUM_VALUES:
            passed, trials = cells(r, [t for t in strata if strata[t] == stratum])
            by_stratum[stratum] = {
                "passed": passed,
                "trials": trials,
                "rate": round(passed / trials, 4) if trials else None,
            }
        per_round.append({"round": r["round"], "harness": r["harness"], "strata": by_stratum})

    def harvest(round_entry: dict) -> float | None:
        reachable = [t for t in round_entry["stats"] if t not in walled]
        passed, trials = cells(round_entry, reachable)
        return round(passed / trials, 4) if trials else None

    return {
        "per_round": per_round,
        "walled": sorted(walled),
        "reachable_harvest": {
            "baseline": harvest(measured[0]),
            "endpoint": harvest(measured[-1]),
            "note": (
                "fraction of non-walled batch cells passed — the loop-failure vs "
                "headroom-exhaustion disambiguator (protocol.md § 0)"
            ),
        },
    }


def batch_trend(rounds: list[dict], identity_generations: tuple[int, ...]) -> dict | None:
    """The reveal's trend statistic over the measured batch rounds — diagnostic by default.

    rounds[g] is run by H_g; a round run by a pre-registered identity harness re-measures
    its predecessor, so it is excluded from the statistic exactly the way the reveal
    excludes carried held-out columns (one harness, one column).
    """
    measured = [(g, r) for g, r in enumerate(rounds) if r["measured"]]
    if not measured:
        return None
    reference = sorted(measured[0][1]["stats"])
    if any(sorted(r["stats"]) != reference for _, r in measured):
        return None  # not one paired task set — no cross-round statistic exists
    results = [
        GenerationResult(
            g,
            {t: tuple(v) for t, v in r["stats"].items()},
            carried=g in identity_generations,
        )
        for g, r in measured
    ]
    verdict = trend_test(results)
    verdict["status"] = "diagnostic unless the freeze's reading key names it"
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-root", type=Path, default=REPO_ROOT / "results", help="results directory"
    )
    args = parser.parse_args()

    lock = lockmod.load_lock()
    # Batch process metrics derive under BOTH batch modes (plan D25: the behavioral
    # counters are prediction channels), so they are written before the fixed-mode
    # refusal below — only the cross-round CURVE is fixed-mode-only.
    metrics_dir = args.results_root / f"experiment_{lock.experiment_id}"
    if metrics_dir.exists():
        for path in process_metrics.write_batch_process_metrics(
            metrics_dir, process_metrics.tool_classes_from_lock(lock)
        ):
            print(f"✓ wrote {path}")
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

    identity = lock.protocol.identity_generations
    manifest = splitmod.load_manifest() if splitmod.SPLIT_MANIFEST_PATH.exists() else {}
    strata = dict(manifest.get("strata") or {})
    walled = set(manifest.get("walled") or [])

    payload: dict = {
        "experiment": lock.experiment_id,
        "computed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "batch_mode": lock.protocol.batch_mode,
        "rounds": rounds,
        "endpoint_test": None,
        "endpoint_status": "descriptive — endpoint pair incomplete",
    }
    base_rounds = [rounds[i] for i in baseline_round_indices(identity)]
    last_round = rounds[-1]
    if all(r["measured"] for r in base_rounds) and last_round["measured"]:
        first = pool_rounds([{t: tuple(v) for t, v in r["stats"].items()} for r in base_rounds])
        last = {t: tuple(v) for t, v in last_round["stats"].items()}
        if sorted(first) == sorted(last):
            payload["endpoint_test"] = paired_endpoint_test(first, last)
            baseline_desc = (
                base_rounds[0]["harness"]
                if len(base_rounds) == 1
                else (
                    "H0 pooled over "
                    + ", ".join(r["round"] for r in base_rounds)
                    + " (pre-registered identity)"
                )
            )
            payload["endpoint_status"] = (
                f"primary — {last_round['harness']} vs {baseline_desc} on the fixed batch"
            )
            verdict = payload["endpoint_test"]
            print(
                f"   endpoint {last_round['harness']} vs {baseline_desc}: "
                f"Σ rate deltas = {verdict['observed_delta_sum']:+.3f}, exact one-sided "
                f"p = {verdict['p_value']:.4f} — "
                + ("significant" if verdict["significant"] else "not significant")
                + f" at alpha = {verdict['alpha']}"
            )
        else:
            payload["endpoint_status"] = "task sets differ — not a paired endpoint"
    else:
        print("   endpoint test: pending — needs the baseline and last batch rounds graded")

    if identity:
        payload["identity_generations"] = list(identity)
        payload["noise_floor"] = noise_floor_entries(rounds, identity)
        for entry in payload["noise_floor"]:
            print(
                f"   noise floor (gen {entry['identity_generation']} identity, "
                f"{entry['rounds'][0]}→{entry['rounds'][1]}): {entry['cells_moved']} cells, "
                f"{entry['pp_moved']} pp on an identical harness"
            )
    if strata:
        payload["strata"] = strata_summary(rounds, strata, walled)
        if payload["strata"] is not None:
            reachable = payload["strata"]["reachable_harvest"]
            print(
                f"   reachable harvest: baseline {reachable['baseline']} → endpoint "
                f"{reachable['endpoint']} (walled: {', '.join(sorted(walled)) or 'none'})"
            )
    trend = batch_trend(rounds, identity)
    if trend is not None:
        payload["trend"] = trend

    out_path = experiment_dir / OUTPUT_NAME
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"   → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
