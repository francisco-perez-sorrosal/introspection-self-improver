"""The episode manifest: one machine-readable row per (task, trial).

This is the artifact `operate` receives at the top of a generation and the improvement
record cites. Before it existed, the (τ task, trial) → conversation join lived
scattered across `results.json` raw_data and `run_metadata.json` accounting, and reading it
required code. A manifest row states the join once, with the completeness and incident flags
beside it, so a diagnosis can start from ground truth instead of reconstruction.

Derivation is pure: rows are computed from τ's results payload plus what the runner recorded
around it. Nothing here is a second opinion — reward comes from τ's file, lineage from the
conversation export, incidents from counters the transports and bridge kept while the episode
ran. τ excludes `infrastructure_error` simulations from its own metrics; the manifest counts
them anyway, because they consume budget and can hide transport defects.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

MANIFEST_NAME = "episode_manifest.jsonl"

# Mirror of fidelity.lane_report.NORMAL_TERMINATIONS, restated here so this module stays
# importable without the fidelity package on sys.path (scripts add benchmark/ themselves).
NORMAL_TERMINATIONS = frozenset(
    {"user_stop", "agent_stop", "TerminationReason.USER_STOP", "TerminationReason.AGENT_STOP"}
)


@dataclass
class EpisodeIncidents:
    """What went wrong around one episode without necessarily failing it.

    Kept by the transport (and, via a callback, the bridge) while the episode runs, because
    none of these survive into τ's record: τ retries an infrastructure error and stores only
    the final attempt, and a stalled rendezvous can still end in a graded 1.0. A regression
    in any of these must surface in the round report, not in a debugging session.
    """

    stall_warnings: int = 0
    prompt_409: int = 0
    prompt_failures: int = 0
    stream_failures: int = 0
    #: Re-attaches spent waiting out the org's sandbox queue (created, not yet started).
    #: Latency, not damage — but a round that queued a lot should say so.
    sandbox_queue_waits: int = 0
    stream_reattaches: int = 0
    settle_timeouts: int = 0

    def count_stall(self) -> None:
        self.stall_warnings += 1

    def as_dict(self) -> dict[str, int]:
        return asdict(self)

    def any(self) -> bool:
        return any(asdict(self).values())


@dataclass(frozen=True)
class RoundContext:
    """What the runner knows about the round that τ's results file does not."""

    experiment_id: str
    transport: str
    generation: str | None = None
    arm_sha: str | None = None
    arm_dirty: bool = False
    split: str | None = None
    # Keyed by pi_session_ref (platform: the task id, which is also the conversation id).
    accounting: dict[str, dict[str, Any]] = field(default_factory=dict)
    incidents_by_ref: dict[str, dict[str, int]] = field(default_factory=dict)
    labels_by_ref: dict[str, str] = field(default_factory=dict)


def episode_summary(sim: Any) -> dict[str, Any]:
    """Whether one episode ran to a graded end — stated, never inferred from the reward.

    `completed` means τ itself ended the episode normally *and* graded it. Any other
    termination is infrastructure or protocol, and a reward attached to it must not be read
    as a measurement. Shared by the runner's console verdicts, `run_metadata.json`, and the
    manifest, so every consumer answers "did this finish?" identically.
    """
    reward = getattr(getattr(sim, "reward_info", None), "reward", None)
    termination = str(sim.termination_reason)
    completed = termination in NORMAL_TERMINATIONS and reward is not None
    info = getattr(sim, "info", None)
    return {
        "task_id": str(sim.task_id),
        "trial": getattr(sim, "trial", None),
        "termination": termination,
        "reward": reward,
        "completed": completed,
        "failure": _failure_of({"info": info if isinstance(info, dict) else None}, completed),
    }


def session_ref_of(sim_payload: dict[str, Any]) -> str | None:
    """The host-side episode identity, read off the trajectory's raw_data."""
    for message in sim_payload.get("messages") or []:
        raw = message.get("raw_data") or {}
        ref = raw.get("pi_session_ref")
        if ref:
            return str(ref)
    return None


def _completed(sim_payload: dict[str, Any]) -> tuple[Any, str, bool]:
    reward = (sim_payload.get("reward_info") or {}).get("reward")
    termination = str(sim_payload.get("termination_reason"))
    return reward, termination, termination in NORMAL_TERMINATIONS and reward is not None


#: Bounded projection of τ's error text: the full traceback stays in results.json.
_FAILURE_ERROR_LIMIT = 500


def _failure_of(sim_payload: dict[str, Any], completed: bool) -> dict[str, Any] | None:
    """The root cause τ recorded for a failed episode, projected onto its manifest row.

    τ's retry-exhaustion placeholder carries `info: {error, error_type, error_traceback,
    failed_after_attempts}` inside results.json — where a held-out round's rewards also
    live, so nothing may read it back. Copying the cause (bounded, traceback excluded)
    onto the row keeps "why did this episode fail" answerable from the manifest alone.
    """
    if completed:
        return None
    info = sim_payload.get("info")
    if not isinstance(info, dict) or not (info.get("error") or info.get("error_type")):
        return None
    return {
        "error_type": info.get("error_type"),
        "error": str(info.get("error"))[:_FAILURE_ERROR_LIMIT],
        "failed_after_attempts": info.get("failed_after_attempts"),
    }


def _finite(value: Any) -> Any:
    """NaN/Inf → None. τ records NaN costs on the platform lane (AG-UI carries no usage),
    and the manifest is JSONL that downstream readers must parse strictly."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def build_rows(results_payload: dict[str, Any], context: RoundContext) -> list[dict[str, Any]]:
    """One row per simulation in τ's results file, joined to the platform evidence behind it.

    Queue-tolerant by construction: N is the number of simulation rows τ recorded — including
    `infrastructure_error` placeholders, which carry no session ref and join to nothing —
    never the number of submissions.
    """
    rows: list[dict[str, Any]] = []
    for sim in results_payload.get("simulations") or []:
        ref = session_ref_of(sim)
        account = context.accounting.get(ref or "") or {}
        reward, termination, completed = _completed(sim)
        recipe_sha = account.get("recipe_git_commit_sha")
        cost = account.get("cost")
        if isinstance(cost, dict):
            cost = cost.get("usd") or cost.get("total") or cost.get("total_cost")
        usage = account.get("usage") if isinstance(account.get("usage"), dict) else {}
        incidents = context.incidents_by_ref.get(ref or "")
        rows.append(
            {
                "tau_task_id": str(sim.get("task_id")),
                "trial": sim.get("trial"),
                "seed": sim.get("seed"),
                "reward": reward,
                "termination": termination,
                "completed": completed,
                "failure": _failure_of(sim, completed),
                "experiment": context.experiment_id,
                "generation": context.generation,
                "split": context.split,
                "transport": context.transport,
                "label": context.labels_by_ref.get(ref or ""),
                # On the platform lane the task id doubles as the conversation id; locally
                # there is no Introspection identity and the Pi session file is the record.
                "introspection_task_id": ref if context.transport == "platform" else None,
                "pi_session_ref": ref,
                "recipe_git_commit_sha": recipe_sha,
                "arm_sha": context.arm_sha,
                "arm_sha_ok": (
                    None
                    if context.transport != "platform" or recipe_sha is None
                    else (not context.arm_dirty and recipe_sha == context.arm_sha)
                ),
                "cost_usd": _finite(cost) if isinstance(cost, (int, float)) else None,
                "agent_cost": _finite(sim.get("agent_cost")),
                "user_cost": _finite(sim.get("user_cost")),
                "total_tokens": usage.get("total_tokens"),
                "span_counts": account.get("metrics"),
                "evidence_complete": account.get("evidence_complete"),
                "stall_warnings": (incidents or {}).get("stall_warnings", 0),
                "incidents": incidents,
                "messages": len(sim.get("messages") or []),
                "duration_seconds": _finite(sim.get("duration")),
            }
        )
    return rows


def write_manifest(out_dir: Path, rows: list[dict[str, Any]]) -> Path:
    """Write the rows beside `run_metadata.json`. JSONL, one episode per line, stable order."""
    path = Path(out_dir) / MANIFEST_NAME
    ordered = sorted(
        rows, key=lambda r: (r["tau_task_id"], r["trial"] if r["trial"] is not None else -1)
    )
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in ordered),
        encoding="utf-8",
    )
    return path


def read_manifest(out_dir: Path) -> list[dict[str, Any]]:
    path = Path(out_dir) / MANIFEST_NAME
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
