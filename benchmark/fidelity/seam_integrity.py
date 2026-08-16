#!/usr/bin/env python3
"""Per-episode seam-integrity audit over a run directory. On-demand diagnostic, not a gate.

Compares the bridge's own per-call record (`bridge_calls.jsonl`, the seam's ground truth:
every arrival, park duration, outcome and result digest) against τ's record of the same
episodes (`results.json` tool messages). The failure classes this can show are the ones
that otherwise grade as agent behaviour:

  count drift     τ recorded more tool results than the bridge served (fabrication /
                  replay) or fewer (a result produced but never consumed).
  cross-talk      calls joined to one episode interleaving into another's τ record — the
                  channel keyspace makes this structurally hard, and this audit is the
                  evidence it stayed that way.
  park pathology  calls the daemon waited long on (the `mcp upstream timed out` precursor;
                  seq 5's batches counted 6 and 4 of those per 24-episode round).

Usage: python fidelity/seam_integrity.py <run_dir> [--park-warn SECONDS]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def load_rows(run_dir: Path) -> list[dict]:
    manifest = run_dir / "episode_manifest.jsonl"
    return [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_calls(run_dir: Path) -> list[dict]:
    path = run_dir / "bridge_calls.jsonl"
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def audit(rows: list[dict], calls: list[dict], park_warn: float) -> list[str]:
    """The findings, as printable strings; empty means the seam record is coherent."""
    findings: list[str] = []
    served: dict[str, int] = defaultdict(int)
    unattributed = 0
    for call in calls:
        if call.get("outcome", "").startswith("refused"):
            continue
        episode = call.get("episode")
        if episode:
            served[episode] += 1
        else:
            unattributed += 1
        duration = float(call.get("duration_seconds") or 0.0)
        if duration >= park_warn:
            findings.append(
                f"park {duration:.1f}s ≥ {park_warn:.0f}s on {call.get('tool')} "
                f"(episode {episode or '?'}, outcome {call.get('outcome')}) — daemon-patience "
                f"territory, the seam-timeout precursor"
            )
    if not served:
        # No call joined to any episode: the local lane (its transport exposes no channel
        # token) or a run predating the join. Park pathology above still stands; the
        # per-episode comparisons would all be false drift, so they are skipped, and
        # skipping is said out loud rather than passed off as a clean audit.
        findings.append(
            "info: no episode join available (local lane or pre-join run) — per-episode "
            "count audit skipped"
        )
        return findings
    for row in rows:
        ref = row.get("pi_session_ref")
        if not ref:
            continue
        tool_messages = row.get("tool_messages")
        if tool_messages is None:
            continue
        if ref in served and served[ref] != tool_messages:
            findings.append(
                f"count drift on {row.get('tau_task_id')} trial {row.get('trial')}: bridge "
                f"served {served[ref]} call(s), τ recorded {tool_messages} tool message(s) — "
                f"either a result τ consumed that the bridge never served, or the reverse"
            )
        elif ref not in served and row.get("transport") == "platform" and tool_messages:
            findings.append(
                f"{row.get('tau_task_id')} trial {row.get('trial')}: τ recorded "
                f"{tool_messages} tool message(s) but no bridge call joined to this episode "
                f"— dead-tunnel signature, or the token join failed"
            )
    if unattributed:
        findings.append(
            f"{unattributed} bridge call(s) joined to no episode — token unknown to any "
            f"transport; if the round was healthy this should be zero"
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="a round directory holding results.json")
    parser.add_argument(
        "--park-warn",
        type=float,
        default=20.0,
        help="flag bridge parks at or above this many seconds (default 20)",
    )
    args = parser.parse_args()

    rows = load_rows(args.run_dir)
    calls = load_calls(args.run_dir)
    if not calls:
        print(
            "no bridge_calls.jsonl in this run (pre-dates the call log); "
            "only τ-side data exists and no audit is possible"
        )
        return 0
    findings = audit(rows, calls, args.park_warn)
    print(f"{len(rows)} episode row(s), {len(calls)} bridge call(s)")
    notes = [f for f in findings if f.startswith("info:")]
    problems = [f for f in findings if not f.startswith("info:")]
    for note in notes:
        print(f"  {note}")
    if not problems:
        print("✓ seam record coherent: counts agree, no unattributed calls, no long parks")
        return 0
    for problem in problems:
        print(f"  ✗ {problem}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
