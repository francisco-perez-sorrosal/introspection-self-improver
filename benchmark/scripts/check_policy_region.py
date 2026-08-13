#!/usr/bin/env python3
"""Verify the Recipe's frozen `<policy>` region against benchmark_lock.yaml.

Stdlib only, and deliberately so. This runs in the pre-commit hook and in CI, where importing
τ² would mean provisioning a 715 MB checkout and a Python environment just to hash a string.
Comparing against the hash the lock recorded is enough to catch an edit, and it makes the gate
cheap enough to run on every commit.

Two gates cover the region between them, and they fail for different reasons:

  this script   the committed region is not what `make policy` wrote  → an edit slipped in
  the adapter   the region is not what env.get_policy() returns       → the lock itself is stale

Neither is sufficient alone.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_MD = REPO_ROOT / "target-agent" / "SYSTEM.md"
LOCK = REPO_ROOT / "benchmark" / "benchmark_lock.yaml"

REGION = re.compile(r"<policy>\n(?P<body>.*?)\n</policy>", re.DOTALL)
PLACEHOLDER = "NOT YET GENERATED"


def fail(message: str) -> int:
    print(f"frozen policy region: {message}", file=sys.stderr)
    return 1


def locked_sha256() -> str | None:
    """Read policy.sha256 without a YAML parser.

    The value is a 64-character hex digest on its own indented line inside the `policy:`
    block; a regex is sufficient and keeps this script dependency-free.
    """
    text = LOCK.read_text(encoding="utf-8")
    block = re.search(r"^policy:\n((?:[ \t]+.*\n?)+)", text, re.MULTILINE)
    if block is None:
        return None
    match = re.search(r"^\s+sha256:\s*([0-9a-f]{64})\s*$", block.group(1), re.MULTILINE)
    return match.group(1) if match else None


def main() -> int:
    if not SYSTEM_MD.exists():
        return fail(f"{SYSTEM_MD.relative_to(REPO_ROOT)} is missing")

    match = REGION.search(SYSTEM_MD.read_text(encoding="utf-8"))
    if match is None:
        return fail("SYSTEM.md has no <policy> … </policy> region on its own lines")
    body = match.group("body").strip("\n")

    if PLACEHOLDER in body:
        return fail("the region is still a placeholder; run `make policy`")

    expected = locked_sha256()
    if expected is None:
        return fail("benchmark_lock.yaml has no policy.sha256; run `make policy`")

    actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if actual != expected:
        return fail(
            "the <policy> region does not match benchmark_lock.yaml.\n"
            f"  region sha256: {actual}\n"
            f"  locked sha256: {expected}\n"
            "This region is benchmark text, not harness surface. If a change to it is "
            "genuinely intended, change the locked domain or retrieval config and run "
            "`make policy` — do not edit the region by hand."
        )

    print(f"✓ frozen policy region matches the lock ({len(body)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
