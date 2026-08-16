#!/usr/bin/env python3
"""Compare graded runs of the same tasks across lanes and say which differences matter.

    python fidelity/compare_lanes.py <run_dir> <run_dir>

Exits non-zero when an adapter invariant fails in any episode. A single episode's reward is
never a verdict — per-task reward is a draw — so rewards and aggregates are reported as
facts, never judged. This is the on-demand cross-lane diagnostic (SIA_EVALUATION_PLAN.md
D4): it cannot prove the lanes score alike — nothing can, against an unseedable agent — but
it can prove the adapter did not change the graded surface, which is the part that would
invalidate every generation silently.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lane_report import (
    EpisodeReport,
    LaneAggregate,
    aggregate,
    build_reports,
    check_invariants,
    locked_tool_names,
)


def _lane_of(run_dir: Path) -> str:
    """Read the lane from the run's own metadata rather than guessing from the directory name."""
    metadata = run_dir / "run_metadata.json"
    if metadata.exists():
        return str(json.loads(metadata.read_text(encoding="utf-8")).get("transport") or "unknown")
    return "unknown"


def _pi_local_of(run_dir: Path) -> set[str]:
    """The D24 suppression registry the run resolved, from its own metadata."""
    metadata = run_dir / "run_metadata.json"
    if metadata.exists():
        payload = json.loads(metadata.read_text(encoding="utf-8"))
        return {str(name) for name in (payload.get("pi_local_tools") or [])}
    return set()


def _print_lane(reports: list[EpisodeReport], summary: LaneAggregate) -> bool:
    print(f"\n── {summary.lane}  ({summary.episodes} episode(s))")
    all_ok = True
    for report in reports:
        findings = check_invariants(report)
        failures = [f for f in findings if not f.ok]
        mark = "PASS" if not failures else "FAIL"
        all_ok = all_ok and not failures
        trial = f" trial{report.trial}" if report.trial is not None else ""
        print(
            f"   [{mark}] {report.task_id}{trial}: termination={report.termination} "
            f"reward={report.reward} messages={report.messages}"
        )
        for finding in failures:
            print(f"          {finding.check}: {finding.detail}")
    print(
        f"   aggregate: pass¹={summary.pass1} over {summary.graded} graded "
        f"({summary.successes} success(es)); mean messages {summary.mean_messages}"
    )
    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", help="run directories holding results.json")
    args = parser.parse_args()

    locked = locked_tool_names()
    lanes: list[tuple[list[EpisodeReport], LaneAggregate]] = []
    ok = True
    for raw in args.runs:
        run_dir = Path(raw).resolve()
        results = run_dir / "results.json"
        if not results.exists():
            print(f"── {run_dir}: no results.json; skipped")
            ok = False
            continue
        reports = build_reports(
            results,
            lane=_lane_of(run_dir),
            locked_tools=locked,
            pi_local_tools=_pi_local_of(run_dir),
        )
        summary = aggregate(reports)
        lanes.append((reports, summary))
        ok = _print_lane(reports, summary) and ok

    if len(lanes) >= 2:
        print("\n── across lanes")
        keysets = [Counter((r.task_id, r.trial) for r in reports) for reports, _ in lanes]
        if any(k != keysets[0] for k in keysets[1:]):
            print("     [FAIL] the lanes ran different (task, trial) sets — nothing to compare")
            ok = False
        else:
            episodes = sum(keysets[0].values())
            print(f"     [PASS] same (task, trial) set in every lane ({episodes} episode(s))")

        offered = {name for reports, _ in lanes for r in reports for name in r.agent_tool_names}
        # The tool *surface* is adapter-owned; which subset a given episode happens to call is not.
        unmapped = offered - locked
        print(
            f"     [{'PASS' if not unmapped else 'FAIL'}] every agent tool across lanes is locked"
            + (f": unexpected {sorted(unmapped)}" if unmapped else "")
        )
        ok = ok and not unmapped

        first, second = lanes[0][1], lanes[1][1]
        print(
            f"     [info] pass¹ {first.lane}={first.pass1} vs {second.lane}={second.pass1}. "
            "Facts, not a verdict — per-task reward is a draw, and the protocol never "
            "compares lanes."
        )

    print(
        "\n"
        + ("adapter invariants hold" if ok else "ADAPTER INVARIANT FAILED — scores are not valid")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
