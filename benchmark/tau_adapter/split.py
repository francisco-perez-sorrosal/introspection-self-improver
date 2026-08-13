"""The three-way task split: propose, load, render, verify.

The split is the experiment's generalisation boundary — discovery is inspectable, validation
returns aggregates only, test is touched at predetermined checkpoints — so its contents are
handled the way the lock's values are: proposed mechanically, frozen by a human, and verified
rather than trusted. A proposal stratifies over everything the vendored task data exposes
that could plausibly move difficulty: `reward_basis` (DB-state versus golden-action grading),
the dominant required-document category, and the required-document count. The vendored data
carries no explicit task category (`annotations` is null throughout), so the dominant
document category is the honest proxy.

Assignment is deterministic. Tasks are sorted by their strata key, shuffled only within
identical keys by the proposal seed, and dealt with a stride scheduler, so every contiguous
stratum lands in every split in proportion. The ACTION tasks in particular must not all land
in one split: nine tasks grade on golden actions, and a split without any would never
exercise that reward basis.
"""

from __future__ import annotations

import json
import random
import textwrap
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from tau_adapter import VENDOR_DIR
from tau_adapter.lock import BENCHMARK_DIR

SPLIT_MANIFEST_PATH = BENCHMARK_DIR / "split_manifest.yaml"

#: Split sizes. The remainder is unused during optimisation. Changing these mid-experiment
#: invalidates it. This module still implements experiment 001's three-way scheme; the
#: generation protocol's G-batches + held-out partition replaces it (SIA_EVALUATION_PLAN.md
#: Phase 1).
SPLIT_SIZES = {"discovery": 30, "validation": 15, "test": 20}

#: Shuffle seed for within-stratum tie-breaking in a proposal. Unrelated to the runner's
#: frozen τ seed; recorded in the manifest header so the proposal is reproducible.
DEFAULT_SEED = 20260812

_UNUSED = "unused"


@dataclass(frozen=True)
class TaskRow:
    task_id: str
    reward_basis: tuple[str, ...]
    category: str
    doc_count: int


def load_task_rows(domain: str) -> list[TaskRow]:
    """Read the vendored task data for ``domain`` into strata rows."""
    path = VENDOR_DIR / "data" / "tau2" / "domains" / domain / "tasks.json"
    tasks = json.loads(path.read_text(encoding="utf-8"))
    return [_row(task) for task in tasks]


def _row(task: dict[str, Any]) -> TaskRow:
    criteria = task.get("evaluation_criteria") or {}
    docs = task.get("required_documents") or []
    return TaskRow(
        task_id=str(task["id"]),
        reward_basis=tuple(criteria.get("reward_basis") or []),
        category=_dominant_category(docs),
        doc_count=len(docs),
    )


def _dominant_category(doc_ids: list[str]) -> str:
    """Two tokens after the ``doc_`` prefix (``credit_cards``); ties break deterministically."""
    if not doc_ids:
        return "none"
    counts = Counter("_".join(doc_id.split("_")[1:3]) for doc_id in doc_ids)
    return max(counts, key=lambda category: (counts[category], category))


def propose(
    rows: list[TaskRow],
    sizes: dict[str, int] | None = None,
    seed: int = DEFAULT_SEED,
) -> dict[str, list[str]]:
    """Deterministic stratified proposal: ``{split name: sorted task ids}``."""
    sizes = dict(SPLIT_SIZES if sizes is None else sizes)
    if sum(sizes.values()) > len(rows):
        raise ValueError(f"split sizes {sizes} exceed the {len(rows)} available tasks")
    rng = random.Random(seed)  # noqa: S311 - deterministic stratification shuffle, not crypto
    ordered = sorted(rows, key=lambda r: (r.reward_basis, r.category, r.doc_count, rng.random()))
    assignment: dict[str, list[str]] = {name: [] for name in sizes}
    for row, label in zip(ordered, _label_sequence(len(ordered), sizes), strict=True):
        if label != _UNUSED:
            assignment[label].append(row.task_id)
    return {name: sorted(ids) for name, ids in assignment.items()}


def _label_sequence(n: int, sizes: dict[str, int]) -> list[str]:
    """Stride-schedule labels so each split samples every contiguous stratum in proportion."""
    quotas = dict(sizes)
    quotas[_UNUSED] = n - sum(sizes.values())
    credits = {name: 0.0 for name in quotas}
    remaining = dict(quotas)
    sequence: list[str] = []
    for _ in range(n):
        for name, quota in quotas.items():
            credits[name] += quota / n
        eligible = [name for name in quotas if remaining[name] > 0]
        pick = max(eligible, key=lambda name: (credits[name], name))
        sequence.append(pick)
        credits[pick] -= 1.0
        remaining[pick] -= 1
    return sequence


def load_manifest(path: Path = SPLIT_MANIFEST_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def verify(manifest: dict[str, Any], rows: list[TaskRow], domain: str) -> list[str]:
    """Mechanical checks on a frozen manifest. Returns problems; empty means it holds."""
    problems: list[str] = []
    if manifest.get("domain") != domain:
        problems.append(f"manifest domain {manifest.get('domain')!r} != locked domain {domain!r}")
    known = {row.task_id for row in rows}
    lists: dict[str, list[str]] = {}
    for name, expected in SPLIT_SIZES.items():
        ids = list(manifest.get(name) or [])
        lists[name] = ids
        if not ids:
            problems.append(f"{name} is empty")
            continue
        if len(ids) != expected:
            problems.append(f"{name} holds {len(ids)} ids, expected {expected}")
        if len(set(ids)) != len(ids):
            problems.append(f"{name} contains duplicates")
        unknown = sorted(set(ids) - known)
        if unknown:
            problems.append(f"{name} names unknown tasks: {', '.join(unknown)}")
    for a, b in (("discovery", "validation"), ("discovery", "test"), ("validation", "test")):
        overlap = sorted(set(lists[a]) & set(lists[b]))
        if overlap:
            problems.append(f"{a} and {b} overlap: {', '.join(overlap)}")
    basis = {row.task_id: row.reward_basis for row in rows}
    action_splits = sorted(
        name
        for name, ids in lists.items()
        if any(basis.get(task_id) == ("ACTION",) for task_id in ids)
    )
    if len(action_splits) < 2:
        where = ", ".join(action_splits) if action_splits else "no split"
        problems.append(
            f"ACTION-basis tasks reach only {where}; they must land in at least two splits"
        )
    return problems


def render_manifest(
    assignment: dict[str, list[str]],
    domain: str,
    task_split_name: str,
    seed: int,
    note: str = "",
) -> str:
    """The frozen manifest's file content, header comments included."""
    lines = [
        "# The three-way task split. A split is nothing more than three lists of tau task ids,",
        "# because tau selects tasks with --task-ids; resizing between experiments costs an edit,",
        "# not a redesign.",
        "#",
        "# Rules:",
        "#   discovery  — fully inspectable. The only set the orchestrator learns from.",
        "#   validation — aggregate outcomes only. Exposing a validation failure in detail turns",
        "#                validation into more discovery data.",
        "#   test       — never inspected during optimisation. Predetermined checkpoints only.",
        "# Tasks in none of the three are unused during optimisation and remain available for",
        "# the full-domain checkpoint runs.",
        "#",
        f"# Proposed by scripts/propose_split.py --seed {seed}: stratified over reward_basis,",
        "# dominant required-document category, and required-document count; frozen by hand.",
        "# Changing any list invalidates the experiment — a new experiment id, never new lists",
        "# under the old one (benchmark_lock.yaml). Verify with scripts/propose_split.py --verify.",
    ]
    if note:
        lines.append("#")
        lines.extend(f"# {chunk}" for chunk in textwrap.wrap(note, width=94))
    lines += ["", "version: 1", f"domain: {domain}", f"task_split_name: {task_split_name}", ""]
    for name in SPLIT_SIZES:
        lines.append(f"{name}:")
        lines.extend(f"  - {task_id}" for task_id in assignment[name])
        lines.append("")
    return "\n".join(lines)


def strata_report(rows: list[TaskRow], assignment: dict[str, list[str]]) -> str:
    """Human-readable stratification table for the freeze review."""
    by_id = {row.task_id: row for row in rows}
    assigned = {task_id for ids in assignment.values() for task_id in ids}
    groups = dict(assignment)
    groups[_UNUSED] = sorted(r.task_id for r in rows if r.task_id not in assigned)
    lines = [f"{'split':<11} {'n':>3} {'ACTION':>6} {'docs μ':>7}  categories"]
    for name, ids in groups.items():
        chosen = [by_id[task_id] for task_id in ids]
        n_action = sum(1 for row in chosen if row.reward_basis == ("ACTION",))
        mean_docs = sum(row.doc_count for row in chosen) / len(chosen) if chosen else 0.0
        categories = Counter(row.category for row in chosen)
        text = " ".join(f"{cat}:{count}" for cat, count in sorted(categories.items()))
        lines.append(f"{name:<11} {len(ids):>3} {n_action:>6} {mean_docs:>7.1f}  {text}")
    return "\n".join(lines)
