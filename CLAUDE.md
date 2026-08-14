# Introspection Self-Improver

Demonstrate a **genuinely self-improving agent harness** built on Introspection's native
operational and improvement primitives, with τ²-bench `banking_knowledge` supplying an
**immutable external objective**.

The evaluation specification is `self_improving_agent_evaluation_protocol.md` — G disjoint
improvement batches drive generations H_0 → H_G, every generation is measured once against the
same fixed held-out set whose results stay hidden until the experiment closes, and the endpoint
question is R_T(H_G) > R_T(H_0). `SIA_EVALUATION_PLAN.md` is the forward tracker (decisions
D1–D10, incrementally validated phases); consult it to see where the path stands. The MVP
design guides and the old milestone tracker were removed 2026-08-13 (git history keeps them);
their evaluation design — pass^k, discovery/validation/test splits, checkpoints — is obsolete,
and what survives of them is the built machinery itself, documented by `README.md` and
`contract/`. "protocol §N" below means the evaluation protocol. This file is the always-loaded
subset an agent must not get wrong.

## The four roles

| Role | Who | Notes |
|---|---|---|
| Task oracle | τ²-bench `banking_knowledge` | Immutable. Gives tasks + reward, never a diagnosis. |
| Target agent (H_n) | An Introspection recipe in `target-agent/` | The only thing being improved. |
| Evidence substrate | Introspection | Conversations, traces, observations, patterns, metrics, judgements, runtime↔commit lineage. |
| Improvement orchestrator | **Claude Code + the Introspection plugin** | There is no orchestrator agent in this repo, and there must never be one. |

Loop: run an improvement batch → collect Introspection evidence → `operate` (discover signal)
→ `improve` (hypothesis + one minimal mutation, landed as a PR) → human approval → next
generation → hidden held-out evaluation → repeat with a fresh batch. Reveal at experiment
close.

## Current state — read before planning work

- **The seam is decided and running.** An MCP tool bridge in `benchmark/tau_adapter/`
  serves τ's tool surface to Pi and rendezvouses on the results, so τ keeps tool execution,
  step counting, trajectory construction, and grading, and nothing is reconstructed. Twelve
  platform-lane episodes across three `banking_knowledge` tasks (and the `mock` smoke) have
  completed end to end and been graded by `tau2 evaluate-trajs`; the A.0a pipe-semantics gate
  PASSed 2026-08-13. `README.md` has the mechanism; `contract/constraints.md` has the
  reasoning and the known divergences.
- **The development lane is built and graded.** `make single_task TRANSPORT=platform` runs the
  episode as a task on the `target-agent` Runtime, and every platform episode leaves a
  conversation carrying cost, usage, span metrics and `recipe_git_commit_sha`, joined to its τ
  episode by `episode_manifest.jsonl`. The runner starts `introspection dev` itself, so
  `operate` has evidence to read. Read
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
- **Cross-lane consistency is a diagnostic, not a gate (plan D4).** The A.0b run (12 episodes
  per lane, 2026-08-13) agreed on the aggregate within Wilson noise but FAILed on 3/12 platform
  timeouts from rendezvous stalls; the remedy — reassembling a run's narration with its tool
  call — landed (`7aee297`) and has since held under load: the Phase 2 platform-health
  batch (3/3 episodes, zero stall/timeout incidents) and the Phase 3.5c concurrent
  minitest both ran clean. Under the evaluation
  protocol the progression metric never crosses lanes (held-out runs locally, D1), so lane
  fidelity guards evidence quality only: `make fidelity` is the on-demand instrument, and the
  plan's Phase 2 platform-health check is the acceptance for batch rounds.
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
- **A single episode's reward is a draw — the protocol pools across tasks instead of repeating
  trials.** Ten runs of `banking_knowledge/task_001` under one frozen configuration returned
  1.0 six times and 0.0 four times (16–44 messages, $0.10–$0.51); τ's `--seed` cannot fix this
  — it seeds τ's own sampling, and Pi owns the agent's. Under the evaluation protocol every
  task runs once and the metric is held-out tasks passed / T (plan D2): variance pools across
  the held-out set, generation deltas inside the binomial noise band (~±17 pp at the debug
  T=8; ~±9 pp at the powered T=28; ~±7 pp at T=47) are noise, `pass^k` is never used
  for generations, and the endpoint reliability study (H_0 and H_G × extra trials,
  post-reveal, conditional per D11) is the named upgrade path. Evidence:
  `results/experiment_dummy/generation_000/task_001_trials/` — removed from the working tree
  with the 2026-08-13 fresh start; recover it from git history at that path.
- **In every inspectable run, reward tracked one retrieved document.** 1.0 iff `KB_search`
  returned `doc_credit_cards_gold_rewards_card_005` (`Annual fee: $0.00`, `2.5% cash back`), which
  is the task's answer; 0.0 whenever it did not. The failing agents reasoned correctly on worse
  evidence, and searched *more* to get *less* (6–8 calls vs 5) — one even queried the card by name
  and `bm25` returned savings-account tables instead. **Do not label this a harness defect yet:**
  query formulation is harness-owned, but much of the effect may be the `bm25` backend — now the
  deliberate freeze, so retrieval-*usage* findings (query formulation, k, iteration, stopping)
  are attributable harness territory. Diagnosis is `operate`'s job.
- **No result here is a result yet.** The experiment numbering was RESET 2026-08-13
  (user-directed): every bring-up artifact was cleared from the working tree into git
  history — including the original bring-up freeze that held the id `001_bm25-sonnet46`
  (12 ad-hoc platform episodes, no reportable number; its closure README sits at
  `results/experiment_001_bm25-sonnet46/README.md` in history). Seq 1 froze the debug
  experiment (G=3, B=4, T=8 per plan D10) and was **voided the same day at H0**:
  `task_034` deterministically crashes τ's text-mode user simulator on the opening turn
  (empty completion at the frozen `temperature: 0.0`), a frozen-surface defect no
  harness mutation can reach — see `results/experiment_001_bm25-sonnet46/README.md`,
  whose vault stays sealed forever. Seq 2 — the debug experiment's second attempt, its
  pool screened pre-partition for that crash class — ran to completion and REVEALED
  2026-08-14: three accepted generations, held-out curve 3/8 → 3/8 → 2/8 → 2/8,
  endpoint inside the ±18 pp band — the loop is demonstrated, no capability claim is
  made. Seq 3 is the **powered** experiment — the tier between debug and full, cut
  PROVISIONAL 2026-08-14 as `003_powered-bm25-sonnet46`: G=5, B=8, T=28 per plan D11,
  sized from seq-2 actuals by `results/experiment_002_bm25-sonnet46/SIZING_ANALYSIS.md`
  (powered for a ~+4–5 pp/generation loop; anything smaller reads directional at any
  affordable T), on a fresh 76-task pool (nothing seq 2 tuned on or revealed), with a
  pre-registered one-sided trend test over H0…H5 at α=0.05 as the primary instrument.
  The full T=47 run defers to seq 4: at measured costs (~$210–230) it buys ~10 pp of
  trend power for ~$80 more. Freeze fingerprints disambiguate the reused id
  mechanically. The model pair is
  deliberate and deliberately asymmetric, and neither half is Sonnet 5 — the agent runs
  Sonnet 4.6 to keep the harness the binding constraint rather than the model, and the user
  simulator runs Sonnet 4.5 because Sonnet 5 rejects τ's `temperature: 0.0`.

## Invariants

These are project-specific and safety-critical: violating one silently invalidates every
cross-generation comparison. This file is their authoritative home — do not restate them
elsewhere; `benchmark/benchmark_lock.yaml` holds the frozen *values*, this holds the *rules*.

**Never**

- Modify the τ evaluator, task definitions, gold state, or reward aggregation.
- Recompute reward anywhere except `tau2 evaluate-trajs`.
- Change the benchmark semantic adapter's semantics. It sits between agent and an untouched
  evaluator, so a defect here changes grades invisibly (the blocking A.0a gate guards this).
- Read held-out tasks, trajectories, per-task rewards, or aggregate scores before the
  experiment's reveal — the firewall applies to every generation, H_0 included. Improvement
  batches are fully observable by design; held-out evaluation runs on the local lane with
  outputs out of tree (plan D1/D9), revealed only after the final generation is frozen.
- Hardcode benchmark answers, or redefine the objective in terms of diagnostics.
- Pre-label failures with a human-authored taxonomy. Open-code the evidence first.
- Fabricate a signal. Every claim cites the executions behind it.

**Frozen for the duration of an experiment** (values in `benchmark/benchmark_lock.yaml`)

`--domain` · task set + task split (two values, not one) · `--retrieval-config` · agent model
+ thinking level (`--agent-llm` is declared-and-unused; Pi owns the model) · `--user-llm` +
args (including `timeout`) · `num_trials` · `--seed` · `--max-steps` · `--max-errors` ·
`timeout_seconds` (τ's `TextRunConfig.timeout`; `--max-steps-seconds` is inert in text mode) ·
`enforce_communication_protocol` · tau2-bench commit SHA · the partition
manifest (improvement batches + held-out set) · the experiment's `protocol:` configuration
(generations, batch size, held-out size).

`max_concurrency` is deliberately NOT on this list (re-decided 2026-08-13): parallelism moves
wall-clock, never what the agent can do inside an episode, so the lock's value is an
operational default that any run may override with `--max-concurrency` (1 = serial); the
effective value is recorded per run in `run_metadata.json`. `make batch` pins 2 to match the
org's observed ~2-sandbox quota. The documented caveat is provider
contention at high N, which shows up as infra retries, not as graded capability.

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
- `deploy` — not used in current scope: generations are served from the git work-tree by
  `introspection dev`. Revisit only if a staging runtime becomes necessary.
- `create` / `migrate` — building the initial recipe.

**Do not reimplement the plugin's methodology.** Baselines, controls, falsification, earliest
divergence, owning layer, one-mechanism-at-a-time — the plugin owns all of it. This repo
supplies only what the plugin cannot know: the objective, the frozen surfaces, the permissions,
and the reproducibility requirements.

The Introspection **CLI is the only interface** for operating the platform. Never substitute the
dashboard, browser automation, or direct API calls for an operator action the CLI owns.

## Experimental discipline

- **Prove the adapter before producing any result.** A.0a — the adapter test suite plus the
  mock-domain smoke — is blocking per experiment. Cross-lane consistency (A.0b) is an
  on-demand diagnostic and the stock-agent anchor (A.0c) is retired (plan D4): the
  progression metric never crosses lanes.
- One coherent mutation per generation. Multi-change generations are uninterpretable.
- Every generation is measured once against the same fixed held-out set. A rejected or failed
  mutation yields an identity generation — H_(g+1) = H_g, result carried forward, recorded —
  and there are no paired baseline/candidate arms.
- **Label every number with its set (batch B_g or held-out) and its N**; report the count
  with the percentage. Never describe generations with `pass^k`; state the scale-aware
  binomial noise band (±17 pp at T=8; ±9 pp at the powered T=28; ±7 pp at T=47)
  wherever the progression curve renders — and the visual bar scales with it: at T=28
  a ≥2-task endpoint gain arises under the null 29% of the time, so "reads
  directional" starts at ≥4–5 tasks (D11).
- When an effect is smaller than the held-out set can resolve, record it as **directional**
  and say so.
- Rejected hypotheses and failed mutations are first-class results — record them.
- Every transition leaves an evidence → signal → hypothesis → mutation → result record under
  `results/experiment_<id>/improvement_records/` (protocol §24), with stable Introspection
  identifiers linking each conclusion back to real evidence.

## Layout

```text
target-agent/   the Introspection recipe under improvement (H_0 anchor: git tag h0-baseline)
benchmark/      tau_adapter/ (the seam) · fidelity/ · scripts/ · tests/ · split_manifest.yaml · benchmark_lock.yaml
contract/       protocol.md · constraints.md
results/        experiment_<id>/ → generation_NNN/ · improvement_records/ · held_out/ (at reveal)
dashboard/      read-only results viewer over results/ (make dashboard; never a pipeline participant)
```

One experiment is one freeze: `experiment.seq` + `experiment.name` in `benchmark_lock.yaml`
name it (id = `<seq, zero-padded to 3>_<name>`, e.g. `001_bm25-sonnet46`; a re-decided freeze
bumps `seq`, and the name may repeat across experiments), results derive to
`results/experiment_<id>/` (the runner refuses any other `results/` path), and once the lock
is no longer `PROVISIONAL` the first run snapshots the freeze into that directory's
`experiment.yaml`, which every later run must match. `experiment_dummy` was the pre-freeze
bring-up bucket, removed from the working tree 2026-08-13 (in git history).

Inside `benchmark/tau_adapter/`, the seam is split by what each piece owns: `tool_bridge.py` (the
MCP server and the rendezvous), `transport.py` (the host-agnostic protocol), `transport_local.py`
and `transport_platform.py` (the two hosts), `dev_lane.py` (the `introspection dev` attachment and
its platform preconditions), `pi_agent.py` (τ's agent interface), `experiment.py` (the
experiment level of `results/` and its freeze snapshot), `lock.py`, `run.py`.

`benchmark/fidelity/` is the on-demand adapter-invariant diagnostic (`make fidelity`,
`benchmark/fidelity/compare_lanes.py`) — per-episode invariants and factual counts only, no
cross-lane statistical judgment; the blocking gate it once fed is retired (plan D4).
`contract/improvement_record.schema.yaml` landed at plan Phase 3 with the generation
lifecycle; `tau_adapter/records.py` loads it to validate every record.

No `orchestrator/` directory. Claude Code is the orchestrator; a directory by that name would
imply a second agent implementation exists.

`contract/protocol.md` will hold the per-generation procedure, written at plan Phase 4 from
the debug generation that actually ran — deliberately not before, and deliberately not
duplicated here.

## Stack

- Introspection recipes: YAML runtime manifest at `.introspection/<name>.yaml` + a recipe
  package. `target-agent/` is deliberately bare — `agents/agent.yaml`, `SYSTEM.md`,
  `package.json`, no TypeScript or Python source; TS extensions and Python deps (via
  `pi.runtime` + a committed `uv.lock`) are available growth surfaces for later generations.
- τ²-bench is Python, pinned to an exact commit, vendored gitignored under
  `benchmark/vendor/`. **uv**, not pixi — τ² mandates it and `pi.runtime.python.lockfile`
  expects `uv.lock`. Python is pinned to 3.12: τ² v1.0.1 reaches `audioop`, removed in 3.13.
- `introspection check` runs in `.githooks/pre-commit`, in CI (`recipe-validation.yml`), and once
  per run inside `benchmark/tau_adapter/run.py` before the first episode is spent.

## Standing guardrails for coding agents

- **Check current Introspection docs and plugin skill sources before assuming any API, CLI
  syntax, recipe layout, or permission behavior.** Repo documentation defers to upstream
  wherever they differ.
- Recipe write access is a code-execution capability. Agent-authored changes land as PRs under
  branch protection; the agent does not merge its own work.
- Keep the first implementation simple enough that the origin of a performance change stays
  interpretable. H0 is deliberately unsophisticated, anchored by the `h0-baseline` tag.
