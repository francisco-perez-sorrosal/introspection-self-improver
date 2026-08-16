"""Read a graded run and separate what the adapter owns from what the model decides.

The point of a fidelity check here is *not* that two lanes produce the same score. They cannot be
expected to: a per-task reward in this domain is a draw (ten runs of one task under one frozen
configuration returned 1.0 six times and 0.0 four times), so equal rewards would prove nothing and
unequal rewards would condemn nothing.

What must hold identically, in every lane and every episode, is the set of properties the adapter
is responsible for. Those are checked as invariants. Everything the agent's sampling controls is
reported as information, clearly labelled, so nobody mistakes variation for a defect.

The distinction is the whole design: an adapter defect and an unlucky sample look the same in a
reward column, and only one of them invalidates the experiment.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# A τ trajectory is a flat message list. These are the shape letters used in the summary string,
# chosen so an episode's structure is legible at a glance across many runs.
AGENT_TEXT = "A"
AGENT_CALL = "A*"
USER_TEXT = "U"
USER_CALL = "U*"
TOOL_RESULT = "t"

NORMAL_TERMINATIONS = frozenset(
    {"user_stop", "agent_stop", "TerminationReason.USER_STOP", "TerminationReason.AGENT_STOP"}
)


@dataclass(frozen=True)
class Finding:
    """A single verdict. `ok=False` means the adapter changed something it must not."""

    check: str
    ok: bool
    detail: str


@dataclass
class EpisodeReport:
    """One episode, split into adapter-owned facts and sampling-owned ones."""

    task_id: str
    lane: str
    # Adapter-owned
    termination: str
    trial: int | None = None
    agent_tool_names: list[str] = field(default_factory=list)
    unmapped_tool_names: list[str] = field(default_factory=list)
    #: Registry names (D24 Pi-local suppression) that reached the τ trajectory anyway.
    #: Always a seam finding: either the filter failed or the runaway cap fired — both
    #: need human eyes before any score from this episode is cited.
    pi_local_leaks: list[str] = field(default_factory=list)
    calls_without_results: list[str] = field(default_factory=list)
    results_without_calls: list[str] = field(default_factory=list)
    reward_present: bool = False
    # Sampling-owned
    reward: float | None = None
    messages: int = 0
    agent_invocations: int = 0
    user_tool_names: list[str] = field(default_factory=list)
    shape: str = ""


def _shape_and_counts(messages: list[dict[str, Any]]) -> tuple[str, int]:
    letters: list[str] = []
    agent_invocations = 0
    previous: str | None = None
    for message in messages:
        role = message.get("role")
        calls = message.get("tool_calls") or []
        if role == "assistant":
            letters.append(AGENT_CALL if calls else AGENT_TEXT)
            # An agent invocation is an assistant message that answers a user turn. Later
            # assistant messages in the same turn are the agent continuing after a tool result.
            if previous == "user":
                agent_invocations += 1
        elif role == "user":
            letters.append(USER_CALL if calls else USER_TEXT)
        else:
            letters.append(TOOL_RESULT)
        previous = role
    return " ".join(letters), agent_invocations


def build_report(
    results_path: Path,
    lane: str,
    locked_tools: set[str],
    pi_local_tools: set[str] = frozenset(),
) -> EpisodeReport:
    """Summarise the first simulation in a τ results file — the single-task instrument."""
    return build_reports(results_path, lane, locked_tools, pi_local_tools)[0]


def build_reports(
    results_path: Path,
    lane: str,
    locked_tools: set[str],
    pi_local_tools: set[str] = frozenset(),
) -> list[EpisodeReport]:
    """Summarise every simulation in a τ results file — the gate-scale instrument."""
    payload = json.loads(Path(results_path).read_text(encoding="utf-8"))
    simulations = payload.get("simulations") or []
    if not simulations:
        # τ writes results.json incrementally, so an interrupted run leaves a well-formed file
        # holding nothing. Name that state; an IndexError here would read as a checker bug.
        raise SystemExit(
            f"{results_path} holds no simulations — an interrupted or empty run, not a record"
        )
    return [_report_of(sim, lane, locked_tools, pi_local_tools) for sim in simulations]


def _report_of(
    sim: dict[str, Any],
    lane: str,
    locked_tools: set[str],
    pi_local_tools: set[str] = frozenset(),
) -> EpisodeReport:
    messages = sim.get("messages") or []
    reward_info = sim.get("reward_info") or {}

    shape, agent_invocations = _shape_and_counts(messages)

    # Both participants hold tools in this domain, and only one surface is the adapter's.
    # The agent gets the 15 locked banking tools through our bridge. The user simulator has its
    # own — `apply_for_credit_card`, whose τ action check carries `requestor: user` — which never
    # touches the bridge and is absent from the locked catalogue by design. Conflating them
    # produces false alarms on precisely the *successful* episodes, the ones where the user
    # applies: first the user's result looks orphaned, then its tool name looks unmapped.
    called: dict[str, str] = {}
    agent_names: set[str] = set()
    user_names: set[str] = set()
    for message in messages:
        role = message.get("role")
        for call in message.get("tool_calls") or []:
            called[str(call.get("id"))] = str(call.get("name"))
            (agent_names if role == "assistant" else user_names).add(str(call.get("name")))
    resulted = {
        str(m.get("id")) for m in messages if m.get("role") == "tool" and m.get("id") is not None
    }
    return EpisodeReport(
        task_id=str(sim.get("task_id")),
        lane=lane,
        trial=sim.get("trial"),
        termination=str(sim.get("termination_reason")),
        agent_tool_names=sorted(agent_names),
        unmapped_tool_names=sorted(n for n in agent_names if n not in locked_tools),
        pi_local_leaks=sorted(n for n in agent_names if n in pi_local_tools),
        calls_without_results=sorted(cid for cid in called if cid not in resulted),
        results_without_calls=sorted(rid for rid in resulted if rid not in called),
        reward_present="reward" in reward_info,
        reward=reward_info.get("reward"),
        messages=len(messages),
        agent_invocations=agent_invocations,
        user_tool_names=sorted(user_names),
        shape=shape,
    )


def check_invariants(report: EpisodeReport) -> list[Finding]:
    """The properties the adapter owns. A failure here invalidates the episode's score."""
    findings = [
        Finding(
            check="the agent's tool names are τ's own",
            ok=not report.unmapped_tool_names,
            detail=(
                "every tool call in the trajectory names a locked τ tool"
                if not report.unmapped_tool_names
                else f"unmapped: {report.unmapped_tool_names} — the reverse name map let a "
                "Recipes-mangled name reach τ, so the graded action is not the action taken"
            ),
        ),
        Finding(
            check="no Pi-local call reached τ (D24)",
            ok=not report.pi_local_leaks,
            detail=(
                "every registry-suppressed name stayed out of the trajectory"
                if not report.pi_local_leaks
                else f"leaked: {report.pi_local_leaks} — the suppression filter failed or the "
                "runaway cap fired; read the episode before citing its score"
            ),
        ),
        Finding(
            check="every tool call was answered",
            ok=not report.calls_without_results,
            detail=(
                "the rendezvous paired every call with a result"
                if not report.calls_without_results
                else f"{len(report.calls_without_results)} unanswered call(s): "
                f"{report.calls_without_results[:5]} — a parked handler that never received a "
                "result, which the agent sees as a tool failure while the score may still look fine"
            ),
        ),
        Finding(
            check="no results without calls",
            ok=not report.results_without_calls,
            detail=(
                "no result was posted for a call the agent did not make"
                if not report.results_without_calls
                else f"orphan results: {report.results_without_calls[:5]}"
            ),
        ),
        Finding(
            check="episode ended normally",
            ok=report.termination in NORMAL_TERMINATIONS,
            detail=(
                f"{report.termination}"
                if report.termination in NORMAL_TERMINATIONS
                else f"{report.termination} — an adapter or infrastructure fault, not a graded outcome"
            ),
        ),
        Finding(
            check="reward came from τ",
            ok=report.reward_present,
            detail=(
                f"reward={report.reward}"
                if report.reward_present
                else "no reward_info: nothing graded this episode"
            ),
        ),
    ]
    return findings


SUCCESS_EPSILON = 1e-6  # τ's own definition: success = reward within 1e-6 of 1.0
INFRASTRUCTURE = "infrastructure_error"


def normalise_termination(value: Any) -> str:
    return str(value or "unknown").rsplit(".", 1)[-1].lower()


def is_success(reward: Any) -> bool:
    return (
        isinstance(reward, (int, float))
        and math.isfinite(reward)
        and abs(reward - 1.0) <= SUCCESS_EPSILON
    )


@dataclass(frozen=True)
class LaneAggregate:
    """One lane's episode counts, stated as facts. `graded` follows τ's convention — only
    infrastructure_error episodes are excluded from the denominator. No statistical judgment
    lives here: the evaluation protocol compares generations on the held-out set, never
    lanes against each other."""

    lane: str
    episodes: int
    graded: int
    successes: int
    pass1: float | None
    mean_messages: float | None


def aggregate(reports: list[EpisodeReport]) -> LaneAggregate:
    graded = [r for r in reports if normalise_termination(r.termination) != INFRASTRUCTURE]
    successes = sum(1 for r in graded if is_success(r.reward))
    n = len(graded)
    return LaneAggregate(
        lane=reports[0].lane if reports else "?",
        episodes=len(reports),
        graded=n,
        successes=successes,
        pass1=round(successes / n, 4) if n else None,
        mean_messages=round(sum(r.messages for r in reports) / len(reports), 1)
        if reports
        else None,
    )


def locked_tool_names() -> set[str]:
    """The frozen tool catalogue, so the check compares against the lock, not against itself."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tau_adapter import lock as lockmod

    return set(lockmod.load_lock().tool_catalog)
