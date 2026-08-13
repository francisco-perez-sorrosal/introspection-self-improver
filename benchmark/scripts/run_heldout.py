#!/usr/bin/env python3
"""Run one hidden held-out evaluation into the vault, printing completeness only.

This is the muted button (SIA_EVALUATION_PLAN.md D1/D9). The runner and the grader execute
as child processes whose entire output — τ's progress, every graded figure, everything —
is appended to the vault's console.log, out of tree at ~/.sia_vault (SIA_VAULT_DIR
overrides). What reaches this terminal is completeness alone: episodes expected and
completed, artifacts present, and the reveal discipline. Stages are idempotent: rerun after
an interruption to resume; a measured round is never run twice.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import heldout as heldoutmod
from tau_adapter import lock as lockmod


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generation",
        required=True,
        help="generation directory name the measurement belongs to, e.g. generation_000 (H0)",
    )
    args = parser.parse_args()
    return heldoutmod.run_round(lockmod.load_lock(), args.generation)


if __name__ == "__main__":
    raise SystemExit(main())
