---
name: sia
description: >-
  Side-kick for the introspection.dev skills — obtained through the `introspection` CLI
  (install it first; `introspection skills` serves the workflows: operate, improve,
  create, migrate, deploy) — when a meta-agent/orchestrator runs generation-based
  improvement experiments over an agent harness. Use at every generation transition:
  before diagnosing a new improvement batch (recall first), when writing or verifying an
  improvement record, when updating backlog target statuses, and when a mutation grows an
  Introspection agent recipe with Pi tools, skills, or sub-agents. Keeps every
  experiment's memory isolated and enforces the held-out firewall (in-loop reads of
  held-out results are forbidden, and the quarantine does not expire at reveal —
  batch evidence is the only decision input); complements the CLI workflows' diagnosis
  and change methodology,
  never substitutes it; not for executing batches or held-out rounds (the run harness
  owns those). Trigger terms: generation transition, improvement batch, improvement
  record, backlog, recall digest, pi skill, pi tool, sub-agent, recipe growth,
  self-improving agent.
staleness_sensitive_sections:
  - "Wiring by surface"
  - "Recipe semantics that bite"
  - "Pi discovery paths — know them to avoid them"
---

# SIA — the orchestrator's generation-transition memory

One experiment is a sequence of generation transitions, each consuming one improvement
batch. This skill makes the orchestrator act on everything the experiment has already
learned before it decides anything new, and makes every decision leave a verifiable trace.
It adds exactly one layer — cross-generation memory inside one experiment, plus the
mechanics of one mutation class (Pi skills) — and defers everything else.

## Ownership map — route, never restate

| Concern | Owner | sia's part |
|---|---|---|
| Evidence reading — conversations, events, task rows, aggregate metrics | `introspection skills operate` | route there; bring the recall digest and evidence pointers |
| Evidence→diagnosis→PR methodology — open-coding, owning layer, falsification, one coherent mechanism **per change** (the set composes many; plan D22) | `introspection skills improve` | route there; enforce record write-through |
| Executing rounds — batch, held-out, reveal, batch curve | the repo's `Makefile` targets | never reimplement; read only their outputs |
| Experiment parameters — lock, `protocol:` block, partition manifest, freeze snapshots | the freeze (user-decided; `benchmark_lock.yaml`) | **read-only**; a needed change is a freeze re-decision to surface to the user (it bumps `seq`), never a sia write |
| Per-generation procedure | `contract/protocol.md` | hook recall/write-through into its steps |
| Frozen values / invariant rules | `benchmark/benchmark_lock.yaml` / root `CLAUDE.md` Invariants | operational checks only |
| Record schema | `contract/improvement_record.schema.yaml` (validated by `tau_adapter/records.py`) | craft guidance, never field definitions |

The Introspection CLI is the only interface to the platform. Where this skill and current
upstream docs disagree, upstream wins (standing guardrail in root `CLAUDE.md`).

Seams between those skills and this experiment — they bind as written; these notes
reconcile, never override:

- **Prevalence**: `operate` steers how-often questions to the aggregate telemetry
  surface. An improvement batch is a complete census — B tasks × `num_trials` episodes,
  enumerated from the manifest — so the full-population read outranks the aggregate
  surface there; use aggregates for cost and volume questions.
- **Proof**: `improve`'s baseline-and-candidate discipline is carried by the scheduled
  rounds, never by ad-hoc runs. A landed mutation is checked by `make check` (plus the
  mock-domain `make smoke` for mechanical changes) and *measured* only by the next
  scheduled batch round — under `batch_mode: fixed` that round is the sanctioned
  within-batch verification — and the hidden held-out round. Never replay benchmark
  tasks ad hoc, and never reach for the platform `experiments` (A/B) surface: the
  protocol has no paired arms.
- **Gates**: `improve`'s confirmation boundaries land on the protocol's existing human
  gates (step 4 decide-with-the-user, step 7 PR merge) — one set of gates, not two.
- **Briefing ≅ record**: `improve`'s align-with-the-user briefing (evidence, owning
  layer, change, expected effect, risks) is the improvement record in interactive form —
  fill the record and present from it, never write the content twice.

## Resolve experiment context first

- Derive the id, never type it: `python3 benchmark/scripts/experiment_id.py` (reads
  `benchmark/benchmark_lock.yaml`). The experiment root is `results/experiment_<id>/`.
- Once per experiment, read the freeze parameters that size everything sia tracks: the
  lock's `protocol:` block (G, B, T, `batch_mode`, `num_trials` — snapshotted into the
  experiment root's `experiment.yaml`) and the partition manifest's header
  (`split_manifest.yaml`: batch composition, exclusions and their rationale).
- Derive the generation position from ground truth, never memory: the records' outcome
  chain, the `exp<seq>-g<NNN>` tags, and the `generation_NNN/` directories must agree —
  a disagreement is an incident to surface, not to paper over.
- Every sia read and write stays inside that root. A record for experiment X never lives
  under, cites, or borrows evidence from experiment Y's root — experiments are isolated.
- Prior experiments' **batch-side** artifacts are readable only once revealed/closed, and
  only as labeled prior-experiment context ("experiment <id> found …") in digests and
  prose — never as evidence in a record. Record evidence is the current batch's
  conversations, nothing else. Prior experiments' **held-out** artifacts and reveal
  analyses are never in-loop inputs at all, revealed or not (D33) — the quarantine has no
  expiry.

## Recall — before every diagnosis

Before exporting the batch conversations (protocol step 3), read in order:

1. `results/experiment_<id>/improvement_records/gen_*.yaml` — all of them, filename order
2. `results/experiment_<id>/improvement_backlog.md`
3. Once, at experiment start: revealed prior experiments' `improvement_records/` and
   `improvement_backlog.md` — their batch-derived memory. **Never their `held_out/`,
   `summary.md`, reveal analyses, or any closure/review section carrying per-task
   held-out content** (D33): in-loop decisions are grounded in batches only, current
   and past, and a prior reveal read here contaminates every mutation this experiment
   selects.

Mine them per the table in [references/record-craft.md](references/record-craft.md). The
four highest-value extractions:

- **Backlog state**: pending vs consumed vs retired targets, current ranking, witness
  counts accumulated across batches, slot accounting against G.
- **Pre-registered predictions**: the last accepted generation's predictions — the
  set-level `expected_effect` AND every `changes[].expected_effect` item (schema v2,
  plan D22). Check each against the new batch explicitly and report confirmed / denied /
  unobservable **per change**: this scoring is the only per-change attribution a
  composite set has, and a denied prediction makes that change a first-class revert
  candidate for the next set.
- **Standing counterevidence**: objections recorded in earlier transitions that still
  apply (disjoint-batch caveats, severity-over-prevalence overrides awaiting judgment).
- **Surface concentration AND availability**: count mutations per `owning_layer` target;
  flag ≥3 on any single surface class in the digest — one observed loop spent four of
  five generations on a single instruction paragraph, two of them repairing defects the
  paragraph itself introduced, and noticed the pattern only at close; a later loop
  repaired that gradient and re-formed it one level up, landing six changes on the
  newly-templated surface while the just-unlocked ones went untouched. The flag is
  **surface-general** and a positive obligation (protocol step 4): the next set includes
  a change on a surface class this experiment has never exercised, or records a
  `surface_exhausted` finding citing a probe or measured fact per unexercised
  alternative. Concentration looks backward; pair it with the forward look — the
  **surface ledger**, kept at project scope, not experiment scope: for each surface
  class, whether it has EVER been exercised in a graded round of any experiment, its
  measurement status (measured on the real domain / mock only / never probed), and its
  current blocker. Ties between candidate surfaces break toward the best-measured one
  unless the digest names that asymmetry out loud — an un-named instrumentation gradient
  is how a loop converges on one surface while believing it chose freely.

Then state a **recall digest** (≤10 lines) to the user before diagnosis begins, so the
memory is visibly applied: generation chain so far, batch about to be read, predictions to
check, top pending targets with witness counts, concentration flags **plus the surface
ledger (project scope: exercised-ever / measurement status / current blocker per
surface)**, slots remaining — and, under `batch_mode: fixed`, the per-task batch matrix
as it forms.

## Write-through — during the transition, never after

- Protocol step 4 (decide with the user): update backlog rows as the decisions land —
  statuses, re-ranking against the new batch, retirements with reasons.
- Protocol step 6: scaffold and fill the record while the transition happens
  (`benchmark/scripts/improvement_record.py`), then verify it. Field craft:
  [references/record-craft.md](references/record-craft.md).
- Protocol step 7 (human gate): set `outcome` and `candidate_commit` on merge or decline,
  re-verify, commit.
- Conversation ids come from `generation_NNN/batch_NN/episode_manifest.jsonl`, never from
  memory. A record is never reconstructed after the fact.
- sia's write surface inside the experiment root is exactly two artifacts:
  `improvement_records/gen_*.yaml` and `improvement_backlog.md`. Everything else there —
  the `benchmark_lock.yaml`/`experiment.yaml`/`split_manifest.yaml` freeze snapshots, the
  `generation_NNN/` round outputs, `held_out/` — is written by the run harness or
  `make reveal`, never by sia; experiment parameters are tracked and used, never touched.

## Firewall — operational checklist

Authority: root `CLAUDE.md` Invariants (enforced here, not restated). At the sia level:

- Never Read, Glob, or Grep under `results/experiment_*/held_out/` of ANY experiment
  while operating in-loop — pre-reveal it is the vault rule; post-reveal it is
  cross-experiment contamination of mutation selection (D33). The same quarantine covers
  prior experiments' `summary.md`, trend/fragility artifacts, and per-task reveal
  content in closures and reviews. Scope every search under `results/` to
  `improvement_records/` or `generation_*/` — a broad grep can surface held-out content
  by accident.
- `held_out_result` is written by `make reveal` only. A non-null value before reveal is an
  incident: stop and surface it to the user.
- Records, backlogs, and digests contain no held-out numbers, no vault paths, and no
  speculation about held-out performance.
- Every batch number is labeled n/B with its set. When the lock's `protocol.batch_mode`
  is `fixed`, batch reads from B2 on measure a tuned-on set — every diagnosis,
  digest, and record says so.
- Contamination runs both ways: never place this skill, its digests, or any
  orchestrator-facing notes in a Pi discovery path (repo-root `.pi/skills/`,
  `.agents/skills/`, `target-agent/skills/`). The target agent must never read the
  instrument's notes. Repo-root `skills/` is safe — it is not a Pi discovery location.

## Mutation classes

A generation lands one improvement **set** — any number of changes, composed per
`contract/protocol.md` step 4 (plan D22): each change one coherent mechanism with its own
evidence and falsifiable prediction, no two changes interacting on one behavior, reverts
of refuted changes first-class. **The surface is part of each change's diagnosis, and it
is where closed instruction-only loops failed**: three experiments measured that *an
instruction added to a prompt does not inherit the scope its author reasoned about*, and
its sharper form — *the escape clause is what the model optimises against* — so when a
mechanism is judgment, scope, verification, or arithmetic, prefer a structural surface;
sets confined to a concentrated surface class carry the surface-general positive
obligation above. Read
`introspection skills improve/capability-set` (its `agent-design` and
`agent-security-review` references own the design methodology) before choosing. Each
surface with its **activation path** — what must be true for it to reach a graded
episode:

- **Instructions** (`SYSTEM.md` `<instructions>`) — always live; the historical default
  where instruction-only loops spend every slot. Since record schema v3 (current: v4),
  every landed instructions change carries per-clause falsifiers (the adversarial
  wording review).
- An **extension hook** (`before_agent_start` / `tool_result` / `context`) — no tool
  call, deterministic; live in every seam configuration and measured functional on the
  real domain. The delivery surface for injected judgment, result transformation, and
  computed context.
- An **extension tool** — a deterministic capability the model calls; live where the
  seam suppresses Pi-local calls from the evaluator (this repo: D24) — the call must be
  registered by a recipe extension AND allowlisted in the agent's `tools:`, which
  doubles as the suppression registry. Where no suppression exists, the call leaks to
  the evaluator as an invalid action: verify the seam before choosing this surface.
  **First use is adoption-first** (protocol step 4): the falsifiable prediction targets
  adoption and correct invocation, reward is deferred to the following round, and the
  tool may bundle its minimal usage instruction as one coherent mechanism — "the model
  would have to choose to call it" is a design input, never a reason not to land it.
- A **sub-agent** — delegation through the auto-generated `agent` tool; same
  availability condition as extension tools (the `agent` call is Pi-local under
  suppression), plus the frozen model pair binds the child (`from:` the parent, no
  `ai:` override). Adoption-first applies here too, and doubly: no sub-agent episode
  has ever run on this seam, so the first use also probes latency and the
  started-not-finished delegation contract before anything rides on them.
- A **declared skill** — measured inert on this seam's local lane (nothing reaches the
  prompt, with or without `read`); skill-shaped judgment ships via a
  `before_agent_start` hook that reads the body itself. Re-verify per host before
  relying on either behavior.

Before landing any structural change, load
[references/recipe-growth.md](references/recipe-growth.md) — verified wiring per
surface, the recipe semantics that bite (array replacement, `ai.model` fresh-config, the
auto-generated `agent` tool), and the measured traps: the load-bearing `tools: []`, the
frozen model pair binding sub-agents, and lane-serving asymmetries (the platform lane
pins the recipe to pushed main; the local lane is the work-tree-faithful probe lane).

Justified diagnostic evals and judges are also mutable surface, routed wholly to
`improve` (read `improve/measure` first): they inform diagnosis and never redefine the
objective — the reward stays `tau2 evaluate-trajs`, nothing else.

## Gotchas

- Outcome discipline (`identity`/`rejected` transitions are first-class records),
  per-change coherence plus the set-composition rules (plan D22), and generation
  accounting are protocol rules (`contract/protocol.md` steps 4, 5 and 7) — sia surfaces
  them in the digest and the record; it never redefines them. Schema-vs-validator
  questions: [references/record-craft.md](references/record-craft.md).
