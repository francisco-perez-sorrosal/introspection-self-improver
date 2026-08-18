# Step-4b surface probe — `sub-agent`, the last unexercised class

**Run 2026-08-18, generation 0, protocol step 4b (required at g=0).** Throwaway branch
`probe/subagent-step-budget` (commit `3ba4989`, branch deleted after extraction). Local lane,
work-tree-faithful, locked domain, **`task_089` — a non-partition task** (neither batch nor
held-out), 3 trials at the frozen `num_trials`. Nothing here is a generation, nothing here is
record provenance, and no partition task was touched.

## The question this probe was reserved to answer

`sub-agent` is the only surface class this project has never run a single episode on, in any
experiment. The open question carried by three closures and by
`skills/sia/references/recipe-growth.md`: **does a child agent's own tool calls travel the τ
bridge and therefore spend the PARENT episode's τ step budget** — in which case delegating
retrieval saves nothing?

## Wiring

`agents/agent.yaml` `subagents: [kb-researcher]` (which auto-generates the `agent` delegation
tool and puts it in the D24 Pi-local suppression registry); `agents/kb-researcher.yaml` with
`from: agent` and **no `ai:` block**, so the frozen model pair binds the child (recipe-growth
trap 3 — confirmed in the session log: the child ran `openai/gpt-5.6-luna` at thinking level
`medium`, identical to the parent); a throwaway `SYSTEM.md` clause telling the agent to
delegate knowledge-base lookups. `make check` green: `✓ 1 Recipe valid`.

## Verdict

### 1. The surface is REACHABLE and correctly suppressed — the adoption half passes

`pi_local_calls: 2` on **3 of 3 episodes**. Every episode's trajectory carries
`raw_data.pi_tool_names: ['agent','agent']` and
`raw_data.pi_suppressed_tool_names: ['agent','agent']`, and τ's graded trajectory contains
**zero** occurrences of `agent` — the only tool call τ ever saw was
`request_human_agent_transfer`. The auto-generated `agent` tool is called, executed by Pi,
and invisible to grading, exactly as D24 specifies. The asynchronous contract works as
documented: `start` returns `Started kb-researcher (agent-run-1) — atm-declines [running]`
and a second `agent` call collects the completed result.

### 2. A child CANNOT use τ's tools — this is the finding, and it is disqualifying

The child inherits the parent's `mcp:` block and resolves the mangled tool name correctly. It
issued `mcp_tau_KB_search_77c5623a9f` and **every call failed**:

| child run | calls | each | outcome |
|---|---|---|---|
| `agent-run-1` | 1 | 120.008 s | `MCP daemon: Timeout; remote outcome is unknown; do not retry automatically.` |
| `agent-run-2` | 2 | 120.008 s, 120.013 s | same |

Evidence: `child_runs/agent-run-*.status.json`, preserved verbatim from Pi's own run state.

**None of those calls reached the bridge.** `bridge_calls.jsonl` for the whole three-episode
run holds exactly **one** row — `transfer_to_human_agents`, `outcome: ok` — which is the
parent's. The child's calls die inside the sandbox MCP daemon at its 120 s patience limit
without ever arriving at the rendezvous.

**The original question is therefore moot rather than answered: a child's tool call spends no
τ step, because it never reaches τ.** What it spends is wall-clock, against the frozen
600 s `timeout_seconds`.

### 3. The cost is measured and severe

3/3 episodes ended `user_stop` at **6 messages** with reward **0.0**, having burned
138 s / 138 s / 270 s. `stall_warnings` 1, 1, 2. In all three the agent, handed
`{"status":"unable_to_complete", …}` by its own child, correctly declined to guess and
transferred to a human. The harness did not misbehave; it was starved.

### 4. A new seam signature, recorded

One episode retried on `AssistantMessage must have either content or tool_calls. Got
AssistantMessage` — the **assistant** side, distinct from the known luna user-simulator
signature. It appeared only with `subagents:` non-empty, i.e. only when a turn is fully
Pi-suppressed with nothing else in it. `contract/constraints.md` divergence 6 states the
turn-level pump "can never hand τ an empty assistant message"; this probe produced one such
retry. τ retried and the episode completed, and **no seq-12 graded round can reach this path**
— H0's `subagents:` is empty and no change landed in this experiment will populate it (see
below) — so it is recorded as a caveat against the surface rather than escalated as a defect
in the seam the experiment actually runs on.

## Operational envelope for the reserved slot

A sub-agent on this seam is usable **only for a bounded job over text the parent already
holds** — no τ tool anywhere in the child. That envelope is real but narrow, and it competes
directly with `context` and `tool_result` extension hooks, which do deterministic work on the
same material at zero added latency and are already measured functional on this domain. Every
delegation also costs two extra model invocations inside a frozen episode budget.

**Consequence for seq 12's reserved slot:** the reservation is discharged **by measurement**.
The class is now EXERCISED (a graded-lane episode ran one, adoption confirmed at 2/2 calls per
episode) and PROBED (its blocking limitation measured, with the failing tool-call records
committed). A `surface_exhausted`-style finding for the retrieval-shaped targets T1 and T3 is
now citable to this measurement rather than to an argument: **the mechanism those targets need
is a child that can search the knowledge base, and a child cannot search the knowledge base.**

## Reproducing

`git show 3ba4989` is unavailable (branch deleted); the wiring is three files and is quoted in
full above. Re-run with `make single_task TASK=<non-partition task> TRANSPORT=local`.
