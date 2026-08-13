#!/usr/bin/env python3
"""Propose, freeze, or verify the three-way task split.

The proposal is deterministic (tau_adapter/split.py): stratified over reward_basis, dominant
required-document category, and required-document count, with a seeded shuffle only within
identical strata. Default invocation prints the proposed manifest to stdout and the strata
report to stderr; a human reviews and freezes it with --write; --verify is the mechanical
check the frozen manifest must keep passing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod
from tau_adapter import split as splitmod


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed",
        type=int,
        default=splitmod.DEFAULT_SEED,
        help="within-stratum shuffle seed, recorded in the manifest header",
    )
    parser.add_argument(
        "--write", action="store_true", help="freeze the proposal into split_manifest.yaml"
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
        "--fidelity-set",
        action="store_true",
        help="print the deterministic A.0b gate task set derived from the frozen manifest",
    )
    args = parser.parse_args()

    lock = lockmod.load_lock()
    rows = splitmod.load_task_rows(lock.domain)

    if args.fidelity_set:
        ids = splitmod.fidelity_task_set(splitmod.load_manifest(), rows)
        if not ids:
            print("split manifest is not populated; freeze it first", file=sys.stderr)
            return 1
        print(" ".join(ids))
        return 0

    if args.verify:
        problems = splitmod.verify(splitmod.load_manifest(), rows, lock.domain)
        if problems:
            for problem in problems:
                print(f"✗ {problem}", file=sys.stderr)
            return 1
        print("✓ split manifest holds: sizes, disjointness, known ids, ACTION spread")
        return 0

    assignment = splitmod.propose(rows, seed=args.seed)
    rendered = splitmod.render_manifest(
        assignment, lock.domain, lock.task_split_name, args.seed, args.note
    )
    print(splitmod.strata_report(rows, assignment), file=sys.stderr)

    if not args.write:
        print(rendered)
        return 0

    existing = splitmod.load_manifest()
    populated = any(existing.get(name) for name in splitmod.SPLIT_SIZES)
    if populated and not args.force:
        print(
            "✗ split_manifest.yaml is already populated — it is frozen; "
            "re-freezing means a new experiment (use --force only for that)",
            file=sys.stderr,
        )
        return 1
    splitmod.SPLIT_MANIFEST_PATH.write_text(rendered + "\n", encoding="utf-8")
    print(f"✓ wrote {splitmod.SPLIT_MANIFEST_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
