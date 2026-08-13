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
    overrides = (args.generations, args.batch_size, args.held_out)
    if all(value is not None for value in overrides):
        return splitmod.partition_sizes(*overrides)
    protocol = lock.protocol
    return splitmod.partition_sizes(
        args.generations or protocol.generations,
        args.batch_size or protocol.improvement_tasks_per_generation,
        args.held_out or protocol.held_out_tasks,
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
    args = parser.parse_args()

    lock = lockmod.load_lock()
    rows = splitmod.load_task_rows(lock.domain)
    sizes = _sizes(args, lock)

    if args.verify:
        problems = splitmod.verify(splitmod.load_manifest(args.manifest), rows, lock.domain, sizes)
        if problems:
            for problem in problems:
                print(f"✗ {problem}", file=sys.stderr)
            return 1
        print(
            "✓ split manifest holds: partition names, sizes, disjointness, known ids, "
            "task budget, ACTION spread"
        )
        return 0

    assignment = splitmod.propose(rows, sizes, seed=args.seed)
    rendered = splitmod.render_manifest(
        assignment, lock.domain, lock.task_split_name, args.seed, args.note
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
