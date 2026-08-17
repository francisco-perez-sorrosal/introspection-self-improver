#!/usr/bin/env python3
"""Propose, freeze, or verify the generation protocol's task partition.

The proposal is deterministic (tau_adapter/split.py): stratified over reward_basis, dominant
required-document category, and required-document count, with a seeded shuffle only within
identical strata. Sizes come from the lock's protocol block — G batches of B tasks plus the
held-out set of T — overridable per flag for sizing a partition ahead of a freeze. Default
invocation prints the proposed manifest to stdout and the strata report to stderr; a human
reviews and freezes it with --write; --verify is the mechanical check the frozen manifest
must keep passing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod
from tau_adapter import split as splitmod


def _sizes(args, lock: lockmod.Lock) -> dict[str, int]:
    """Partition sizes from the lock's protocol block, each overridable per flag."""
    protocol = lock.protocol
    return splitmod.partition_sizes(
        args.generations or protocol.generations,
        args.batch_size or protocol.improvement_tasks_per_generation,
        args.held_out or protocol.held_out_tasks,
        protocol.batch_mode,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed",
        type=int,
        default=splitmod.DEFAULT_SEED,
        help="within-stratum shuffle seed, recorded in the manifest header",
    )
    parser.add_argument(
        "--generations", type=int, help="override the lock's protocol.generations (G)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="override the lock's protocol.improvement_tasks_per_generation (B)",
    )
    parser.add_argument(
        "--held-out", type=int, help="override the lock's protocol.held_out_tasks (T)"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=splitmod.SPLIT_MANIFEST_PATH,
        help="manifest path to write or verify (default: the frozen benchmark/split_manifest.yaml)",
    )
    parser.add_argument(
        "--write", action="store_true", help="freeze the proposal into the manifest path"
    )
    parser.add_argument(
        "--force", action="store_true", help="allow --write over an already-populated manifest"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="check the frozen manifest against the vendored task data; non-zero on any problem",
    )
    parser.add_argument(
        "--note",
        default="",
        help="extra header line recorded at --write (e.g. the held-out enforcement strength)",
    )
    parser.add_argument(
        "--batch-tasks",
        default="",
        help=(
            "comma-separated task ids for an EXPLICIT batch list (batch_mode fixed: the one "
            "task set every batch round measures). Bypasses the stratified proposal; the "
            "composition is itself a freeze decision — record its rationale in --note."
        ),
    )
    parser.add_argument(
        "--held-out-tasks",
        default="",
        help="comma-separated task ids for an EXPLICIT held-out list (paired with --batch-tasks)",
    )
    parser.add_argument(
        "--exclude",
        default="",
        help=(
            "comma-separated task ids dropped from the pool before proposing (e.g. the "
            "user-sim screen's crashers); recorded in the manifest header. Unknown ids "
            "are refused."
        ),
    )
    parser.add_argument(
        "--strata",
        default="",
        help=(
            "task_id:stratum pairs (comma-separated; strata anchor/marginal/headroom) "
            "recording the pre-freeze H0 screen for a fixed batch (protocol.md § 0). "
            "Every batch task needs one; requires --batch-tasks."
        ),
    )
    parser.add_argument(
        "--walled",
        default="",
        help=(
            "comma-separated headroom task ids proven domain-walled by the reachability "
            "screen — declared wall-monitors outside the primary's movable set"
        ),
    )
    args = parser.parse_args()

    lock = lockmod.load_lock()
    rows = splitmod.load_task_rows(lock.domain)
    sizes = _sizes(args, lock)
    excluded = sorted({t.strip() for t in args.exclude.split(",") if t.strip()})
    if excluded:
        try:
            rows = splitmod.exclude_rows(rows, excluded)
        except ValueError as error:
            print(f"✗ {error}", file=sys.stderr)
            return 1
        exclusion_note = (
            f"excluded from the pool before proposal: {', '.join(excluded)} "
            "(benchmark/data/user_sim_screen.json has the evidence)."
        )
        args.note = f"{exclusion_note} {args.note}".strip()

    if args.verify:
        problems = splitmod.verify(
            splitmod.load_manifest(args.manifest),
            rows,
            lock.domain,
            sizes,
            lock.protocol.batch_mode,
        )
        if problems:
            for problem in problems:
                print(f"✗ {problem}", file=sys.stderr)
            return 1
        print(
            "✓ split manifest holds: partition names, sizes, disjointness, known ids, "
            "task budget, ACTION spread"
        )
        return 0

    batch_tasks = sorted({t.strip() for t in args.batch_tasks.split(",") if t.strip()})
    held_out_tasks = sorted({t.strip() for t in args.held_out_tasks.split(",") if t.strip()})
    if bool(batch_tasks) != bool(held_out_tasks):
        print("✗ --batch-tasks and --held-out-tasks come together or not at all", file=sys.stderr)
        return 1
    if batch_tasks:
        known = {row.task_id for row in rows}
        unknown = sorted((set(batch_tasks) | set(held_out_tasks)) - known)
        if unknown:
            print(f"✗ unknown task id(s): {', '.join(unknown)}", file=sys.stderr)
            return 1
        assignment = splitmod.explicit_assignment(batch_tasks, held_out_tasks, sizes)
    else:
        if lock.protocol.batch_mode == "fixed":
            print(
                "✗ batch_mode fixed takes an explicit, deliberately chosen batch "
                "(--batch-tasks/--held-out-tasks); a stratified proposal would defeat "
                "the composition decision",
                file=sys.stderr,
            )
            return 1
        assignment = splitmod.propose(rows, sizes, seed=args.seed)
    strata = {
        task.strip(): stratum.strip()
        for task, _, stratum in (
            pair.partition(":") for pair in args.strata.split(",") if pair.strip()
        )
    }
    walled = sorted({t.strip() for t in args.walled.split(",") if t.strip()})
    if strata and not batch_tasks:
        print(
            "✗ --strata records a fixed batch's screen; it requires --batch-tasks", file=sys.stderr
        )
        return 1
    if strata:
        strata_problems = (
            [
                f"strata task {t} is not in --batch-tasks"
                for t in sorted(set(strata) - set(batch_tasks))
            ]
            + [f"batch task {t} has no stratum" for t in sorted(set(batch_tasks) - set(strata))]
            + [
                f"stratum {s!r} for {t} is not one of {'/'.join(splitmod.STRATUM_VALUES)}"
                for t, s in sorted(strata.items())
                if s not in splitmod.STRATUM_VALUES
            ]
            + [f"walled task {t} is not headroom" for t in walled if strata.get(t) != "headroom"]
        )
        if strata_problems:
            for problem in strata_problems:
                print(f"✗ {problem}", file=sys.stderr)
            return 1
    rendered = splitmod.render_manifest(
        assignment,
        lock.domain,
        lock.task_split_name,
        args.seed,
        args.note,
        lock.protocol.batch_mode,
        strata=strata or None,
        walled=walled or None,
    )
    print(splitmod.strata_report(rows, assignment), file=sys.stderr)

    if not args.write:
        print(rendered)
        return 0

    existing = splitmod.load_manifest(args.manifest) if args.manifest.exists() else {}
    populated = any(
        existing.get(name) for name in ("batches", splitmod.HELD_OUT, *splitmod.LEGACY_KEYS)
    )
    if populated and not args.force:
        print(
            f"✗ {args.manifest} is already populated — it is frozen; "
            "re-freezing means a new experiment (use --force only for that)",
            file=sys.stderr,
        )
        return 1
    args.manifest.write_text(rendered + "\n", encoding="utf-8")
    print(f"✓ wrote {args.manifest}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
