"""The generation protocol's task partition: propose, load, render, verify.

The partition is the experiment's generalisation boundary — G disjoint improvement batches
are fully observable and drive the generations, the held-out set is measured once per
generation and stays hidden until reveal — so its contents are handled the way the lock's
values are: proposed mechanically, frozen by a human, and verified rather than trusted.
Sizes come from the lock's protocol block, with (G*B)+T ≤ N enforced at proposal and at
verification. A proposal stratifies over everything the vendored task data exposes that
could plausibly move difficulty: `reward_basis` (DB-state versus golden-action grading),
the dominant required-document category, and the required-document count. The vendored
data carries no explicit task category (`annotations` is null throughout), so the dominant
document category is the honest proxy.

Assignment is deterministic. Tasks are sorted by their strata key, shuffled only within
identical keys by the proposal seed, and dealt with a stride scheduler, so every contiguous
stratum lands in every partition in proportion. The ACTION-basis tasks in particular must
not concentrate: verify holds each side of the partition to its proportional floor —
⌊n_ACTION * T/N⌋ for the held-out set, ⌊n_ACTION * (G*B)/N⌋ jointly for the batches — so
neither side silently loses golden-action grading where its share affords one.
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

#: The manifest format this module writes and verifies. Version 1 was the retired
#: three-way discovery/validation/test scheme, frozen as closed experiment 001's record.
MANIFEST_VERSION = 2

HELD_OUT = "held_out"
_BATCH_PREFIX = "batch_"
LEGACY_KEYS = ("discovery", "validation", "test")

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


def batch_name(generation: int) -> str:
    return f"{_BATCH_PREFIX}{generation:02d}"


def partition_sizes(
    generations: int, tasks_per_generation: int, held_out_tasks: int
) -> dict[str, int]:
    """The partition's names and sizes: G improvement batches, then the held-out set."""
    sizes = {batch_name(g): tasks_per_generation for g in range(1, generations + 1)}
    sizes[HELD_OUT] = held_out_tasks
    return sizes


def exclude_rows(rows: list[TaskRow], excluded: list[str]) -> list[TaskRow]:
    """Drop screened-out tasks from the pool before proposing (e.g. user-sim crashers).

    Refuses unknown ids loudly: a typo in an exclusion list must never silently leave a
    known-bad task eligible for the partition.
    """
    known = {row.task_id for row in rows}
    unknown = sorted(set(excluded) - known)
    if unknown:
        raise ValueError(f"cannot exclude unknown task id(s): {', '.join(unknown)}")
    remaining = [row for row in rows if row.task_id not in set(excluded)]
    return remaining


def propose(
    rows: list[TaskRow],
    sizes: dict[str, int],
    seed: int = DEFAULT_SEED,
) -> dict[str, list[str]]:
    """Deterministic stratified proposal: ``{partition name: sorted task ids}``."""
    total = sum(sizes.values())
    if total > len(rows):
        raise ValueError(
            f"partition sizes demand {total} tasks ((G*B)+T), but only {len(rows)} exist"
        )
    rng = random.Random(seed)  # noqa: S311 - deterministic stratification shuffle, not crypto
    ordered = sorted(rows, key=lambda r: (r.reward_basis, r.category, r.doc_count, rng.random()))
    assignment: dict[str, list[str]] = {name: [] for name in sizes}
    for row, label in zip(ordered, _label_sequence(len(ordered), sizes), strict=True):
        if label != _UNUSED:
            assignment[label].append(row.task_id)
    return {name: sorted(ids) for name, ids in assignment.items()}


def _label_sequence(n: int, sizes: dict[str, int]) -> list[str]:
    """Stride-schedule labels so each partition samples every contiguous stratum in proportion."""
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


def partition_lists(manifest: dict[str, Any]) -> dict[str, list[str]]:
    """The manifest's partitions as one flat mapping: batches first, held-out last."""
    lists = {name: list(ids or []) for name, ids in (manifest.get("batches") or {}).items()}
    lists[HELD_OUT] = list(manifest.get(HELD_OUT) or [])
    return lists


def verify(
    manifest: dict[str, Any],
    rows: list[TaskRow],
    domain: str,
    sizes: dict[str, int],
) -> list[str]:
    """Mechanical checks on a frozen manifest. Returns problems; empty means it holds."""
    if any(key in manifest for key in LEGACY_KEYS) or manifest.get("version") == 1:
        return [
            "this manifest is the retired three-way split (discovery/validation/test) — "
            "the frozen record of closed experiment 001. The generation protocol "
            "partitions into batch_NN + held_out; propose a fresh manifest with "
            "scripts/propose_split.py"
        ]
    problems: list[str] = []
    if manifest.get("version") != MANIFEST_VERSION:
        problems.append(f"manifest version {manifest.get('version')!r} != {MANIFEST_VERSION}")
    if manifest.get("domain") != domain:
        problems.append(f"manifest domain {manifest.get('domain')!r} != locked domain {domain!r}")
    lists = partition_lists(manifest)
    expected_batches = sorted(name for name in sizes if name != HELD_OUT)
    found_batches = sorted(name for name in lists if name != HELD_OUT)
    if found_batches != expected_batches:
        problems.append(
            f"manifest holds batches [{', '.join(found_batches) or 'none'}], the protocol "
            f"config expects [{', '.join(expected_batches)}]"
        )
    total = sum(sizes.values())
    if total > len(rows):
        problems.append(f"(G*B)+T = {total} exceeds the {len(rows)} available tasks")
    problems += _list_problems(lists, sizes, rows)
    problems += _disjointness_problems(lists)
    problems += _action_spread_problems(lists, sizes, rows)
    return problems


def _list_problems(
    lists: dict[str, list[str]], sizes: dict[str, int], rows: list[TaskRow]
) -> list[str]:
    known = {row.task_id for row in rows}
    problems: list[str] = []
    for name, expected in sizes.items():
        ids = lists.get(name)
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
    return problems


def _disjointness_problems(lists: dict[str, list[str]]) -> list[str]:
    membership: dict[str, list[str]] = {}
    for name, ids in lists.items():
        for task_id in set(ids):
            membership.setdefault(task_id, []).append(name)
    return [
        f"{task_id} appears in multiple partitions: {', '.join(sorted(names))}"
        for task_id, names in sorted(membership.items())
        if len(names) > 1
    ]


def _action_spread_problems(
    lists: dict[str, list[str]], sizes: dict[str, int], rows: list[TaskRow]
) -> list[str]:
    """Each side of the partition must hold its proportional share of ACTION-basis tasks.

    The floors scale with the configuration — ⌊n_ACTION * T/N⌋ for held-out (4 at T=47
    against the 97-task pool), ⌊n_ACTION * (G*B)/N⌋ jointly for the batches — so a debug
    partition too small for a share is not held to one, and a full partition cannot
    quietly lose golden-action grading from either side.
    """
    action_ids = {row.task_id for row in rows if row.reward_basis == ("ACTION",)}
    if not action_ids:
        return []
    n = len(rows)
    held_quota = sizes.get(HELD_OUT, 0)
    batch_quota = sum(quota for name, quota in sizes.items() if name != HELD_OUT)
    held_floor = len(action_ids) * held_quota // n
    batch_floor = len(action_ids) * batch_quota // n
    held_count = len(action_ids & set(lists.get(HELD_OUT) or []))
    batch_count = sum(len(action_ids & set(ids)) for name, ids in lists.items() if name != HELD_OUT)
    problems: list[str] = []
    if held_count < held_floor:
        problems.append(
            f"held_out holds {held_count} ACTION-basis tasks, below its proportional "
            f"share of {held_floor}"
        )
    if batch_count < batch_floor:
        problems.append(
            f"the batches jointly hold {batch_count} ACTION-basis tasks, below their "
            f"proportional share of {batch_floor}"
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
        "# The generation protocol's task partition: G disjoint improvement batches plus the",
        "# fixed held-out set, as lists of tau task ids because tau selects tasks with",
        "# --task-ids. Sizes derive from the lock's protocol block; resizing between",
        "# experiments costs an edit there, not a redesign here.",
        "#",
        "# Rules (SIA_EVALUATION_PLAN.md D1/D9; invariants in CLAUDE.md):",
        "#   batch_NN — the improvement batch consumed by generation NN. Platform lane,",
        "#              fully observable by design, used once and never reused.",
        "#   held_out — measured once per generation on the local lane. Tasks, trajectories,",
        "#              and rewards stay out of tree (the vault) until the experiment's reveal.",
        "# Tasks in neither list are unused by this experiment.",
        "#",
        f"# Proposed by scripts/propose_split.py --seed {seed}: stratified over reward_basis,",
        "# dominant required-document category, and required-document count; frozen by hand.",
        "# Changing any list invalidates the experiment — a new experiment id (bump",
        "# experiment.seq in benchmark_lock.yaml), never new lists under the old one. Verify",
        "# with scripts/propose_split.py --verify.",
    ]
    if note:
        lines.append("#")
        lines.extend(f"# {chunk}" for chunk in textwrap.wrap(note, width=94))
    lines += [
        "",
        f"version: {MANIFEST_VERSION}",
        f"domain: {domain}",
        f"task_split_name: {task_split_name}",
        "",
        "batches:",
    ]
    for name in sorted(name for name in assignment if name != HELD_OUT):
        lines.append(f"  {name}:")
        lines.extend(f"    - {task_id}" for task_id in assignment[name])
    lines += ["", f"{HELD_OUT}:"]
    lines.extend(f"  - {task_id}" for task_id in assignment[HELD_OUT])
    return "\n".join(lines)


def strata_report(rows: list[TaskRow], assignment: dict[str, list[str]]) -> str:
    """Human-readable stratification table for the freeze review."""
    by_id = {row.task_id: row for row in rows}
    assigned = {task_id for ids in assignment.values() for task_id in ids}
    groups = dict(assignment)
    groups[_UNUSED] = sorted(r.task_id for r in rows if r.task_id not in assigned)
    lines = [f"{'partition':<11} {'n':>3} {'ACTION':>6} {'docs μ':>7}  categories"]
    for name, ids in groups.items():
        chosen = [by_id[task_id] for task_id in ids]
        n_action = sum(1 for row in chosen if row.reward_basis == ("ACTION",))
        mean_docs = sum(row.doc_count for row in chosen) / len(chosen) if chosen else 0.0
        categories = Counter(row.category for row in chosen)
        text = " ".join(f"{cat}:{count}" for cat, count in sorted(categories.items()))
        lines.append(f"{name:<11} {len(ids):>3} {n_action:>6} {mean_docs:>7.1f}  {text}")
    return "\n".join(lines)
