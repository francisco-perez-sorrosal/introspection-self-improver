#!/usr/bin/env python3
"""Print the experiment id — or, with --dir, the results directory component — from
benchmark_lock.yaml.

Stdlib-only so the Makefile can resolve the results path without the uv environment,
mirroring check_policy_region.py. The lock is a controlled file, so the parse is a
strict line scan: a top-level `experiment:` block holding an `id:` line. Anything else
exits non-zero rather than letting an empty string become a path component.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LOCK_PATH = Path(__file__).resolve().parents[1] / "benchmark_lock.yaml"
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def experiment_id(lock_text: str) -> str | None:
    in_experiment_block = False
    for line in lock_text.splitlines():
        content = line.split("#", 1)[0].rstrip()
        if not content:
            continue
        if not content.startswith(" "):
            in_experiment_block = content == "experiment:"
            continue
        if in_experiment_block:
            match = re.match(r"^\s+id:\s*(\S+)$", content)
            if match:
                return match.group(1).strip("'\"")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", action="store_true", help="print experiment_<id> instead of <id>")
    args = parser.parse_args()
    value = experiment_id(LOCK_PATH.read_text(encoding="utf-8"))
    if not value or not ID_PATTERN.match(value):
        print(f"{LOCK_PATH}: no usable experiment.id (found {value!r})", file=sys.stderr)
        return 1
    print(f"experiment_{value}" if args.dir else value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
