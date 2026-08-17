# Step-4b surface probe, g=0 — the `tool_result` hook on the real domain

Required at g=0 by `contract/protocol.md` step 4b, and specifically needed here because
gen-001's C1 depends on a surface this project had only ever certified by **inference**:
`skills/sia/references/recipe-growth.md` trap 4 lists `tool_result` beside
`before_agent_start` as "legal", but only `before_agent_start` was ever measured on the
real domain (`benchmark/probes/2026-08-16-surface-probes/` P1). A verdict the loop is about
to spend a mutation slot on must be measured, never inherited.

Mutation lived on throwaway branch `probe/tool-result-hook` (deleted, never merged):
`target-agent/extensions/probe-toolresult.ts` + a `pi.extensions` declaration. Lane: local
(`pi --recipe … --mode rpc`) — the work-tree-faithful lane; the platform lane pins the
recipe to pushed main and would have measured the wrong arm (probe P3). Task: `task_096`,
3 trials, the frozen configuration. `introspection check` green before the run.

## The three questions, and what was measured

**1. Does `tool_result` fire for the tau MCP tools the bridge serves, and under what name?**
**Yes — 56 firings across the three episodes, every tau tool represented:**

| toolName | firings |
|---|---|
| `mcp_tau_KB_search_77c5623a9f` | 24 |
| `mcp_tau_call_discoverable_agent_tool_80c68890a7` | 11 |
| `mcp_tau_unlock_discoverable_agent_tool_c32286d3af` | 8 |
| `mcp_tau_get_user_information_by_name_a1dd4e6c8f` | 3 |
| `mcp_tau_get_current_time_38ed8300e7` | 3 |
| `mcp_tau_log_verification_3f7e938a8d` | 3 |
| `mcp_tau_transfer_to_human_agents_ef54745fe2` | 3 |
| `mcp_tau_get_credit_card_accounts_by_user_408270c3e9` | 1 |

The name arrives as `mcp_tau_<tau tool name>_<hash>`, so a handler must match on a
substring, never on equality. `event.content` is an array of `{type: "text"}` blocks
(a single block, 16,653 chars on the first `KB_search`), `event.isError` is present, and
**`event.input` carries the tool's own arguments** (`inputKeys: ["query"]` for `KB_search`)
— which means a handler can key its behaviour on what was asked as well as what came back.

**2. Can the returned patch change what the MODEL reads? Yes.** The handler appended a
marker text block to `KB_search` results only. The marker appears **24 times across the
three Pi session files** — exactly the number of `KB_search` firings, so every patch landed
and none was dropped.

**3. Does any of it reach tau's graded trajectory? No.** The marker occurs **0 times** in
`results.json`, and the round carried **0 tool-error messages**. τ executed the tool and
recorded its own result; the Pi-side transform is strictly downstream of that record. This
is the same category as the D24 suppression: agent-internal cognition, invisible to
grading, fully visible to diagnosis.

Rewards were 0.0/0.0/0.0 — `task_096` is a frozen headroom task at 0/31 lifetime, and the
probe's marker carried no task information, so this is the expected non-result and is
recorded rather than read as a finding.

## Verdict

`tool_result` is **measured functional on the banking domain, local lane** (CLI 0.28.0 /
Pi 0.84.1 / recipes 0.19.3): it sees every tau tool result, can rewrite what the model
subsequently reads, costs no τ step and produces no invalid call. It is a legitimate home
for deterministic transformation of retrieved content. `recipe-growth.md` trap 4 is updated
from inferred to measured on the strength of this run.

**What this probe does NOT establish**, stated so a later citation cannot over-read it:
platform-lane behaviour (unverified here — the platform pins the recipe to pushed main, so
that check happens post-merge, in gen-001's own `batch_02`); whether patching a result
*changes model behaviour usefully* (that is C1's hypothesis, and the batch is its test, not
this probe); and anything about `context`, which remains inferred.

## Raw evidence

`hook_firings.json` (all 56 firings with toolName, block types, text length, input keys,
and a truncated head), `verdict.json` (the three counts above, computed from the artifacts
rather than asserted), `episode_manifest.jsonl`, `run_metadata.json`. The run directory
`task_096_probe_toolresult/` was deleted after extraction, per the probe convention. Run
ids appear here as probe evidence only and are never cited as record provenance — a probe
precedes its batch, and record provenance validates against batch manifests.
