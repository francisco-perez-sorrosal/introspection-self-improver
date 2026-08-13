#!/usr/bin/env python3
"""Print the experiment id — or, with --dir, the results directory component — from
benchmark_lock.yaml.

The id is derived, never stored: `experiment.seq` (zero-padded to three digits) plus
`experiment.name`, e.g. `001_bm25-sonnet46`. The sequence disambiguates freezes that share
a descriptive name — a second bm25 + Sonnet 4.6 experiment is `002_bm25-sonnet46`.

Stdlib-only so the Makefile can resolve the results path without the uv environment,
mirroring check_policy_region.py. The lock is a controlled file, so the parse is a
strict line scan: a top-level `experiment:` block holding `seq:` and `name:` lines.
Anything else exits non-zero rather than letting an empty string become a path component.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LOCK_PATH = Path(__file__).resolve().parents[1] / "benchmark_lock.yaml"
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def experiment_fields(lock_text: str) -> tuple[int | None, str | None]:
    in_experiment_block = False
    seq: int | None = None
    name: str | None = None
    for line in lock_text.splitlines():
        content = line.split("#", 1)[0].rstrip()
        if not content:
            continue
        if not content.startswith(" "):
            in_experiment_block = content == "experiment:"
            continue
        if in_experiment_block:
            match = re.match(r"^\s+(seq|name):\s*(\S+)$", content)
            if not match:
                continue
            value = match.group(2).strip("'\"")
            if match.group(1) == "seq":
                seq = int(value) if value.isdigit() else None
            else:
                name = value
    return seq, name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", action="store_true", help="print experiment_<id> instead of <id>")
    args = parser.parse_args()
    seq, name = experiment_fields(LOCK_PATH.read_text(encoding="utf-8"))
    if seq is None or seq < 1 or not name or not NAME_PATTERN.match(name):
        print(
            f"{LOCK_PATH}: no usable experiment.seq/name (found seq={seq!r}, name={name!r})",
            file=sys.stderr,
        )
        return 1
    value = f"{seq:03d}_{name}"
    print(f"experiment_{value}" if args.dir else value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
