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

- **The §11.1 seam is decided and running.** An MCP tool bridge in `benchmark/tau_adapter/`
  serves τ's tool surface to Pi and rendezvouses on the results, so τ keeps tool execution,
  step counting, trajectory construction, and grading, and nothing is reconstructed. One
  `banking_knowledge` task and one `mock` task complete end to end and are graded by
  `tau2 evaluate-trajs`. `README.md` has the mechanism; `contract/constraints.md` has the
  reasoning and the known divergences.
- **The development lane is built and graded.** `make single_task TRANSPORT=platform` runs the
  episode as a task on the `target-agent` Runtime: reward 1.0, 8 τ tool calls through the bridge,
  and a conversation carrying cost, usage, span metrics and `recipe_git_commit_sha`. The runner
  starts `introspection dev` itself, so `operate` now has evidence to read. Read
  `benchmark/tau_adapter/dev_lane.py` before touching it — three of its constraints were found by
  experiment and are invisible in the docs (`--mcp` carries no credentials; a *connected* `tau`
  binding overrides `--mcp` and breaks every episode; an empty task races its own sandbox).
- **A turn ends when the platform run ends, not when τ has a message.** Prompting a task whose run
  is still streaming returns `409 Task is already processing`, which τ books as an infrastructure
  error and retries the episode over — it presented as "stuck on turn 2", and τ still graded one
  such episode **1.0** on the answers that had already landed. `PlatformTransport` gates on
  `RUN_FINISHED`; the bridge warns after 25s (`STALL_WARN_SECONDS`) because the sandbox's MCP
  daemon abandons a call long before the bridge's 300s ceiling, and that gap is otherwise silent.
  A green reward that hides a broken rendezvous is the failure this repo exists to prevent.
- **Cross-lane comparison is still unproven.** One clean graded episode per lane is not the §15
  A.0 fidelity gate. The known divergences are listed in `contract/constraints.md`; the one that
  could actually bias a score — an unpaired rendezvous — is now loud rather than silent, but not
  yet ruled out.
- **The lanes are not equally capable.** The platform lane is locked-domain only: `dev` serves the
  Recipe from the git work-tree, and diagnostic mode materialises a modified Recipe elsewhere, so
  `make smoke` and the fidelity gate stay local. The runner refuses the combination rather than
  running something misleading.
- **Locally the recipe is launched by `pi` directly, and that is a measured choice, not a
  shortcut.** `introspection local -- --mode rpc` was verified to work and to be behaviourally
  identical (`get_state` agrees on model, provider, base URL, thinking level), but costs +5.5s
  per episode — ~9 min per 97-task sweep — for validation the repo already does at commit, in
  CI, and once per run inside the runner. `LAUNCHER=introspection` switches back and stays
  exercised, because it is how the development lane resolves the recipe. Two consequences worth
  keeping: the CLI puts Pi two processes down, so teardown must kill the process *group*; and
  its recipe validation reads gitignore, so a materialised recipe must live inside the work
  tree, not `/tmp`.
- **A single task's reward is not stable, so `num_trials: 1` cannot support a comparison.** Ten
  runs of `banking_knowledge/task_001` under one frozen configuration returned 1.0 six times and
  0.0 four times (16–44 messages, $0.10–$0.51). τ's `--seed` cannot fix this: it seeds τ's own
  sampling, and Pi owns the agent's. Treat any single-trial per-task reward as a draw, raise
  `num_trials` before G0, and report pass^k. Evidence: `results/generation_000/task_001_trials/`.
- **In every inspectable run, reward tracked one retrieved document.** 1.0 iff `KB_search`
  returned `doc_credit_cards_gold_rewards_card_005` (`Annual fee: $0.00`, `2.5% cash back`), which
  is the task's answer; 0.0 whenever it did not. The failing agents reasoned correctly on worse
  evidence, and searched *more* to get *less* (6–8 calls vs 5) — one even queried the card by name
  and `bm25` returned savings-account tables instead. **Do not label this a harness defect yet:**
  query formulation is harness-owned, but `retrieval_config` is on the provisional offline `bm25`
  fallback, and that may be most of the effect. Settle the retrieval config before G0 or the first
  generation will attribute a benchmark artefact to the harness. Diagnosis is `operate`'s job.
- **No result here is a result yet.** `benchmark/benchmark_lock.yaml` is `PROVISIONAL`,
  `benchmark/split_manifest.yaml` is an empty stub, and the adapter-fidelity gate has never
  run. One lock value still needs a human decision before G0: the retrieval config is on the
  offline `bm25` fallback because this machine's `OPENAI_API_KEY` returns
  `429 billing_not_active`. The model pair is now deliberate and deliberately asymmetric, and
  neither half is Sonnet 5 — the agent runs Sonnet 4.6 to keep the harness the binding
  constraint rather than the model, and the user simulator runs Sonnet 4.5 because Sonnet 5
  rejects τ's `temperature: 0.0`. See `contract/protocol.md` for the ordering.
- Four items in the frozen-surface list below are wrong or incomplete as written; the
  corrections are in `contract/constraints.md § Corrections to the MVP document`.

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
benchmark/      tau_adapter/ (the seam) · scripts/ · tests/ · split_manifest.yaml · benchmark_lock.yaml
contract/       protocol.md · constraints.md
results/        generation_000/ ...
```

Inside `benchmark/tau_adapter/`, the seam is split by what each piece owns: `tool_bridge.py` (the
MCP server and the rendezvous), `transport.py` (the host-agnostic protocol), `transport_local.py`
and `transport_platform.py` (the two hosts), `dev_lane.py` (the `introspection dev` attachment and
its platform preconditions), `pi_agent.py` (τ's agent interface), `lock.py`, `run.py`.

§23 also lists `benchmark/fidelity/` and `contract/learning_record.schema.yaml`. Neither exists
yet: the fidelity gate has not been built and no learning record has been written, so creating
either now would be an empty promise. They arrive with §15 Phase A.0 and G0 respectively.

No `orchestrator/` directory. Claude Code is the orchestrator; a directory by that name would
imply a second agent implementation exists.

`contract/protocol.md` holds the per-generation procedure (§15) — loaded when running a
generation, deliberately not duplicated here.

## Stack

- Introspection recipes: YAML manifest at `.introspection/<name>.yaml` + TypeScript.
  Python deps are possible via `pi.runtime` with a committed `uv.lock`.
- τ²-bench is Python, pinned to an exact commit (§6.2), vendored gitignored under
  `benchmark/vendor/`. **uv**, not pixi — τ² mandates it and `pi.runtime.python.lockfile`
  expects `uv.lock`. Python is pinned to 3.12: τ² v1.0.1 reaches `audioop`, removed in 3.13.
- `introspection check` runs in `.githooks/pre-commit`, in CI (`recipe-validation.yml`), and once
  per run inside `benchmark/tau_adapter/run.py` before the first episode is spent.

## Standing guardrails for coding agents

- **Check current Introspection docs and plugin skill sources before assuming any API, CLI
  syntax, recipe layout, or permission behavior.** The MVP document is dated 2026-08-12 and
  defers to upstream wherever they differ.
- Recipe write access is a code-execution capability. Agent-authored changes land as PRs under
  branch protection; the agent does not merge its own work.
- Keep the first implementation simple enough that the origin of a performance change stays
  interpretable. Baseline G0 is deliberately unsophisticated (§13).
