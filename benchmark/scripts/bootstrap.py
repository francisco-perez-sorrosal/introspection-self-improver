#!/usr/bin/env python3
"""Reproduce the benchmark lane from benchmark_lock.yaml.

Idempotent: safe to re-run. Fetches the pinned tau2-bench checkout into vendor/, verifies
its commit against the lock, installs the Python environment, and derives the recipe's MCP
binding file from its committed example.

Deliberately stdlib-only apart from the YAML read, so it can run before the environment it
creates exists.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BENCHMARK_DIR.parent
VENDOR_DIR = BENCHMARK_DIR / "vendor" / "tau2-bench"
LOCK_PATH = BENCHMARK_DIR / "benchmark_lock.yaml"
RECIPE_DIR = REPO_ROOT / "target-agent"


def fail(message: str) -> None:
    print(f"bootstrap: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], cwd: Path | None = None, capture: bool = False) -> str:
    printable = " ".join(cmd)
    if not capture:
        print(f"  $ {printable}")
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=capture, check=False)
    if result.returncode != 0:
        if capture and result.stderr:
            print(result.stderr, file=sys.stderr)
        fail(f"command failed ({result.returncode}): {printable}")
    return (result.stdout or "").strip()


def read_lock() -> dict:
    """Minimal reader for the fields bootstrap needs.

    PyYAML is not importable until `uv sync` has run, and it is `uv sync` that this
    function's output configures. Parsing four scalars out of a flat block is cheaper than
    the bootstrap-your-own-bootstrap alternative.
    """
    text = LOCK_PATH.read_text(encoding="utf-8")
    wanted = ("repository", "commit", "tag")
    found: dict[str, str] = {}
    for key in wanted:
        match = re.search(rf"^\s{{2}}{key}:\s*(\S+)\s*$", text, re.MULTILINE)
        if match:
            found[key] = match.group(1)
    missing = [k for k in wanted if k not in found]
    if missing:
        fail(f"{LOCK_PATH.name} is missing benchmark.{', benchmark.'.join(missing)}")
    if not re.fullmatch(r"[0-9a-f]{40}", found["commit"]):
        fail(f"benchmark.commit must be a full 40-character SHA, got {found['commit']!r}")
    return found


def head_sha(path: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def ensure_checkout(lock: dict) -> None:
    url = f"https://github.com/{lock['repository']}.git"
    want = lock["commit"]

    if VENDOR_DIR.exists():
        current = head_sha(VENDOR_DIR)
        if current == want:
            print(f"✓ tau2-bench already at {want[:12]} ({lock['tag']})")
            return
        if current is None:
            fail(f"{VENDOR_DIR} exists but is not a git checkout; remove it and re-run")
        print(f"  vendor checkout is at {current[:12]}, want {want[:12]}; fetching")
        run(["git", "fetch", "--depth", "1", "origin", want], cwd=VENDOR_DIR)
        run(["git", "checkout", "--quiet", "--detach", want], cwd=VENDOR_DIR)
    else:
        VENDOR_DIR.parent.mkdir(parents=True, exist_ok=True)
        print(f"  cloning {lock['repository']} at {lock['tag']} (~715 MB of domain data)")
        run(
            [
                "git",
                "clone",
                "--quiet",
                "--depth",
                "1",
                "--branch",
                lock["tag"],
                url,
                str(VENDOR_DIR),
            ]
        )

    got = head_sha(VENDOR_DIR)
    if got != want:
        # A moved tag is exactly the evaluator drift the pin exists to prevent, so this is
        # a hard stop rather than something to reconcile.
        fail(
            f"pinned commit mismatch: {LOCK_PATH.name} says {want}, checkout is at {got}. "
            f"Tag {lock['tag']!r} may have moved."
        )
    print(f"✓ tau2-bench at {want[:12]} ({lock['tag']})")


def ensure_environment() -> None:
    if not (BENCHMARK_DIR / "uv.lock").exists():
        print("  no uv.lock yet; resolving for the first time")
    run(["uv", "sync", "--extra", "dev"], cwd=BENCHMARK_DIR)
    print("✓ python environment synced")


def ensure_mcp_binding() -> None:
    example = RECIPE_DIR / ".pi" / "mcp.local.example.json"
    target = RECIPE_DIR / ".pi" / "mcp.local.json"
    if not example.exists():
        fail(f"missing {example.relative_to(REPO_ROOT)}")
    if target.exists():
        print(f"✓ {target.relative_to(REPO_ROOT)} already present")
        return
    target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    # Both placeholders are supplied per episode by the runner, so the file itself carries
    # no endpoint and no secret.
    placeholders = sorted(set(re.findall(r"\$\{([A-Z_][A-Z0-9_]*)\}", target.read_text())))
    print(
        f"✓ wrote {target.relative_to(REPO_ROOT)} (bound per episode via {', '.join(placeholders)})"
    )


def report_data_dir() -> None:
    data_dir = VENDOR_DIR / "data"
    if not (data_dir / "tau2" / "domains").is_dir():
        fail(f"expected domain data at {data_dir}/tau2/domains")
    domains = sorted(p.name for p in (data_dir / "tau2" / "domains").iterdir() if p.is_dir())
    print(f"✓ TAU2_DATA_DIR={data_dir}")
    print(f"  domains: {', '.join(domains)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="emit resolved paths as JSON on the last line"
    )
    args = parser.parse_args()

    lock = read_lock()
    print(f"bootstrap: reproducing benchmark lane from {LOCK_PATH.name}")
    ensure_checkout(lock)
    ensure_environment()
    ensure_mcp_binding()
    report_data_dir()

    if args.json:
        print(
            json.dumps(
                {
                    "vendor_dir": str(VENDOR_DIR),
                    "data_dir": str(VENDOR_DIR / "data"),
                    "commit": lock["commit"],
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
