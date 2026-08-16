"""The Pi-local tool registry: which tool names the seam suppresses from τ.

Decided at the 2026-08-16 seam re-decision (user-directed, SIA_EVALUATION_PLAN.md D24;
the measurement that motivated it is `results/experiment_006_fixedb-bm25-luna56/
generation_000/seam_probe/`): a tool call that Pi executes locally — a recipe extension
tool, or the auto-generated `agent` delegation tool — is not forwarded to τ, costs no τ
step and no `max_errors`, and is logged in full on the assistant message's `raw_data`
(`pi_suppressed_tool_names`), so diagnosis sees everything grading does not.

The registry is the recipe's own committed declarations, never a heuristic:

  * `agents/agent.yaml` `tools:` — the model-callable allowlist. τ's tools arrive through
    the `mcp` block, never through `tools:`, so every `tools:` entry is by construction a
    Pi-side capability (Pi built-ins and extension-registered tools).
  * plus `agent`, exactly when `subagents:` is non-empty — delegation surfaces as the
    auto-generated `agent` tool.

A name in neither the τ catalogue nor this registry still forwards as-is: an agent calling
a tool nobody owns is graded behaviour (τ reports the invalid call), not seam business.
"""

from __future__ import annotations

from pathlib import Path

import yaml

AGENT_TOOL_NAME = "agent"


def pi_local_tool_names(recipe_dir: Path) -> frozenset[str]:
    """The suppression set, resolved once per run from the recipe that will serve it."""
    agent_yaml = Path(recipe_dir) / "agents" / "agent.yaml"
    data = yaml.safe_load(agent_yaml.read_text(encoding="utf-8")) or {}
    names = {str(name) for name in (data.get("tools") or [])}
    if data.get("subagents"):
        names.add(AGENT_TOOL_NAME)
    return frozenset(names)
