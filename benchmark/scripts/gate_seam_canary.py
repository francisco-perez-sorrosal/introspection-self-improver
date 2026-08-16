#!/usr/bin/env python3
"""Record the platform seam-canary verdict — the gate the local A.0a cannot be.

A.0a proves the adapter's semantics on the local lane; it structurally cannot exercise the
`introspection dev` tunnel, the sandbox MCP daemon, or its patience. The 2026-08-15
disconnect regression passed 309 tests and a mock smoke while denying platform agents their
tools, and it was found by a human reading a conversation. This gate closes that hole: one
canary run of a non-partition task on the platform lane, judged on the seam counters the
regression forced into existence, its verdict recorded so a batch round can refuse to start
against an unvalidated seam (see run.py::_seam_canary_problem).

Pass condition — on every episode that produced a conversation: all four sandbox seam
counters zero and `evidence_complete` true; and at least one such episode exists. τ
infrastructure placeholders (provider weather, e.g. user-sim empty completions) are
REPORTED but do not fail the gate: they are frozen-surface weather, not seam health — the
infra classes in the verdict are the operator's go/no-go weather read.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tau_adapter.experiment import RESULTS_ROOT
from tau_adapter.lock import BENCHMARK_DIR, REPO_ROOT, load_lock

#: The counters the canary judges. Any nonzero value on any episode fails the gate.
SEAM_COUNTERS = (
    "sandbox_seam_disconnects",
    "sandbox_seam_timeouts",
    "sandbox_seam_unclassified",
    "sandbox_tool_errors",
)


def _repo_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout.strip()


def judge(rows: list[dict]) -> tuple[bool, list[str]]:
    """The verdict over manifest rows: (passed, findings). Pure, so it is testable."""
    findings: list[str] = []
    verifiable = [row for row in rows if row.get("evidence_complete") is True]
    completed = [row for row in rows if row.get("completed")]
    for row in rows:
        for counter in SEAM_COUNTERS:
            if row.get(counter):
                findings.append(
                    f"trial {row.get('trial')}: {counter}={row[counter]} — the seam failed"
                )
    for row in completed:
        if row.get("evidence_complete") is not True:
            findings.append(
                f"trial {row.get('trial')}: completed but its conversation is missing or "
                "incomplete — an unverifiable episode cannot attest the seam"
            )
    if not verifiable:
        findings.append("no episode produced a complete conversation — nothing attests the seam")
    return (not findings), findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        default="task_001",
        help=(
            "τ task id for the canary. Must not sit in the current experiment's unrevealed "
            "held-out set — run.py's firewall guard refuses that combination."
        ),
    )
    args = parser.parse_args()

    lock = load_lock()
    experiment_dir = RESULTS_ROOT / f"experiment_{lock.experiment_id}"
    out_dir = experiment_dir / "generation_000" / "seam_canary"

    print(f"── seam canary: {args.task} on the platform lane → {out_dir}")
    run = subprocess.run(
        [
            sys.executable,
            "tau_adapter/run.py",
            "--task-ids",
            args.task,
            "--transport",
            "platform",
            "--out",
            str(out_dir),
            "--overwrite",
        ],
        cwd=BENCHMARK_DIR,
        check=False,
    )
    if run.returncode != 0:
        print(f"✗ canary run exited {run.returncode}; no verdict recorded", file=sys.stderr)
        return 1

    manifest_path = out_dir / "episode_manifest.jsonl"
    rows = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    passed, findings = judge(rows)
    infra = {}
    for row in rows:
        failure = row.get("failure") or {}
        if failure:
            infra[str(failure.get("error_type"))] = infra.get(str(failure.get("error_type")), 0) + 1

    verdict = {
        "gate": "seam-canary",
        "passed": passed,
        "generated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "adapter_sha": _repo_head(),
        "task": args.task,
        "findings": findings,
        "infra_failures": infra,
        "episodes": [
            {
                "trial": row.get("trial"),
                "completed": row.get("completed"),
                "evidence_complete": row.get("evidence_complete"),
                **{counter: row.get(counter) for counter in SEAM_COUNTERS},
                "bridge_calls": row.get("bridge_calls"),
                "bridge_park_max_seconds": row.get("bridge_park_max_seconds"),
            }
            for row in rows
        ],
    }
    gates_dir = experiment_dir / "gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    (gates_dir / "seam_canary.json").write_text(
        json.dumps(verdict, indent=2) + "\n", encoding="utf-8"
    )
    (gates_dir / "seam_canary.md").write_text(
        f"# Seam canary — {'PASS' if passed else 'FAIL'}\n\n"
        f"- recorded {verdict['generated']}, adapter at `{verdict['adapter_sha'][:12]}`\n"
        f"- {args.task}, {len(rows)} episode(s); findings: "
        f"{'; '.join(findings) if findings else 'none'}\n"
        f"- infra weather (does not gate): {infra or 'none'}\n",
        encoding="utf-8",
    )
    status = "PASS" if passed else "FAIL"
    print(f"\n── seam canary {status} → {gates_dir / 'seam_canary.json'}")
    for finding in findings:
        print(f"   ✗ {finding}", file=sys.stderr)
    if infra:
        print(f"   weather (non-gating): {infra} — consider holding rounds until it clears")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
