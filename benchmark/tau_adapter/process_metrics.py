"""Sub-reward process metrics, derived from graded records — held-out at reveal, batch
rounds any time (batch evidence is observable by design).

The headline artifacts answer "what did each round score"; these CSVs answer "what moved
underneath" — partial credit (DB match, gold-action match, write match, mean action
reward) and behavioral signatures (retrieval intensity, discoverable tool usage, human
transfers, episode length and cost). Everything derives from a round's
`graded/updated_results.json`, the canonical grading record — never from logs, and never
from the vault: on the held-out side this module reads only already-revealed files, so it
is safe to re-derive post-reveal (`scripts/reveal.py --derive-only`).

Under plan D25 the behavioral counters are first-class prediction channels: a change's
`expected_effect` may name a counter here instead of pass/fail, because these move
smoothly where the binary rate thrashes (one revealed experiment's
`partial_action_reward_pct` climbed near-monotonically +4.6 pp while its pass curve
round-tripped). Diagnostic descriptive statistics; no noise band is defined; renderers
present direction, never significance.

The domain-specific tool names live in the lock (`operational.process_metric_tools`),
never in this module: the code is task- and domain-agnostic, the configuration says
which tools mean "search", "transfer", and "capability discovery" for the frozen domain
(`tool_classes_from_lock`; the defaults keep pre-D25 experiments derivable).
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROCESS_BY_GENERATION_CSV = "process_metrics_by_generation.csv"
PROCESS_BY_TASK_CSV = "process_metrics_by_task.csv"
BATCH_PROCESS_BY_ROUND_CSV = "batch_process_metrics_by_round.csv"
BATCH_PROCESS_BY_TASK_CSV = "batch_process_metrics_by_task.csv"
GRADED_RELPATH = Path("graded") / "updated_results.json"


@dataclass(frozen=True)
class ToolClasses:
    """Which tool names count as which behavioral signature, for the frozen domain.

    The user's own discoverable calls are deliberately excluded from `discoverable` —
    they measure the simulated user, not the harness.
    """

    search: str | None
    discoverable: frozenset[str]
    transfer: str | None


#: Pre-D25 defaults (the banking_knowledge freeze's names): keeps every already-graded
#: experiment derivable without a lock edit. A different domain overrides via the lock.
DEFAULT_TOOL_CLASSES = ToolClasses(
    search="KB_search",
    discoverable=frozenset(
        {
            "unlock_discoverable_agent_tool",
            "call_discoverable_agent_tool",
            "give_discoverable_user_tool",
        }
    ),
    transfer="transfer_to_human_agents",
)


def tool_classes_from_lock(lock: Any) -> ToolClasses:
    """Read `operational.process_metric_tools` off a Lock; defaults when absent.

    Lives in `operational:` — outside the freeze fingerprint — because these names
    configure derived diagnostics, never what the agent can do inside an episode.
    """
    section = (getattr(lock, "raw", None) or {}).get("operational") or {}
    tools = section.get("process_metric_tools") or {}
    if not tools:
        return DEFAULT_TOOL_CLASSES
    return ToolClasses(
        search=tools.get("search"),
        discoverable=frozenset(str(name) for name in (tools.get("discoverable") or [])),
        transfer=tools.get("transfer"),
    )


def derive_task_rows(
    graded_payload: dict[str, Any],
    generation_label: str,
    tool_classes: ToolClasses = DEFAULT_TOOL_CLASSES,
) -> list[dict[str, Any]]:
    """One row per simulation in a graded record (held-out generation or batch round)."""
    bases = {
        str(task["id"]): list((task.get("evaluation_criteria") or {}).get("reward_basis") or [])
        for task in graded_payload.get("tasks") or []
    }
    rows: list[dict[str, Any]] = []
    for sim in graded_payload.get("simulations") or []:
        reward_info = sim.get("reward_info") or {}
        checks = reward_info.get("action_checks") or []
        writes = [c for c in checks if c.get("tool_type") == "write"]
        kb = discoverable = transfers = 0
        for message in sim.get("messages") or []:
            for tool_call in message.get("tool_calls") or []:
                name = str(tool_call.get("name"))
                if name == tool_classes.search:
                    kb += 1
                elif name in tool_classes.discoverable:
                    discoverable += 1
                elif name == tool_classes.transfer:
                    transfers += 1
        task_id = str(sim.get("task_id"))
        basis = bases.get(task_id, [])
        reward = (reward_info.get("reward") or 0.0) if reward_info else 0.0
        rows.append(
            {
                "generation": generation_label,
                "task_id": task_id,
                "reward_basis": "+".join(basis),
                "reward": reward,
                "passed": reward == 1.0,
                "db_match": (
                    bool((reward_info.get("db_check") or {}).get("db_match"))
                    if "DB" in basis
                    else None
                ),
                "actions_matched": sum(1 for c in checks if c.get("action_match")),
                "actions_total": len(checks),
                "writes_matched": sum(1 for c in writes if c.get("action_match")),
                "writes_total": len(writes),
                "partial_action_reward": (
                    sum(c.get("action_reward") or 0.0 for c in checks) / len(checks)
                    if checks
                    else None
                ),
                "kb_search_calls": kb,
                "discoverable_ops": discoverable,
                "transfers": transfers,
                "messages": len(sim.get("messages") or []),
                "cost_usd": (sim.get("agent_cost") or 0.0) + (sim.get("user_cost") or 0.0),
                "duration_seconds": sim.get("duration"),
            }
        )
    return rows


def aggregate_generation(task_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """One aggregate row over one measured generation's task rows."""
    n = len(task_rows)
    db_rows = [r for r in task_rows if r["db_match"] is not None]
    partials = [
        r["partial_action_reward"] for r in task_rows if r["partial_action_reward"] is not None
    ]
    actions_total = sum(r["actions_total"] for r in task_rows)
    writes_total = sum(r["writes_total"] for r in task_rows)
    return {
        "generation": task_rows[0]["generation"],
        "tasks": n,
        "passed": sum(1 for r in task_rows if r["passed"]),
        "db_matched": sum(1 for r in db_rows if r["db_match"]),
        "db_basis_tasks": len(db_rows),
        "actions_matched": sum(r["actions_matched"] for r in task_rows),
        "actions_total": actions_total,
        "action_match_pct": (
            100 * sum(r["actions_matched"] for r in task_rows) / actions_total
            if actions_total
            else None
        ),
        "writes_matched": sum(r["writes_matched"] for r in task_rows),
        "writes_total": writes_total,
        "write_match_pct": (
            100 * sum(r["writes_matched"] for r in task_rows) / writes_total
            if writes_total
            else None
        ),
        "partial_action_reward_pct": (100 * sum(partials) / len(partials) if partials else None),
        "kb_search_calls": sum(r["kb_search_calls"] for r in task_rows),
        "discoverable_ops": sum(r["discoverable_ops"] for r in task_rows),
        "transfers": sum(r["transfers"] for r in task_rows),
        "messages_mean": sum(r["messages"] for r in task_rows) / n if n else None,
        "cost_usd_mean": sum(r["cost_usd"] for r in task_rows) / n if n else None,
    }


def derive_from_held_out_dir(
    held_out_dir: Path,
    tool_classes: ToolClasses = DEFAULT_TOOL_CLASSES,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(task rows, generation rows) over every measured generation directory present.

    Carried (identity) generations have no directory — they produced no episodes —
    and so appear in neither CSV; renderers align by generation label and mark gaps.
    """
    task_rows: list[dict[str, Any]] = []
    generation_rows: list[dict[str, Any]] = []
    for gen_dir in sorted(held_out_dir.glob("generation_*")):
        graded_path = gen_dir / GRADED_RELPATH
        if not graded_path.exists():
            continue
        payload = json.loads(graded_path.read_text(encoding="utf-8"))
        rows = derive_task_rows(payload, gen_dir.name, tool_classes)
        rows.sort(key=lambda r: r["task_id"])
        task_rows.extend(rows)
        if rows:
            generation_rows.append(aggregate_generation(rows))
    return task_rows, generation_rows


def derive_from_batch_rounds(
    experiment_dir: Path,
    tool_classes: ToolClasses = DEFAULT_TOOL_CLASSES,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(task rows, round rows) over every graded batch round in an experiment tree.

    Batch evidence is fully observable by design, so this derives at any time — during
    the experiment (the counters are the D25 prediction channels the next diagnosis
    scores) as well as at close. Valid under BOTH batch modes: under `fresh` the rounds
    hold different tasks and the per-round aggregates are read per-round, never as a
    curve; under `fixed` they are the paired saturation instrument's process view.
    The row label is the batch round name (`batch_NN`).
    """
    task_rows: list[dict[str, Any]] = []
    round_rows: list[dict[str, Any]] = []
    for graded_path in sorted(experiment_dir.glob("generation_*/batch_*/" + str(GRADED_RELPATH))):
        round_name = graded_path.parent.parent.name
        payload = json.loads(graded_path.read_text(encoding="utf-8"))
        rows = derive_task_rows(payload, round_name, tool_classes)
        rows.sort(key=lambda r: r["task_id"])
        task_rows.extend(rows)
        if rows:
            round_rows.append(aggregate_generation(rows))
    return task_rows, round_rows


def _fmt(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return value


def by_task_csv(task_rows: list[dict[str, Any]]) -> str:
    fields = [
        "generation",
        "task_id",
        "reward_basis",
        "reward",
        "passed",
        "db_match",
        "actions_matched",
        "actions_total",
        "writes_matched",
        "writes_total",
        "partial_action_reward",
        "kb_search_calls",
        "discoverable_ops",
        "transfers",
        "messages",
        "cost_usd",
        "duration_seconds",
    ]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(fields)
    for row in task_rows:
        writer.writerow([_fmt(row[f]) for f in fields])
    return out.getvalue()


def by_generation_csv(generation_rows: list[dict[str, Any]]) -> str:
    fields = [
        "generation",
        "tasks",
        "passed",
        "db_matched",
        "db_basis_tasks",
        "actions_matched",
        "actions_total",
        "action_match_pct",
        "writes_matched",
        "writes_total",
        "write_match_pct",
        "partial_action_reward_pct",
        "kb_search_calls",
        "discoverable_ops",
        "transfers",
        "messages_mean",
        "cost_usd_mean",
    ]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(fields)
    for row in generation_rows:
        writer.writerow([_fmt(row[f]) for f in fields])
    return out.getvalue()


def write_process_metrics(
    held_out_dir: Path,
    tool_classes: ToolClasses = DEFAULT_TOOL_CLASSES,
) -> list[Path]:
    """Derive and write both CSVs beside the other revealed artifacts; idempotent."""
    task_rows, generation_rows = derive_from_held_out_dir(held_out_dir, tool_classes)
    by_task_path = held_out_dir / PROCESS_BY_TASK_CSV
    by_generation_path = held_out_dir / PROCESS_BY_GENERATION_CSV
    by_task_path.write_text(by_task_csv(task_rows), encoding="utf-8")
    by_generation_path.write_text(by_generation_csv(generation_rows), encoding="utf-8")
    return [by_generation_path, by_task_path]


def write_batch_process_metrics(
    experiment_dir: Path,
    tool_classes: ToolClasses = DEFAULT_TOOL_CLASSES,
) -> list[Path]:
    """Derive and write the batch-round CSVs at the experiment root; idempotent."""
    task_rows, round_rows = derive_from_batch_rounds(experiment_dir, tool_classes)
    by_task_path = experiment_dir / BATCH_PROCESS_BY_TASK_CSV
    by_round_path = experiment_dir / BATCH_PROCESS_BY_ROUND_CSV
    by_task_path.write_text(by_task_csv(task_rows), encoding="utf-8")
    by_round_path.write_text(by_generation_csv(round_rows), encoding="utf-8")
    return [by_round_path, by_task_path]
