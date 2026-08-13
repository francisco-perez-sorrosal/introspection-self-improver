"""The reveal: the one sanctioned read of the vault, at the end of a configured experiment.

Runnable only once the final generation tag exists (protocol guardrail 19), it copies the
vault's held-out rounds into results/experiment_<id>/held_out/, computes the progression
artifacts — held-out count per generation, the task x generation matrix, per-transition
gains/retained/regressions/unresolved, the currently-solved vs ever-solved retention
diagnostic — writes summary.md with the D2 noise band, and fills every improvement
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

from tau_adapter import generations as gensmod
from tau_adapter import heldout as heldoutmod
from tau_adapter import records as recordsmod
from tau_adapter.lock import Lock

PASS_THRESHOLD = 1.0 - 1e-9

HELD_OUT_DIRNAME = "held_out"
RESULTS_BY_GENERATION_CSV = "results_by_generation.csv"
TASK_GENERATION_MATRIX_CSV = "task_generation_matrix.csv"
SUMMARY_NAME = "summary.md"


class RevealError(RuntimeError):
    pass


@dataclass(frozen=True)
class GenerationResult:
    generation: int
    passed: dict[str, bool]  # task_id -> solved
    carried: bool  # identity generation: predecessor's result, not a measurement

    @property
    def count(self) -> int:
        return sum(1 for solved in self.passed.values() if solved)

    @property
    def label(self) -> str:
        return f"H{self.generation}"


def generation_dirname(generation: int) -> str:
    return f"generation_{generation:03d}"


def noise_band_pp(held_out_tasks: int) -> int:
    """One binomial standard error at p=0.5, in percentage points (≈7 at T=47, per D2)."""
    return round(100 * 0.5 / math.sqrt(held_out_tasks))


# ---------------------------------------------------------------- assembling results


def load_measured(vault_generation_dir: Path) -> dict[str, bool] | None:
    """{task_id: passed} from a vault round's graded output; None when it does not exist."""
    graded = vault_generation_dir / heldoutmod.GRADED_DIR / heldoutmod.GRADED_RESULTS
    if not graded.exists():
        return None
    payload = json.loads(graded.read_text(encoding="utf-8"))
    passed: dict[str, bool] = {}
    for sim in payload.get("simulations") or []:
        task_id = str(sim.get("task_id"))
        if task_id in passed:
            raise RevealError(
                f"{graded} holds more than one trial for {task_id}: the progression "
                "metric is single-trial (D2); an endpoint reliability study is a separate "
                "artifact, never mixed into this one"
            )
        reward = (sim.get("reward_info") or {}).get("reward")
        passed[task_id] = reward is not None and float(reward) >= PASS_THRESHOLD
    return passed


def load_records(records_path: Path, total_generations: int) -> dict[int, dict[str, Any]]:
    """All G transition records, validated; refuses on any missing or broken link."""
    schema = recordsmod.load_schema()
    records: dict[int, dict[str, Any]] = {}
    missing, broken = [], []
    for source in range(total_generations):
        path = records_path / recordsmod.record_name(source)
        if not path.exists():
            missing.append(path.name)
            continue
        record = recordsmod.load_record(path)
        problems = recordsmod.validate(record, filename=path.name, schema=schema)
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
        measured = load_measured(vault_experiment_dir / generation_dirname(generation))
        if generation in identity:
            if measured is not None:
                raise RevealError(
                    f"{generation_dirname(generation)} is an identity generation (its "
                    "record's outcome pins H to its predecessor), yet the vault holds a "
                    "measurement for it — a held-out round that should never have run"
                )
            results.append(GenerationResult(generation, dict(results[-1].passed), carried=True))
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
    rows = []
    for before, after in itertools.pairwise(results):
        gains = sum(1 for t, ok in after.passed.items() if ok and not before.passed[t])
        regressions = sum(1 for t, ok in after.passed.items() if not ok and before.passed[t])
        retained = sum(1 for t, ok in after.passed.items() if ok and before.passed[t])
        rows.append(
            {
                "transition": f"{before.label}→{after.label}",
                "gains": gains,
                "retained": retained,
                "regressions": regressions,
                "unresolved": len(after.passed) - gains - regressions - retained,
                "net": gains - regressions,
                "identity": after.carried,
            }
        )
    return rows


def retention(results: list[GenerationResult]) -> list[dict[str, Any]]:
    ever: set[str] = set()
    rows = []
    for result in results:
        ever |= {task for task, ok in result.passed.items() if ok}
        rows.append({"generation": result.label, "currently": result.count, "ever": len(ever)})
    return rows


def results_by_generation_csv(results: list[GenerationResult], total: int) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["generation", "passed", "total", "percent", "basis"])
    for result in results:
        writer.writerow(
            [
                result.label,
                result.count,
                total,
                f"{100 * result.count / total:.1f}",
                "carried" if result.carried else "measured",
            ]
        )
    return out.getvalue()


def task_generation_matrix_csv(results: list[GenerationResult], task_ids: list[str]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["task_id", *(result.label for result in results)])
    for task_id in task_ids:
        writer.writerow([task_id, *(int(result.passed[task_id]) for result in results)])
    return out.getvalue()


def summary_md(lock: Lock, results: list[GenerationResult], revealed_on: str) -> str:
    protocol = lock.protocol
    total = protocol.held_out_tasks
    band = noise_band_pp(total)
    first, last = results[0], results[-1]
    delta = last.count - first.count
    delta_pp = 100 * delta / total
    verdict = f"R_T(H{last.generation}) - R_T(H0) = {delta:+d} task(s) ({delta_pp:+.1f} pp) — " + (
        "outside the noise band"
        if abs(delta_pp) > band
        else "inside the noise band; directional only"
    )
    lines = [
        f"# Experiment {lock.experiment_id} — held-out reveal",
        "",
        f"Revealed {revealed_on}. G={protocol.generations} generations x "
        f"B={protocol.improvement_tasks_per_generation} improvement tasks; held-out "
        f"T={total}, one trial per task (D2). Noise band: ±{band} pp (one binomial "
        f"standard error at p=0.5, T={total}) — deltas inside it are noise, and pass^k "
        "is never used for generations.",
        "",
        "## Progression",
        "",
        "| generation | passed | of | % | basis |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {r.label} | {r.count} | {total} | {100 * r.count / total:.1f}% "
        f"| {'carried (identity)' if r.carried else 'measured'} |"
        for r in results
    ]
    lines += ["", f"**Endpoint:** {verdict}", "", "## Transitions", ""]
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
        "| generation | currently solved | ever solved |",
        "|---|---|---|",
    ]
    lines += [
        f"| {row['generation']} | {row['currently']}/{total} | {row['ever']}/{total} |"
        for row in retention(results)
    ]
    lines += [
        "",
        "## Provenance",
        "",
        f"- `{HELD_OUT_DIRNAME}/{RESULTS_BY_GENERATION_CSV}`, "
        f"`{HELD_OUT_DIRNAME}/{TASK_GENERATION_MATRIX_CSV}` — computed at this reveal.",
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
        f"  passed: {result.count}\n"
        f"  total: {total}\n"
        f"  carried: {str(result.carried).lower()}\n"
    )
    text = path.read_text(encoding="utf-8")
    replaced, count = re.subn(r"^held_out_result:.*\n", filled, text, count=1, flags=re.MULTILINE)
    if count == 0:
        replaced = text + ("" if text.endswith("\n") else "\n") + filled
    path.write_text(replaced, encoding="utf-8")
