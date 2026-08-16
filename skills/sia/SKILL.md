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
  experiment's memory isolated and enforces the held-out firewall (never reads unrevealed
  held-out results); complements the CLI workflows' diagnosis and change methodology,
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
- Prior experiments are readable only once revealed/closed, and only as labeled
  prior-experiment context ("experiment <id> found …") in digests and prose — never as evidence in a
  record. Record evidence is the current batch's conversations, nothing else.

## Recall — before every diagnosis

Before exporting the batch conversations (protocol step 3), read in order:

1. `results/experiment_<id>/improvement_records/gen_*.yaml` — all of them, filename order
2. `results/experiment_<id>/improvement_backlog.md`
3. Once, at experiment start: revealed prior experiments' closure `README.md`/`summary.md`

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
- **Surface concentration**: count mutations per `owning_layer` target. Flag ≥3 on one
  surface in the digest — one observed loop spent four of five generations on a single
  instruction paragraph, two of them repairing defects the paragraph itself introduced,
  and noticed the pattern only at close.

Then state a **recall digest** (≤10 lines) to the user before diagnosis begins, so the
memory is visibly applied: generation chain so far, batch about to be read, predictions to
check, top pending targets with witness counts, concentration flags, slots remaining —
and, under `batch_mode: fixed`, the per-task batch matrix as it forms.

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

- Never Read, Glob, or Grep under `results/experiment_<id>/held_out/` of an unrevealed
  experiment. Scope every search under `results/` to `improvement_records/` or
  `generation_*/` — a broad grep can surface held-out content by accident.
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
of refuted changes first-class. The recipe offers four surfaces, choosing among them is
part of each change's diagnosis, and the choice is where two closed experiments say the
loop previously failed — read `introspection skills improve/capability-set` (its
`agent-design` and `agent-security-review` references own the design methodology) before
choosing:

- **`SYSTEM.md` instructions** — the historical default, where instruction-only loops
  spend every slot. Seq 4 + seq 5 measured the failure mode: six of seven mutations were
  prompt text, four failed because *an instruction does not inherit the scope its author
  reasoned about*. When a change's mechanism is judgment, scope, or verification, prefer
  a structural surface below; a set that stays prompt-only after the concentration flag
  fires (≥3 prompt mutations on one surface) must state why no structural surface fits.
- A **Pi skill** in the recipe — packaged, named judgment loaded near the work.
- A **Pi extension tool** — a deterministic TypeScript capability the model calls.
- A **sub-agent** — a delegatable recipe agent with its own tools, skills, instructions.

For the three growth surfaces, load
[references/recipe-growth.md](references/recipe-growth.md) first — verified wiring for
each, the recipe semantics that bite (array replacement, `ai.model` fresh-config, the
auto-generated `agent` tool), and this experiment's traps, chief among them the
load-bearing `tools: []` and the frozen model pair binding sub-agents.

Justified diagnostic evals and judges are also mutable surface, routed wholly to
`improve` (read `improve/measure` first): they inform diagnosis and never redefine the
objective — the reward stays `tau2 evaluate-trajs`, nothing else.

## Gotchas

- Outcome discipline (`identity`/`rejected` transitions are first-class records),
  per-change coherence plus the set-composition rules (plan D22), and generation
  accounting are protocol rules (`contract/protocol.md` steps 4, 5 and 7) — sia surfaces
  them in the digest and the record; it never redefines them. Schema-vs-validator
  questions: [references/record-craft.md](references/record-craft.md).
