# Introspection Self-Improver

Demonstrate a **genuinely self-improving agent harness** built on Introspection's native
operational and improvement primitives, with τ²-bench `banking_knowledge` supplying an
**immutable external objective**.

The full design is `introspection_self_improving_agent_mvp.md` (§ references below point into it).
That document is the specification; this file is the always-loaded subset an agent must not
get wrong.

## The four roles

| Role | Who | Notes |
|---|---|---|
| Task oracle | τ²-bench `banking_knowledge` | Immutable. Gives tasks + reward, never a diagnosis. |
| Target agent (H_n) | An Introspection recipe in `target-agent/` | The only thing being improved. |
| Evidence substrate | Introspection | Conversations, traces, observations, patterns, metrics, judgements, runtime↔commit lineage. |
| Improvement orchestrator | **Claude Code + the Introspection plugin** | There is no orchestrator agent in this repo, and there must never be one. |

Loop: run τ tasks → collect Introspection evidence → `operate` (discover signal) →
`improve` (hypothesis + one minimal mutation) → validate against τ → accept/reject → repeat.

## Current state — read before planning work

- **Blocking:** the seam between τ and Introspection (§11.1) is **undecided**. τ executes the
  agent's tool calls; a Pi agent executes its own. Nothing may assume a resolution. The
  timeboxed spike in §11.1 runs *before* any other MVP work, and its outcome becomes the design.
- `introspection check` reports **no recipe manifests**. Recipes live at `.introspection/<name>.yaml`.
  `.introspection/local.json` pins runtime `everyday-muse` — scaffolding, not a built agent.
- **Not a git repository yet**, despite `.githooks/pre-commit` and `.github/workflows/`.
  Recipe-as-repository, PR review, and per-generation commit lineage all depend on fixing this.
- `target-agent/`, `benchmark/`, `contract/`, and `results/` do not exist yet (§23 defines them).

## Invariants

These are project-specific and safety-critical: violating one silently invalidates every
cross-generation comparison. This file is their authoritative home — do not restate them
elsewhere; `benchmark/benchmark_lock.yaml` holds the frozen *values*, this holds the *rules*.

**Never**

- Modify the τ evaluator, task definitions, gold state, or reward aggregation.
- Recompute reward anywhere except `tau2 evaluate-trajs`.
- Change the benchmark semantic adapter's semantics. It sits between agent and an untouched
  evaluator, so a defect here changes grades invisibly (§15 Phase A.0 gates this).
- Read or optimize against the **test split**. Discovery is inspectable; validation returns
  aggregate outcomes only; test is used at predetermined checkpoints alone.
- Hardcode benchmark answers, or redefine the objective in terms of diagnostics.
- Pre-label failures with a human-authored taxonomy. Open-code the evidence first.
- Fabricate a signal. Every claim cites the executions behind it.

**Frozen for the duration of an experiment** (values in `benchmark/benchmark_lock.yaml`)

`--domain` · `--task-set-name` · `--retrieval-config` · `--agent-llm` + args ·
`--user-llm` + args · `--num-trials` · `--seed` · `--max-steps` · `--max-errors` ·
`--max-steps-seconds` · `--max-concurrency` · tau2-bench commit SHA · the split manifest.

Three of these are the ones that actually get missed:
- `--retrieval-config` rewrites the tool set **and** the policy text the agent is graded
  against. It is benchmark configuration, not harness. Improve how retrieval is *used*.
- `--user-llm` moves scores with no harness change at all.
- The execution budgets are exactly how a later generation "improves" by being allowed to do more.

**Mutable** — the target agent's harness: system prompt, instructions, skills, tool descriptions,
retrieval *usage* (query formulation, k, iteration, stopping), policy application, orchestration,
retry, context management, verification, tests, and justified diagnostic evals/judges.

## Working with the Introspection plugin

Route by what the work ends in; the plugin's own `BOUNDARIES.md` is binding.

- `operate` — inspect evidence, measure prevalence, diagnose. Ends in an answer.
- `improve` — land a harness change through the repository. Ends in a PR.
- `deploy` — only when a candidate must be activated to run. Not every generation needs it
  (§23.3; the spike decides).
- `create` / `migrate` — building the initial recipe.

**Do not reimplement the plugin's methodology.** Baselines, controls, falsification, earliest
divergence, owning layer, one-mechanism-at-a-time — the plugin owns all of it. This repo
supplies only what the plugin cannot know: the objective, the frozen surfaces, the permissions,
and the reproducibility requirements.

The Introspection **CLI is the only interface** for operating the platform. Never substitute the
dashboard, browser automation, or direct API calls for an operator action the CLI owns.

## Experimental discipline

- **Prove the adapter before producing any result.** Stock τ `LLMAgent`, adapter path vs. native,
  same seed and task IDs, scores must agree (§15 Phase A.0). Blocking, not a formality.
- One coherent mutation per candidate. Multi-change generations are uninterpretable.
- Run the unchanged baseline under identical configuration before claiming improvement.
  Pair baseline and candidate on identical task IDs, interleaved in one batch.
- **Label every score with its split and its N.** Never present the full-domain number as a
  held-out result. Report pass^k alongside pass¹.
- When an effect is smaller than the split can resolve, record it as **directional** and say so.
- Rejected hypotheses and failed mutations are first-class results — record them.
- Every generation leaves an evidence → signal → hypothesis → mutation → result record under
  `results/generation_NNN/` (§16, §24), with stable Introspection identifiers linking each
  conclusion back to real evidence.

## Layout (§23)

```text
target-agent/   the Introspection recipe under improvement
benchmark/      tau_adapter/ (the seam) · fidelity/ · split_manifest.yaml · benchmark_lock.yaml
contract/       protocol.md · constraints.md · learning_record.schema.yaml
results/        generation_000/ ...
```

No `orchestrator/` directory. Claude Code is the orchestrator; a directory by that name would
imply a second agent implementation exists.

`contract/protocol.md` holds the per-generation procedure (§15) — loaded when running a
generation, deliberately not duplicated here.

## Stack

- Introspection recipes: YAML manifest at `.introspection/<name>.yaml` + TypeScript.
  Python deps are possible via `pi.runtime` with a committed `uv.lock`.
- τ²-bench is Python, pinned to an exact commit (§6.2). Package manager not yet chosen.
- `introspection check` runs in `.githooks/pre-commit` and in CI (`recipe-validation.yml`).

## Standing guardrails for coding agents

- **Check current Introspection docs and plugin skill sources before assuming any API, CLI
  syntax, recipe layout, or permission behavior.** The MVP document is dated 2026-08-12 and
  defers to upstream wherever they differ.
- Recipe write access is a code-execution capability. Agent-authored changes land as PRs under
  branch protection; the agent does not merge its own work.
- Keep the first implementation simple enough that the origin of a performance change stays
  interpretable. Baseline G0 is deliberately unsophisticated (§13).
