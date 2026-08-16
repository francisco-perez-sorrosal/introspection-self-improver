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
and every retrieval-tool result are untrusted content; each added capability widens what
they can reach). This file adds only the mapping and this repo's constraints:

| Diagnosed mechanism shape | Surface |
|---|---|
| Behavioral guidance, policy application, judgment | `SYSTEM.md` `<instructions>` (the default) — or skill-shaped content delivered by a `before_agent_start` hook: a **declared** skill measurably reaches nothing on this seam's local lane (trap 1), so hook injection is the only working delivery |
| Deterministic operation that should not depend on model judgment (parsing, checking, structured transformation, value verification) | **extension tool** — but see trap 4: in THIS repo's seam every extension-tool call costs a τ step and an error, so prefer a no-tool-call hook (`tool_result`, `context`, `before_agent_start`) |
| Retrieval-usage enforcement instructions failed to hold — search budgets, stopping rules, k discipline | **extension event interception** — `tool_result` / `context` / `before_agent_start` only. Do NOT block a τ tool call from `tool_call`: trap 4 shows τ executes it regardless |
| A bounded job delegatable with a stable contract and an independently checkable result | **sub-agent** — but see trap 4: in THIS repo's seam a sub-agent's delegation call reaches τ as an invalid tool call, so the surface is unavailable |
| External service capability | MCP server — **not** a sanctioned growth surface here without explicit seam work: the tau binding/`--mcp` interplay is fragile (`dev_lane.py`), so surface it as a user decision, never land it as an ordinary mutation |

## Wiring by surface
<!-- last-verified: 2026-08-16 note: against CLI-served introspection-docs/pi-recipes-docs (recipe-format, recipe-manifest, agent-composition, recipe-skills, recipe-agents) and the installed Pi 0.84.1 docs/extensions.md + docs/skills.md; corrected the "declared twice" claim for extensions -->

All three land inside `target-agent/`. **Skills and sub-agents are declared twice** —
package manifest (what the package ships) + `agents/agent.yaml` (what this agent may use).
**Extensions are declared once, in the manifest only**: package membership means execution
— the closure loads for every session in the package, and agent YAML cannot select or
remove extensions (upstream-normative). `introspection check` validates the declarations
(`make check`; also pre-commit, CI, and once per run), and **every explicitly authored
path or glob must match something** — a declared glob with no files is a check failure,
so prefer explicit file paths over globs for single files.

**Skill** — packaged, on-demand judgment:

- `target-agent/skills/<name>/SKILL.md`, Agent Skills standard: frontmatter `name`
  (≤64 chars, lowercase a–z 0–9 hyphens; Pi relaxes the name-equals-directory rule) +
  `description` (≤1024 chars). Limit violations warn but load; a **missing description
  prevents loading**. Optional `scripts/`, `references/`, `assets/`.
- Manifest: `"pi": { "skills": [...] }` (currently `[]`); a declared glob must match.
- Agent: `skills:` list, referenced **by frontmatter name, not path**.
- **What actually reaches the model — measured on this seam (2026-08-16,
  `benchmark/probes/2026-08-16-surface-probes/`): NOTHING.** On the local lane
  (`pi --recipe` rpc, recipes 0.19.3 host) a declared skill left the effective prompt
  byte-identical to `SYSTEM.md` and the full Pi session free of any skill trace — with
  `tools: []` **and** with `read` granted. Pi-core sessions document the opposite
  (`formatSkillsForPrompt`: an `<available_skills>` block with name, description,
  absolute path, and a standing "use the read tool" instruction, body via `read`;
  `disable-model-invocation: true` removes it all) — that behavior does not manifest
  through this host path. Platform-host behavior unverified. See trap 1.
- Local exemplar of the spelling: `.pi/skills/share-to-traces-pi/SKILL.md`.

**Extension tool** — deterministic TypeScript the model can call:

- A `.ts` file in the recipe package (e.g. `target-agent/extensions/<name>.ts`); Pi loads
  the TypeScript directly (jiti), no build step. Default-export factory receiving the
  `ExtensionAPI`; register with `pi.registerTool({ name, description, parameters:
  Type.Object(...), async execute(toolCallId, params, signal, onUpdate, ctx) {...} })`
  (TypeBox schemas; `StringEnum` from the pi-ai package for enums). Import types from
  `@earendil-works/pi-coding-agent` — the docs' and the recipe peer-dependency's name
  (the ambient `.pi/extensions/traces.ts` exemplar imports an older package name; do not
  copy it). Type-only imports erase at runtime and create no `dependencies`/lockfile
  obligation; runtime deps do (committed lockfile, never `devDependencies`).
- Manifest: `"pi": { "extensions": ["extensions/<name>.ts"] }` — **explicit declaration
  only; no convention discovery; prefer the explicit path over a glob** (an unmatched
  glob fails `introspection check`). Declared once — no `agent.yaml` counterpart exists.
- Agent: a registered tool is model-callable **only if allowlisted in `tools:`** — but
  `tools:` limits model-callable tools, not hook execution: **extension code retains its
  non-tool behavior (all lifecycle hooks) even under `tools: []`** (upstream-normative).
- Loading and failure semantics (upstream-verified): extensions load sequentially in
  declaration order and hooks run in load order, middleware-chained; an extension **load**
  failure is fatal before any model call (the session aborts — a broken extension cannot
  silently degrade an episode); a handler **runtime** error is logged and swallowed
  (`tool_call` excepted — its errors block the tool). A probe therefore cannot signal
  through an exception; log a marker instead.
- Recipes' own host extension applies `SYSTEM.md` through an earlier-registered
  `before_agent_start`, so a recipe-owned `before_agent_start` runs after it and sees the
  fully composed prompt.
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
<!-- last-verified: 2026-08-16 note: against CLI-served pi-recipes-docs/agent-composition + recipe-format -->

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
  `session` change is its own coherent mutation, never a rider. Unlike the arrays it
  **merges recursively**; a declared `mcp` block **replaces the complete inherited
  policy**; `system_instructions: replace` discards `SYSTEM.md` too.

## Pi discovery paths — know them to avoid them
<!-- last-verified: 2026-08-16 note: against Pi 0.84.1 docs + recipes 0.19.3 embedded-session defaults; lane asymmetry noted, platform-host behavior unverified -->

Beyond package declaration, Pi discovers ambient content from the working tree: skills
from `.pi/skills/` and `.agents/skills/` in ancestor directories up to git root (plus
global dirs, settings, `--skill`), and extensions from `.pi/extensions/*.ts`
project-local (plus global, `-e`, settings) once the project is trusted. **The two lanes
do not have the same ambient exposure** (corrected 2026-08-16): the local lane launches
`pi --recipe` from the repo root with no `--no-skills`/`--no-extensions` flags, so
repo-root `.pi/skills/` and `.pi/extensions/` (which holds `traces.ts` today) sit inside
its potential discovery scope once trusted — while embedded Recipe sessions disable
ambient extensions, skills, prompt templates, and context files by default (whether the
platform sandbox uses that host is unverified; measure, don't assume). Consequences:

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

1. **A declared skill reaches NOTHING on this seam's local lane — measured 2026-08-16**
   (`benchmark/probes/2026-08-16-surface-probes/`, probe P2; this item has now been
   corrected twice — "inert, description surfaces" pre-2026-08-16, "adverse read-tool
   injection" earlier the same day — both against the measurement). A valid declared
   skill (`check` green, `pi.skills` + `agent.yaml skills:`) left the effective prompt
   byte-identical to `SYSTEM.md` and the Pi session free of any skill trace, with
   `tools: []` and with `read` granted on a mock-only discriminator. Two consequences:
   (a) skill-shaped judgment reaches a graded episode **only** as deterministic
   `before_agent_start` injection — extension code reads the body itself (host
   authority; keep reach inside the recipe dir via `PI_RECIPE_DIR`); (b) on any OTHER
   host, Pi-core sessions document an `<available_skills>` block that instructs the
   model to *use the `read` tool* — for a read-less agent that instruction would be
   adverse (an unregistered `read` call forwards to τ as an invalid call, trap 4), so
   re-verify per host before relying on either behavior. `read` itself stays withheld —
   deliberately and load-bearingly (the `tools: []` comment in
   `target-agent/agents/agent.yaml`: it denies a locally-hosted agent any path to the
   task definitions and gold state in `benchmark/vendor/`); granting it is not a legal
   enabler. Before proposing any skill-shaped mutation, verify its delivery in the lane
   that serves the work-tree (trap 7) and record the verifying run/conversation id in
   the improvement record's evidence.
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
   `before_agent_start` (replace/augment the system prompt; **measured functional on the
   banking domain, local lane, 2026-08-16** — probe P1: fires every session, sees the
   fully composed prompt, `undefined` leaves it unchanged, zero τ-side visibility),
   `tool_result` (transform what the model sees after a τ tool returns), `context`
   (inject messages) — plus `SYSTEM.md` (a declared skill's name/description measurably
   does NOT arrive here; trap 1). Changing the forwarding itself is **seam work**, not an
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
7. **Verify in both lanes — but know what each lane serves (measured 2026-08-16, probe
   P3).** The **platform lane pins the recipe to pushed `main`**: with unpushed commits
   the runner refuses, and `--allow-dirty` runs pushed main's recipe anyway, marking
   every row `arm_sha_ok=false` — it does NOT serve your branch. So pre-merge
   verification of a recipe change runs on the **local lane** (work-tree-faithful:
   `make single_task TRANSPORT=local` / `make smoke`), and the platform-side check
   happens post-push (seam canary or a dev-lane episode on the landed commit), with the
   record citing the verifying run/conversation ids. Budget the dev-lane iteration
   correctly (upstream `development-lifecycle`): a skill **body** edit takes effect on
   the next turn of the same chat, but `SYSTEM.md`, agent YAML, prompts, **extensions**,
   and MCP declarations need a **new chat**, and `.introspection/*.yaml` a new runtime
   version — one fresh task per extension revision.

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
