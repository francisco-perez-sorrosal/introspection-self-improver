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


def _graded_tool_calls(simulations: list[dict]) -> list[tuple[str, object]]:
    """(tool name, turn_idx) for every tool call in τ's graded trajectory."""
    calls: list[tuple[str, object]] = []
    for simulation in simulations or []:
        for message in simulation.get("messages") or []:
            for call in message.get("tool_calls") or []:
                if call.get("name"):
                    calls.append((call["name"], message.get("turn_idx")))
    return calls


def suppression_judge(
    rows: list[dict], simulations: list[dict], expect_tool: str
) -> tuple[bool, list[str]]:
    """The D24 suppressing-path verdict: seam health, plus engagement, plus no leak.

    Seam-health findings carry over from judge(); on top of them the suppressing path must
    have ENGAGED (≥1 manifest row with pi_local_calls ≥ 1 — a canary the model never
    called attests nothing) and the expected tool name must be absent from τ's graded
    trajectory (a registered name that τ saw is a suppression leak). Pure, so testable.
    """
    _, findings = judge(rows)
    findings = list(findings)
    if not any((row.get("pi_local_calls") or 0) >= 1 for row in rows):
        findings.append(
            f"no episode recorded a Pi-local call — the model never called "
            f"'{expect_tool}', so the suppressing path never engaged and nothing attests it"
        )
    leaked_turns = [turn for name, turn in _graded_tool_calls(simulations) if name == expect_tool]
    if leaked_turns:
        findings.append(
            f"'{expect_tool}' appears in τ's graded trajectory "
            f"(turns {leaked_turns}) — suppression leaked"
        )
    return (not findings), findings


def _read_rows(manifest_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _suppression_main(args: argparse.Namespace, experiment_dir: Path) -> int:
    """The pre-freeze D24 suppressing-path canary (or a zero-episode re-judge).

    Needs a recipe on pushed main whose registry declares --expect-tool and whose
    instructions nudge one call — the suppressing path only exists where the model calls a
    registered tool. Run it as a pre-freeze groundwork event (temporary declaration,
    reverted before h0-baseline is tagged), or re-judge the experiment's first real tool
    generation with --judge-only <round dir> at zero extra episodes.
    """
    if args.judge_only is not None:
        out_dir = args.judge_only
        if not out_dir.is_absolute():
            out_dir = (REPO_ROOT / out_dir).resolve()
        print(f"── suppression canary: judge-only over {out_dir}")
    else:
        out_dir = experiment_dir / "generation_000" / "suppression_canary"
        print(f"── suppression canary: {args.task} on the platform lane → {out_dir}")
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

    rows = _read_rows(out_dir / "episode_manifest.jsonl")
    results_path = out_dir / "results.json"
    if results_path.is_file():
        simulations = json.loads(results_path.read_text(encoding="utf-8")).get("simulations", [])
        passed, findings = suppression_judge(rows, simulations, args.expect_tool)
    else:
        passed, findings = (
            False,
            [
                f"no graded trajectory at {results_path} — the leak check cannot run, and "
                "'could not check' must never grade as 'checked and clean'"
            ],
        )

    verdict = {
        "gate": "suppression-canary",
        "passed": passed,
        "generated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "adapter_sha": _repo_head(),
        "expect_tool": args.expect_tool,
        "round_dir": str(out_dir),
        "judge_only": args.judge_only is not None,
        "findings": findings,
        "episodes": [
            {
                "trial": row.get("trial"),
                "completed": row.get("completed"),
                "evidence_complete": row.get("evidence_complete"),
                "pi_local_calls": row.get("pi_local_calls"),
                **{counter: row.get(counter) for counter in SEAM_COUNTERS},
            }
            for row in rows
        ],
    }
    gates_dir = experiment_dir / "gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    (gates_dir / "suppression_canary.json").write_text(
        json.dumps(verdict, indent=2) + "\n", encoding="utf-8"
    )
    (gates_dir / "suppression_canary.md").write_text(
        f"# Suppression canary — {'PASS' if passed else 'FAIL'}\n\n"
        f"- recorded {verdict['generated']}, adapter at `{verdict['adapter_sha'][:12]}`\n"
        f"- expected tool `{args.expect_tool}`, {len(rows)} episode(s), "
        f"{'re-judged' if verdict['judge_only'] else 'fresh run'} at `{out_dir}`\n"
        f"- findings: {'; '.join(findings) if findings else 'none'}\n",
        encoding="utf-8",
    )
    status = "PASS" if passed else "FAIL"
    print(f"\n── suppression canary {status} → {gates_dir / 'suppression_canary.json'}")
    for finding in findings:
        print(f"   ✗ {finding}", file=sys.stderr)
    return 0 if passed else 1


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
    parser.add_argument(
        "--suppression",
        action="store_true",
        help=(
            "judge the D24 suppressing path instead of bare seam health: requires "
            "--expect-tool; verdict lands in gates/suppression_canary.json (sibling file — "
            "seam_canary.json and its staleness semantics are untouched)"
        ),
    )
    parser.add_argument(
        "--expect-tool",
        default=None,
        help="registered Pi-local tool name the canary episode is expected to call",
    )
    parser.add_argument(
        "--judge-only",
        type=Path,
        default=None,
        help=(
            "re-judge an existing round directory at zero episodes (suppression mode only); "
            "relative paths resolve against the repo root"
        ),
    )
    args = parser.parse_args()
    if args.suppression and not args.expect_tool:
        parser.error("--suppression requires --expect-tool <registered tool name>")
    if args.judge_only is not None and not args.suppression:
        parser.error("--judge-only is a suppression-mode flag; pass --suppression")

    lock = load_lock()
    experiment_dir = RESULTS_ROOT / f"experiment_{lock.experiment_id}"
    if args.suppression:
        return _suppression_main(args, experiment_dir)
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

    rows = _read_rows(out_dir / "episode_manifest.jsonl")
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
