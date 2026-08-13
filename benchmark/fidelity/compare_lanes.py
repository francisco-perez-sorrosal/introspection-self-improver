#!/usr/bin/env python3
"""Compare graded runs of the same tasks across lanes and say which differences matter.

    python fidelity/compare_lanes.py <run_dir> <run_dir> [--gate] [--verdict-out PATH]

Exits non-zero when an adapter invariant fails in any episode, and — under --gate — when the
lanes' aggregate pass rates disagree beyond trial noise. A single episode's reward is never a
verdict: per-task reward is a draw (§3.1), so the single-task `make fidelity` reports rewards
without judging them, while the A.0b gate (`make fidelity_gate`) compares aggregates over a
task set × the frozen trial count, where "within noise" at least has a defined meaning —
overlapping 95% Wilson intervals on pass¹. At gate N that is a deliberately coarse
instrument; the verdict file records the N so nobody mistakes agreement for power.

This is the §15 Phase A.0 instrument applied to the two transports rather than to a stock τ
agent. It cannot prove the lanes score alike — nothing can, against an unseedable agent — but
it can prove the adapter did not change the graded surface, which is the part that would
invalidate every generation silently.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lane_report import (
    EpisodeReport,
    LaneAggregate,
    aggregate,
    build_reports,
    check_invariants,
    locked_tool_names,
    within_noise,
)


def _lane_of(run_dir: Path) -> str:
    """Read the lane from the run's own metadata rather than guessing from the directory name."""
    metadata = run_dir / "run_metadata.json"
    if metadata.exists():
        return str(json.loads(metadata.read_text(encoding="utf-8")).get("transport") or "unknown")
    return "unknown"


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
    interval = (
        f" [{summary.interval[0]:.2f}, {summary.interval[1]:.2f}]" if summary.interval else ""
    )
    print(
        f"   aggregate: pass¹={summary.pass1}{interval} over {summary.graded} graded "
        f"({summary.successes} success(es)); mean messages {summary.mean_messages}"
    )
    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", help="run directories holding results.json")
    parser.add_argument(
        "--gate",
        action="store_true",
        help="A.0b mode: aggregate disagreement beyond trial noise is a failure, not a note",
    )
    parser.add_argument(
        "--verdict-out",
        default=None,
        help="write a machine-readable verdict JSON here (the gates/ record)",
    )
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
        reports = build_reports(results, lane=_lane_of(run_dir), locked_tools=locked)
        summary = aggregate(reports)
        lanes.append((reports, summary))
        ok = _print_lane(reports, summary) and ok

    noise_verdict: bool | None = None
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
        noise_verdict = within_noise(first, second)
        if noise_verdict is None:
            print("     [info] aggregate agreement not assessable (a lane graded nothing)")
            if args.gate:
                ok = False
        elif args.gate:
            mark = "PASS" if noise_verdict else "FAIL"
            print(
                f"     [{mark}] pass¹ agreement within trial noise: "
                f"{first.lane} {first.pass1} vs {second.lane} {second.pass1} "
                "(overlapping 95% Wilson intervals — coarse at this N, and recorded as such)"
            )
            ok = ok and noise_verdict
        else:
            print(
                f"     [info] pass¹ {first.lane}={first.pass1} vs {second.lane}={second.pass1}. "
                "Not a verdict below gate scale: per-task reward is a draw."
            )

    if args.verdict_out:
        verdict_path = Path(args.verdict_out).resolve()
        verdict_path.parent.mkdir(parents=True, exist_ok=True)
        verdict_path.write_text(
            json.dumps(
                {
                    "gate": "A.0b" if args.gate else "fidelity",
                    "passed": ok,
                    "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "runs": [str(Path(r).resolve()) for r in args.runs],
                    "lanes": [
                        {
                            "lane": s.lane,
                            "episodes": s.episodes,
                            "graded": s.graded,
                            "successes": s.successes,
                            "pass1": s.pass1,
                            "wilson95": list(s.interval) if s.interval else None,
                            "mean_messages": s.mean_messages,
                        }
                        for _, s in lanes
                    ],
                    "within_noise": noise_verdict,
                    "note": (
                        "within_noise means overlapping 95% Wilson intervals on pass¹; at "
                        "gate N this bounds gross divergence only, not equivalence"
                    ),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"\n   verdict → {verdict_path}")

    print(
        "\n"
        + ("adapter invariants hold" if ok else "ADAPTER INVARIANT FAILED — scores are not valid")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
