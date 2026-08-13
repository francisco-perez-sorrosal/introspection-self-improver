#!/usr/bin/env python3
"""Record the A.0a pipe-semantics verdict (v2 §4 W4).

A.0a claims the bridge and transports preserve tool calls, arguments, results and message
boundaries exactly. The evidence is the adapter test suite — the name transform pinned
byte-for-byte against the platform's JS implementation, the AG-UI contract pinned against
captured live event shapes, the mailbox and reset semantics — plus the mock end-to-end
smoke. This script runs both and writes the verdict under the generation's gates/ directory,
because a gate that only ever passed in a terminal is a gate nobody can cite. Blocking:
a failure stops the experiment (v2 §4 W4).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter.lock import BENCHMARK_DIR, REPO_ROOT


def _repo_head() -> str:
    return subprocess.run(  # noqa: S603, S607
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gen-dir",
        required=True,
        help="the generation directory the verdict is recorded under (…/generation_NNN)",
    )
    args = parser.parse_args()
    gen_dir = Path(args.gen_dir).resolve()

    print("── A.0a: adapter suite")
    suite = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "tests", "-q"],
        cwd=BENCHMARK_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    suite_summary = (suite.stdout or "").strip().splitlines()[-1:] or ["(no output)"]
    print(f"   {suite_summary[0]}")

    print("── A.0a: mock end-to-end smoke (local lane)")
    smoke = subprocess.run(  # noqa: S603, S607
        ["make", "--no-print-directory", "smoke", "TRANSPORT=local", f"GEN={gen_dir.name}"],
        cwd=REPO_ROOT,
        check=False,
    )

    episodes: list[dict] = []
    smoke_metadata = gen_dir / "mock_smoke" / "run_metadata.json"
    if smoke_metadata.exists():
        episodes = json.loads(smoke_metadata.read_text(encoding="utf-8")).get("episodes") or []
    smoke_completed = bool(episodes) and all(e.get("completed") for e in episodes)

    passed = suite.returncode == 0 and smoke.returncode == 0 and smoke_completed
    verdict = {
        "gate": "A.0a",
        "passed": passed,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "adapter_sha": _repo_head(),
        "suite": {"returncode": suite.returncode, "summary": suite_summary[0]},
        "smoke": {
            "returncode": smoke.returncode,
            "episodes": episodes,
            "completed": smoke_completed,
        },
    }
    gates_dir = gen_dir / "gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    (gates_dir / "a0a.json").write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    (gates_dir / "a0a.md").write_text(
        f"# A.0a — pipe semantics: {'PASS' if passed else 'FAIL'}\n\n"
        f"- recorded {verdict['generated']}, adapter at `{verdict['adapter_sha'][:12]}`\n"
        f"- adapter suite: {suite_summary[0]}\n"
        f"- mock smoke: rc={smoke.returncode}, "
        f"{'all episodes completed' if smoke_completed else 'DID NOT COMPLETE'}\n\n"
        "A.0a claims the bridge and transports preserve tool calls, arguments, results and\n"
        "message boundaries exactly. Blocking: a failure stops the experiment (v2 §4 W4).\n",
        encoding="utf-8",
    )
    print(f"\n── A.0a {'PASS' if passed else 'FAIL'} → {gates_dir / 'a0a.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
