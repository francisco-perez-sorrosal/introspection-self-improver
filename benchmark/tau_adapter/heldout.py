"""Held-out rounds: the vault, the muted stages, and the completeness report.

A held-out evaluation is the one measurement the orchestrator must not see
(SIA_EVALUATION_PLAN.md D1/D9). This module is the machinery behind scripts/run_heldout.py:
it owns the out-of-tree vault layout, drives the runner and the grader as child processes
whose every output line lands in the vault's console.log, and reduces what the terminal
shows to completeness — episodes expected and completed, artifacts present — with not one
graded figure. The stages are idempotent: a measured round is not re-run (one measurement
per generation), an ungraded run is graded, and a rerun after an interruption resumes τ's
own checkpoint. Nothing here reads a graded value; row counts are the only thing computed
from the vault's contents.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

from tau_adapter import manifest as manifestmod
from tau_adapter import split as splitmod
from tau_adapter.experiment import COMPLETION_SENTINEL, CONSOLE_LOG
from tau_adapter.lock import BENCHMARK_DIR, Lock

VAULT_ENV = "SIA_VAULT_DIR"
DEFAULT_VAULT = Path.home() / ".sia_vault"
GRADED_DIR = "graded"
#: τ's evaluator names its output `updated_<input filename>`; the runner's file is results.json.
GRADED_RESULTS = "updated_results.json"

#: A child-process runner: argv plus the open console-log handle both streams go to.
RunChild = Callable[[list[str], IO[str]], int]


def vault_root() -> Path:
    """`~/.sia_vault`, or `SIA_VAULT_DIR` when set (tests, relocated vaults)."""
    override = os.environ.get(VAULT_ENV)
    return Path(override) if override else DEFAULT_VAULT


def round_dir_for(lock: Lock, generation: str, root: Path | None = None) -> Path:
    """The one directory a generation's held-out artifacts live in (D9)."""
    return (root or vault_root()) / f"experiment_{lock.experiment_id}" / generation


def run_round(
    lock: Lock,
    generation: str,
    *,
    root: Path | None = None,
    manifest: dict[str, Any] | None = None,
    run_child: RunChild | None = None,
) -> int:
    """Drive one held-out round through its idempotent stages; print completeness only."""
    if not generation.startswith("generation"):
        raise SystemExit(
            f"{generation!r} is not a generation directory name (generation_NNN): the vault "
            "and the run's labels both key on it."
        )
    manifest = splitmod.load_manifest() if manifest is None else manifest
    held_ids = list(manifest.get(splitmod.HELD_OUT) or [])
    if not held_ids:
        raise SystemExit(
            "the partition manifest holds no held_out list; propose and freeze one with "
            "scripts/propose_split.py before running a held-out round"
        )
    round_dir = round_dir_for(lock, generation, root)
    round_dir.mkdir(parents=True, exist_ok=True)
    console_path = round_dir / CONSOLE_LOG
    run_child = run_child or _default_run_child

    expected_episodes = len(held_ids) * lock.num_trials
    already_measured = (round_dir / COMPLETION_SENTINEL).exists()
    if already_measured and not _measurement_complete(round_dir, expected_episodes):
        # τ's runner returned, but the round holds non-measurements — e.g. an
        # infrastructure_error placeholder that τ's own resume replaces. The sentinel
        # means "runner returned", never "measured": drop it, and the grading derived
        # from the incomplete results, so the documented interrupted-run path resumes.
        # Completed episodes are not re-spent, and a complete round never reaches here.
        (round_dir / COMPLETION_SENTINEL).unlink()
        shutil.rmtree(round_dir / GRADED_DIR, ignore_errors=True)
        already_measured = False
    if not already_measured:
        rc = _run_stage(_runner_argv(round_dir), console_path, run_child)
        if rc != 0:
            print(_failure_notice("runner", rc, round_dir, generation))
            return rc or 1
    graded_path = round_dir / GRADED_DIR / GRADED_RESULTS
    if not graded_path.exists() and (round_dir / "results.json").exists():
        rc = _run_stage(_grade_argv(round_dir), console_path, run_child)
        if rc != 0:
            print(_failure_notice("grading", rc, round_dir, generation))
            return 1

    report, complete = completeness_report(
        experiment_id=lock.experiment_id,
        generation=generation,
        round_dir=round_dir,
        expected_tasks=len(held_ids),
        num_trials=lock.num_trials,
        rows=manifestmod.read_manifest(round_dir),
        graded_present=graded_path.exists(),
        already_measured=already_measured,
        incident_totals=_incident_totals(round_dir),
    )
    print(report)
    return 0 if complete else 1


def _measurement_complete(round_dir: Path, expected: int) -> bool:
    """Row counts only, per this module's vault doctrine — nothing graded is read."""
    rows = manifestmod.read_manifest(round_dir)
    return sum(1 for row in rows if row.get("completed")) >= expected


def _incident_totals(round_dir: Path) -> dict[str, int] | None:
    """The round's seam-incident counters, projected out of the sealed record.

    run_metadata.json carries graded values elsewhere in the file; only the counters leave
    this function. This is what lets a sealed round still answer the attribution question —
    was the seam healthy? — without anyone opening the console log.
    """
    path = round_dir / COMPLETION_SENTINEL
    if not path.exists():
        return None
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    totals = (meta.get("incidents") or {}).get("totals") or {}
    return {key: int(value) for key, value in totals.items()}


def completeness_report(
    *,
    experiment_id: str,
    generation: str,
    round_dir: Path,
    expected_tasks: int,
    num_trials: int,
    rows: list[dict[str, Any]],
    graded_present: bool,
    already_measured: bool,
    incident_totals: dict[str, int] | None = None,
) -> tuple[str, bool]:
    """The terminal's entire view of a held-out round. Counts, paths — nothing graded."""
    expected = expected_tasks * num_trials
    completed = sum(1 for row in rows if row.get("completed"))
    complete = completed >= expected and graded_present
    title = f"\n── held-out round: {experiment_id} {generation}"
    if already_measured:
        title += " — already measured (one measurement per generation)"
    lines = [
        title,
        f"   vault         {_display(round_dir)}",
        f"   console       {CONSOLE_LOG} — every runner and grading line, sealed in the vault",
        f"   episodes      {completed}/{expected} completed"
        f" ({expected_tasks} task(s) x {num_trials} trial(s))"
        + ("" if completed >= expected else " — INCOMPLETE" + _failure_classes(rows)),
        f"   manifest      {manifestmod.MANIFEST_NAME}: {len(rows)} row(s)",
        f"   incidents     {_incident_text(incident_totals)}",
        (
            f"   graded        {GRADED_DIR}/{GRADED_RESULTS} — persisted, not shown"
            if graded_present
            else f"   graded        MISSING — {GRADED_DIR}/{GRADED_RESULTS} was not produced"
        ),
        "",
    ]
    if complete:
        lines += [
            "   Nothing graded is shown here. The vault is read at reveal (make reveal),",
            "   never before — SIA_EVALUATION_PLAN.md D1/D9.",
        ]
    else:
        lines += [
            f"   Rerun `make heldout GEN={generation}` to resume: τ re-runs only the",
            "   missing (trial, task, seed) pairs and replaces infrastructure_error",
            "   placeholders; completed episodes are not re-spent.",
        ]
    return "\n".join(lines), complete


def _failure_classes(rows: list[dict[str, Any]]) -> str:
    """Termination and cause classes of the non-completed rows — infrastructure facts,
    never graded outcomes, so an incomplete round names its failure mode without anyone
    opening the vault. The cause is the exception class alone; free-text error messages
    stay in the sealed record."""
    classes: Counter[str] = Counter()
    for row in rows:
        if row.get("completed"):
            continue
        name = str(row.get("termination"))
        error_type = (row.get("failure") or {}).get("error_type")
        classes[f"{name}:{error_type}" if error_type else name] += 1
    if not classes:
        return ""
    return " (" + ", ".join(f"{name}={count}" for name, count in sorted(classes.items())) + ")"


def _incident_text(totals: dict[str, int] | None) -> str:
    """One line of seam health. Counters are infrastructure facts, never graded outcomes."""
    if totals is None:
        return "unknown — the run left no metadata"
    noted = ", ".join(f"{key}={value}" for key, value in sorted(totals.items()) if value)
    return f"{noted} — seam counters, not graded outcomes" if noted else "none"


def _runner_argv(round_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(BENCHMARK_DIR / "tau_adapter" / "run.py"),
        "--heldout",
        "--out",
        str(round_dir),
    ]


def _grade_argv(round_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(BENCHMARK_DIR / "scripts" / "grade.py"),
        str(round_dir / "results.json"),
        "--output-dir",
        str(round_dir / GRADED_DIR),
        "--quiet",
    ]


def _run_stage(argv: list[str], console_path: Path, run_child: RunChild) -> int:
    """One child process, everything it says appended to the vault's console log."""
    with console_path.open("a", encoding="utf-8") as console:
        console.write(f"\n===== {datetime.now(UTC).isoformat()} $ {' '.join(argv)}\n")
        console.flush()
        return run_child(argv, console)


def _default_run_child(argv: list[str], console: IO[str]) -> int:
    proc = subprocess.run(  # noqa: S603 - argv is built above from repo paths, not input
        argv,
        cwd=BENCHMARK_DIR,
        stdout=console,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode


def _failure_notice(stage: str, rc: int, round_dir: Path, generation: str) -> str:
    return (
        f"\n── held-out round: the {stage} exited {rc} before completion.\n"
        f"   vault         {_display(round_dir)}\n"
        f"   Rerun `make heldout GEN={generation}` to resume — τ re-runs only what is\n"
        f"   missing. {CONSOLE_LOG} holds the full trace, but it may already carry graded\n"
        "   output for finished episodes: prefer resuming over reading it, and record\n"
        "   any read in the experiment record."
    )


def _display(path: Path) -> str:
    """Home-relative for the terminal; the absolute path stays in the artifacts."""
    home = str(Path.home())
    text = str(path)
    return "~" + text.removeprefix(home) if text.startswith(home) else text
