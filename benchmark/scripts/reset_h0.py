#!/usr/bin/env python3
"""Restore the recipe to the H0 baseline (decision D6): replace, not merge.

The sequence, in order and stopping at the first failure:

  1. restore  — target-agent/ and .introspection/target-agent.yaml reset to the
                h0-baseline tag, staged; files added after the tag stage as deletions.
                The machine-local .introspection/local.json is preserved, never touched.
  2. bootstrap — regenerates the untracked runtime state the restore removed
                 (.pi/mcp.local.json from its committed example; vendor re-verified).
  3. check    — `introspection check` must accept the restored Recipe.
  4. verify   — byte-identity against the tag, asserted rather than assumed.

The restore is left staged, deliberately uncommitted: the operator reviews and commits,
because platform rounds refuse a dirty recipe tree and the commit is the experiment's own
record of starting from H0.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter import generations
from tau_adapter.lock import REPO_ROOT


def _run_step(name: str, argv: list[str]) -> None:
    print(f"── reset_h0: {name}")
    proc = subprocess.run(argv, cwd=REPO_ROOT, check=False)
    if proc.returncode != 0:
        raise SystemExit(f"✗ {name} failed (exit {proc.returncode}); the reset is incomplete")


def main() -> int:
    print("── reset_h0: restore (replace, not merge)")
    generations.restore_h0(REPO_ROOT)
    _run_step("bootstrap", [sys.executable, "benchmark/scripts/bootstrap.py"])
    _run_step("introspection check", ["introspection", "check", "-o", "report"])
    problems = generations.verify_h0(REPO_ROOT)
    if problems:
        for problem in problems:
            print(f"✗ {problem}", file=sys.stderr)
        return 1
    status = subprocess.run(
        ["git", "status", "--short", "--", *generations.ANCHORED_PATHS],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout.rstrip()
    print(f"\n✓ recipe is byte-identical to {generations.H0_TAG}")
    print(f"  preserved     {generations.PRESERVED_LOCAL_BINDING} (machine-local, CLI-written)")
    if status:
        print("  staged        changes ready to commit:\n" + status)
        print("\n  Commit them before any platform round — the lane refuses a dirty recipe tree.")
    else:
        print("  staged        nothing — the recipe already was H0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
