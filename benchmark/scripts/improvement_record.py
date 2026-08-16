#!/usr/bin/env python3
"""Scaffold or verify an improvement record (protocol §24; decision D5).

--scaffold G prints (or, with --write, freezes into the experiment's improvement_records/)
a template for the H_G → H_(G+1) transition with everything derivable prefilled: the
experiment id, the batch that transition consumes (batch_(G+1) from the frozen partition),
and the source commit — leaving TODOs only where prose belongs. --verify holds one or more
record files to the schema plus the D5 rules; a record that fails is a broken link in the
evidence chain and the transition is not done until it passes.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod
from tau_adapter import records as recordsmod
from tau_adapter import split as splitmod
from tau_adapter.experiment import RESULTS_ROOT
from tau_adapter.lock import REPO_ROOT


def _head_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return proc.stdout.strip()


def _scaffold(args, lock) -> int:
    manifest = splitmod.load_manifest()
    batch_name = splitmod.batch_name(args.scaffold + 1)
    task_ids = (manifest.get("batches") or {}).get(batch_name)
    if not task_ids:
        raise SystemExit(
            f"the partition manifest holds no {batch_name}: transition "
            f"H{args.scaffold} → H{args.scaffold + 1} consumes it, so the record cannot "
            "be scaffolded before the partition is frozen"
        )
    text = recordsmod.scaffold(
        lock,
        from_generation=args.scaffold,
        batch_name=batch_name,
        batch_task_ids=task_ids,
        source_commit=_head_sha(),
    )
    if not args.write:
        print(text)
        return 0
    target = recordsmod.records_dir(lock, RESULTS_ROOT) / recordsmod.record_name(args.scaffold)
    if target.exists() and not args.force:
        print(
            f"✗ {target} already exists — a transition's record is written once; "
            "--force only to restart a scaffold that was never filled in",
            file=sys.stderr,
        )
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"✓ wrote {target} (source_commit = HEAD; fill in the TODOs as they happen)")
    return 0


def _verify(paths: list[str], revealed: bool) -> int:
    schema = recordsmod.load_schema()
    failed = False
    for raw in paths:
        path = Path(raw)
        problems = recordsmod.validate(
            recordsmod.load_record(path), filename=path.name, revealed=revealed, schema=schema
        )
        if problems:
            failed = True
            for problem in problems:
                print(f"✗ {path.name}: {problem}", file=sys.stderr)
        else:
            print(f"✓ {path.name} holds")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--scaffold",
        type=int,
        metavar="G",
        help="print a record template for the H_G → H_(G+1) transition",
    )
    mode.add_argument(
        "--verify", nargs="+", metavar="PATH", help="validate one or more record files"
    )
    mode.add_argument(
        "--verify-current",
        action="store_true",
        help=(
            "validate every committed record of the LOCK's experiment (no-op when none "
            "exist). Run by `make check`, so a record edited after its transition — or one "
            "whose evidence stopped resolving — fails a commit instead of surviving "
            "unnoticed. Reveal state is inferred from held_out/ existing."
        ),
    )
    parser.add_argument(
        "--write", action="store_true", help="freeze the scaffold into improvement_records/"
    )
    parser.add_argument(
        "--force", action="store_true", help="allow --write over an existing record"
    )
    parser.add_argument(
        "--revealed",
        action="store_true",
        help="post-reveal validation: held_out_result is expected to be filled",
    )
    args = parser.parse_args()
    if args.verify:
        return _verify(args.verify, args.revealed)
    if args.verify_current:
        lock = lockmod.load_lock()
        experiment_dir = RESULTS_ROOT / f"experiment_{lock.experiment_id}"
        paths = sorted(str(p) for p in (experiment_dir / "improvement_records").glob("*.yaml"))
        if not paths:
            print(f"✓ no improvement records yet for {lock.experiment_id}; nothing to verify")
            return 0
        revealed = args.revealed or (experiment_dir / "held_out").is_dir()
        return _verify(paths, revealed)
    return _scaffold(args, lockmod.load_lock())


if __name__ == "__main__":
    raise SystemExit(main())
