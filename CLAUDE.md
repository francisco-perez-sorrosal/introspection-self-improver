# Introspection Self-Improver

Demonstrate a **genuinely self-improving agent harness** built on Introspection's native
operational and improvement primitives, with τ²-bench `banking_knowledge` supplying an
**immutable external objective**.

The evaluation specification is `self_improving_agent_evaluation_protocol.md` — G disjoint
improvement batches drive generations H_0 → H_G, every generation is measured once against the
same fixed held-out set whose results stay hidden until the experiment closes, and the endpoint
question is R_T(H_G) > R_T(H_0). `SIA_EVALUATION_PLAN.md` is the forward tracker (the
decisions ledger, incrementally validated phases); consult it to see where the path stands. The MVP
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
| Improvement orchestrator | **Claude Code + the introspection.dev skills, served by the Introspection CLI (`introspection skills`)** | There is no orchestrator agent in this repo, and there must never be one. |

Loop: run an improvement batch → collect Introspection evidence → `operate` (discover signal)
→ `improve` (hypotheses + one coherent improvement set — any number of individually-evidenced
changes across the mutable surface, landed as one PR; plan D22) → human approval → next
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
  made. Seq 4 is the **powered** experiment — the tier between debug and full, cut
  PROVISIONAL 2026-08-14 (as seq 3) and renumbered 2026-08-15 under the **parity
  convention** (plan D15: even seqs = stable, reportable experiments; odd seqs =
  experimentation — 1 is the voided debug freeze, 3 keeps the powered bring-up it
  already holds: the D12–D14 detours, pilots and seam validations under
  `results/experiment_003_powered-bm25-*/`; parity layers on the freeze discipline —
  a re-decide still bumps seq, to the next number of the right parity):
  `004_powered-bm25-luna56`, G=5, B=8, T=28 per plan D11,
  sized from seq-2 actuals by `results/experiment_002_bm25-sonnet46/SIZING_ANALYSIS.md`
  (powered for a ~+4–5 pp/generation loop; anything smaller reads directional at any
  affordable T), on a fresh 76-task pool (nothing seq 2 tuned on or revealed), with a
  pre-registered one-sided trend test over H0…H5 at α=0.05 as the primary instrument.
  The full T=47 run defers to seq 6: at measured costs (~$210–230) it buys ~10 pp of
  trend power for ~$80 more. Freeze fingerprints disambiguate any reused id
  mechanically. The model pair settled 2026-08-15 after three re-decisions (D12
  luna for cost → D13 haiku interim while a platform sandbox defect 400'd every
  openai/* model → D14 luna restored when the fix shipped): BOTH halves run
  `openai/gpt-5.6-luna`; the recipe uses the modern `ai:` spelling (validated by
  cloud validator 0.3.0 and locally since CLI 0.27.1) and deliberately omits
  `thinking_level` — the lock asserts the absence, and the sandbox's injected
  default (medium) is the effective level. The user simulator runs
  `reasoning_effort: medium` with no temperature (luna rejects 0.0; D2's pooling
  absorbs the stochasticity). Verified end to end 2026-08-15: local smoke and pilot
  green, platform episode graded reward 1.0 at
  $0.0157/episode with zero seam incidents. **H0 anchor corrected 2026-08-15 (D16)**:
  the h0-baseline tag had drifted onto seq-2-mutated recipes, so it was re-tagged at
  the restore commit — SYSTEM.md byte-identical to `h0-baseline-sonnet46`'s, only the
  sanctioned `ai:` block current — and `make reset_h0` verifies that identity.
  Calibration of record: the corrected-H0 luna pilot (baseline 6/28 = 21.4%,
  $0.022/local episode — results/experiment_004_powered-bm25-luna56/CALIBRATION_PILOT.md);
  the earlier 003 pilot measured the contaminated harness (25%, superseded). The haiku
  detour (baseline 10.7%, its own pilot + 20M-prompt-bytes/hour org-cap caveat) is
  archived at results/experiment_003_powered-bm25-haiku45/.
- **Seq 4 is REVEALED (2026-08-15) and demonstrates no improvement.** Held-out curve
  6/28 → 8 → 5 → 6 → 7 → **4/28**; endpoint −2 tasks (−7.1 pp) inside the ±9 pp band;
  pre-registered trend z = −0.85, p = 0.802. The honest reading (closure README, which
  also corrects the reveal commit's over-read): the data are consistent with the five
  mutations having NO systematic effect — every movement sits inside single-trial
  sampling noise, the exposure D2 accepted. What IS demonstrated: the loop's machinery —
  208 episodes, zero seam incidents, five verified records, firewall enforced, all
  twenty §29 guardrails HELD. The finding that outlives the number: four of five
  generations went into ONE instruction paragraph, two of them repairing defects the
  paragraph itself introduced (gen-002 forbade a policy-required transfer; gen-003
  licensed a policy-forbidden one; gen-005 deleted the guidance and deferred to the
  policy). Two mutations carry direct positive batch evidence (gen-003's task_032,
  gen-004's task_040). Value-resolution from bm25 (T9) — the mode the batches kept
  pointing at — never got a slot.
- **Seq 5 is the loop-reliability experiment (plan D17/D18/D19), `005_fixedb-bm25-luna56`,
  REVEALED 2026-08-16 — and the loop did NOT improve the harness.** Deliberately ODD per
  D15: it studies the loop, not the capability claim. `protocol.batch_mode: fixed`
  measured ONE hand-chosen batch of 8 known-fail tasks under every generation (the last
  batch round is the endpoint round, consumed by no transition), asking "can the loop fix
  what it stares at?"; `num_trials: 3` turned per-task cells into pass rates (band ±5 pp
  at T=28). G was 2 (plan D20). **Result:** the pre-registered primary — the paired batch
  endpoint test, H2 vs H0 — gave Σ rate deltas −0.333, exact one-sided p = 1.0000, with
  the batch curve 4.2% → 8.3% → **0.0%**; held-out ran 19.0% → 15.5% → 19.0%, endpoint
  +0.0 pp, trend z = 0.00, p = 0.500. Against the frozen reading key (B↑T↑ works; B↑T→
  overfits; **B flat → the meta-agent is the problem**) the answer is the third line.
  **The finding that outlives the number:** gen-002 repeated seq 4's transfer-guidance
  failure *with that history in hand and two structural guards built against it* — the
  threshold delegated to the policy, the scope limited to "when the customer asks" — and
  neither held: transfers on DB tasks went 9/21 → 8/21 → 0/21, and `task_014`, whose gold
  IS a transfer, went 1/3 → 0/3 with zero transfers. **An instruction added to a prompt
  does not inherit the scope its author reasoned about.** Four of seven mutations across
  seq 4 and seq 5 have now failed that way, all in the same `SYSTEM.md` paragraph, while
  the recipe's three growth surfaces (Pi skill, extension tool, sub-agent) remain unused —
  that is the live hypothesis for a next experiment. Two genuine wins are on the record,
  both from gen-001 and both visible only because `batch_mode: fixed` measures the same
  tasks twice: retrieval of the defining document began to determine the argument
  (`task_014`, passing tracks retrieval instead of luck), and volunteering an unsourced
  optional argument stopped (`task_065` flipped on that alone). Closure:
  `results/experiment_005_fixedb-bm25-luna56/README.md`; §29 walk has nineteen HELD and
  **one WAIVED — human approval, waived by explicit user instruction, not held**.
- **Seq 6 is REVEALED (2026-08-16), `006_fixedb-bm25-luna56` — and its two instruments
  disagree.** Seq 5's design at depth: G=6, B=8 (the same eight tasks every round), T=28,
  `num_trials: 3`, composite improvement sets (D22), everything measured carried from seq 5,
  run **fully autonomously** (D23 — approval frozen false, not waived). **Pre-registered
  primary — the paired batch endpoint test, H6's `batch_07` vs H0's `batch_01` — is NULL:**
  Σ rate deltas −0.333, exact one-sided p = 1.0000, curve 8.3 → 4.2 → 12.5 → **16.7** → 4.2 →
  4.2 → **4.2%**. The **secondary held-out probe rose**: 15.5% → 22.6%, endpoint +2 tasks
  (+7.1 pp, outside the ±5 pp band), trend z = 1.77, **p = 0.038** — the first positive
  held-out signal in the project. **It is not a capability claim**: those 28 tasks are on
  their third experiment and both predecessors revealed, which is exactly why D23 made the
  batch curve primary. Observed B↓T↑ is not on the frozen reading key; the two surviving
  readings — a floor-selected batch whose range is three tasks at three trials, versus
  exposure on the held-out set — cannot be separated by this run.
- **What seq 6 established that outlives the number.** (a) **Every change that told the agent
  what to RETRIEVE or in what ORDER to act confirmed; every change that told it what NOT to do
  or offered an ALTERNATIVE failed** — eleven changes (two slots spent purely on reverts),
  three reverted after refutation, one superseded. (b) The sharper form of the standing
  lesson: *an instruction's escape clause is what the model optimises against, and one naming
  a precondition teaches the model to satisfy the precondition, not to drop the behaviour* —
  C2's "or explained" produced a zero-difference report, the lesson's clean witness. (E2's
  failure was long misquoted as this mode; its two landed sentences carry no precondition —
  the "apply the KB first" wording was D2's, co-resident in the prompt. E2 targeted the
  escalation motive and moved the rate the wrong way: 27 writes, then a transfer anyway.
  Errata: the seq-6 independent review § 6.)
  (c) **Transfer is a single dial** and this batch holds tasks on both sides of it (E2 present:
  15/24 transfers, `task_014` 2/3; reverted: 6/24, `task_014` 0/3) — six mutations across three
  experiments have moved the rate, none the discrimination. (d) **Two of the three "unused
  growth surfaces" were never available**: a g=0 probe measured that a Pi-local extension-tool
  call reaches τ as an invalid tool call costing a step and an error, sub-agents take the same
  path, and blocking a τ call lets τ execute the write anyway — `recipe-growth.md` claimed the
  opposite and was corrected. That re-reads both prior closures. (Since answered: the D24 seam
  re-decision suppresses registry-declared Pi-local calls from τ with full evidence-stream
  logging, re-opening extension tools and sub-agents — `contract/constraints.md` divergence 6.) (e) The fixed batch worked as
  designed: fixing `task_065`'s class choice exposed an ordering/eligibility constraint that
  had been masked, and fixing that produced its first pass. Closure:
  `results/experiment_006_fixedb-bm25-luna56/README.md`; §29 walk has **all twenty HELD or
  N/A-by-design, none waived**; 756 episodes, zero seam disconnect/timeout counters across
  168 platform episodes (one benign `sandbox_tool_error`; platform spend $4.08, ≈$16.75
  total).
- **The § 8 groundwork is landed (2026-08-16, plan D24–D27) — the common ground for the next
  experiment, applied task-agnostically from the seq-6 independent review.** The seam now
  suppresses registry-declared Pi-local tool calls from τ with full evidence-stream logging
  (D24 — `agent.yaml tools:` doubles as the registry; demoed live: a registered tool called
  in 3/3 episodes, invisible to grading, logged in `raw_data`/manifest); record schema v3
  adds per-clause falsifiers for instruction changes and a mechanically-gated backlog stamp
  (D26, with protocol step 4b surface probes and the positive-obligation concentration
  flag); the instrument gains a mechanical full-quadrant reading key, stratified-batch and
  fresh-holdout freeze rules, trend fragility at reveal (backfilled into seq 6), and batch
  process counters as prediction channels (D25); the recipe ships a committed-undeclared
  `before_agent_start` template with `h0-baseline` re-anchored at the scaffold commit
  (D27). Measured along the way (`benchmark/probes/2026-08-16-surface-probes/`): a DECLARED
  skill reaches nothing on this seam's local lane (with or without `read` — hook injection
  is the only skill delivery), and the platform lane pins the recipe to pushed main
  (`--allow-dirty` runs pushed main, `arm_sha_ok=false`). Results under D24 are not
  comparable to seq ≤ 6.
- **Seq 8 is REVEALED (2026-08-17), `008_stratb-bm25-luna56` — NULL on both instruments, and
  the first experiment whose instrument was calibrated by measurement.** Seq 6's design with
  two repairs (plan D28): a batch spanning strata *measured under H0 before the freeze*
  (2 anchors + 3 marginals + 3 headroom), and a mechanical nine-cell reading key. G=6, B=8,
  T=28, `num_trials: 3`, fully autonomous, first run on the D24 seam. **Primary** (paired
  batch endpoint, H6 vs H0): Σ rate deltas **+1.333**, exact p = **0.250** — positive but not
  significant, which the frozen rule classes FLAT. **Secondary** (held-out, FOURTH exposure,
  no capability claim): z = 0.60, p = 0.274, +1 task inside the ±5 pp band. Batch curve
  41.7 → 54.2 → 45.8 → 62.5 → **66.7** → 58.3 → 58.3%. The primary was underpowered by the
  batch's own endpoint structure — only 2 of 8 tasks had a non-zero endpoint delta and the
  exact sign-flip test needs 5 — which was computed and recorded *before* the endpoint round.
  Honest summary: **the loop changed the harness's behaviour and did not improve its
  capability.**
- **What seq 8 established that outlives the number.** (a) A **measured noise floor**: gen-005
  removed a change that never executed, so H5 was behaviourally identical to H4 and its batch
  round still moved **2 cells (8.3 pp)** — the first behavioural-identity round in this
  project, and it re-reads every attribution ever made here. (b) **Framing, not surface, moves
  an injected note**: a bare *list* changed nothing (reverted); a *missing-state* note changed
  behaviour **and suppressed unasked** (transfer rate 9/24 → 6/24 with no suppression
  requested); a *completed-state* note was safe and inert; a *consequence-stating* note
  confirmed. So it is not only escape clauses — **any** statement about a missing precondition
  can be read as a bar to acting. (c) **Transfer discrimination moved for the first time** in
  four experiments and seven prior mutations (`task_014` 1/3 → 3/3 with the gold reason code;
  every endpoint trial that issued the prescribed lookup chose the gold reason, the one that
  did not, did not) — **and only on one side**: over-escalation did not improve. (d) The rule
  **a denied prediction is not a revert trigger; a denied *mechanism* is** — with a measured
  counterfactual, since the change kept under it produced the clearest win two rounds later.
  (e) Anchors **42/42 across seven rounds**: the regression channel worked, and it produced a
  finding a known-fail batch cannot (a duplicate write diagnosed by reading a passing trial
  against a failing one of the same task). (f) The remaining headroom is **surface-exhausted**,
  proven by five rounds of layer-peeling — `task_026` ended calling the gold tool with three of
  four values *exact* and one off by one; reaching a rounding convention needs domain knowledge
  the invariants forbid. Recorded as first-class results: two reverts, one change measured
  **inert**, one retirement reversed, an erratum against its own gen-001 record, and three
  process failures. §29: seventeen HELD, two N/A, one HELD by frozen delegation, **none
  waived**; 756 episodes, one fingerprint, zero seam disconnects/timeouts, ≈ $17.
  **`pi_local_calls` was 0 across all 168 platform episodes** — every landed change was a hook,
  so the D24 seam ran its pump path and never its suppressing path, and **extension tools and
  sub-agents remain available but unexercised in a graded round**.

## Invariants

These are project-specific and safety-critical: violating one silently invalidates every
cross-generation comparison. This file is their authoritative home — do not restate them
elsewhere; `benchmark/benchmark_lock.yaml` holds the frozen *values*, this holds the *rules*.

**Never**

- Modify the τ evaluator, task definitions, gold state, or reward aggregation.
- Recompute reward anywhere except `tau2 evaluate-trajs`.
- Change the benchmark semantic adapter's semantics **mid-experiment, or silently**. It sits
  between agent and an untouched evaluator, so a defect here changes grades invisibly (the
  blocking A.0a gate guards this). The one sanctioned path — first taken by D24 (2026-08-16,
  user-directed): between experiments only, by explicit user decision recorded in the plan's
  D-ledger, with the A.0a suite extended to cover the changed semantics before any result is
  produced, and the cross-change non-comparability of results stated with the decision.
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
effective value is recorded per run in `run_metadata.json`. `make batch` pins 4 — the
"~2-sandbox org quota" was a misdiagnosis, corrected 2026-08-14 (three concurrent
sandboxes proven in the org's task history, no admission cap ever observed), and 4-wide
was validated 2026-08-15: four sandboxes provisioning concurrently at 35–65s each, zero
seam incidents (`generation_000/concurrency_smoke`). What bites is heavy-tailed sandbox
start latency (40–650s) against the transport's 240s queue budget
(`contract/constraints.md` § Platform-lane concurrency has the evidence); drop the value
per run if a round shows that churn. The documented
caveat is provider contention at high N, which shows up as infra retries, not as graded
capability.

Three of these are the ones that actually get missed:
- `--retrieval-config` rewrites the tool set **and** the policy text the agent is graded
  against. It is benchmark configuration, not harness. Improve how retrieval is *used*.
- `--user-llm` moves scores with no harness change at all.
- The execution budgets are exactly how a later generation "improves" by being allowed to do more.

**Mutable** — the target agent's harness: system prompt, instructions, skills, tool descriptions,
retrieval *usage* (query formulation, k, iteration, stopping), policy application, orchestration,
retry, context management, verification, tests, and justified diagnostic evals/judges.

## Working with the introspection.dev skills

The Introspection methodology ships with the CLI: `introspection skills` lists the workflows
with their routing descriptions, and `introspection skills <workflow>` (or
`<workflow>/<step>`) loads one. Route by what the work ends in; the workflow descriptions
the CLI serves are binding.

- `operate` — inspect evidence, measure prevalence, diagnose. Ends in an answer.
- `improve` — land a harness change through the repository. Ends in a PR.
- `deploy` — not used in current scope: generations are served from the git work-tree by
  `introspection dev`. Revisit only if a staging runtime becomes necessary.
- `create` / `migrate` — building the initial recipe.

**Do not reimplement the skills' methodology.** Baselines, controls, falsification, earliest
divergence, owning layer, one-mechanism-at-a-time — the CLI-served skills own all of it. This
repo supplies only what they cannot know: the objective, the frozen surfaces, the permissions,
the reproducibility requirements, and the experiment's cross-generation memory — the
project-local `sia` skill (`skills/sia`) is their side-kick for that last part.

The Introspection **CLI is the only interface** for operating the platform. Never substitute the
dashboard, browser automation, or direct API calls for an operator action the CLI owns.

## Experimental discipline

- **Prove the adapter before producing any result.** A.0a — the adapter test suite plus the
  mock-domain smoke — is blocking per experiment. Cross-lane consistency (A.0b) is an
  on-demand diagnostic and the stock-agent anchor (A.0c) is retired (plan D4): the
  progression metric never crosses lanes.
- One coherent **improvement set** per generation (plan D22, from seq 6): any number of
  changes, each individually evidenced, each one coherent mechanism with its own falsifiable
  prediction. The generation is the unit of measurement; the change is the unit of diagnosis;
  per-change attribution is mechanistic (predictions scored against the next batch), never
  statistical. One branch, one commit per change, one PR, one human gate. Seq ≤5 ran one
  mutation per generation — read their records under that rule.
- Every generation is measured once against the same fixed held-out set. A rejected or failed
  mutation yields an identity generation — H_(g+1) = H_g, result carried forward, recorded —
  and there are no paired baseline/candidate arms. The cadence — baseline measured first,
  every batch preceded by its generation's held-out round, the experiment always ending on
  the final harness's measurement — is MECHANICAL: `run.py` refuses a batch whose
  generation is unmeasured or whose recipe is not that generation's tag (identity chains
  resolved), and `make reveal` refuses to close while any non-identity generation lacks
  its round; the held-out runner symmetrically refuses to measure H_N before batch_N is
  graded and its record accepted, so no generation the loop never learned for can enter
  the curve (protocol.md § Per generation has the full guarantee).
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
skills/         orchestrator-facing Claude Code skills (sia — generation-transition memory; wired via .claude/skills/, never a Pi discovery path)
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

`contract/protocol.md` holds the per-generation procedure, written at plan Phase 4 from
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

- **Check current Introspection docs and the CLI-served skills (`introspection skills
  <selector>`) before assuming any API, CLI syntax, recipe layout, or permission behavior.** Repo documentation defers to upstream
  wherever they differ.
- Recipe write access is a code-execution capability. Agent-authored changes land as PRs under
  branch protection; the agent does not merge its own work.
- Keep the first implementation simple enough that the origin of a performance change stays
  interpretable. H0 is deliberately unsophisticated, anchored by the `h0-baseline` tag.
