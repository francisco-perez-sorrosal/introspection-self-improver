# Growing the recipe: Pi skills, extension tools, and sub-agents

For generations whose one coherent mechanism grows the target-agent recipe beyond
`SYSTEM.md` — a packaged skill, a deterministic extension tool, or a delegatable
sub-agent. Verify against current docs before landing — repo notes defer to upstream
(standing guardrail): [pi.dev/docs/latest](https://pi.dev/docs/latest) (skills,
extensions, packages) ·
[docs.introspection.dev/recipes](https://docs.introspection.dev/recipes) (agent-yaml,
extensions-and-tools, agents, manifest, skills).

## Choosing the surface

The design methodology is owned upstream: read `introspection skills
improve/capability-set` before choosing — its `agent-design` reference carries capability
shape (start narrow; omit never-allowed capabilities entirely; sub-agents only for work
with a stable contract and independently checkable result) and its
`agent-security-review` reference carries the untrusted-content review (τ's user messages
and every `KB_search` result are untrusted content; each added capability widens what
they can reach). This file adds only the mapping and this repo's constraints:

| Diagnosed mechanism shape | Surface |
|---|---|
| Behavioral guidance, policy application, judgment | `SYSTEM.md` `<instructions>` (the default) — or a **skill** when the judgment is bounded, named, and better loaded near the work |
| Deterministic operation that should not depend on model judgment (parsing, checking, structured transformation, value verification) | **extension tool** — but see trap 4: in THIS repo's seam every extension-tool call costs a τ step and an error, so prefer a no-tool-call hook (`tool_result`, `context`, `before_agent_start`) |
| Retrieval-usage enforcement instructions failed to hold — search budgets, stopping rules, k discipline | **extension event interception** — `tool_result` / `context` / `before_agent_start` only. Do NOT block a τ tool call from `tool_call`: trap 4 shows τ executes it regardless |
| A bounded job delegatable with a stable contract and an independently checkable result | **sub-agent** — but see trap 4: in THIS repo's seam a sub-agent's delegation call reaches τ as an invalid tool call, so the surface is unavailable |
| External service capability | MCP server — **not** a sanctioned growth surface here without explicit seam work: the tau binding/`--mcp` interplay is fragile (`dev_lane.py`), so surface it as a user decision, never land it as an ordinary mutation |

## Wiring by surface
<!-- last-verified: 2026-08-15 note: against docs.introspection.dev/recipes (manifest, agent-yaml, agents, extensions-and-tools) and pi.dev/docs/latest (skills, extensions) -->

All three land inside `target-agent/` and are declared twice: once in the package
manifest (what the package ships) and once in `agents/agent.yaml` (what this agent may
use). `introspection check` validates both (`make check`; also pre-commit, CI, and once
per run).

**Skill** — packaged, on-demand judgment:

- `target-agent/skills/<name>/SKILL.md`, Agent Skills standard: frontmatter `name`
  (≤64 chars, lowercase a–z 0–9 hyphens, keep equal to the directory) + `description`
  (≤1024 chars; missing description prevents loading). Optional `scripts/`,
  `references/`, `assets/`.
- Manifest: `"pi": { "skills": ["skills/**/SKILL.md"] }` (currently `[]`).
- Agent: `skills:` list, referenced **by frontmatter name, not path**.
- Local exemplar of the spelling: `.pi/skills/share-to-traces-pi/SKILL.md`.

**Extension tool** — deterministic TypeScript the model can call:

- A `.ts` file in the recipe package (e.g. `target-agent/extensions/<name>.ts`); Pi loads
  the TypeScript directly, no build step. Default-export factory receiving the
  `ExtensionAPI`; register with `pi.registerTool({ name, description, parameters:
  Type.Object(...), async execute(toolCallId, params, signal, onUpdate, ctx) {...} })`
  (TypeBox schemas; `StringEnum` from the pi-ai package for enums). Local exemplar:
  `.pi/extensions/traces.ts`.
- Manifest: `"pi": { "extensions": ["extensions/*.ts"] }` — **explicit declaration only;
  no convention discovery**. Node runtime deps go in `dependencies` with a committed
  lockfile (never `devDependencies`).
- Agent: a registered tool is accessible **only if allowlisted in `tools:`** — the
  manifest loads the extension into every agent session in the package (delegated
  children included), but `tools: []` keeps every registered tool unreachable.
- Extensions receive `PI_RECIPE_DIR` and `PI_AGENT_NAME`; locate package files through
  them, never hardcoded paths.
- Beyond `registerTool`, an extension can intercept lifecycle events — modify tool
  results, inject context, augment the system prompt — the deterministic home for stopping
  rules and budgets that prose failed to hold. Same file, same manifest declaration.
  **This was the item that said MCP-tool interception "must be dev-lane-verified against
  the bridge's turn semantics before any PR". It has been (2026-08-16) and the verdict is
  in trap 4: `registerTool` and `tool_call` blocking are both unavailable here; only the
  no-tool-call hooks are.**

**Sub-agent** — a delegatable recipe agent:

- Its own `target-agent/agents/<name>.yaml` with `name`, `description`, `ai:`, `tools:`,
  `skills:`, `subagents: []` (delegation is one level deep — a sub-agent gets no `agent`
  tool).
- Parent `agents/agent.yaml`: add the name under `subagents:`. The `agent` tool is
  **auto-generated from that list — never list `agent` in `tools:` manually**.
- Delegation is asynchronous: the `agent` tool exposes `start` (returns a run id),
  `status`, `wait`, `message`, `interrupt`, `close`. Instructions must handle "started,
  not finished" explicitly.

## Recipe semantics that bite
<!-- last-verified: 2026-08-15 note: against docs.introspection.dev/recipes/agent-yaml -->

- **Arrays never merge.** A declared `tools:`, `skills:`, or `subagents:` list replaces
  the inherited one entirely; `[]` clears it. A `from:`-derived agent declaring
  `tools: [x]` receives only `x`.
- **`ai.model` starts a fresh AI config**, dropping inherited thinking level and provider
  policy. For a sub-agent that must run the frozen model pair, prefer `from: agent` with
  **no** `ai:` block (inherits the frozen one) over re-declaring it.
- `extensions` and `mcp` require explicit manifest declaration; `agents`/`skills`/
  `prompts` have directory-convention defaults. Typos inside the `pi` block are errors.
- `session` (retry, compaction, tool_execution, provider timeouts) is a closed, validated
  schema — recipe-side and within the mutable list ("retry, context management"), but a
  `session` change is its own coherent mutation, never a rider.

## Pi discovery paths — know them to avoid them
<!-- last-verified: 2026-08-15 note: against pi.dev/docs/latest/skills and pi.dev/docs/latest/extensions -->

Beyond package declaration, Pi discovers ambient content from the working tree: skills
from `.pi/skills/` and `.agents/skills/` in ancestor directories up to git root (plus
global dirs, settings, `--skill`), and extensions from `.pi/extensions/*.ts`
project-local (plus global, `-e`, settings) once the project is trusted. Both lanes
launch Pi with its working directory inside this repo, so repo-root `.pi/skills/` and
`.pi/extensions/` (which holds `traces.ts` today) sit inside the target agent's potential
discovery scope. Consequences:

- An intended mutation goes through the recipe's explicit declaration, never an ambient
  path: the audited surface is the recipe tree — the held-out round verifies
  byte-identity of the recipe against H_g's tag, and an ambient skill or extension
  outside `target-agent/` would mutate the harness where that check cannot see it.
- `tools: []` keeps ambient-registered tools unreachable, but an ambient extension's
  lifecycle hooks may still run — when auditing an episode's effective surface, inspect
  the system prompt and tool list of a dev-lane episode, not just the recipe files.
- Orchestrator-facing content (sia itself, digests, notes) never goes in a discovery
  path. Repo-root `skills/` is safe: no root `package.json`, and bare `skills/`
  directories are scanned only inside packages.

## Experiment constraints — the traps

1. **`tools: []` × read-on-demand skill loading.** Pi surfaces skill names and
   descriptions in the system prompt and loads a skill's full body on demand via the
   `read` tool. This agent has no `read` — deliberately and load-bearingly (see the
   `tools: []` comment in `target-agent/agents/agent.yaml`: withholding `read`/`bash`
   denies a locally-hosted agent any path to the task definitions and gold state in
   `benchmark/vendor/`). Granting `read` is not a legal enabler. Before proposing a skill
   mutation, verify in the dev lane what a declared `skills:` entry actually does for a
   read-less agent — run a dev-lane episode (`make single_task TRANSPORT=platform`; read
   `benchmark/tau_adapter/dev_lane.py` before touching anything there — three of its
   constraints are invisible in the docs) and inspect the effective system prompt and
   behavior. If only the description surfaces, the mutation is inert as designed and the
   mechanism belongs in `SYSTEM.md` instead. Record the verifying conversation id in the
   improvement record's evidence.
2. **The gold-state leak generalizes to every surface.** No `read`/`bash`-class
   capability for the agent **or any sub-agent** (the upstream sub-agent example shows
   `tools: [read, bash]` — exactly what is forbidden here). Extension code runs in the Pi
   host with full permissions: an extension tool's `execute` must not read
   `benchmark/vendor/`, `results/`, or fetch benchmark content — state the tool's actual
   reach (filesystem, network, subprocess) in the PR and the record so the human gate
   reviews it.
3. **The frozen model pair binds sub-agents.** A sub-agent invoking a different or better
   model "improves" the way the freeze exists to prevent (the model is a comparison
   variable, not harness). Sub-agents inherit the frozen `ai:` block (`from: agent`, no
   `ai:` override); wanting anything else is a freeze re-decision to surface to the user,
   never an ordinary mutation.
4. **A Pi-local tool call is NOT invisible to τ — measured, and it rules two surfaces out.**
   This item previously claimed extension tools and sub-agents "never traverse the bridge,
   consume no τ steps". That is false for this seam and was corrected 2026-08-16 by a probe
   whose evidence is committed at
   `results/experiment_006_fixedb-bm25-luna56/generation_000/seam_probe/`.
   `transport_local._assistant_turn` forwards **every** `toolCall` block in a Pi assistant
   message, and `pi_agent._to_tau_message` passes an unmapped name through "as-is so τ
   reports it as the invalid call it is". The probe's trajectory shows exactly that:
   `assistant calls=['probe_note']` → `tool err=True :: Error: Tool 'probe_note' not found.`
   So:
   - an **extension tool** call costs a τ step and one of the episode's `max_errors` (10),
     and is recorded in the graded trajectory;
   - a **sub-agent** goes through the auto-generated `agent` tool, i.e. the same path;
   - **blocking a τ tool call** from a `tool_call` hook is worse than either: the call is
     still forwarded, so τ executes the write while the agent is told it was stopped, and
     agent and grader histories diverge.

   What stays legal is every extension hook that introduces **no tool call** —
   `before_agent_start` (replace/augment the system prompt), `tool_result` (transform what
   the model sees after a τ tool returns), `context` (inject messages) — plus `SYSTEM.md`
   and a skill's name/description. Changing the forwarding itself is **seam work**, not an
   ordinary mutation, and hiding agent tool calls from the graded trajectory is the kind of
   adapter helpfulness that makes a harness unmeasurable. The counterpart still holds:
   Pi-local work spends **wall-clock and tokens**, and τ's frozen `timeout_seconds` bounds
   the episode — measure episode latency in the dev lane before landing anything that adds
   a model invocation to the turn path.
5. **Answer-hardcoding extends to code and instructions.** No task-specific artifacts —
   KB document ids, gold values, per-task procedures — in skill bodies, tool code, or
   sub-agent instructions; general procedure only. The frozen `<policy>` text is never
   embedded anywhere.
6. **One coherent mutation.** The whole addition — content file(s) + manifest
   declaration + `agent.yaml` allowlist/reference (+ sub-agent YAML) — is one mechanism:
   one branch, one PR, one record, `make check` green. No riders.
7. **Verify in both lanes before the PR.** The platform sandbox must resolve the same
   surface the local lane does (deps from the committed lockfile, extension loading,
   sub-agent delegation); a dev-lane episode plus a local smoke is the floor, and the
   record cites the verifying conversation ids.

## Checklist before the PR

- [ ] `improve/capability-set` read (`agent-design`; `agent-security-review` when the
      capability widens what untrusted content can reach)
- [ ] Current upstream docs re-checked; loading behavior confirmed in the dev lane, with
      the verifying conversation id recorded
- [ ] Surface wired in both places (manifest + `agent.yaml`) in the same commit as the
      content; `make check` green
- [ ] No `read`/`bash`-class reach anywhere; extension tool reach stated in PR + record
- [ ] Sub-agents inherit the frozen `ai:` block; no model or thinking-level drift
- [ ] No frozen policy text, no instance answers, no orchestrator meta-knowledge
- [ ] Record's `owning_layer` names the surface; `expected_effect` scoped to the
      held-out set with named risks for the next batch
