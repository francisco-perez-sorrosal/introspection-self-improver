# Introspection Self-Improving Agent MVP — v2

## Grounded Design, Remaining Path, and Orchestrator Integration

**Status:** Forward guide — supersedes `introspection_self_improving_agent_mvp.md` (v1)\
**Date:** 2026-08-12\
**Ground truth:** The source code in this repository. Where this document and the code
disagree, the code wins and this document gets fixed.\
**Primary goal:** Unchanged from v1 — demonstrate a genuinely self-improving agent harness
using Introspection's native operational and improvement primitives, with τ²-bench
`banking_knowledge` supplying an immutable external objective.

------------------------------------------------------------------------

# 0. What This Document Is

v1 designed a system that did not exist. Most of its load-bearing uncertainty is now
resolved by construction or by measurement: the τ↔Introspection seam (v1 §11.1, "undecided,
carries nearly all of the implementation risk") is built and graded in two lanes; the
evidence surface it speculated about has been enumerated against the live platform and the
installed plugin; and the first empirical results (trial variance, reward↔retrieval
coupling, per-episode cost) contradict several of v1's working assumptions.

v2 does three things:

1. **Records the system as built** (§2) — the seam, the two lanes, the evidence each
   episode produces, and the enforcement machinery — so no future plan re-derives or
   contradicts it.
2. **Re-plans the remaining path to G0 and G1** (§4) against measured reality (§3), with
   each workstream carrying an exit criterion and the two open human decisions named.
3. **Designs the improvement loop in operational detail** (§5) — the integration between
   the Improvement Orchestrator (Claude Code + the Introspection plugin) and the benchmark:
   how a benchmark round becomes platform evidence, how `operate` mines that evidence into
   signals, how signals become learning records and pull-request proposals through
   `improve`, and how candidates are validated and accepted. This is the part of the MVP
   that has not been built, and it is the reason this revision exists.

## 0.1 Document ownership map

This repository deliberately splits its truth across files. v2 does not restate what
another file owns:

| Content | Authoritative home |
|---|---|
| Project invariants (never / frozen / mutable) | `CLAUDE.md` |
| Frozen **values**, mechanically asserted per run | `benchmark/benchmark_lock.yaml` |
| Permission envelope, enforcement, known divergences | `contract/constraints.md` |
| Per-generation operational procedure | `contract/protocol.md` — written at G1 (§4, W7) |
| Seam mechanism, lanes, run modes | `README.md` |
| Design rationale, remaining path, orchestrator integration | **this document** |
| v1's conceptual essays (SIA / Prime Agent / SquareDiff, why τ-Knowledge, why not Harbor first) | v1, unchanged — carried by reference |

Appendix A maps every v1 section to its disposition. Appendix C lists the places where
existing documentation lags the code, found while grounding this revision.

------------------------------------------------------------------------

# 1. Unchanged Foundations

Stated once, briefly. The rationale lives in v1 §§0–10 and is not repeated.

**Research question:** Can an LLM Improvement Orchestrator use Introspection's operational
evidence to autonomously discover actionable failure signals, formulate hypotheses about an
agent's behavior, and evolve its harness such that performance improves on unseen
τ-Knowledge tasks?

**The four roles:**

| Role | Who |
|---|---|
| Task oracle | τ²-bench `banking_knowledge` — immutable; tasks + reward, never a diagnosis |
| Target agent (H_n) | The Introspection recipe in `target-agent/` — the only thing improved |
| Evidence substrate | Introspection — conversations, spans, observations, patterns, metrics, lineage |
| Improvement orchestrator | Claude Code + the Introspection plugin — no orchestrator agent exists or may exist in this repo |

**Core loop:** run τ tasks → collect Introspection evidence → `operate` (discover signal) →
`improve` (hypothesis + one minimal mutation, landed as a PR) → validate against τ →
accept/reject → repeat.

**Standing principles carried forward without modification:** objective ≠ diagnostics
(v1 §2.2); open-code evidence before imposing a taxonomy (v1 §2.3); model fixed, harness
mutable (v1 §2.4); minimal hypothesis-driven mutations (v1 §2.5); the G0 competence floor
of ≥20–25 % pass on discovery, below which the comparative method loses its controls
(v1 §13.1); orchestrator-prior-knowledge honesty — keep the τ-Knowledge paper and
leaderboard out of the orchestrator's context, and label any signal the literature already
names (v1 §22.9); held-out enforcement is procedural unless mechanically separated, and
must be reported as whichever it was (v1 §22.10).

------------------------------------------------------------------------

# 2. The System As Built

Everything in this section exists and runs today. File references are current at the commit
this document was written against.

## 2.1 The seam (v1 §11.1 — resolved)

v1 left the τ↔Pi control-flow mismatch as an open spike with three candidates. The built
answer is the **MCP tool bridge with a rendezvous** (`benchmark/tau_adapter/`), which is
v1's "MCP shim + `introspection dev`" candidate generalized to both lanes:

1. Pi calls an MCP tool served by the bridge (`tool_bridge.py`).
2. The handler parks. The call surfaces to τ as an ordinary `tool_calls` message.
3. τ's orchestrator executes it against the environment — τ, not the bridge, owns execution.
4. The `ToolMessage` is posted back; the parked handler returns it; Pi continues.

Ownership is strict and is the design's core property:

| Owns | Party |
|---|---|
| Tool execution, step counting, trajectory construction, termination, grading | τ² |
| Assistant-message production (reasoning, tool-call decisions, wording) | Pi (the recipe) |
| Message-shape and tool-name translation — nothing else | the bridge |

Mechanics that matter downstream:

- The rendezvous mailbox is keyed by **τ tool name + canonicalized arguments**, not call
  order (`tool_bridge.py:75-95`), which is why the platform lane works even though the
  AG-UI event reaches τ before the sandbox's MCP request crosses the tunnel. Repeated
  identical calls queue; the mailbox is reset per episode so a τ infrastructure retry
  cannot consume a stale result.
- Timeouts: 300 s result ceiling, 25 s stall warning (`STALL_WARN_SECONDS`) — the sandbox's
  MCP daemon abandons a parked call at ~30 s, long before the ceiling, and without the
  warning that gap is silent.
- **The adapter is a pipe, not a participant.** No repair, no retry, no reformatting.
  A Pi message mixing narration with tool calls is forwarded unaltered even though τ's
  protocol disallows it, because every place the adapter helps the agent is a place the
  harness stops being measurable — and an unmeasurable harness cannot be improved
  (`contract/constraints.md`).
- Reward is computed only by `tau2 evaluate-trajs`, only via `make grade`.
  `scripts/grade.py` exists solely to rebuild the evaluation environment with the run's
  **recorded** retrieval config instead of τ's default fallback (`alltools`), which the
  upstream evaluator would otherwise silently use. The reward function itself is τ's,
  untouched.

The five known divergences from a stock τ run (mangled tool names in the prompt, unreplayed
canned greeting, recipe-owned model selection, platform message-splitting, agent
unseedability) are recorded in `contract/constraints.md` and are constant across
generations — they bound comparability with published numbers, not cross-generation
comparison. §4 W4 turns them into a measured gate.

## 2.2 The two lanes

Both are implemented; the same seam and rendezvous drive both (`TRANSPORT=local|platform`).

| | `local` (default) | `platform` |
|---|---|---|
| Agent host | Pi subprocess on this machine | cloud sandbox on the `target-agent` dev Runtime |
| τ environment | in-process, loopback bridge | in-process, bridged via `introspection dev --mcp tau=<url>` |
| Introspection evidence | **none** — Pi session file only | conversation, spans, cost, usage, commit lineage |
| Measured episode cost / wall clock | ~$0.17 / ~45 s | ~$0.26 / ~75 s (+ ~20 s one-off `dev` attach) |
| Role going forward | bring-up, debugging, cheap seam gate | **the experiment lane** — every G0+ round runs here |

The platform lane's episode lifecycle, established by experiment and enforced in code
(`dev_lane.py`, `transport_platform.py`; the full story is in `README.md`):

- One Introspection **task per episode**; the task is created *with* τ's first user turn as
  `--prompt` (an empty task races its own sandbox). Task id **is** the conversation id.
- Turn gating on `RUN_FINISHED`: τ hands the floor to its user simulator as soon as it
  holds an assistant message, but prompting a still-streaming task returns
  `409 Task is already processing`, which τ books as an infrastructure error and retries
  the episode. The transport therefore gates every prompt on the platform run actually
  finishing.
- The `tasks stream` attach is spawned before `tasks prompt` so their ~5.5 s CLI startups
  overlap — serial startup was consuming a third of the sandbox MCP daemon's ~30 s
  per-call budget. A clean episode answers every bridged call in ~250–350 ms.
- At episode end the task is **retitled** (`τ²-bench <domain> <task>`) **and archived** —
  never deleted. Archiving settles the task immediately (sandbox released) and keeps the
  conversation's name in the dashboard.
- `warm_runtime` burns up to three throwaway tasks before the first graded episode so no
  graded episode absorbs the cold start; τ's own infrastructure retry absorbs the residual
  "sandbox not ready" first-task failure.

The platform lane is **locked-domain only**: `introspection dev` serves the recipe from the
git work-tree, and diagnostic mode materializes a modified recipe elsewhere, so `make
smoke` (mock domain) is local-only by refusal, not by accident.

## 2.3 Evidence produced per episode — the identifier spine

This join is the connective tissue of the whole experiment. As built:

```text
τ task_id × trial ──────────────── results.json (τ-owned ground truth)
   │   simulations[]: messages, tool calls, reward_info, termination, agent_cost
   │
   ├─ raw_data on every adapter-produced assistant message:
   │     pi_model, pi_tool_names, pi_session_ref
   │     pi_session_ref = Pi session id (local) │ Introspection task id (platform)
   │
   └─ platform lane: task id == conversation id
         │
         ├─ conversation record: spans, per-call cost/usage, GenAI items   (immediate)
         ├─ observations / patterns / judgements                            (deferred — §5.4)
         ├─ runtime version (immutable) + recipe_git_commit_sha             (lineage)
         └─ run_metadata.json → platform.accounting[<task_id>]:
               cost, usage, metrics (span/tool/LLM-call counts),
               recipe_git_commit_sha, evidence_complete, item_count
```

`run_metadata.json` is written only after τ's runner returns, so its presence is the run's
completion sentinel. Its `episodes` list records per-simulation `termination`, `reward`,
and a `completed` verdict — true only when τ itself ended the episode normally *and* graded
it. On the platform lane, `evidence_complete` records whether the conversation export had
settled when read. **A generation must assert all three before its evidence is used**
(§5.3): a green reward concealing a broken rendezvous is the failure this repository exists
to prevent, and it has already been observed once (the 409/turn-gate incident).

Two limits of the as-built join, both scheduled for repair in §4 W3:

- On a multi-task sweep the platform task label cannot name the τ task — the agent factory
  never learns which simulation it serves — so labels fall back to the domain alone.
- No standalone per-episode manifest exists; the (τ task, trial) → conversation-id join
  currently requires reading `raw_data` out of `results.json`.

## 2.4 Enforcement as built

Every frozen value is asserted mechanically before a run; nothing in the lock is
documentation (`lock.py`, `run.py`):

- vendored τ² commit vs `benchmark.commit`; recipe model/thinking level vs lock; live τ
  tool surface vs `tool_catalog` (15 tools); `<policy>` region of `SYSTEM.md` vs the lock's
  hash (pre-commit + CI) **and** vs the live `env.get_policy()` at every episode start;
  recipe validity via `introspection check` (pre-commit hook, CI `recipe-validation.yml`,
  and once per run).
- `.github/workflows/frozen-surfaces.yml` gates PRs: the policy-region hash fails the
  check, and any diff touching `benchmark/` or `contract/` is surfaced for human review.
  Branch protection means the agent-side of the loop can open PRs but never merge.
- The monorepo cannot express the permission split (a GitHub token cannot be path-scoped),
  so the boundary is detected-and-blocked at merge, not made impossible — recorded
  honestly in `contract/constraints.md`, with `git subtree split` as the eventual durable
  fix.

## 2.5 The platform surface the orchestrator will actually use

Verified against the installed plugin (v0.7.0), the CLI's own help, and
docs.introspection.dev. This is the concrete counterpart to v1 §3.3's abstract list.

**Evidence-reading CLI** (all commands take `-o json` by default, `--query <JMESPath>`,
Arrow output where noted; every leaf help names the API endpoint it wraps):

```text
introspection tasks list --status <s> --runtime-id <id> [--limit ≤1000 --next <cursor>]
introspection tasks get <task-id>                     # task row; completion reason
introspection conversations list --lookback 24h --sort cost|turns|tokens [--format arrow]
introspection conversations get <ids…> --format json|arrow|trajectory   # ≤20 ids/call
introspection conversations get <id> --summary-only | --judge-fixtures
introspection events list --event-name introspection.observation --filter conversation_id=<id>
introspection events list --event-name introspection.observation_clustering.run  # analysis status
introspection events list --event-name introspection.pattern [--end …]
introspection metrics query @query.json               # POST /v1/metrics, forwarded unchanged
introspection runtimes list|get|versions              # immutable versions, pinned commits
```

`metrics query` aggregates over six views — `spans, conversations, events, judgements,
observations, patterns` — with up to 6 metrics (`count/sum/avg/min/max/p50–p99`),
4 dimensions, 20 filters, and time-series support. Dimensions include runtime version and
**recipe commit hash**, which is what makes per-arm slicing possible (§5.7).

**Evidence timing** (documented numbers): a conversation becomes observation-eligible after
**30 minutes** without new activity; the background scan runs about **every 10 minutes**;
patterns are clusters over many observations, scoped per organization, project, lens, and
**runtime group**, and the cluster map is regenerated periodically. Observations without
runtime-group attribution fall into a separate project-level bucket — one more reason every
generation runs on the same Runtime (§5.2).

**Dev-lane analysis:** no documentation excludes any environment lane from
observation/pattern analysis; eligibility is defined purely by conversation completion plus
inactivity, dev-lane conversations carry full runtime-version attribution, and the judges
documentation states that lower environments are graded in full (only production is
sampled). The working assumption is therefore that the dev lane is analyzed like any other
— **but it is unconfirmed empirically and is checked explicitly at G0** (§4 W6). The loop
is designed so that if the assumption fails, the conversation-evidence harvest (§5.3) still
carries a generation.

**Lineage:** runtime versions are immutable recipe pins created from git commits;
resolution is sticky per task. The dev lane's caveat: `introspection dev` overlays
**uncommitted work-tree edits** onto the resolved version, so `recipe_git_commit_sha`
identifies the base commit, not necessarily the served bytes. Nothing asserts a clean tree
today — §4 W3 adds that assertion, because without it the lineage claim behind every
generational comparison is soft.

**Scale:** task concurrency is organization-level and plan-derived, with no
user-configurable knob; a queued task can be cancelled by the platform after a queue-wait
budget. A sweep must therefore tolerate failed-pre-agent rows and derive its N from task
rows, not from submissions. Bulk evidence pulls use Arrow output and pagination
(`--page-all`, limit ≤1000).

**Skill routing** (installed plugin, binding): route by what the work ends in —
`operate` ends in an answer or changed live state, never a recipe edit; `improve` ends in
a repository change through a PR; `deploy` only when what an environment resolves to must
change. The dev-lane loop needs `deploy` for nothing; it enters only if the experiment
later moves to staging runtimes (§8).

## 2.6 What Introspection contributes — status of v1 §2.6's five capabilities

| Capability | Status today |
|---|---|
| Observations & patterns | Reachable for dev-lane episodes (per §2.5); **never yet exercised** — first exercised at G0 (§4 W6) |
| Population-level telemetry (`metrics query`) | Available; unexercised; central to §5.5 prevalence discipline |
| Judges as durable instruments | Deliberately deferred — only if a recurring behavioral risk earns one (the `improve` skill itself gates eval/judge creation to recurring, important risks) |
| Runtime ↔ commit lineage | Partial: every platform episode records `recipe_git_commit_sha` and resolves an immutable runtime version; weakened by the missing clean-tree assertion (§4 W3) and by the dev overlay caveat |
| The repository loop | **Not used in MVP-A, deliberately.** The improvement PRs are authored by the orchestrator (Claude Code on this machine) with ordinary git + `gh` under branch protection. The platform's own repository loop — the *target agent* holding write access to its own recipe via a `runtime.github` grant — is the MVP-B/self-hosted variant (§8), and claiming it earlier would misdescribe the architecture |

Where the MVP does not use a platform capability, it says so — the τ objective in
particular is computed by τ outside the platform's eval machinery, by design (v1 §2.6).

## 2.7 The results tree — experiments over generations

`results/` carries one level above generations, so runs produced under different freezes —
different models, retrieval configs, splits, trial counts — can never interleave:

```text
results/
  experiment_<id>/              # one experiment = one freeze; <id> from benchmark_lock.yaml
    experiment.yaml             # freeze snapshot, written on the first non-PROVISIONAL run
    generation_000/             # one improvement cycle under one incumbent harness H_n
      fidelity_task_001/        # W4 gate rounds are ordinary rounds (run under H_0)
      anchor_stock/             # A.0c stock-agent reference (native tau2 run)
      discovery_baseline/       # <split>_<arm>: results.json, run_metadata.json,
      validation_baseline/      #   pi_sessions/, episode_manifest.jsonl (W3)
      checkpoint_full_domain/   # §6 checkpoint, G0 and final generation only
      learning_record.yaml      # + decision.md, candidate diff pointers (v1 §24)
    generation_001/
      discovery_baseline/  validation_baseline/  validation_candidate/  ...
  experiment_dummy/             # pre-freeze bring-up bucket (PROVISIONAL runs; unreportable)
```

**Everything the runner writes is a round inside a generation** — named
`<purpose>[_<arm>][_platform]` — and the experiment level holds only the snapshot, a
README, and cross-generation summaries (the pass^1/pass^k curves at close-out). The W4
gates and the full-domain checkpoints are ordinary rounds in the generation whose
incumbent harness they ran under (the gates re-run under whichever H_n is incumbent if
the adapter ever changes mid-experiment), so no reserved sibling directories exist to
drift. Operationally that is just `make <target> GEN=generation_NNN`; the runner accepts
any round path inside the lock's experiment.

Three properties are enforced, not documented (`tau_adapter/experiment.py`):

- **The path is derived, never chosen.** The id lives in the lock (`experiment.id`); the
  Makefile resolves it and the runner refuses any `results/` path outside the lock's
  experiment — before `--overwrite` can delete anything, so a mis-aimed run cannot clear
  another experiment's record.
- **The freeze is snapshotted.** The first run of a non-`PROVISIONAL` lock writes
  `experiment.yaml` — a fingerprint of the parsed lock plus split manifest — and every
  later run must match it, regardless of the lock's current status. Values are compared,
  not bytes: a comment edit never trips it; a re-decided frozen value refuses the run
  with "start a new experiment".
- **Runs carry their experiment.** `run_metadata.json` records the experiment id, and
  every platform task title ends in `[exp:<id>]`, so platform evidence stays filterable
  by experiment even where two experiments share a recipe commit (a user-simulator-only
  change, for instance).

The two levels split exactly along the experiment's mutable/immutable axis: the
**experiment pins what must not change** (the benchmark freeze — the snapshot fingerprint
deliberately covers the lock and split manifest, never the recipe), while **generations
track the one thing that does** (the harness). `generation_NNN/` holds one improvement
cycle — every round run while H_n was the incumbent, baseline and candidate arms both,
distinguished by `recipe_git_commit_sha` — and the next cycle opens `generation_NNN+1/`
whether the candidate was accepted or rejected, since a rejection is a first-class result.
Operationally a new generation is just `GEN=generation_NNN` on the make invocation; the
harness-state ↔ generation mapping lives in the learning record's `arms` block and in
every episode's lineage, not in the directory name.

This is the mechanical form of the lock's own header — "changing any value invalidates
cross-generation comparison; start a new experiment instead, and say so in the results
directory" — and it is what makes v1 §27's later experiments (cross-model transfer,
budget scaling, alternative splits) storable without redesign: each is a sibling
`experiment_<id>/` with its own snapshot, generations, and learning records.

------------------------------------------------------------------------

# 3. Measured Reality That Reshapes the Plan

Four empirical results exist. Each changes the protocol; none was in v1.

## 3.1 A single episode's reward is a draw

Ten runs of `banking_knowledge/task_001` under one frozen configuration: reward 1.0 six
times, 0.0 four times; 16–44 messages; $0.10–$0.51 per episode
(`results/experiment_dummy/generation_000/task_001_trials/`).

The seed analysis behind it, corrected and sharpened against τ's source: τ's `--seed`
derives one seed per trial and passes it into the *stock* agent's and user simulator's
LLM args as the provider `seed` parameter — but (a) our Pi agent implements no `set_seed`,
so it receives nothing, and (b) litellm's `drop_params` silently discards `seed` for
providers that do not support it, which includes Anthropic. So for this experiment the
agent is unseeded by construction and the user simulator's reproducibility rests entirely
on `temperature: 0.0`. Episode-level reward is a random variable, full stop.

Consequences, now binding:

- `num_trials: 1` supports a gate, never a comparison. G0 onward runs at the frozen trial
  count decided in §4 H2 (recommended: 4 — it matches the leaderboard's native
  pass^1..pass^4 reporting and the pass^k estimator's need for uniform trials per file).
- **Within-task trial divergence is the primary control set.** The same task, same frozen
  configuration, one trial passing and another failing is a matched comparison v1's
  cross-task "successful controls" cannot approach. The variance is not only noise; it is
  the experiment's best microscope.
- pass^k is reported alongside pass^1 from G0 (τ computes pass-hat-k natively:
  C(c,k)/C(n,k) per task, averaged; success = reward within 1e-6 of 1.0).

## 3.2 Reward mechanics, and the retrieval confound

From the pinned τ source: 88 of 97 tasks grade on `reward_basis: ["DB"]` (agent-and-user
database end-state hashes vs a golden reference trajectory), 9 on `["ACTION"]`
(all-or-nothing golden-action matching); `communicate_info` is empty everywhere, so no
banking task needs τ's judge LLM to grade. Premature termination (max_steps, errors,
timeout) is reward 0 regardless; `infrastructure_error` simulations are **excluded** from
τ's metrics — the manifest (§4 W3) must count them anyway, because they consume budget and
can hide transport defects.

In every inspectable G0-era run, reward tracked one retrieved document: 1.0 iff `KB_search`
returned `doc_credit_cards_gold_rewards_card_005`. Failing agents reasoned correctly on
worse evidence and searched *more* to get *less* (6–8 calls vs 5); one queried the card by
name and bm25 returned savings-account tables. **This is not yet attributable to the
harness**: the lock is on the offline `bm25` fallback, not the intended
`openai_embeddings`, and the retrieval backend may be most of the effect. This is exactly
the confound that would poison G1's first attribution — hence §4 H1 blocks G0.

## 3.3 The generation budget is now computable

Measured inputs: ~$0.26 and ~75 s per platform episode (mid-range; observed spread
$0.10–$0.51), serial execution (`max_concurrency: 1` — the run-scoped bridge is
single-episode-safe), harvest wait ~40 min after the last episode (§5.4).

At the recommended split sizes (§4 W2: discovery 30 / validation 15 / test 20) and
`num_trials: 4`:

| Round | Episodes | ≈ Cost | ≈ Wall clock (serial) |
|---|---|---|---|
| G0 discovery | 30 × 4 = 120 | $30 | 2 h 30 m |
| G0 validation | 15 × 4 = 60 | $15 | 1 h 15 m |
| Full-domain checkpoint (×4 trials) | 97 × 4 = 388 | $100 | 8 h |
| G1+ generation, both arms on discovery + validation | (30+15) × 4 × 2 = 360 | $90 | 7.5 h |
| — cheaper variant: candidate-only discovery, both arms validation | (30 + 2×15) × 4 = 240 | $60 | 5 h |

Wall clock, not dollars, is the binding constraint at `max_concurrency: 1`. Raising
concurrency is a real build item with two prerequisites (bridge episode-multiplexing and a
re-freeze) and is deliberately **out of MVP scope**; the schedule absorbs serial rounds
instead. τ's own default of 3 and the platform's organization-level queue are both idle
capacity until then. (Note: the lock file's comment claims per-episode bridge ports; the
code disagrees — `run.py` documents the single run-scoped bridge as single-episode-safe.
The code is the truth; the comment is queued for W0.)

## 3.4 Completion is recorded, not inferred — and must stay that way

The 409/turn-gate incident (an episode "stuck on turn 2" that τ still graded 1.0 on
already-landed answers) established the repository's sharpest lesson: **a turn ends when
the platform run ends, not when τ has a message**, and every silent gap in the rendezvous
eventually presents as a plausible score. The mitigations are in place — `RUN_FINISHED`
gating, the 25 s stall warning, `episodes[].completed`, `evidence_complete` — and §5.3
makes asserting them a per-round obligation rather than a debugging tool.

------------------------------------------------------------------------

# 4. The Remaining Path

Dependency-ordered workstreams. **Decide** items need a human; **build** items are code;
**run** items produce results. Nothing below G0 in this table may be skipped; the ordering
mirrors `contract/protocol.md`'s stub: the fidelity gate gates any claim, the split gates
any generalization claim, the evidence join gates the diagnosis half of the loop.

## W0 — Documentation truth pass (build, small)

The code has moved past four documents; stale always-loaded context is how a future
session plans against a world that no longer exists. Fix: `CLAUDE.md`'s claim that
`benchmark/fidelity/` does not exist (it does — `compare_lanes.py`, `make fidelity`);
`contract/protocol.md`'s claim that Operate is blocked on a missing dev-lane transport
(it landed); `results/experiment_dummy/generation_000/README.md`'s platform row (reward, cost, task id, and
the delete-vs-archive story are one refresh behind); the lock's per-episode-bridge-port
comment (§3.3). Exit: no document contradicts the code.

## H1 — Decide the retrieval config (decide, blocks G0)

The single highest-leverage open decision, because §3.2 shows retrieval quality plausibly
dominating reward on the current fallback.

- **Intended:** `openai_embeddings` — one `KB_search` tool backed by
  `text-embedding-3-large`, requires a working `OPENAI_API_KEY` (the key on this machine
  returns `429 billing_not_active`), document embeddings cached on disk after one warm-up,
  and the config closest to the published-comparable setting. Grading rebuilds the
  retrieval environment, so the key is needed at grade time too.
- **Fallback:** stay on `bm25` — fully offline, same single `KB_search` tool surface,
  different backend *and different policy text*. Legitimate **only** if pinned knowingly
  for the whole experiment, with the explicit caveat that no published number was produced
  on it and comparability claims are dropped. The G0 floor check still governs.

Either way: one value, pinned in the lock before G0, `make policy` rerun (the flag rewrites
the graded policy text and the tool set), and the `PROVISIONAL` marker dropped only when
every `frozen:` value has been re-decided (H2). Fixing the OpenAI billing state is the
recommended path; it buys back the comparability story v1 promised.

## H2 — Re-decide the freeze (decide, blocks G0)

`num_trials` (recommendation: 4 — §3.1), `seed` (300, inert for our agent but pinned for
the stock-agent anchor in W4), `max_concurrency` (1 for the MVP — §3.3), the checkpoint
trial count for the full-domain runs (×4 matches leaderboard reporting at ~$100/checkpoint;
×1 halves the recognizable number's cost but weakens it), and approval of the §3.3 budget.
H2 also **names the experiment**: re-deciding the freeze assigns the `experiment.id` all
G0+ results live under (`results/experiment_<id>/`, §2.7), retiring the `experiment_dummy`
bring-up bucket; the first run then snapshots the freeze into `experiment.yaml`.
Exit: `frozen.status: PROVISIONAL` removed; every value in the lock is an experiment
freeze, not a bring-up placeholder; the experiment is named.

## W2 — Populate the split manifest (build + decide, blocks any generalization claim)

`benchmark/split_manifest.yaml` is a deliberate stub. Populate it by stratified sampling
over the vendored task data — strata: `reward_basis` (88 DB / 9 ACTION — the ACTION tasks
must not all land in one split), task category, and required-document count (vendored mean
9.8, max 30) — sizes **discovery 30 / validation 15 / test 20**, remainder unused except by
full-domain checkpoints. A small script generates the proposal; a human freezes it. The
test list's enforcement is procedural (v1 §22.10); at minimum, test-split simulation output
stays out of the orchestrator's working tree, and the writeup states plainly which
enforcement level was used. Exit: three disjoint frozen id lists; the honesty caveat
recorded.

## W3 — Close the evidence join (build, gates the diagnosis loop)

The §2.3 spine, made complete and load-bearing at sweep scale:

1. **Per-episode labels that name the τ task.** The platform task title (and therefore the
   conversation's dashboard name) must carry `<domain> <task_id> trial<k> gen<NNN> [exp:<id>]`
   even on sweeps — the `[exp:<id>]` suffix exists today (§2.7); the per-task part is the gap. Candidate mechanism: post-run retitle — `run.py` already recovers the
   (τ task → platform task) map from `raw_data` after τ's runner returns, and the CLI can
   retitle archived rows; threading the label through the factory at episode start is the
   cleaner alternative if τ's construction order permits it.
2. **An episode manifest** — one machine-readable row per (task, trial):
   `{tau_task_id, trial, seed, reward, termination, completed, introspection_task_id,
   recipe_git_commit_sha, cost, usage, span_counts, evidence_complete, stall_warnings}` —
   emitted beside `run_metadata.json`. This is the artifact `operate` receives (§5.3) and
   the learning record cites; today its content is scattered across `results.json` and
   `run_metadata.json`.
3. **A clean-tree assertion for platform runs** (verified absent today): refuse to start —
   or at minimum record prominently — when `target-agent/` has uncommitted changes, because
   `introspection dev` serves the work-tree while `recipe_git_commit_sha` names the base
   commit. Without this the arm attribution in §5.7 is unverifiable.
4. **Arm assertion:** after any arm's round, assert every conversation's
   `recipe_git_commit_sha` equals the arm's intended SHA.
5. **Queue-tolerant accounting:** failed-pre-agent and platform-cancelled tasks appear in
   the manifest with their termination class; N is derived from task rows, never
   submissions.

Exit: a multi-task platform sweep yields a manifest that joins every episode to its named
conversation and its commit, with completeness flags, and the labels are visible in the
dashboard.

## W4 — The adapter fidelity gate, re-specified (build + run, gates any claim)

v1 Phase A.0 prescribed "run τ's stock `LLMAgent` through the adapter path and natively;
scores must agree." **As written, that gate cannot run**: the as-built seam does not host
arbitrary τ agents — it replaces the agent host with Pi. There is no "same agent, two
paths" configuration. Pretending otherwise would leave the gate permanently unrun and the
claim permanently unmeasured, so v2 decomposes it into what the architecture actually lets
us measure, ordered by strength:

- **A.0a — Pipe semantics (deterministic, blocking).** The claim: the bridge and transports
  preserve tool calls, arguments, results, and message boundaries exactly. Evidence: the
  63-test adapter suite (name mangling pinned byte-for-byte against the platform's JS
  implementation; AG-UI event contract pinned against captured live shapes; mailbox and
  reset semantics), plus the `mock` end-to-end smoke in both… lanes where the lane
  supports it. Extension if warranted: a scripted MCP-client replay agent that re-issues a
  recorded episode's calls and asserts byte-level trajectory equality — cheap, and the
  strongest possible statement of "the pipe adds nothing".
- **A.0b — Cross-lane consistency (blocking for the platform lane).** `make fidelity`
  exists: the same task through both lanes, adapter-owned invariants asserted
  (`fidelity/compare_lanes.py`) — deliberately *not* per-task reward at `num_trials: 1`,
  which §3.1 shows would compare two draws. Extend to a small task set × the frozen trial
  count once H2 lands, and require aggregate agreement within trial noise. Until this
  passes, a platform score is not a substitute for a local one.
- **A.0c — Stock-agent reference anchor (run, informational).** Run τ's stock `LLMAgent`
  **natively** under the lock's exact configuration (`--agent llm_agent`, agent model =
  the lock's, user simulator = the lock's, same seed/split/trials). This measures the
  *scaffold delta* between the stock agent and the Pi recipe and anchors comparability
  with published-method numbers. It is not an adapter test — the agent differs by design —
  so it informs but does not block. It is also the only configuration in the experiment
  where τ's seed mechanism has any reach (§3.1), and it doubles as an independent estimate
  of the H1 retrieval decision's effect size.

Exit: A.0a and A.0b pass and their results are recorded under the experiment's directory;
A.0c's anchor numbers are recorded beside them. A failed blocking component stops the
experiment, exactly as v1 demanded. The blocking components re-run for every new
experiment (§2.7): a new freeze — H1's retrieval value above all — changes exactly the
surfaces they measure.

## W5 — Sweep robustness (build)

A generation is a 240–390-episode obligation on a serial lane; a crash at episode 200 must
not cost 200 episodes. (1) **Resume:** τ ships checkpoint/resume keyed
`(trial, task_id, seed)` under `--save-to`; the runner bypasses it with explicit output
paths — adopt τ's mechanism or implement per-task incremental output; `--overwrite`'s
`rm -rf` semantics stay for intentional restarts only. (2) **Stall/incident accounting:**
stall warnings, 409s, and infrastructure retries land in the episode manifest as counts,
so a rendezvous regression surfaces in the round report rather than in a debugging
session. (3) **Idle-timeout tuning** on episode tasks so an interrupted run does not leave
sandboxes idling toward the 600 s backstop. Exit: an interrupted 97-task sweep resumes
without re-spending completed episodes, and every incident class is visible in the
manifest.

## W6 — G0 baseline (run)

With H1/H2/W2–W5 landed: discovery + validation rounds at the frozen configuration on the
platform lane; grade; emit manifests; **check the ≥20–25 % floor** on discovery (below it,
strengthen G0's basic competence per v1 §13.1 and rerun — do not proceed); run the
full-domain checkpoint once at the H2-decided trial count; and perform the **first
observation/pattern harvest** — including the explicit empirical check of the dev-lane
analysis assumption (§2.5): an `introspection.observation` event for a platform episode's
conversation ≥40 min after episode end. Record everything under
`results/experiment_<id>/generation_000/` — the experiment H2 named; G0 is the first
record outside the `experiment_dummy` bring-up bucket — in the §5.9 layout. Exit: G0 pass^1 and pass^4 on discovery and validation with N stated;
floor verdict; analysis-assumption verdict; budget actuals vs §3.3.

## W7 — The first improvement generation (run, then write)

Execute §5 end-to-end once: operate → signal → learning record → improve → PR → human
review → candidate round → decision → `results/experiment_<id>/generation_001/`. Then — and only then —
write `contract/protocol.md` from what actually ran, per its own stated policy of not
describing a process nothing has run. The learning-record schema
(`contract/learning_record.schema.yaml`) lands here, instantiated from §5.6, not before.
Exit: one accepted or cleanly rejected candidate with a complete evidence → signal →
hypothesis → mutation → result record; `protocol.md` written; the loop demonstrated.

------------------------------------------------------------------------

# 5. The Improvement Loop, Grounded

This is the MVP's centerpiece: the operational integration between the Improvement
Orchestrator and the benchmark. Everything here uses only surfaces verified in §2. The
orchestrator is Claude Code with the Introspection plugin — `operate` and `improve` own the
methodology (controls, falsification, earliest divergence, owning layer, one mechanism,
open-coding); this repository supplies what the plugin cannot know: the objective, the
frozen surfaces, the permission envelope, and the artifacts below. Do not reimplement the
plugin's methodology here; that boundary is v1 §23.2 and it held.

## 5.1 What the orchestrator receives at the top of a generation

A generation starts from artifacts, not from ambient state:

- the **episode manifest(s)** for the round just run (W3) — outcome, identifiers,
  completeness per episode;
- `benchmark/benchmark_lock.yaml` (the freeze) and `benchmark/split_manifest.yaml`
  (what may be inspected: discovery only);
- the prior generations' learning records under `results/`;
- the standing envelope: `CLAUDE.md` invariants + `contract/constraints.md`.

Explicitly *not* in context: the τ-Knowledge paper, the leaderboard, test-split anything
(v1 §22.9, §22.10).

## 5.2 Phase A — Execute a round

```text
make <round target> GEN=generation_NNN   # W3-extended runner: --task-ids from
                                         # split_manifest, TRANSPORT=platform,
                                         # labels + manifest emission
make grade OUT=results/experiment_<id>/generation_NNN/<round>
```

Pre-flight (all mechanical, all existing or W3): lock assertions and the experiment
freeze snapshot (§2.7); clean committed
`target-agent/` tree at the intended arm SHA; no connected `tau` binding; runtime
resolved; warm-up absorbed. Post-flight: `run_metadata.json` present (completion
sentinel); every episode `completed: true` or accounted; every `evidence_complete: true`
or re-exported; zero unexplained stall warnings; arm SHA assertion (W3.4).

All rounds run on the **same Runtime** (`target-agent`, development environment). One
runtime group is what makes observations cluster together and pattern trends comparable
across generations (§2.5).

## 5.3 Phase B, harvest 1 — conversation evidence (immediate)

Available the moment grading finishes. The `operate` skill's discipline applies from the
task row outward; the round's concrete workflow:

1. **Build the outcome table** from the manifest: per (task, trial) reward, termination,
   cost, conversation id. τ-side ground truth; nothing platform-side consulted yet.
2. **Select the comparison set.** Primary controls: **within-task divergent trials**
   (§3.1) — same task, pass and fail under one configuration. Secondary: cross-task
   successes matched on category/required-document count. This ordering is a v2 change
   from v1, bought by the variance measurement.
3. **Pull trajectories and spans:**

   ```text
   introspection conversations get <failed-id> <control-id> --format trajectory
   introspection conversations get <ids…> --format json      # spans, per-call cost, items
   introspection metrics query @spans_round.json             # tool latencies, call counts
   ```

   (≤20 ids per call; Arrow + `--page-all` for whole-round pulls.)
4. **Open-code.** Free annotation of what actually happened, per the plugin's method —
   no pre-imposed taxonomy (v1 §2.3 is binding; the §3.2 retrieval coupling is recorded
   G0 evidence, not a category handed to the orchestrator).
5. **Locate the earliest meaningful divergence** between failed and control trajectories
   — with within-task pairs this is unusually sharp: identical task, identical prompt,
   first differing decision.

Every product of this harvest is labeled **"conversation evidence; asynchronous analysis
pending"** until harvest 2 lands.

## 5.4 Phase B, harvest 2 — observations, patterns, prevalence (deferred)

Earliest ~40 min after the round's last episode (30 min eligibility + scan cadence);
a serial multi-hour round ages its early episodes during the run, so in practice harvest 2
begins almost immediately after grading for all but the final episodes.

1. **Check analysis status first** — the difference between "no findings" and "not yet
   analyzed" (v1 §3.3.1, now with a concrete command):

   ```text
   introspection events list --event-name introspection.observation_clustering.run --limit 5
   ```

2. **Per-episode observations**, and round-window sweeps:

   ```text
   introspection events list --event-name introspection.observation \
       --filter conversation_id=<id>
   introspection events list --event-name introspection.observation --lookback 24h
   ```

   Lens validity under a simulated user (v1 §3.3.2, unchanged): *user sentiment* carries
   no signal, *user intent* restates the task; the load-bearing lenses are **task
   resolution, agent struggle, environment issue**.
3. **Patterns**, scoped to the runtime group; treat as candidate cross-episode phenomena
   to be verified against conversations, not as conclusions.
4. **Prevalence by aggregation, never anecdote** — the `operate` skill's rule, given
   teeth by `metrics query` over the round's window: how many conversations exhibit the
   open-coded phenomenon; does it co-vary with reward; is it concentrated in a task
   stratum. Dimensions include recipe commit hash, so prior generations are one filter
   away for trend claims.

**Fallback (designed, §2.5):** if G0's empirical check finds dev-lane conversations are
not analyzed, harvest 2 degrades to metrics-over-spans plus manual clustering of harvest-1
open codes, and the generation proceeds — with the learning record stating which evidence
tier it ran on.

## 5.5 Phase C — Signal and hypothesis

Unchanged in substance from v1 §15 Phase B/C, now with concrete grounding requirements: a
candidate signal states the phenomenon, its **measured** prevalence (harvest 2), the
supporting and counterexample **conversation ids**, the within-task pairs behind the
earliest-divergence claim, and the honesty flag `previously_published` (v1 §22.9). The
hypothesis adds owning layer, predicted effect, expected non-regressions, and confidence —
the shape the learning record (§5.6) serializes.

## 5.6 The learning record

Schema lands at `contract/learning_record.schema.yaml` in W7; v1 §16's shape is carried
with these v2 additions, all join-spine fields now actually available:

```yaml
experiment: <id>                        # results/experiment_<id>/ — the freeze (§2.7)
evidence:
  round_manifests: [results/experiment_<id>/generation_NNN/<round>/episode_manifest.jsonl]
  conversations_cited: [<ids>]          # every claim traceable
  within_task_pairs: [{task, pass_trial, fail_trial}]
  observation_event_ids: [...]          # empty + analysis_status recorded, if harvest 2 degraded
  analysis_status: analyzed | pending | unavailable
arms:
  baseline_sha: <commit>                # asserted against every conversation's lineage
  candidate_sha: <commit>
completeness:
  episodes_completed: n/n
  evidence_complete: n/n
  infrastructure_errors: n              # excluded from τ metrics, counted here
results:
  pass1: {...}   pass_k: {...}          # per split, per arm, N stated
  effect_resolvable: true|false         # false ⇒ decision is directional (v1 §12.0)
```

## 5.7 Phase D — Improve: from hypothesis to proposal

The `improve` skill drives; the repository constrains:

- **Scope:** one coherent mechanism, inside `contract/constraints.md`'s mutable table —
  `SYSTEM.md` `<instructions>`, `agents/agent.yaml` tools/skills/subagents, `package.json`
  pi.skills/pi.extensions. The frozen surfaces (policy region, model, thinking level,
  `pi.mcp`, everything outside `target-agent/`) are asserted at the next run anyway; a
  mutation that touches them is dead on arrival by machinery, not memory.
- **Vehicle: a pull request authored by the orchestrator** (git + `gh`), branch
  `gen-NNN/<slug>`, under branch protection + the `frozen surfaces` workflow. The
  orchestrator never merges. Human review is MVP-A's approval gate (v1 §20), and it maps
  exactly onto the `improve` skill's own confirm-before-edit/PR checkpoints.
- **The PR body is the proposal artifact.** It must carry: the hypothesis; the evidence
  citations (conversation ids, prevalence, within-task pairs); the predicted effect and
  expected non-regressions; the affected discovery cases; a pointer to the learning
  record. A reviewer must be able to trace claim → conversation without asking. Rollback
  is `git revert` — one mechanism per PR keeps that true.
- The baseline is preserved by construction: it is a commit SHA, and every baseline
  episode's lineage asserts it.

## 5.8 Phase E — Validate

- **Arms are separate invocations** — measured fact: one `tau2 run` carries exactly one
  agent configuration, and merging arms into one results file would falsify its `Info`.
  "Interleaved in one batch" (v1) is therefore implemented at the orchestration layer:
  the runner alternates arms round-robin over the task list (or, minimally, runs the two
  arms back-to-back in one session) so provider drift lands on both arms alike.
- **Pairing:** identical `--task-ids`, identical seed (τ's per-trial seed derivation is
  deterministic, so separate invocations at the same `--seed` produce identical trial
  seeds — inert for our agent, §3.1, but it pins the environment's side), identical
  everything else by lock assertion. Comparison is paired per task; pass^k computed per
  arm's results file (uniform trials per file, as τ's estimator requires).
- **Mechanical arm attribution:** every conversation's `recipe_git_commit_sha` equals its
  arm's SHA (W3.4) — the platform's lineage, not the runner's bookkeeping, is what makes
  "which harness produced this score" a verified claim.
- **Traces behind deltas:** before any accept, inspect the trajectories behind the score
  movement — did the intended mechanism actually occur in the improved cases
  (`trace_review.intended_mechanism_observed`), and did the predicted non-regressions
  hold. A higher aggregate alone is insufficient (v1 §15 Phase F, unchanged).
- **Validation information policy** (v1 §12.2, unchanged): the orchestrator receives
  aggregate validation outcomes only; escalating any validation failure to inspection is
  a logged, deliberate exception, or validation silently becomes discovery.

## 5.9 Phase F — Decide, record, close

- **Accept** iff the paired validation comparison improves and the effect is at or above
  what the split resolves (at validation N = 15 × 4 trials the coarse quantum is roughly
  one task — state `effect_resolvable` honestly); pass^k must not regress materially.
  Accept ⇒ merge (human), candidate SHA becomes H_{n+1}'s baseline.
- **Reject** ⇒ close the PR unmerged; the record is a first-class result (v1's stance,
  kept: rejected hypotheses are research output).
- **Directional** ⇒ below resolution: retain H_n, record the direction, optionally fold
  the evidence into the next generation's discovery.
- **Record** under `results/experiment_<id>/generation_NNN/` (v1 §24's layout + the episode manifests and
  the learning record; raw evidence stays in the platform, stable identifiers travel in
  the record). Close-out: verify tasks archived, update the generation curves
  (pass^1/pass^k per split per generation), append actual cost and wall clock.

## 5.10 One generation, end to end

```text
        (H_n at SHA_b, lock frozen, split frozen)
run discovery round ──► grade ──► manifest ──► assert completeness      [~2.5 h, $30]
        │
        ├─ harvest 1: outcome table, within-task pairs, trajectories, open codes
        └─ harvest 2 (≥40 min): analysis status, observations, patterns, prevalence
        ▼
signal(s) + hypothesis ──► learning record (draft)
        ▼
improve: one mechanism ──► PR gen-NNN/<slug> ──► human review            [approval gate]
        ▼
candidate SHA_c ──► validation rounds, both arms, paired                 [~5–7.5 h, $60–90]
        ▼
trace review ──► accept / reject / directional ──► results/experiment_<id>/generation_NNN/
        ▼
   H_{n+1} (or retained H_n) ──► next generation
```

------------------------------------------------------------------------

# 6. Measurement and Reporting

Carried from v1 §17 with the estimator facts now pinned to τ's implementation:

- **Primary:** pass^1 on the τ objective, graded only via `make grade`. **Alongside, always:
  pass^k** (native pass-hat-k; k up to `num_trials`; success = reward 1.0 within 1e-6) —
  §3.1 makes reliability plausibly *where the headroom is*, and v1's intuition to that
  effect is now a measurement.
- **Two numbers at checkpoints, both labeled** (v1 §17.1.1, unchanged): the held-out test
  score with its N and an interval, and the full-97-task score explicitly labeled as
  contaminated by discovery. G0 and final generation only.
- **Efficiency, tracked not optimized:** τ-side (steps, agent cost, messages) and
  platform-side (`accounting`: cost, usage, span/tool/LLM-call counts) per episode, in the
  manifest.
- **Process metrics** (v1 §17.4, unchanged): acceptance rate, validation gain per accepted
  mutation, cost per accepted improvement, signals discovered vs signals that led to
  accepted interventions.
- **Statistical honesty:** paired per-task comparisons; `effect_resolvable`; directional
  results named as such; `infrastructure_error` episodes excluded from scores (τ's rule)
  but reported in the manifest; every number carries split + N + arm SHA + experiment id.
- **The record is renderable.** `dashboard/` (its own swimlane; `make dashboard`) serves
  the results tree read-only: experiment dropdown + freeze strip, generation curves with
  intervals (pass¹ and pass^k, candidate arms as hollow marks), efficiency small
  multiples, a task × generation heatmap with within-task instability marked, and
  round/episode drill-down to full transcripts, with the learning-record ribbon lighting
  up once W7 lands. It consumes only the committed record and regrades nothing — τ's
  recorded rewards in, display aggregates out — so the §3.4 completeness flags and
  diagnostic-mode muting surface in the UI instead of being averaged away.

------------------------------------------------------------------------

# 7. Threats to Validity — Updated

v1 §22's register, re-weighted by what is now measured. Unchanged entries are carried by
reference (leakage §22.1, Goodharting §22.2, multi-change generations §22.7, false causal
stories §22.8).

| Threat | Status in v2 |
|---|---|
| **Per-episode variance** | Measured (§3.1). Mitigated by trials, pairing, pass^k, within-task controls — and by refusing single-trial conclusions anywhere. |
| **Retrieval confound (bm25 fallback)** | Live until H1. Any pre-H1 "finding" about retrieval behavior is quarantined as potentially a backend artifact. |
| **Orchestrator prior knowledge** (v1 §22.9) | Unchanged and permanent: mitigations are context hygiene, per-signal grounding in cited conversations, and the `previously_published` flag. Mitigated, not eliminated — say so in the writeup. |
| **Held-out enforcement is honor-system** (v1 §22.10) | Unchanged. W2 records which of the three enforcement strengths was chosen. |
| **Model / provider drift** | Frozen by lock (both models + user args); arms run adjacent in time (§5.8). Anthropic ignores the sampling seed, so drift control rests on freezing + adjacency, not seeding. |
| **Dev-lane lineage softness** | New: uncommitted-overlay caveat + missing clean-tree assertion. Closed by W3.3/W3.4. |
| **Rendezvous integrity** | Incident observed and fixed (§3.4); standing mitigations asserted per round; any recurrence is loud by construction. |
| **Adapter divergence from stock τ** | Constant across generations, so it cannot bias the improvement claim; bounds comparability with published numbers; measured by W4 (A.0b/A.0c) instead of asserted. |
| **Stale documentation steering future sessions** | New, observed in practice (Appendix C). W0, plus this document's rule that code wins. |

------------------------------------------------------------------------

# 8. Deliberately Out of MVP Scope

Kept visible so their absence reads as a decision, not an omission:

- **`deploy` and staging/production lanes.** The dev lane needs no deployment; per-
  generation immutable version pins via endpoint bindings and staging runtimes are the
  upgrade path if the experiment outgrows `introspection dev`.
- **The platform repository loop as the improver** — the target agent proposing changes to
  its own recipe via a `runtime.github` grant, i.e. the self-hosted MVP-B variant. The
  showcase-strongest artifact, and exactly one step beyond MVP-A's orchestrator-authored
  PRs.
- **Concurrency > 1** (§3.3), **judges as durable instruments** (§2.6), **Harbor
  portability and the fully-native eval loop** (v1 §7), and v1 §27's later experiments
  (cross-model transfer, human-vs-self-improved comparison, budget scaling).

------------------------------------------------------------------------

# Appendix A — v1 Section Disposition Map

| v1 § | Disposition |
|---|---|
| 0–4 (framing, principles, roles, operate/improve) | Carried; condensed into §1; plugin capabilities now verified (§2.5) |
| 5–6 (why banking_knowledge; versioning) | Carried; values live in the lock; task-set/split flag conflation corrected in lock comments |
| 7–10 (Harbor; SIA; Prime Agent; SquareDiff) | Carried by reference, unchanged |
| 11 (architecture) | Superseded by §2 (as built) |
| 11.1 (the undecided seam + spike) | **Resolved** — §2.1; spike exit criteria 1–3 met; criterion 4 re-specified as W4 |
| 12 (splits) | Carried; instantiated by W2 with stratification and sizes |
| 13 (baseline agent + floor) | Carried; G0 recipe exists; floor checked at W6 |
| 14 (mutable/immutable) | Carried; **authoritative form now lives in `CLAUDE.md` + lock + `constraints.md`**, including v1's four listed corrections |
| 15 (generation phases) | Superseded by §5; Phase A.0 re-specified as W4 |
| 16 (learning record) | Carried; extended §5.6; schema lands at W7 |
| 17 (metrics) | Carried; §6 with native pass^k facts and the computed budget (§3.3) |
| 18–20 (self-improvement definition; permissions; HITL) | Carried; monorepo reality + orchestrator-authored PRs stated in §2.4/§2.6/§5.7 |
| 21 (expected evolution) | Carried unchanged — researcher hypotheses, never given to the orchestrator |
| 22 (threats) | Updated as §7 |
| 23–24 (layout; artifacts) | Realized; `orchestrator/` prohibition holds; `fidelity/` exists; `learning_record.schema.yaml` at W7 |
| 25 (success criteria) | Carried, with criterion 0 read against W4's re-specified gate |
| 26 (sequence) | Superseded by §4 |
| 27–32 (later work; questions; references; guardrails; short form) | Carried by reference; §31 guardrail 16 re-read via W4 |

# Appendix B — Open Decisions Requiring a Human

1. **H1 — retrieval config**: fix OpenAI billing and pin `openai_embeddings` (recommended),
   or knowingly pin `bm25` and drop comparability claims.
2. **H2 — the freeze**: `num_trials` (recommended 4), checkpoint trial count, budget
   approval (§3.3), `max_concurrency` (recommended: keep 1), and the `experiment.id`
   naming the freeze (§2.7).
3. **W2 — split sizes and the held-out enforcement strength** (v1 §22.10's three levels).
4. **Timing of the `target-agent/` repository split** (`git subtree split`) — required
   before any real agent-held write grant; optional during MVP-A.

# Appendix C — Documentation Lagging the Code (feeds W0)

Found while grounding this revision; each is a place a future session would mis-plan:

- `CLAUDE.md`: says `benchmark/fidelity/` does not exist (it does: `compare_lanes.py`,
  `lane_report.py`, `make fidelity`).
- `contract/protocol.md`: lists Operate as blocked on a missing dev-lane transport — the
  transport landed; the honest blocker is now W3's evidence join + the unexercised harvest.
- `results/experiment_dummy/generation_000/README.md`: platform row one refresh stale
  (reward/cost/task id) and still describes delete-at-close instead of retitle-and-archive.
- `contract/constraints.md`: "evaluate-trajs offline defect … not worked around here" —
  `scripts/grade.py` now injects the recorded retrieval config (still τ's evaluator).
- `benchmark/benchmark_lock.yaml` comment: claims per-episode bridge ports; the code runs
  one run-scoped bridge, single-episode-safe (`run.py`).
- `target-agent/README.md`: names `agent.yaml` key `ai.model`; the file deliberately uses
  the legacy `model:` spelling.
