#!/usr/bin/env python3
"""End-of-experiment reveal: unseal the vault into results/ and compute the progression.

Runnable only once the final generation tag exists; refuses a populated held_out/, a
missing or invalid improvement record, an unmeasured generation, or a measurement where
an identity generation should have none. On success this terminal shows the numbers for
the first time — that is the point of the reveal.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod
from tau_adapter import process_metrics
from tau_adapter import reveal as revealmod
from tau_adapter.experiment import RESULTS_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--derive-only",
        action="store_true",
        help=(
            "recompute only the derived process-metrics CSVs from an ALREADY revealed "
            "held_out/ directory (no vault access, no record stamping; idempotent). "
            "For backfilling experiments revealed before the metrics existed."
        ),
    )
    args = parser.parse_args()
    lock = lockmod.load_lock()
    if args.derive_only:
        held_out_dir = (
            RESULTS_ROOT / f"experiment_{lock.experiment_id}" / revealmod.HELD_OUT_DIRNAME
        )
        if not held_out_dir.exists() or not any(held_out_dir.iterdir()):
            print(f"✗ {held_out_dir} is not a revealed experiment", file=sys.stderr)
            return 1
        for path in process_metrics.write_process_metrics(
            held_out_dir, process_metrics.tool_classes_from_lock(lock)
        ):
            print(f"✓ wrote {path}")
        import json

        results = revealmod.results_from_revealed(held_out_dir)
        fragility_path = held_out_dir / revealmod.TREND_FRAGILITY_JSON
        fragility_path.write_text(
            json.dumps(revealmod.fragility(results), indent=2) + "\n", encoding="utf-8"
        )
        print(f"✓ wrote {fragility_path}")
        return 0
    try:
        experiment_dir = revealmod.reveal(lock, results_root=RESULTS_ROOT)
    except revealmod.RevealError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    print((experiment_dir / revealmod.SUMMARY_NAME).read_text(encoding="utf-8"))
    print(f"✓ revealed into {experiment_dir / revealmod.HELD_OUT_DIRNAME}")
    print(f"✓ {revealmod.SUMMARY_NAME} written; improvement records stamped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
