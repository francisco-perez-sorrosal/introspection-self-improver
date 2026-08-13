#!/usr/bin/env python3
"""Compare two graded runs of the same task and say which differences matter.

    python fidelity/compare_lanes.py results/<gen>/task_001 results/<gen>/task_001_platform

Exits non-zero only when an adapter invariant fails. A different reward, a different trajectory
shape or a different message count is *not* a failure: per-task reward here is a draw, so the
comparison reports those and refuses to draw a conclusion from them.

This is the §15 Phase A.0 instrument applied to the two transports rather than to a stock τ agent.
It cannot prove the lanes score alike — nothing can, at n=1 against a stochastic agent — but it can
prove the adapter did not change the graded surface, which is the part that would invalidate every
generation silently.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lane_report import EpisodeReport, build_report, check_invariants, locked_tool_names


def _lane_of(run_dir: Path) -> str:
    """Read the lane from the run's own metadata rather than guessing from the directory name."""
    import json

    metadata = run_dir / "run_metadata.json"
    if metadata.exists():
        return str(json.loads(metadata.read_text(encoding="utf-8")).get("transport") or "unknown")
    return "unknown"


def _print_report(report: EpisodeReport) -> bool:
    print(f"\n── {report.lane}  (task {report.task_id})")
    print("   adapter-owned")
    all_ok = True
    for finding in check_invariants(report):
        mark = "PASS" if finding.ok else "FAIL"
        all_ok = all_ok and finding.ok
        print(f"     [{mark}] {finding.check}: {finding.detail}")
    print("   sampling-owned (reported, never asserted)")
    print(f"     reward            {report.reward}")
    print(f"     messages          {report.messages}")
    print(f"     agent invocations {report.agent_invocations}")
    print(f"     agent tools used  {', '.join(report.agent_tool_names) or '(none)'}")
    print(f"     user tools used   {', '.join(report.user_tool_names) or '(none)'}")
    print(f"     shape             {report.shape}")
    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", help="run directories holding results.json")
    args = parser.parse_args()

    locked = locked_tool_names()
    reports: list[EpisodeReport] = []
    ok = True
    for raw in args.runs:
        run_dir = Path(raw).resolve()
        results = run_dir / "results.json"
        if not results.exists():
            print(f"── {run_dir}: no results.json; skipped")
            ok = False
            continue
        report = build_report(results, lane=_lane_of(run_dir), locked_tools=locked)
        reports.append(report)
        ok = _print_report(report) and ok

    if len(reports) >= 2:
        print("\n── across lanes")
        tasks = {r.task_id for r in reports}
        if len(tasks) > 1:
            print(f"     [FAIL] different tasks compared: {sorted(tasks)}")
            ok = False
        else:
            print(f"     [PASS] same task in every lane: {tasks.pop()}")

        surfaces = {tuple(r.agent_tool_names) for r in reports}
        # The tool *surface* is adapter-owned; which subset a given episode happens to call is not.
        offered = {name for r in reports for name in r.agent_tool_names}
        unmapped = offered - locked
        print(
            f"     [{'PASS' if not unmapped else 'FAIL'}] every agent tool across lanes is locked"
            + (f": unexpected {sorted(unmapped)}" if unmapped else "")
        )
        ok = ok and not unmapped
        if len(surfaces) > 1:
            print("     [info] the lanes called different subsets of tools — expected: the agent")
            print("            chooses, and its sampling is not reproducible from τ's seed")

        rewards = [r.reward for r in reports]
        if len(set(rewards)) > 1:
            print(f"     [info] rewards differ ({rewards}). Not a verdict: a per-task reward here")
            print("            is a draw, so neither agreement nor disagreement is evidence.")

    print(
        "\n"
        + ("adapter invariants hold" if ok else "ADAPTER INVARIANT FAILED — scores are not valid")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
