#!/usr/bin/env python3
"""End-of-experiment reveal: unseal the vault into results/ and compute the progression.

Runnable only once the final generation tag exists; refuses a populated held_out/, a
missing or invalid improvement record, an unmeasured generation, or a measurement where
an identity generation should have none. On success this terminal shows the numbers for
the first time — that is the point of the reveal.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import lock as lockmod
from tau_adapter import reveal as revealmod
from tau_adapter.experiment import RESULTS_ROOT


def main() -> int:
    lock = lockmod.load_lock()
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
