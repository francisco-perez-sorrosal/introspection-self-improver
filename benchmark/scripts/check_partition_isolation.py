#!/usr/bin/env python3
"""Cross-experiment partition isolation: what this experiment reuses from earlier ones.

`propose_split.py --verify` checks a partition against itself — names, sizes, batch↔held-out
disjointness, known ids. It cannot see the axis that actually threatens a capability claim:
whether these tasks were already spent, diagnosed, or REVEALED under a previous experiment.

That axis was previously carried in prose alone. Seq 5 reuses seq 4's entire held-out set
(the 97-task pool holds no virgin tasks), which is a deliberate, recorded decision — but a
decision recorded only in a manifest comment is one a later experiment can repeat by
accident. This turns it into a declaration that is checked.

Severity is about what the ORCHESTRATOR could have learned, so it turns on whether the prior
experiment was revealed:

  held_out ∩ prior held_out   the same hidden set twice. If the prior revealed, its per-task
                              results are known and this experiment's firewall is weaker than
                              it looks.
  held_out ∩ prior batch      tasks this orchestrator read transcripts of, in full, as
                              diagnosis evidence — now sitting behind the firewall.
  batch    ∩ prior held_out   a previously hidden task becomes observable; if the prior
                              revealed, its result is known before this loop tunes on it.
  batch    ∩ prior batch      observable in both, so nothing hidden leaks — but the loop is
                              tuning on ground a prior loop already tuned on. Reported, never
                              blocking: under `batch_mode: fixed` it is the design.

Undeclared overlap above the reporting tier exits non-zero. Declarations live in
benchmark/partition_reuse.yaml — outside the freeze fingerprint on purpose, because it
describes history rather than configuration, and because adding a fingerprinted key
mid-experiment would invalidate a running freeze.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod
from tau_adapter import split as splitmod
from tau_adapter.lock import REPO_ROOT

DECLARATIONS_PATH = Path(__file__).resolve().parents[1] / "partition_reuse.yaml"
RESULTS_ROOT = REPO_ROOT / "results"

#: Overlap kinds that must be declared, worst first. `batch_from_batch` is deliberately
#: absent: it hides nothing, and fixed batch mode makes it the intended shape.
BLOCKING_KINDS = ("held_out_from_held_out", "held_out_from_batch", "batch_from_held_out")
REPORTING_KINDS = ("batch_from_batch",)


def partition_of(manifest: dict[str, Any]) -> tuple[set[str], set[str]]:
    """(batch tasks, held-out tasks) from a manifest of either schema version."""
    batch: set[str] = set()
    for ids in (manifest.get("batches") or {}).values():
        batch |= set(ids or [])
    for legacy in splitmod.LEGACY_KEYS:
        batch |= set(manifest.get(legacy) or [])
    return batch, set(manifest.get(splitmod.HELD_OUT) or [])


def prior_experiments() -> list[tuple[str, dict[str, Any], bool]]:
    """Every earlier experiment's committed partition snapshot, with its revealed flag.

    Revealed means `held_out/` exists in its results directory — the one sanctioned unseal,
    and therefore the line between "these tasks were hidden" and "their results are known".
    """
    found = []
    for path in sorted(RESULTS_ROOT.glob("experiment_*/split_manifest.yaml")):
        manifest = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        experiment_id = path.parent.name.removeprefix("experiment_")
        revealed = (path.parent / "held_out").is_dir()
        found.append((experiment_id, manifest, revealed))
    return found


def overlaps(
    current: tuple[set[str], set[str]], prior: tuple[set[str], set[str]]
) -> dict[str, list[str]]:
    """The four cross-experiment intersections, by kind, as sorted task ids."""
    cur_batch, cur_held = current
    old_batch, old_held = prior
    return {
        "held_out_from_held_out": sorted(cur_held & old_held),
        "held_out_from_batch": sorted(cur_held & old_batch),
        "batch_from_held_out": sorted(cur_batch & old_held),
        "batch_from_batch": sorted(cur_batch & old_batch),
    }


def load_declarations(path: Path, experiment_id: str) -> dict[str, set[str]]:
    """Declared reuse for this experiment: prior experiment id -> acknowledged kinds."""
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    declared: dict[str, set[str]] = {}
    for entry in payload.get("declarations") or []:
        if str(entry.get("experiment")) != experiment_id:
            continue
        if not str(entry.get("reason") or "").strip():
            # A declaration without a reason is a silencer, not a record.
            continue
        declared.setdefault(str(entry.get("reuses_from")), set()).update(
            str(kind) for kind in entry.get("kinds") or []
        )
    return declared


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=splitmod.SPLIT_MANIFEST_PATH,
        help="partition to check (default: the frozen benchmark/split_manifest.yaml)",
    )
    parser.add_argument(
        "--declarations", type=Path, default=DECLARATIONS_PATH, help="reuse declarations file"
    )
    args = parser.parse_args()

    lock = lockmod.load_lock()
    experiment_id = lock.experiment_id
    current = partition_of(yaml.safe_load(args.manifest.read_text(encoding="utf-8")) or {})
    declared = load_declarations(args.declarations, experiment_id)

    problems: list[str] = []
    notes: list[str] = []
    for prior_id, manifest, revealed in prior_experiments():
        if prior_id == experiment_id:
            continue
        found = overlaps(current, partition_of(manifest))
        acknowledged = declared.get(prior_id, set())
        for kind in BLOCKING_KINDS:
            tasks = found[kind]
            if not tasks:
                continue
            state = "REVEALED" if revealed else "sealed"
            detail = (
                f"{experiment_id} reuses {len(tasks)} task(s) from {prior_id} ({state}) "
                f"as {kind}: {', '.join(tasks[:6])}{' …' if len(tasks) > 6 else ''}"
            )
            if kind in acknowledged:
                notes.append(f"declared — {detail}")
            else:
                problems.append(detail)
        for kind in REPORTING_KINDS:
            if found[kind]:
                notes.append(
                    f"note — {experiment_id} shares {len(found[kind])} batch task(s) with "
                    f"{prior_id}; observable in both, so nothing hidden leaks"
                )

    for note in notes:
        print(f"  {note}")
    if problems:
        print(f"\n✗ undeclared cross-experiment task reuse for {experiment_id}:", file=sys.stderr)
        for problem in problems:
            print(f"  ✗ {problem}", file=sys.stderr)
        print(
            f"\n  Reuse is sometimes correct — a pool can be exhausted — but it is a freeze\n"
            f"  decision, not a detail. Declare it in {args.declarations.name} with a reason,\n"
            f"  or repartition onto tasks no prior experiment spent.",
            file=sys.stderr,
        )
        return 1
    print(f"✓ partition isolation holds for {experiment_id}: no undeclared cross-experiment reuse")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
