# Introspection Self-Improver

Demonstrate a **genuinely self-improving agent harness** built on Introspection's native
operational and improvement primitives, with τ²-bench `banking_knowledge` supplying an
**immutable external objective**.

The evaluation specification is `self_improving_agent_evaluation_protocol.md` — G improvement
batches drive generations H_0 → H_G (disjoint fresh draws under `batch_mode: fresh`; one fixed
batch re-measured every round under `fixed`, the mode every experiment since seq 5 has run),
every generation is measured once against the same fixed held-out set whose results stay hidden
until the experiment closes, and the endpoint question is R_T(H_G) > R_T(H_0). `SIA_EVALUATION_PLAN.md` is the forward tracker (the
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
changes across the mutable surface, landed as one PR; plan D22) → approval gate (human, or the
frozen D23-envelope autonomy) → next generation → hidden held-out evaluation → repeat (under
`batch_mode: fixed` the same batch is re-measured each round). Reveal at experiment close.

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
- **A single episode's reward is a draw — pool across tasks and trials.** Ten runs of
  `banking_knowledge/task_001` under one frozen configuration returned 1.0 six times and
  0.0 four times (16–44 messages, $0.10–$0.51); τ's `--seed` cannot fix this — it seeds
  τ's own sampling, and Pi owns the agent's. The current doctrine (D18, since seq 5;
  D2's single-trial era ended there): one knob, `frozen.num_trials`, governs both lanes
  — 3 since seq 5 and for seq 10 — per-task cells are pass RATES, the aggregate is the
  mean per-task rate, and the noise band is stated at the current scale wherever a
  curve renders (±5 pp at T=28×3; ≈±4.5 pp at the D34 T=36×3; the measured
  identical-harness floor on a B=8×3 batch is 2 cells / 8.3 pp). `pass^k` is never
  used for generations; within-generation pass@3 is legitimate reliability texture.
  Evidence: `results/experiment_dummy/generation_000/task_001_trials/` — removed from
  the working tree with the 2026-08-13 fresh start; recover it from git history.
- **In every inspectable run, reward tracked one retrieved document.** 1.0 iff `KB_search`
  returned `doc_credit_cards_gold_rewards_card_005` (`Annual fee: $0.00`, `2.5% cash back`), which
  is the task's answer; 0.0 whenever it did not. The failing agents reasoned correctly on worse
  evidence, and searched *more* to get *less* (6–8 calls vs 5) — one even queried the card by name
  and `bm25` returned savings-account tables instead. **Do not label this a harness defect yet:**
  query formulation is harness-owned, but much of the effect may be the `bm25` backend — now the
  deliberate freeze, so retrieval-*usage* findings (query formulation, k, iteration, stopping)
  are attributable harness territory. Diagnosis is `operate`'s job.
- **No result here is a result yet — the experiment ledger.** Even seqs are stable,
  reportable experiments; odd seqs are experimentation (parity convention, plan D15; a
  re-decided freeze still bumps seq, to the next number of the right parity; freeze
  fingerprints disambiguate reused ids mechanically). The configuration facts binding
  every experiment since 2026-08-15: BOTH halves run `openai/gpt-5.6-luna` (D12–D14);
  the recipe uses the modern `ai:` spelling and deliberately omits `thinking_level`
  (the lock asserts the absence; the sandbox's injected default, medium, is the
  effective level); the user simulator runs `reasoning_effort: medium` with no
  temperature (luna rejects 0.0; D2's pooling absorbs the stochasticity); a new
  experiment's H0 is the ORIGINAL harness plus only the sanctioned model/config block
  and the inert zero-state scaffold — the `h0-baseline` tag moves only to commits
  satisfying that identity (D16; re-tagged since per D27/D31), verified by
  `make reset_h0`. Calibration of record: corrected-H0 luna pilot, baseline 21.4%,
  `results/experiment_004_powered-bm25-luna56/CALIBRATION_PILOT.md`.

  | seq | design | verdict | closure |
  |---|---|---|---|
  | 1 | debug freeze (G=3, B=4, T=8) | **VOIDED at H0** — `task_034` deterministically crashes τ's user sim: a frozen-surface defect no harness mutation can reach; vault sealed forever | `experiment_001_bm25-sonnet46/` |
  | 2 | debug run, sonnet46 pair | REVEALED 2026-08-14 — loop demonstrated end to end; endpoint inside ±18 pp; no claim | `experiment_002_bm25-sonnet46/` |
  | 3 | powered bring-up (odd) | model-pair detours (D12–D14), pilots, seam validations; no reportable number | `experiment_003_powered-bm25-*/` |
  | 4 | powered fresh-batch (G=5, B=8, T=28, ×1 trial) | REVEALED 2026-08-15 — null (trend p = 0.802); four of five slots went into ONE `SYSTEM.md` paragraph | `experiment_004_powered-bm25-luna56/` |
  | 5 | fixed-batch loop-reliability (odd; G=2, ×3 trials) | REVEALED 2026-08-16 — null primary, B flat; §29 carries the project's one WAIVED guardrail (human approval, by explicit user instruction) | `experiment_005_fixedb-bm25-luna56/` |
  | 6 | fixed-batch at depth (G=6, autonomous, composite sets) | REVEALED 2026-08-16 — null primary; held-out rose (p = 0.038, third exposure, not a claim); the two instruments could not be reconciled by that run | `experiment_006_fixedb-bm25-luna56/` + `INDEPENDENT_REVIEW.md` |
  | 8 | stratified batch, first run on the D24 seam (G=6, autonomous) | REVEALED 2026-08-17 — null on both instruments; the loop saturated the reachable batch range (15/15 non-walled cells at peak) and the endpoint test could not say yes; noise floor measured | `experiment_008_stratb-bm25-luna56/` + `INDEPENDENT_REVIEW.md` |
  | 10 | both-curves, marginal batch + pure holdout (G=8, identity gen-001, autonomous) | REVEALED 2026-08-18 — **null on both instruments** (batch primary Σ+1.333, p = 0.184; held-out trend z = 0.03, p = 0.486; endpoint +0.0 pp). Reading key cell `primary_flat_secondary_flat` with harvest 0.667: every precondition a prior null could be blamed on was removed and the loop still found nothing. FIRST graded use of a Pi-local surface in project history (`pi_local_calls` 0 → 39) | `experiment_010_adopt-bm25-luna56/` |
  | 11 | ceiling probe (odd, PROVISIONAL — not an experiment) | H0 vs a hand-built H-expert over 35 tasks under both backends; chose `openai_embeddings` on headroom (+15.2 vs +6.7 pp), GO, envelope REACHABLE | `experiment_011_ceiling-probe/` + `benchmark/probes/2026-08-18-phase0-ceiling-probe/` |
  | 12 | THE CEILING EXPERIMENT — first freeze with a measured maximum (G=7, B=26, T=36, embeddings, autonomous) | REVEALED 2026-08-19 — **null on both instruments with every prior excuse removed**. Primary 34.62% → 34.62%, Σ −0.000, p = 0.566: the loop closed **0.0% of the measured +20.5 pp headroom**. Held-out endpoint +4.6 pp, trend p = 0.133. Key cell `primary_flat × secondary_flat`, harvest low (0.346). Not comparable to seq ≤ 10 (backend changed) | `experiment_012_ceiling-emb-luna56/` |

  **Results under the D24 seam (seq 8 on) are not comparable to seq ≤ 6.** Under D33,
  in-loop sessions read prior experiments' `improvement_records/` and backlogs only —
  closures' held-out sections are quarantined; this table's aggregate verdicts are the
  sanctioned summary.
- **Standing lessons the loop must not re-learn** — each measured in a named experiment;
  the operational versions live in the sia skill and `contract/protocol.md`, the evidence
  in the closures: (a) *an instruction added to a prompt does not inherit the scope its
  author reasoned about* — four failures in one `SYSTEM.md` paragraph across seq 4+5,
  one of them landed WITH structural guards built against exactly that mode. (b) *The
  escape clause is what the model optimises against*, and sharper (seq 8): **any**
  injected statement about a missing precondition can read as a bar to acting — framing,
  not surface, moves an injected note (bare list inert — **replicated by seq 10 on a
  different surface and subject matter, so this one is settled: do not spend a slot on a
  bare list**; missing-state changes behaviour and suppresses unasked; completed-state
  safe; consequence-stating confirmed).
  (c) Changes telling the agent what to RETRIEVE or in what ORDER confirmed; prohibitions
  and offered alternatives failed (seq 6, eleven changes). (d) Transfer is a single
  dial: seven mutations moved the rate before one (seq 8's missing-state context hook)
  moved *discrimination* — and only toward gold transfers; over-escalation never
  improved. (e) **Round-to-round noise on an identical harness is 2 cells / 8.3 pp** on
  a B=8×3 batch (seq 8's behavioural-identity round; the held-out lane showed the same
  churn) — an attribution without a mechanism *and* a counter is noise. (f) A denied
  prediction is not a revert trigger, a denied *mechanism* is; retirements need two
  rounds of witnesses. (g) A preflight verifies a change *runs*, never that it *works* —
  seq 8's F1 preflighted 3/3 against a 0/12 baseline for a hook that never executed
  (keyed on role `tool` where the measured host vocabulary says `toolResult`); verify
  injected text in a fetched conversation before reading any behavioural number.
  (h) Surface status is measured, never inherited: a DECLARED skill reaches NOTHING on
  this seam (hook injection is the only skill delivery); the no-tool-call hooks are
  measured functional on the real domain; and **the extension-tool surface is EXERCISED
  and works** — seq 10's C1 took `pi_local_calls` from 0 across all 168 seq-8 platform
  episodes to **39 in one graded round**, well-formed arguments, no leak into τ's
  trajectory, after the pre-freeze suppression canary converted the D24 path from
  assumption to measurement. **`sub-agent` is now the ONLY class never exercised and never
  probed**; no `surface_exhausted` finding is claimed for it, and the open question a probe
  must answer first is whether a child's own tool calls spend the PARENT's τ step budget.
  (i) **Adoption is not improvement** (seq 10): C1 was adopted enthusiastically and moved
  no reward. That a surface is reachable and that it is useful are separate claims needing
  separate evidence — which is what adoption-first keeps apart, and why a confirmed
  adoption with unmoved reward is not a mechanism denial. (j) **A dead primary is declared,
  not drifted into** (seq 10): its endpoint became arithmetically unreachable after
  `batch_07` — both remaining slots went to reverts, which cannot raise an endpoint — and
  nothing in the process noticed. The futility check (`contract/protocol.md`) fires from
  the midpoint, and the response is to re-purpose the remaining slots for knowledge rather
  than to stop: seq 10's post-futility tail produced two of its best findings.
- **SEQ 12 RAN AND CLOSED (2026-08-19), and its most useful number is not a score:
  THE NOISE AND THE HEADROOM ARE THE SAME SIZE.** The A/A identity round moved
  **16 cells / 20.5 pp on a byte-identical harness**, and the batch's entire measured harness
  headroom is also **20.5 pp** — this instrument cannot resolve the effect it was built to
  detect, and that was knowable before the first mutation. Twelve changes landed across six
  mutation slots: **one confirmed (C2), one directional (C3), six denied, three reverts**. The
  primary closed **0.0%** of the reachable range. Read the closure's `§ Batch-derived
  findings`; its `§ Held-out reveal analysis` is quarantined (D33). Four things outlive it:
  (a) **the surface is not the axis for demands the model does not want to satisfy** — one
  rule denied through prose AND through a hook verified firing on the graded lane, counter
  9/9/9/8 across four rounds, which narrows the "prefer a structural surface" doctrine to
  mechanisms needing STATE the model cannot hold; (b) **adoption is not improvement and
  neither is a moving mechanism counter** — two state tools called 578 and 1515 times, no
  reward; (c) **the futility check is unstable near its threshold** — it fired at gen-004 on a
  0.3 pp margin and the next round refuted it, then fired correctly at gen-007 on 8.9 pp, so
  require two consecutive firings or compute capacity from the ceiling; (d) **`sub-agent` is
  exercised at last** — delegation works and is cleanly suppressed, but a child cannot reach
  τ's tools at all (120 s daemon timeout, never reaches the bridge), so the long-carried
  step-budget question is moot. A future experiment wanting a different answer should change
  the INSTRUMENT — more trials per cell, or a batch whose rates are not concentrated where the
  A/A pair moved most — not the loop.
- **Phase 0 measured the ceiling, and that is the number five prior experiments lacked.**
  Under a seq 11 PROVISIONAL lock, an H0 arm and a hand-built **H-expert** arm ran 35
  candidate tasks × 3 trials under BOTH backends (416/420 episodes, $12.82,
  `benchmark/probes/2026-08-18-phase0-ceiling-probe/`):
  **bm25 → H0 28.6%, expert 35.2%, headroom +6.7 pp; openai_embeddings → H0 23.8%, expert
  39.1%, headroom +15.2 pp.** The backend rule (freeze the larger HARNESS HEADROOM, never
  the larger absolute score) earned its keep on first use — the two criteria disagreed, and
  embeddings has the LOWER H0. **`--retrieval-config` moving means seq 12's absolute numbers
  do not compare to seq ≤ 10**; gap-closure against the measured ceiling is what normalizes
  them, which is why the primary reports that way. `h0-baseline` was re-tagged at `f157fab`
  for the regenerated `<policy>` region, mutable surface verified byte-identical.
  τ² pins every `openai_embeddings*` variant to `text-embedding-3-large`; a `-small` variant
  is not a published retrieval config and selecting one would mean editing the benchmark.
- **The measured ceiling is a LOWER bound, and the reason is a standing lesson.** H-expert
  *regressed* 5 tasks H0 passes under embeddings (7 under bm25): gross gain +21.0 pp against
  gross loss −5.7 pp. Two opposite modes — over-work (24–25 tool calls where H0 used 5–11)
  and early stopping (14–17 messages where H0 used 22–43). A long, carefully-reasoned
  instruction block written by someone who *knew* about scope leakage still leaked. Read
  +15.2 pp as conservative, and treat H-expert as the range's floor rather than its roof.
- **The batch is the best this project has frozen, and its composition is a measurement.**
  B=26 rather than the designed 30 because only 26 of 35 candidates earned an **empirical
  reachability certificate** (a task H-expert passes is provably harness-reachable), and the
  pre-registered rule says shrink (floor 24) rather than admit a wall. The certificate reads
  as EITHER arm passing — the letter would have dropped `task_063` (H0 3/3) as "walled".
  3 anchors / 12 marginals / **11 headroom**, no walled task, **53 reachable failing cells at
  H0** against seq 10's 17 and seq 8's ~5 — the first headroom stratum admitted on proof
  rather than on a trajectory guess. Envelope REACHABLE: 11.4 pp detectable at α inside
  15.2 pp; 80% power would need 17.2 pp, which the headroom does not cover, and that is
  recorded rather than smoothed.
- **Round-to-round noise, measured a third time and at the largest scale yet.** 33 of the
  Phase 0 candidates had been screened one day earlier under a recipe whose `target-agent`
  tree hash is byte-identical (`50ac0d6`, verified): **12 of 33 task rates moved** — 7 up,
  5 down, **+3.0 pp aggregate drift on no change at all**, largest single-task swing 2 cells.
  With seq 10's identity round (14 of 36 trial cells flipping) this is settled: per-task cell
  movement is not evidence on its own, and gen-001's identity round is doing real work.
- Loop policy for seq 12 is in `contract/protocol.md`: bundle 3–5 non-interacting changes, a
  ≥3-task-or-structural target bar, counters stated as DELTAS, ≤2 reverts, one slot reserved
  for `sub-agent` (still never exercised — the suppression canary certifies the Pi-local path
  it needs), and the **futility check** from the midpoint — declare a dead primary out loud
  and re-purpose the remaining slots for knowledge rather than score. Deferred by user
  decision: the control arm (a non-diagnosing loop, the sharpest test of the self-improvement
  claim) and the weak-H0/strong-H0 pair.
- **Seq 10 ran and closed (2026-08-18); read its closure's batch-derived half before
  designing seq 12.** Four results outlive it. (a) *The D24 structural surfaces work*: a
  registered extension tool went from zero Pi-local calls in project history to 39 in one
  round with well-formed arguments — the "unusable structural surfaces" hypothesis three
  closures carried is dead, and the pre-freeze suppression canary is what killed it.
  (b) *Adoption is not improvement*: that tool was adopted enthusiastically and moved no
  reward. (c) *The bare-list null REPLICATES* — a list appended to what the model reads
  moves nothing, now measured twice across different experiments, surfaces and subject
  matter; do not spend a slot on one. (d) *Retrieval volume is the turn cost*, established
  by elimination across three rounds (halve the tool calls: no change; raise KB_search 31%:
  length rises; remove that instruction: KB_search 11.6 → 9.3, messages 46.5 → 43.3).
  Method: a marginal-only batch buys dynamic range and pays in variance (14 of 36 trial
  cells flip on an identical harness while the round total holds), so a pre-registered
  identity round at generation 1 is the highest-value slot in the design — it fixes the
  attribution bar before the first mutation. `sub-agent` remains the one surface class
  never exercised and never probed; no `surface_exhausted` finding is claimed for it.
- **The groundwork is landed in two waves and seq 10 is designed.** Wave one
  (2026-08-16, plan D24–D27, from the seq-6 review): the D24 seam suppression, record
  schema v3 (per-clause falsifiers, gated backlog stamp), the mechanical reading key +
  fragility + process counters (D25), step-4b surface probes and the concentration flag
  (D26), and the first zero-state template (D27). Wave two (2026-08-17, plan D29–D33):
  the independent review (`results/experiment_008_stratb-bm25-luna56/INDEPENDENT_REVIEW.md`)
  added the saturation reading — at its peak round the loop had passed 15/15 reachable batch
  cells under a null primary — and drove the repairs: the concentration flag is
  **surface-general**; first use of any surface is **adoption-first** (schema v4
  `adoption_stage`/`host_facts`; extension role literals linted against
  `benchmark/probes/host_facts.yaml`); preflights have a slot and a rule (they verify a change
  *runs*, never that it *works*); reverts trigger on denied mechanisms, retirements need two
  rounds. A freeze now computes its power envelope, pre-registers a behavioural-identity round
  (`identity_generations`; gen-1 placement pools the primary's baseline), screens headroom for
  *reachability* (walled tasks are wall-monitors outside the primary), reads flat primaries
  against the **reachable-harvest co-metric** ("loop failed" vs "objective exhausted" are
  different verdicts now), and certifies the D24 suppressing path with a platform canary
  (`make gate_suppression`). `recipe-growth.md` no longer argues against the D24 surfaces (its
  stale trap-4 verdicts had steered "prefer a no-tool-call hook" through all of seq 8). The
  scaffold has zero-state parity — `noop-tool.ts` (`probe_note`) and `noop-subagent.yaml`
  beside `noop-hook.ts`, all inert — with `h0-baseline` re-tagged at the parity commit and the
  recipe reset to H0. **Seq 10 (D34, `010_adopt-bm25-luna56`) is the both-curves
  experiment — pre-registered success is the batch curve AND the held-out curve rising:
  G=8 with gen-001 as the designed identity round (noise floor first, baseline pooled to
  six trials/task; seven mutation slots), B=12 (2 anchors + 10 screened tasks targeting
  ≥15 reachable failing cells at H0 — seq 8's batch held ~5 and saturated), T=36
  pure-holdout (the legacy 28 + seq-2's 8 never-batched tasks) carrying a capability
  claim on the D33 procedural basis, `num_trials: 3` on both lanes, autonomous, ≈$29.
  Preflights may draw burned non-partition tasks as candidate-generalization probes.
  Freeze runbook: plan Phase 5.10. The pool holds ZERO virgin tasks, so the unqualified
  zero-exposure claim still requires a domain decision (user-owned, pencilled seq 12).**

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
  **And the firewall does not expire at reveal (plan D33)**: in-loop mutation decisions are
  grounded in improvement batches only — current and past. Held-out traces, per-task
  results, and reveal analyses of ANY experiment, revealed included, stay outside in-loop
  recall forever; reveal analysis is a closure-phase activity whose outputs are quarantined
  from later experiments' recall. Aggregate curves in this file are history, never
  diagnosis material.
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
effective value is recorded per run in `run_metadata.json`. `make batch` pins 3 (4 → 3 at
the seq-6 freeze, user-directed) — the
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
  statistical. One branch, one commit per change, one PR, one approval gate (human, or the
  frozen D23-envelope autonomy). Seq ≤5 ran one
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
  binomial noise band at the frozen trial count wherever the progression curve renders
  (±5 pp at T=28×3; ≈±4.5 pp at T=36×3 — the single-trial-era bands ±17/±9/±7 pp and
  the "≥4–5 tasks reads directional" bar were D11 calibrations at ×1 trial; recompute,
  don't reuse), and read any movement against the measured identical-harness noise
  floor before attributing it.
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
  package. `target-agent/` is deliberately bare at runtime — `agents/agent.yaml`,
  `SYSTEM.md`, `package.json`, plus three committed-INERT zero-state templates
  (`extensions/noop-hook.ts`, `extensions/noop-tool.ts`, `agents/noop-subagent.yaml` —
  undeclared/unreferenced, so H0 behavior is unchanged; D27/D31); TS extensions and Python
  deps (via `pi.runtime` + a committed `uv.lock`) are the growth surfaces generations
  enable.
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
  branch protection; the agent does not merge its own work — except under an experiment's
  frozen `require_human_approval: false` envelope (D23/D28; decision authority, never
  access), where CI and branch protection still gate every merge.
- Keep the first implementation simple enough that the origin of a performance change stays
  interpretable. H0 is deliberately unsophisticated, anchored by the `h0-baseline` tag.
