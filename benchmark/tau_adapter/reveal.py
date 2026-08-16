"""The reveal: the one sanctioned read of the vault, at the end of a configured experiment.

Runnable only once the final generation tag exists (protocol guardrail 19), it copies the
vault's held-out rounds into results/experiment_<id>/held_out/, computes the progression
artifacts — held-out count per generation, the task x generation matrix, per-transition
gains/retained/regressions/unresolved, the currently-solved vs ever-solved retention
diagnostic, the pre-registered trend test (D11) — writes summary.md with the D2 noise
band and the trend verdict, and fills every improvement
record's held_out_result. Identity generations (D5) carry their predecessor's result
forward and are labeled as carried, never re-measured; a vault measurement existing for
one is a protocol violation and refuses the reveal.

Pass means τ's full reward, exactly: a partial action reward is capability evidence but
not a solved task, and the protocol's metric is held-out tasks *passed* / T.
"""

from __future__ import annotations

import csv
import io
import itertools
import json
import math
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from tau_adapter import generations as gensmod
from tau_adapter import heldout as heldoutmod
from tau_adapter import process_metrics
from tau_adapter import records as recordsmod
from tau_adapter.experiment import COMPLETION_SENTINEL, SNAPSHOT_NAME
from tau_adapter.lock import Lock

PASS_THRESHOLD = 1.0 - 1e-9

HELD_OUT_DIRNAME = "held_out"
RESULTS_BY_GENERATION_CSV = "results_by_generation.csv"
TASK_GENERATION_MATRIX_CSV = "task_generation_matrix.csv"
TRANSITIONS_CSV = "transitions.csv"
RETENTION_CSV = "retention.csv"
TREND_TEST_JSON = "trend_test.json"
TREND_FRAGILITY_JSON = "trend_fragility.json"
SUMMARY_NAME = "summary.md"

#: Pre-registered before any seq-3 round (SIA_EVALUATION_PLAN.md D11): the one primary
#: significance test, fixed n, no interim looks. Changing it after data exists voids the
#: pre-registration — that is a new experiment, never a new alpha under the old one.
TREND_ALPHA = 0.05


class RevealError(RuntimeError):
    pass


@dataclass(frozen=True)
class GenerationResult:
    """One generation's held-out measurement, rate-native.

    ``stats`` maps task_id -> (passed_trials, trials). At one trial per task every rate
    is 0 or 1 and every derived quantity reduces exactly to the original binary
    semantics; at num_trials > 1 each cell is a per-task pass rate, which is what turns
    a coin flip into an estimate (plan D18).
    """

    generation: int
    stats: dict[str, tuple[int, int]]  # task_id -> (passed_trials, trials)
    carried: bool  # identity generation: predecessor's result, not a measurement

    def rate(self, task_id: str) -> float:
        passed_trials, trials = self.stats[task_id]
        return passed_trials / trials

    @property
    def rates(self) -> dict[str, float]:
        return {task_id: self.rate(task_id) for task_id in self.stats}

    @property
    def expected(self) -> float:
        """Expected solved-task count: the sum of per-task rates (an integer at 1 trial)."""
        return sum(self.rate(task_id) for task_id in self.stats)

    @property
    def trials(self) -> int:
        """Trials per task, uniform across the round (load_measured enforces it)."""
        return next(iter(self.stats.values()))[1] if self.stats else 1

    @property
    def label(self) -> str:
        return f"H{self.generation}"


def fmt_count(value: float) -> str:
    """Render an expected count: integral values as ints, else one decimal."""
    return f"{value:.0f}" if abs(value - round(value)) < 1e-9 else f"{value:.1f}"


def generation_dirname(generation: int) -> str:
    return f"generation_{generation:03d}"


def noise_band_pp(held_out_tasks: int, trials: int = 1) -> int:
    """One SE of the mean per-task rate at p=0.5, in percentage points (D2/D18):
    0.5/sqrt(T*n) — ≈7 pp at T=47 n=1, ≈5 pp at T=28 n=3."""
    return round(100 * 0.5 / math.sqrt(held_out_tasks * trials))


def trend_test(results: list[GenerationResult]) -> dict[str, Any]:
    """One-sided trend over the measured generations — the pre-registered primary (D11).

    S = Σ_t Σ_j c_j x_tj with c_j the centered generation index over MEASURED columns
    only: an identity generation carries its predecessor's draws forward, so including
    it would count one measurement more than once. The null holds each task's own
    outcomes fixed and treats their order as exchangeable (task difficulty stays; a
    harness that never changed has no direction), giving the exact per-task permutation
    variance (sum c^2) * sum_j (x_tj - xbar_t)^2 / (m - 1); the tail is normal-approximated.
    One-sided because the pre-registered question is improvement: large positive S.
    """
    measured = [result for result in results if not result.carried]
    verdict: dict[str, Any] = {
        "test": "one-sided trend, permutation-variance normal approximation",
        "alpha": TREND_ALPHA,
        "measured_generations": [result.label for result in measured],
        "excluded_identity": [result.label for result in results if result.carried],
    }
    columns = len(measured)
    if columns < 2:
        return {**verdict, "statistic": 0.0, "z": 0.0, "p_value": 1.0, "significant": False}
    center = sum(result.generation for result in measured) / columns
    coefficients = [result.generation - center for result in measured]
    coefficient_ss = sum(c * c for c in coefficients)
    statistic = 0.0
    variance = 0.0
    # Outcomes are per-task pass RATES: 0/1 at one trial (the original binary case),
    # c/n at num_trials > 1. The permutation null — a task's own outcomes across
    # generations are exchangeable — holds for rates exactly as for booleans.
    for task in measured[0].stats:
        outcomes = [result.rate(task) for result in measured]
        mean = sum(outcomes) / columns
        statistic += sum(c * x for c, x in zip(coefficients, outcomes, strict=True))
        variance += coefficient_ss * sum((x - mean) ** 2 for x in outcomes) / (columns - 1)
    if variance == 0:
        return {**verdict, "statistic": statistic, "z": 0.0, "p_value": 1.0, "significant": False}
    z = statistic / math.sqrt(variance)
    p_value = 0.5 * math.erfc(z / math.sqrt(2))
    return {
        **verdict,
        "statistic": statistic,
        "z": z,
        "p_value": p_value,
        "significant": p_value < TREND_ALPHA,
    }


def fragility(results: list[GenerationResult]) -> dict[str, Any]:
    """Sensitivity of the trend verdict — reported beside it, never gating it (plan D25).

    Two cheap perturbations, both advisory. Leave-one-task-out: rerun the trend with
    each task removed; a significance that any single task can flip is resting on that
    task's cells. Endpoint-cell sensitivity: a task whose only nonzero rates appear in
    the final measured generation sits on the largest contrast weight, so its cells buy
    more statistic than any others — zeroing them asks whether the verdict survives
    without the last round's first-evers. Neither perturbation changes the
    pre-registered test; they qualify how much of its answer one task or one round
    carries. (The review of one revealed experiment found p = 0.038 that six different
    single tasks could each push past 0.05, with two endpoint-only first-passes
    supplying 3.0 of the statistic's 8.0 — worth knowing next to the p-value.)
    """
    base = trend_test(results)
    base_slice = {key: base[key] for key in ("statistic", "z", "p_value", "significant")}
    measured = [result for result in results if not result.carried]
    tasks = sorted(measured[0].stats) if measured else []

    leave_one_out: list[dict[str, Any]] = []
    for task in tasks:
        reduced = [
            GenerationResult(
                result.generation,
                {t: cell for t, cell in result.stats.items() if t != task},
                result.carried,
            )
            for result in results
        ]
        test = trend_test(reduced)
        leave_one_out.append(
            {
                "task_id": task,
                "z": test["z"],
                "p_value": test["p_value"],
                "significant": test["significant"],
            }
        )
    load_bearing = sorted(
        entry["task_id"]
        for entry in leave_one_out
        if base["significant"] and not entry["significant"]
    )

    endpoint_only: list[str] = []
    without_endpoint: dict[str, Any] | None = None
    if len(measured) >= 2:
        final = measured[-1]
        endpoint_only = sorted(
            task
            for task in tasks
            if final.rate(task) > 0 and all(result.rate(task) == 0 for result in measured[:-1])
        )
        if endpoint_only:
            adjusted = [
                result
                if result.carried or result.generation != final.generation
                else GenerationResult(
                    result.generation,
                    {
                        task: ((0, cell[1]) if task in endpoint_only else cell)
                        for task, cell in result.stats.items()
                    },
                    result.carried,
                )
                for result in results
            ]
            test = trend_test(adjusted)
            without_endpoint = {
                key: test[key] for key in ("statistic", "z", "p_value", "significant")
            }

    return {
        "note": (
            "sensitivity of the pre-registered trend verdict; advisory context beside "
            "the p-value, never a gate and never a replacement test"
        ),
        "base": base_slice,
        "leave_one_task_out": leave_one_out,
        "load_bearing_tasks": load_bearing,
        "endpoint_only_first_passes": endpoint_only,
        "without_endpoint_first_passes": without_endpoint,
    }


def results_from_revealed(held_out_dir: Path) -> list[GenerationResult]:
    """Reconstruct GenerationResults from an already-revealed held_out/ directory.

    The matrix cells are exact `passed/trials` fractions and the by-generation CSV
    carries the identity flags, so a revealed experiment's fragility (and any future
    derived statistic) can be backfilled without touching a vault. Read-only over the
    revealed artifacts — the one place these numbers are legitimately visible.
    """
    matrix_lines = (
        (held_out_dir / TASK_GENERATION_MATRIX_CSV).read_text(encoding="utf-8").splitlines()
    )
    header = matrix_lines[0].split(",")
    labels = header[1:]
    stats_by_label: dict[str, dict[str, tuple[int, int]]] = {label: {} for label in labels}
    for line in matrix_lines[1:]:
        if not line.strip():
            continue
        cells = line.split(",")
        task_id = cells[0]
        for label, cell in zip(labels, cells[1:], strict=True):
            passed, trials = cell.split("/")
            stats_by_label[label][task_id] = (int(passed), int(trials))
    carried_by_label: dict[str, bool] = {}
    by_generation = (
        (held_out_dir / RESULTS_BY_GENERATION_CSV).read_text(encoding="utf-8").splitlines()
    )
    columns = by_generation[0].split(",")
    for line in by_generation[1:]:
        if not line.strip():
            continue
        row = dict(zip(columns, line.split(","), strict=True))
        carried_by_label[row["generation"]] = row.get("basis") != "measured"
    return [
        GenerationResult(
            generation=int(label.removeprefix("H")),
            stats=stats_by_label[label],
            carried=carried_by_label.get(label, False),
        )
        for label in labels
    ]


def fragility_sentence(report: dict[str, Any]) -> str:
    """The summary.md rendering of the fragility report."""
    load_bearing = report["load_bearing_tasks"]
    endpoint_only = report["endpoint_only_first_passes"]
    parts: list[str] = []
    if not report["base"]["significant"]:
        parts.append("the trend is not significant, so no single task's removal can flip it")
    elif load_bearing:
        parts.append(
            f"significance is load-bearing on {len(load_bearing)} task(s) — dropping any "
            f"one of {', '.join(load_bearing)} pushes p above alpha"
        )
    else:
        parts.append("significance survives leave-one-task-out for every task")
    if endpoint_only:
        clause = (
            f"{len(endpoint_only)} first-ever pass(es) appear only in the final measured "
            f"generation ({', '.join(endpoint_only)})"
        )
        without = report["without_endpoint_first_passes"]
        if without is not None:
            clause += (
                f"; zeroing those cells gives z = {without['z']:.2f}, p = {without['p_value']:.3f}"
            )
        parts.append(clause)
    return "; ".join(parts)


def trend_sentence(trend: dict[str, Any]) -> str:
    """The summary.md rendering of the trend verdict."""
    if trend["p_value"] >= 1.0:
        body = "no discordance across the measured generations — no trend evidence (p = 1)"
    else:
        outcome = "significant" if trend["significant"] else "not significant"
        body = (
            f"one-sided trend over the measured generations "
            f"({', '.join(trend['measured_generations'])}): z = {trend['z']:.2f}, "
            f"p = {trend['p_value']:.3f} — {outcome} at alpha = {trend['alpha']}"
        )
    if trend["excluded_identity"]:
        body += (
            f". Identity generations ({', '.join(trend['excluded_identity'])}) carry "
            "their predecessor's draws and are excluded from the statistic"
        )
    return body


# ---------------------------------------------------------------- assembling results


def load_measured(
    vault_generation_dir: Path, expected_trials: int
) -> dict[str, tuple[int, int]] | None:
    """{task_id: (passed_trials, trials)} from a vault round's graded output.

    None when the round does not exist. Every task must carry exactly the freeze's
    num_trials graded trials — a short task means an incomplete round, an over-count
    means trials leaked in from outside the freeze; either way the curve would compare
    unequal estimates, so the reveal refuses.
    """
    graded = vault_generation_dir / heldoutmod.GRADED_DIR / heldoutmod.GRADED_RESULTS
    if not graded.exists():
        return None
    payload = json.loads(graded.read_text(encoding="utf-8"))
    stats: dict[str, list[int]] = {}
    for sim in payload.get("simulations") or []:
        task_id = str(sim.get("task_id"))
        reward = (sim.get("reward_info") or {}).get("reward")
        entry = stats.setdefault(task_id, [0, 0])
        entry[0] += int(reward is not None and float(reward) >= PASS_THRESHOLD)
        entry[1] += 1
    uneven = sorted(t for t, (_, n) in stats.items() if n != expected_trials)
    if uneven:
        raise RevealError(
            f"{graded} holds a trial count other than the frozen num_trials="
            f"{expected_trials} for: {', '.join(uneven)} — the curve cannot compare "
            "unequal estimates"
        )
    return {task_id: (c, n) for task_id, (c, n) in stats.items()}


def load_records(records_path: Path, total_generations: int) -> dict[int, dict[str, Any]]:
    """All G transition records, validated; refuses on any missing or broken link."""
    schema = recordsmod.load_schema()
    # records_path is <results_root>/experiment_<id>/improvement_records — the provenance
    # check must resolve against the SAME results tree, not the module default, or an
    # injected tree (tests, an out-of-tree reveal) validates against the wrong repo.
    results_root = records_path.parent.parent
    records: dict[int, dict[str, Any]] = {}
    missing, broken = [], []
    for source in range(total_generations):
        path = records_path / recordsmod.record_name(source)
        if not path.exists():
            missing.append(path.name)
            continue
        record = recordsmod.load_record(path)
        problems = recordsmod.validate(
            record, filename=path.name, schema=schema, results_root=results_root
        )
        if problems:
            broken.append(f"{path.name}: " + "; ".join(problems))
        records[source] = record
    if missing:
        raise RevealError(
            "the evidence chain is incomplete — improvement records missing for: "
            + ", ".join(missing)
            + ". Every transition writes its record as it happens (protocol §24); "
            "reconstruct nothing, and reveal only when the chain holds."
        )
    if broken:
        raise RevealError("improvement records fail validation:\n  ✗ " + "\n  ✗ ".join(broken))
    return records


def verify_freeze_chain(
    experiment_dir: Path,
    vault_experiment_dir: Path,
    results: list[GenerationResult],
) -> None:
    """Every measured round must have run under the experiment's one frozen configuration.

    The runner stamps each round's run_metadata.json with the freeze fingerprint it ran
    under, and the in-tree snapshot (experiment.yaml, written on the experiment's first
    frozen round — the H0 held-out round included) pins the experiment's. A mismatch, or a
    measurement with no recorded fingerprint, means the curve would compare measurements
    taken under different configurations — exactly what the freeze forbids.
    """
    snapshot_path = experiment_dir / SNAPSHOT_NAME
    if not snapshot_path.exists():
        raise RevealError(
            f"{snapshot_path} does not exist: a frozen experiment writes it on first "
            "contact (the H0 held-out round included), so its absence means these "
            "measurements were taken under a PROVISIONAL lock — not a revealable "
            "experiment."
        )
    pinned = (yaml.safe_load(snapshot_path.read_text(encoding="utf-8")) or {}).get("fingerprint")
    for result in results:
        if result.carried:
            continue
        meta_path = (
            vault_experiment_dir / generation_dirname(result.generation) / COMPLETION_SENTINEL
        )
        recorded = None
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8")) or {}
            except json.JSONDecodeError:
                meta = {}
            recorded = meta.get("freeze_fingerprint")
        if recorded != pinned:
            raise RevealError(
                f"{generation_dirname(result.generation)} was not measured under this "
                f"experiment's freeze: its round records fingerprint {recorded!r}, the "
                f"snapshot pins {pinned!r}. The progression curve cannot mix "
                "configurations."
            )


def assemble(
    lock: Lock,
    vault_experiment_dir: Path,
    records: dict[int, dict[str, Any]],
    held_out_ids: list[str],
) -> list[GenerationResult]:
    """H0..HG in order, identity generations carried forward, every measurement checked."""
    identity = {
        record["transition"]["to_generation"]
        for record in records.values()
        if record["outcome"] != recordsmod.OUTCOME_ACCEPTED
    }
    expected = set(held_out_ids)
    results: list[GenerationResult] = []
    for generation in range(lock.protocol.generations + 1):
        measured = load_measured(
            vault_experiment_dir / generation_dirname(generation), lock.num_trials
        )
        if generation in identity:
            if measured is not None:
                raise RevealError(
                    f"{generation_dirname(generation)} is an identity generation (its "
                    "record's outcome pins H to its predecessor), yet the vault holds a "
                    "measurement for it — a held-out round that should never have run"
                )
            results.append(GenerationResult(generation, dict(results[-1].stats), carried=True))
            continue
        if measured is None:
            raise RevealError(
                f"the vault holds no graded round for {generation_dirname(generation)}: "
                f"run `make heldout GEN={generation_dirname(generation)}` to completion "
                "before revealing"
            )
        if set(measured) != expected:
            extra = sorted(set(measured) - expected)
            absent = sorted(expected - set(measured))
            raise RevealError(
                f"{generation_dirname(generation)} was not measured on the frozen held-out "
                f"set: missing {absent or 'none'}, unexpected {extra or 'none'}"
            )
        results.append(GenerationResult(generation, measured, carried=False))
    return results


# ---------------------------------------------------------------- derived artifacts


def transitions(results: list[GenerationResult]) -> list[dict[str, Any]]:
    """Per-transition movement, on rates: gains = rate rose, regressions = rate fell,
    retained = rate equal and above zero, unresolved = rate equal at zero. At one trial
    per task this is exactly the original binary table (fail-to-pass, pass-to-fail,
    pass-to-pass, fail-to-fail)."""
    rows = []
    for before, after in itertools.pairwise(results):
        deltas = {t: after.rate(t) - before.rate(t) for t in after.stats}
        gains = sum(1 for d in deltas.values() if d > 0)
        regressions = sum(1 for d in deltas.values() if d < 0)
        retained = sum(1 for t, d in deltas.items() if d == 0 and after.rate(t) > 0)
        rows.append(
            {
                "transition": f"{before.label}→{after.label}",
                "gains": gains,
                "retained": retained,
                "regressions": regressions,
                "unresolved": len(after.stats) - gains - regressions - retained,
                "net": gains - regressions,
                "identity": after.carried,
            }
        )
    return rows


def retention(results: list[GenerationResult]) -> list[dict[str, Any]]:
    """currently = tasks at rate 1.0 (every trial passed), partial = 0 < rate < 1,
    ever = tasks that have passed at least one trial under any generation so far. At one
    trial per task, partial is structurally zero and the table is the original one."""
    ever: set[str] = set()
    rows = []
    for result in results:
        ever |= {task for task in result.stats if result.rate(task) > 0}
        rows.append(
            {
                "generation": result.label,
                "currently": sum(1 for task in result.stats if result.rate(task) == 1.0),
                "partial": sum(1 for task in result.stats if 0 < result.rate(task) < 1),
                "ever": len(ever),
            }
        )
    return rows


def results_by_generation_csv(results: list[GenerationResult], total: int) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["generation", "passed", "total", "percent", "basis", "trials_per_task"])
    for result in results:
        writer.writerow(
            [
                result.label,
                fmt_count(result.expected),
                total,
                f"{100 * result.expected / total:.1f}",
                "carried" if result.carried else "measured",
                result.trials,
            ]
        )
    return out.getvalue()


def _matrix_cell(result: GenerationResult, task_id: str) -> str:
    """`0`/`1` at one trial (the original format); `c/n` at num_trials > 1."""
    passed_trials, trials = result.stats[task_id]
    return str(passed_trials) if trials == 1 else f"{passed_trials}/{trials}"


def task_generation_matrix_csv(results: list[GenerationResult], task_ids: list[str]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["task_id", *(result.label for result in results)])
    for task_id in task_ids:
        writer.writerow([task_id, *(_matrix_cell(result, task_id) for result in results)])
    return out.getvalue()


def transitions_csv(results: list[GenerationResult]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        ["transition", "gains", "retained", "regressions", "unresolved", "net", "identity"]
    )
    for row in transitions(results):
        writer.writerow(
            [
                row["transition"],
                row["gains"],
                row["retained"],
                row["regressions"],
                row["unresolved"],
                row["net"],
                str(row["identity"]).lower(),
            ]
        )
    return out.getvalue()


def retention_csv(results: list[GenerationResult], total: int) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["generation", "currently_solved", "partially_solved", "ever_solved", "total"])
    for row in retention(results):
        writer.writerow([row["generation"], row["currently"], row["partial"], row["ever"], total])
    return out.getvalue()


def summary_md(lock: Lock, results: list[GenerationResult], revealed_on: str) -> str:
    protocol = lock.protocol
    total = protocol.held_out_tasks
    trials = results[0].trials if results else lock.num_trials
    band = noise_band_pp(total, trials)
    first, last = results[0], results[-1]
    delta = last.expected - first.expected
    delta_pp = 100 * delta / total
    delta_text = f"{'+' if delta >= 0 else '-'}{fmt_count(abs(delta))}"
    verdict = (
        f"R_T(H{last.generation}) - R_T(H0) = {delta_text} task(s) ({delta_pp:+.1f} pp) — "
        + (
            "outside the noise band"
            if abs(delta_pp) > band
            else "inside the noise band; directional only"
        )
    )
    trials_text = (
        "one trial per task (D2)"
        if trials == 1
        else f"{trials} trials per task — per-task cells are pass RATES, not flips (D18)"
    )
    lines = [
        f"# Experiment {lock.experiment_id} — held-out reveal",
        "",
        f"Revealed {revealed_on}. G={protocol.generations} generations x "
        f"B={protocol.improvement_tasks_per_generation} improvement tasks; held-out "
        f"T={total}, {trials_text}. Noise band: ±{band} pp (one standard error of the "
        f"mean per-task rate at p=0.5, T={total}, n={trials}) — deltas inside it are "
        "noise, and pass^k is never used for generations.",
        "",
        "## Progression",
        "",
        "| generation | passed (expected) | of | % | basis |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {r.label} | {fmt_count(r.expected)} | {total} | {100 * r.expected / total:.1f}% "
        f"| {'carried (identity)' if r.carried else 'measured'} |"
        for r in results
    ]
    lines += [
        "",
        f"**Endpoint:** {verdict}",
        "",
        f"**Pre-registered primary (D11):** {trend_sentence(trend_test(results))}.",
        "",
        f"**Fragility (advisory, D25):** {fragility_sentence(fragility(results))}.",
        "",
        "## Transitions",
        "",
    ]
    lines += [
        "| transition | gains | retained | regressions | unresolved | net | note |",
        "|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {row['transition']} | {row['gains']} | {row['retained']} | "
        f"{row['regressions']} | {row['unresolved']} | {row['net']:+d} "
        f"| {'identity' if row['identity'] else ''} |"
        for row in transitions(results)
    ]
    lines += [
        "",
        "## Retention",
        "",
        "| generation | fully solved | partially solved | ever solved |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {row['generation']} | {row['currently']}/{total} | {row['partial']}/{total} "
        f"| {row['ever']}/{total} |"
        for row in retention(results)
    ]
    lines += [
        "",
        "## Provenance",
        "",
        f"- `{HELD_OUT_DIRNAME}/{RESULTS_BY_GENERATION_CSV}`, "
        f"`{HELD_OUT_DIRNAME}/{TASK_GENERATION_MATRIX_CSV}`, "
        f"`{HELD_OUT_DIRNAME}/{TRANSITIONS_CSV}`, `{HELD_OUT_DIRNAME}/{RETENTION_CSV}`, "
        f"`{HELD_OUT_DIRNAME}/{TREND_TEST_JSON}` — "
        "computed at this reveal.",
        f"- `{HELD_OUT_DIRNAME}/generation_NNN/` — the vault rounds, copied verbatim.",
        "- `improvement_records/` — the evidence chain, `held_out_result` filled at this "
        "reveal and at no other time.",
        "",
        "Firewall, as enforced: improvement batches ran fully observable on the platform "
        "lane; held-out rounds ran on the local lane with outputs out of tree, structurally "
        "invisible to the platform and procedurally sealed locally until this reveal "
        "(SIA_EVALUATION_PLAN.md D1/D9).",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- the reveal itself


def reveal(
    lock: Lock,
    *,
    results_root: Path,
    vault_root: Path | None = None,
    repo_root: Path | None = None,
    manifest: dict[str, Any] | None = None,
) -> Path:
    """Perform the reveal; returns the experiment directory. Refuses anything half-true."""
    from tau_adapter import split as splitmod

    final_tag = gensmod.final_generation_tag(lock)
    if not gensmod.tag_exists(final_tag, repo_root or gensmod.REPO_ROOT):
        raise RevealError(
            f"the final generation tag {final_tag!r} does not exist: the reveal is "
            "runnable only after the last configured generation is frozen (guardrail 19). "
            "Nothing was read."
        )
    experiment_dir = results_root / f"experiment_{lock.experiment_id}"
    held_out_dir = experiment_dir / HELD_OUT_DIRNAME
    if held_out_dir.exists() and any(held_out_dir.iterdir()):
        raise RevealError(
            f"{held_out_dir} is already populated: a reveal happens once. If it must "
            "truly be redone, delete the directory by hand and record why."
        )
    vault_experiment_dir = (
        vault_root or heldoutmod.vault_root()
    ) / f"experiment_{lock.experiment_id}"
    if not vault_experiment_dir.exists():
        raise RevealError(f"the vault holds nothing for this experiment ({vault_experiment_dir})")

    manifest = splitmod.load_manifest() if manifest is None else manifest
    held_out_ids = list(manifest.get(splitmod.HELD_OUT) or [])
    records = load_records(experiment_dir / recordsmod.RECORDS_DIRNAME, lock.protocol.generations)
    results = assemble(lock, vault_experiment_dir, records, held_out_ids)
    verify_freeze_chain(experiment_dir, vault_experiment_dir, results)

    held_out_dir.mkdir(parents=True, exist_ok=True)
    for result in results:
        if result.carried:
            continue
        source = vault_experiment_dir / generation_dirname(result.generation)
        shutil.copytree(source, held_out_dir / generation_dirname(result.generation))
    total = lock.protocol.held_out_tasks
    (held_out_dir / RESULTS_BY_GENERATION_CSV).write_text(
        results_by_generation_csv(results, total), encoding="utf-8"
    )
    (held_out_dir / TASK_GENERATION_MATRIX_CSV).write_text(
        task_generation_matrix_csv(results, held_out_ids), encoding="utf-8"
    )
    (held_out_dir / TRANSITIONS_CSV).write_text(transitions_csv(results), encoding="utf-8")
    (held_out_dir / RETENTION_CSV).write_text(retention_csv(results, total), encoding="utf-8")
    (held_out_dir / TREND_TEST_JSON).write_text(
        json.dumps(trend_test(results), indent=2) + "\n", encoding="utf-8"
    )
    (held_out_dir / TREND_FRAGILITY_JSON).write_text(
        json.dumps(fragility(results), indent=2) + "\n", encoding="utf-8"
    )
    process_metrics.write_process_metrics(
        held_out_dir, process_metrics.tool_classes_from_lock(lock)
    )
    revealed_on = datetime.now(UTC).strftime("%Y-%m-%d")
    (experiment_dir / SUMMARY_NAME).write_text(
        summary_md(lock, results, revealed_on), encoding="utf-8"
    )
    for source_generation, record in records.items():
        _fill_record_result(
            experiment_dir / recordsmod.RECORDS_DIRNAME / recordsmod.record_name(source_generation),
            results[record["transition"]["to_generation"]],
            total,
        )
    return experiment_dir


def _fill_record_result(path: Path, result: GenerationResult, total: int) -> None:
    """Stamp held_out_result into a record, preserving the rest of the file byte for byte."""
    filled = (
        "held_out_result:\n"
        f"  passed: {fmt_count(result.expected)}\n"
        f"  total: {total}\n"
        f"  trials_per_task: {result.trials}\n"
        f"  carried: {str(result.carried).lower()}\n"
    )
    text = path.read_text(encoding="utf-8")
    replaced, count = re.subn(r"^held_out_result:.*\n", filled, text, count=1, flags=re.MULTILINE)
    if count == 0:
        replaced = text + ("" if text.endswith("\n") else "\n") + filled
    path.write_text(replaced, encoding="utf-8")
