# Introspection Self-Improver

A τ²-bench-evaluated agent built as an Introspection Recipe, plus the machinery to improve
it generation by generation without ever touching the objective.

The improvement loop itself is not a program in this repository — Claude Code drives it in
conversation ([Driving an experiment from Claude Code](#driving-an-experiment-from-claude-code)).
What lives here is everything the loop runs against: an immutable objective, a minimal
harness under improvement, a frozen/mutable boundary enforced mechanically rather than by
convention, and the generation lifecycle — improvement batches, a sealed held-out vault,
improvement records, an end-of-experiment reveal. The evaluation design is
`self_improving_agent_evaluation_protocol.md`; `SIA_EVALUATION_PLAN.md` tracks the path
and holds every decision's rationale (D1–D11) plus the distilled lessons;
`contract/protocol.md` is the per-generation procedure as it actually runs, and
`contract/constraints.md` the permission envelope. Deeper analyses live beside the
results they analyze (e.g. `results/experiment_002_bm25-sonnet46/SIZING_ANALYSIS.md`).
The debug-scale experiment has run to completion and is revealed —
`results/experiment_002_bm25-sonnet46/` holds the record (summary, guardrail walk,
improvement records, per-generation evidence). Its endpoint sits inside the noise band,
so it demonstrates the loop, not a capability claim. Next is the **powered**
experiment — seq 3, G=5 generations / 8-task batches / 28 held-out tasks, the tier
between debug and full, sized from the debug run's own data
(`results/experiment_002_bm25-sonnet46/SIZING_ANALYSIS.md`, plan D11) so a working
loop has a real chance to show on the curve at ~63% of full-experiment cost; the
full-scale run (T=47) is deferred until the powered outcome argues for it.

```
τ²-bench  ──tasks──▶  target-agent (Introspection Recipe)  ──tool calls──▶  τ² environment
   ▲                                                                             │
   └────────────────────────── reward, via tau2 evaluate-trajs ◀─────────────────┘
```

- [Quick start](#quick-start) — bootstrap, checks, round types
- [The lanes](#the-lanes) — who may change what
- [Generations and the vault](#generations-and-the-vault) — H0, tags, sealed held-out results
- [Driving an experiment from Claude Code](#driving-an-experiment-from-claude-code) — the conversation that runs the loop
- [How the seam works](#how-the-seam-works) — the τ ↔ Pi rendezvous
- [Two run modes](#two-run-modes) — locked vs diagnostic
- [Two transports](#two-transports) — local vs platform, and the lessons behind them
- [Frozen surfaces](#frozen-surfaces) — what is asserted before every run
- [One experiment, one freeze](#one-experiment-one-freeze) — experiment identity, and two values decided the hard way

## Quick start

```bash
make bootstrap   # pinned τ²-bench checkout + Python environment  (~715 MB, one time)
make check       # recipe validity + every frozen surface
make smoke       # one mock-domain task end to end, then grade it
make single_task # one locked-domain task, then grade it  (TASK=task_001 by default)
make bench       # the WHOLE locked split (97 tasks) — long and costly

make single_task TRANSPORT=platform   # same task, agent on an Introspection dev runtime
```

The generation protocol's own round types and lifecycle
(see *Generations and the vault* below):

```bash
make propose_split                    # freeze prep: propose the partition from the lock (WRITE=1 freezes)
make batch B=1 GEN=generation_000     # improvement batch: platform lane, fully observable
make heldout GEN=generation_000       # held-out round: local lane, sealed into the vault
make reset_h0                         # restore the recipe to the h0-baseline tag
make reveal                           # end of experiment: unseal the vault into results/
```

`TRANSPORT` selects where the agent runs and defaults to `local`; see *Two transports* below.

`make smoke` is the cheap seam gate and takes about 15 seconds. Its results are **not
reportable** — see *Two run modes* below.

## The lanes

| Directory | Role | Who may change it |
|---|---|---|
| `target-agent/` | The harness under improvement (H_n). An Introspection Recipe. | The improvement loop, via pull request |
| `benchmark/` | The objective and the seam to it. τ² pinned by commit, the adapter, the lock. | Humans only |
| `contract/` | The permission envelope the orchestrator works inside. | Humans only |
| `results/` | Per-experiment, per-generation record: trajectories, Pi sessions, graded outcome. | Append-only |
| `dashboard/` | Read-only results viewer over `results/`: generation curves, task heatmap, episode transcripts (`make dashboard`). | Humans only |

The dependency runs one way — `benchmark/` reaches `target-agent/` by path, never the reverse
— so the Recipe can be split into its own repository with `git subtree split` when the agent is
eventually granted write access to it. That split matters: a GitHub installation token cannot be
scoped to a sub-path, so an agent granted `contents: write` here to edit its own Recipe can also
write the benchmark lane. Until the split, the boundary is enforced by branch protection plus
the `frozen surfaces` workflow, not by the grant.

## Generations and the vault

A generation is an approved merge commit on `main`; a rejected mutation leaves an
*identity generation* instead — the predecessor carried forward unchanged. Two tags carry
the whole identity scheme:

- `h0-baseline` — the H0 anchor: `target-agent/` plus `.introspection/target-agent.yaml`,
  byte-identical to the baseline freeze. `make reset_h0` restores it as a replace, not a
  merge (files committed after the tag stage as deletions), regenerates the untracked
  runtime state, runs `introspection check`, and leaves the restore staged for a human
  commit. The machine-local `.introspection/local.json` is preserved, never restored.
- `exp<seq>-g<NNN>` — H_NNN of experiment `<seq>` (e.g. `exp2-g001`), applied to the
  approved merge commit of each accepted mutation. A rejected or identity transition
  still gets its tag — placed on the same commit the previous generation's tag points
  at, since H_NNN *is* that harness — with the why recorded in the transition's
  improvement record and no held-out measurement of its own. Tagging every slot keeps
  the reveal's gate mechanical: `make reveal` requires the final tag `exp<seq>-g<G>`
  to exist however the last transition resolved.

Held-out rounds write **nothing inside the repository**. Their episodes, sessions, graded
results and console log live in the vault at `~/.sia_vault/experiment_<id>/generation_NNN/`
(`SIA_VAULT_DIR` overrides), out of reach of every repo sweep and of the dashboard, and the
terminal shows completeness only. A held-out round measures exactly one generation and
proves it before any spend: it refuses a dirty recipe surface and requires the tree
byte-identical to the measured generation's tag (`h0-baseline` for H0). An incomplete
round (a transient provider failure, an environment defect) resumes with the same
command: τ re-runs only the missing episodes and replaces infrastructure placeholders;
completed episodes are never re-spent, and the completeness report names the failure
class — reward-free — so the operator can tell transient from deterministic without
unsealing anything.
`make reveal` — runnable once `exp<seq>-g<G>` exists —
is the single door between the two worlds: it copies the vault into
`results/experiment_<id>/held_out/`, computes the progression artifacts (per-generation
counts, task x generation matrix, transitions, retention), writes `summary.md`, and fills
each improvement record's `held_out_result`. Until then, nothing graded from a held-out
round appears anywhere the orchestrator reads.

Each transition's evidence chain — batch, signals, hypothesis, mutation, approval —
lives in `results/experiment_<id>/improvement_records/` (schema:
`contract/improvement_record.schema.yaml`; scaffold and check with
`benchmark/scripts/improvement_record.py`).

## Driving an experiment from Claude Code

The improvement loop has no program of its own: Claude Code is the orchestrator, and an
experiment is one conversation in which the human speaks at five gates. Everything
between the gates is Claude Code working the CLI — the make targets above, the
Introspection plugin's `operate` and `improve` skills, git. The shape of every run
(the step-by-step procedure with each command: `contract/protocol.md`):

1. **Freeze** — screen the pool, propose and freeze the partition (`make
   propose_split`), `make reset_h0`, flip the lock to FROZEN, record the A.0a PASS.
2. **Measure H0** on the held-out set — sealed into the vault, completeness only.
3. **Per generation** — run the next improvement batch (fully observable) → diagnose
   with `operate` → the human picks mutation targets → `improve` opens one PR → the
   human merges or rejects (merge = the next generation; reject = an identity
   generation, carried forward) → measure the new generation (sealed).
4. **Reveal** — the one sanctioned read of the vault: curve, matrix, transitions,
   retention, and the pre-registered trend verdict.

This is how the debug-scale run actually went — seq 2, condensed; every number below
is from the record at `results/experiment_002_bm25-sonnet46/`:

> **You:** Start the debug experiment.
>
> **Claude Code:** Pre-flight done: partition verified against the lock (3×4 batches +
> 8 held out over the 96-task screened pool), recipe byte-identical to `h0-baseline`,
> lock flipped PROVISIONAL → FROZEN, A.0a gate PASS recorded. Held-out results stay
> sealed in the vault until reveal — I only ever see completeness. Proceed?
>
> **You:** Go.
>
> **Claude Code:** H0 baseline — `make heldout GEN=generation_000`: 8/8 episodes
> completed, zero seam incidents, graded results sealed in the vault. Batch 1 —
> `make batch B=1 GEN=generation_000`: 4/4 episodes clean on the platform lane,
> rewards visible by design: 0/4 — the viability read (plan D8) fires, so I diagnose
> before any mutation. `operate` over the four conversations (the observation harvest
> returned nothing inside its window; the full-transcript read carried the diagnosis):
> every failure is agent behavior, not infrastructure. Misapplied KB knowledge, 2/4 —
> facts assembled from broad `KB_search` results, committed without verifying the
> specific entity; capability blindness, 1/4; premature escalation, 1/4. Against a
> broken-H0 reading: identity verification passed 3/4, and one failing episode still
> drove a multi-step tool flow at 6/9 gold actions. Halt, or proceed?
>
> **You:** Proceed — fix the KB one.
>
> **Claude Code:** `improve` proposes one mutation: verify each KB-derived claim
> against its specific entity before committing writes or recommendations — one
> instruction block in `SYSTEM.md`, outside the frozen `<policy>` region. PR open on
> `gen-001/kb-answer-verification`.
>
> **You:** *(reads `! gh pr diff`)* Merge it.
>
> **Claude Code:** Merged, tagged `exp2-g001`, improvement record `gen_000_to_001.yaml`
> written and validated. Measuring H1 — `make heldout GEN=generation_001`: 8/8
> completed, sealed. Generation 2 consumes batch 2. Go?

Two more cycles ran the same shape: batch 2 graded 0/4 but with the action-match
profile sharply up (19/20 and 5/6 near-misses — the g1 mechanism observably firing),
diagnosis *ungrounded selection*, mutation `gen-002/source-grounded-selection`;
batch 3 graded 2/4 — the experiment's first batch passes — diagnosis
*required-procedure incompleteness*, mutation `gen-003/procedure-completion`.

> **You:** Reveal.
>
> **Claude Code:** `make reveal` — the vault unseals into
> `results/experiment_002_bm25-sonnet46/held_out/`: H0 3/8 → H1 3/8 → H2 2/8 →
> H3 2/8. Endpoint −1 task (−12.5 pp), inside the ±18 pp band — directional only.
> One sustained gain (task_051: fail at H0, pass from g1 onward, retained); the
> task×generation matrix, transitions, retention and `summary.md` are written, and
> every improvement record now carries its `held_out_result`.

The whole run recorded ≈ $32 and ≈ 3.5 h including review latency, with zero mid-run
mechanics patching. At the debug scale that curve demonstrates the loop, not a
capability claim — carrying a claim is what the powered experiment (seq 3) is sized
for. The voided first freeze that preceded this run is its own record,
`results/experiment_001_bm25-sonnet46/README.md`.

The gates where the human speaks: ratify the freeze; decide each diagnosis (the batch
read is visible by design, so Claude Code presents the failure modes with prevalence
and conversation ids as a multi-select — opt into any subset, or all, as approved
mutation targets; one generation still lands one coherent mechanism and the rest queue
in the experiment's improvement backlog for later generations — or record an identity
generation, or halt); merge or reject each `improve` PR (the merge is what defines a
generation — the agent never merges its own work); the budget go at each generation
boundary; order the reveal. The firewall held throughout the run above: no held-out
task id, trajectory, or score appeared in the conversation before the reveal —
including while diagnosing a held-out infrastructure failure, which the completeness
report attributes by failure class without unsealing anything.

**When the environment itself breaks.** The first real run hit this immediately and the
loop absorbed it. An H0 round came back 7/8 with `infrastructure_error:ValueError=1` on
its INCOMPLETE line; "run it again" resumed only the missing episode. When the failure
proved deterministic — a τ-side user-simulator defect no harness mutation can reach
([tau2-bench#470](https://github.com/sierra-research/tau2-bench/issues/470)) — the
remedy was never to patch τ, which is frozen: the freeze was voided with a closure
README, the task pool screened for the crash class, and a new experiment frozen under
the next `seq` with the poisoned task excluded, documented in the split manifest.
Benchmark defects travel upstream as issues and PRs (tracked in
`.ai-state/UPSTREAM_ISSUES.md`), never as local patches.

### Showcasing the run in the dashboard

`make dashboard` serves a read-only viewer over `results/` at `http://127.0.0.1:8787/`,
rendering the run as the improvement story it is — worth keeping open while driving:

- **During the run** — batch evidence is fully observable: the generation ribbon gives
  one card per improvement cycle (pass¹, Δ vs previous, the improvement record's outcome
  and hypothesis, cost, recipe SHAs), every episode opens into its full transcript —
  messages, tool calls, arguments — for walking an audience through a diagnosis, and the
  efficiency small multiples (cost, messages, `KB_search` calls per episode across
  generations) show how behaviour is shifting before any held-out score can. The
  held-out card only states that the measurement is sealed in the vault. Diagnostic
  rounds (the A.0a mock smoke and its `create_task_1`) stay visible in round lists with
  their "not reportable" badge but are excluded from every statistic.
- **After `make reveal`** — the held-out progression card is the headline, and the main
  question — did H_G beat H0? — is read there: the tasks-solved/T curve from H0 to H_G
  with the noise band as whiskers (improvement is an endpoint gap that clears the band,
  not a wiggle inside it), identity generations as hollow marks, the ever-solved
  retention line, and the task × generation matrix showing which tasks each transition
  gained, kept, or regressed. Beneath it, a collapsed **process signals** panel opens
  the sub-reward story — partial credit (DB match, gold-action match, write match) and
  behavioral signatures (retrieval intensity, discoverable-tool usage, transfers) per
  generation, with a per-task gold-action heatmap — for what moved even when pass/fail
  did not.

The dashboard never reads the vault and regrades nothing: held-out data renders only
from the artifacts `make reveal` writes under `results/…/held_out/`. The full view list
is `dashboard/README.md`.

### The phrasebook

None of these are commands — they are intents, and any phrasing works; Claude Code maps
them onto the machinery above. The ones worth knowing:

| Say | What happens |
|---|---|
| "Create a new experiment" | Bumps `experiment.seq` in the lock (a new freeze identity), restores the recipe to `h0-baseline`, re-proposes the partition if the sizes changed; stays `PROVISIONAL` until you freeze |
| "Freeze it" / "start the experiment" | Verifies the partition against the lock, flips the lock to `FROZEN`, commits, records the A.0a gate PASS — and then drives the whole loop, pausing at the gates |
| "Measure the baseline" | `make heldout GEN=generation_000` — completeness only, results sealed in the vault |
| "Run it again" (after an INCOMPLETE round) | The same command resumes: τ re-runs only the missing episodes and replaces infrastructure placeholders; completed episodes are never re-spent |
| "Run the next batch" | `make batch B=g GEN=generation_<g-1>`, graded into `graded/`; batch 1 carries the viability read (plan D8). The platform lane refuses an unpushed HEAD — lineage pins to pushed `main` |
| "Diagnose it" | The `operate` skill over the batch's conversations — prevalence, cited conversation ids, second harvest after the observation window (at these batch sizes the async observations often lag it, and the full-transcript read is the stated fallback, not a degradation) |
| "Fix these two" / "all of them" | The selected failure modes become approved targets in `results/experiment_<id>/improvement_backlog.md`; each generation consumes the top one (composed only when they form one coherent mechanism), the rest carry forward re-ranked by fresh evidence |
| "Propose the fix" | The `improve` skill — one coherent mutation (the backlog's top approved target), branch `gen-NNN/<slug>`, PR citing the evidence |
| "Merged" | Pull, tag `exp<seq>-g<NNN>`, push, write and validate the improvement record, then measure the new generation |
| "Rejected" | Identity generation: tag on the unchanged commit, record says why, no held-out measurement |
| "Measure H2" | `make heldout GEN=generation_002` — refuses unless the tree is byte-identical to `exp<seq>-g002` |
| "Reveal" | `make reveal` — requires the final generation tag; the one sanctioned read of the vault |
| "What moved under the curve?" | The reveal's `process_metrics_*.csv` (post-reveal analysis; `scripts/reveal.py --derive-only` backfills) — rendered as the dashboard's collapsed process panel |
| "This task can never pass — void the experiment" | Closure README with the evidence, vault sealed forever, pool screened for the failure class, new freeze under the next `seq` with exclusions documented in the manifest |
| "File it upstream" | Issue (and fix PR when the mechanism is clear) on the offending dependency, drafted for review before anything posts; tracked in `.ai-state/UPSTREAM_ISSUES.md` |
| "Reset the agent" | `make reset_h0` alone — replace-not-merge restore, staged for a human commit |
| "Open the dashboard" | `make dashboard` — the viewer above |

## How the seam works

τ² and Pi have opposite control flow. τ's orchestrator executes the agent's tool calls itself
and hands back a result; a Pi agent executes its own tools. `benchmark/tau_adapter/` reconciles
them with a rendezvous, and neither side gives up authority:

1. Pi calls an MCP tool served by the bridge.
2. The handler parks. The call surfaces to τ as an ordinary `tool_calls` message.
3. τ's orchestrator executes it against the environment.
4. The resulting `ToolMessage` is posted back, the parked handler returns it, and Pi continues.

τ keeps tool execution, step counting, trajectory construction, termination, and grading. The
bridge never touches the environment, so it cannot become a second implementation of the
benchmark's semantics. Nothing about the trajectory is reconstructed.

One bridge serves the whole run, and every episode rendezvouses on its own **channel** — its
own mailbox — so results cannot cross between episodes, even at `max_concurrency` above 1
with identical tool calls in flight. What differs per lane is only how a request finds its
channel: the local lane hands each Pi subprocess its channel's `/mcp/<token>` URL through
the environment, while the development lane's tunnel stamps every forwarded request with its
sandbox session (`x-introspection-session-id`) and the transport binds each episode's
channel to its task's `agent_session_id` — so N concurrent tasks share the one `dev`
attachment without sharing any rendezvous state (`contract/constraints.md` § Platform-lane
concurrency). `max_concurrency` is an operational knob: the lock's value is the default,
`--max-concurrency` overrides it per run, and 1 asks for serial execution. The full design
record — intake adjudication, the refuted attachment pool, the session-keyed end state —
is `CONCURRENCY_DESIGN.md`.

**The adapter is a pipe, not a participant.** It translates message shapes and tool names and
does nothing else — no repair, no retry, no reformatting. Anywhere the adapter helps the agent
is somewhere the harness stops being measurable, and an unmeasurable harness cannot be improved.
So an assistant message that mixes narration with a tool call is forwarded exactly as produced,
even though the protocol disallows it.

## Two run modes

|  | locked | diagnostic |
|---|---|---|
| Trigger | `--domain` is the locked domain (the default) | any other domain, e.g. `make smoke` |
| Recipe | the committed one, unmodified | materialised into `.diagnostic-workspace/` with that domain's policy |
| `<policy>` check | asserted against the live environment | trivially satisfied by construction |
| Results | may be reported | **not comparable to anything** |

Diagnostic mode exists because the committed Recipe carries the locked domain's policy in its
system prompt, so running a different domain needs a different prompt. It is used for seam
bring-up and for the A.0a pipe-semantics gate on `mock`.

## Two transports

The rendezvous is driven by the bridge, not by the transport, so the same seam runs either way.

| | `TRANSPORT=local` (default) | `TRANSPORT=platform` |
|---|---|---|
| Agent host | Pi subprocess on this machine | cloud sandbox on a dev runtime |
| τ environment | in-process, loopback bridge | in-process, bridged by `introspection dev --mcp` |
| Introspection evidence | **none** | conversation, traces, spans, cost, commit lineage |
| Episode cost / wall clock (seq-2 manifests) | $0.53 median / $0.62 mean, ~2.8 min | $0.50 median / $0.70 mean, ~3.1 min (+~20 s one-off `dev` attach) |
| Prerequisites | none | login, pushed repo, App grant, Runtime, dev API-key agent |

Episode length, not lane, dominates cost — a 112-message platform episode billed ~$1.

Both are implemented. `local` contacts nothing, so no task and therefore no conversation exists
— Pi's session file under `results/<experiment>/<gen>/<run>/pi_sessions/` is the only record. `platform` makes
every episode a real task, so the exchange is readable afterwards:

```bash
make single_task TRANSPORT=platform          # writes results/<experiment>/<gen>/<task>_platform/
introspection conversations export <task-id> --format trajectory
```

The task id is also the conversation id, and `run_metadata.json` records it alongside the cost,
usage, span metrics and `recipe_git_commit_sha` that the platform holds. No public tunnel is
needed: `introspection dev` routes the Recipe's declared `tau` server to a local URL with
`--mcp NAME=URL`, so the τ environment never leaves this machine.

**The rendezvous is unchanged between the lanes**, because it is driven by the MCP bridge rather
than the transport. One detail differs and is worth knowing: on the platform the AG-UI event
reaches τ *before* the sandbox's MCP request crosses the tunnel, so the result is posted before
the handler asks for it. Each episode's channel mailbox is keyed by name and arguments rather
than by arrival order, which is why that works.

Five things about the development lane were established by experiment, not from documentation.
Each is enforced in code, because each one fails in a way that points nowhere near its cause:

- `--mcp tau=<url>` conveys the transport and **no credentials**. That is why the bridge puts its
  token in the URL path instead of an `Authorization` header — one mechanism for both lanes.
- A **connected** `tau` MCP binding *overrides* `--mcp` with the binding's own URL. Binding URLs
  must be `https` or `host.docker.internal`, neither of which reaches this machine from a cloud
  sandbox, so a connected binding turns every episode into a 5-second catalog-discovery timeout.
  The runner refuses to start while one is connected, and prints the disconnect command.
- A task created empty and prompted afterwards races its own sandbox, so the task is created
  *with* τ's first user turn as `--prompt`.
- **A turn is not over when τ thinks it is.** τ hands the floor to its user simulator as soon as
  it holds an assistant message, but a platform *run* may still be streaming, and prompting then is
  refused with `409 Task is already processing` — which τ records as an infrastructure error and
  retries the whole episode. The transport gates the next prompt on `RUN_FINISHED`, exactly as the
  local one gates on Pi's `agent_settled`.
- **CLI startup must stay off the tool-call critical path.** Every `introspection` invocation
  pays ~5.5 s of process startup, the stream subprocess is the only path by which τ learns a tool
  call exists, and the sandbox's MCP daemon gives that parked call only ~30 s. Paying the prompt's
  startup and then the stream's serially ate a third of the budget before τ could see anything —
  observed as `tools/call` spans of 15–30 s and daemon-abandoned calls. The stream for a turn is
  now spawned *before* its `tasks prompt`, so the two startups overlap; the envelope's own
  `run_id` filters out a replay of the previous run, and a fully lost attach race is recovered by
  one reattach under the explicit run id. A clean episode answers every call in ~250–350 ms.

The turn-gate lesson was found the hard way. It presented as an episode "stuck on turn 2": a
`tools/call` parked for 30 s, the sandbox's MCP daemon abandoned it, the agent carried on, and τ
still graded the episode **1.0** on the answers that had already succeeded. A green reward
concealing a broken rendezvous is precisely the unmeasurable-harness failure this repository
exists to avoid, so the bridge now also warns after 25 s (`STALL_WARN_SECONDS`) — the sandbox
gives up well before the bridge's own 300 s ceiling, and without the warning that gap is silent.

With the gate and the overlapped attach in place a graded episode runs clean: every tool call
paired, no 409s, no stalls, and no daemon-abandoned calls.

**The task is retitled and archived at episode end — not deleted.** The first design deleted it,
and that was verified evidence-safe for the *export*: the task 404s while its conversation still
returns full spans, cost and usage. What deletion destroys is presentation — the dashboard shows
the task's `title` as the conversation's summary line, so a deleted task demotes its conversation
to a bare id in the UI. The record survived; its name did not. The transport therefore sets the τ
episode label (`τ²-bench <domain> <task>`) as the task title and archives the row, which keeps
the summary and hides the finished task from the default list. The label carries the lock's
experiment id as its `[exp_<seq>:<name>]` prefix, so platform evidence stays separable across
experiments even when two share a recipe commit. Archiving also settles the task:
the archived row came back `status: cancelled` with `completed_at` stamped at archive time, ~74s
after creation rather than after the 600s idle timeout, so the sandbox is released immediately —
the inactivity timeout remains only as the backstop for episodes that never reach `close()`.
Conversations whose task was deleted before this change keep serving through the CLI but remain
bare-id rows in the UI: a deleted task's row cannot be recreated afterwards.

"The episode finished" is likewise recorded rather than inferred, in both lanes. Each run's
`run_metadata.json` carries an `episodes` list with every simulation's termination, reward, and a
`completed` verdict — true only when τ itself ended the episode normally *and* graded it, the
same definition the fidelity checker asserts post-hoc. The runner prints the verdict per episode
and exits non-zero when a run produced no simulation at all. `run_metadata.json` is written only
after τ's runner returns, so its presence is the run's completion sentinel: a directory holding
`results.json` without it is an interrupted run, not a record. On the platform lane the file
additionally stores the export's own `meta.complete` as
`platform.accounting.<task>.evidence_complete` — `false` means the record is a snapshot of
something that had not settled when it was read.

One rough edge remains, and it is the platform's rather than ours: the first task after `dev`
attaches can come back `Task sandbox is not ready`. τ's own infrastructure retry absorbs it, at
the cost of one episode. The adapter deliberately does not retry on its own — it is a pipe.

### Two launchers for the local transport

Both reach the same Pi RPC protocol, and a run records which one it used in
`run_metadata.json`:

| | `LAUNCHER=pi` (default) | `LAUNCHER=introspection` |
|---|---|---|
| Command | `pi --recipe <dir> …` | `introspection local --work-dir <ws> -- …` |
| Recipe resolved by | path | the `.introspection/` Runtime manifest |
| Validated | once per run | once per run, and again per episode |
| Median time to first event | 1.8s | 7.3s |

`pi` is the default on cost: +5.5s per episode is about 9 minutes on a 97-task sweep, and it
buys a check the repository already performs — `make check` in `.githooks/pre-commit` and in CI,
plus the runner's own `introspection check` before the first episode. Nothing else differs;
`get_state` under both agrees on model, provider, base URL and thinking level.

The CLI path is kept working rather than kept as a comment, because it is how the development
lane will resolve the recipe. `make smoke LAUNCHER=introspection` exercises it.

## Frozen surfaces

`benchmark/benchmark_lock.yaml` holds the values; `contract/constraints.md` holds the rules.
Every value in the lock is asserted before a run starts, because a frozen surface that is only
documented is not frozen:

- the τ²-bench commit, against the vendored checkout's `HEAD`;
- the agent's model and thinking level, against `target-agent/agents/agent.yaml`;
- the recipe's validity, via `introspection check` — an invalid harness must not be graded;
- the τ tool surface, against the live environment;
- the `<policy>` region of `SYSTEM.md`, against both the lock's hash (pre-commit and CI) and
  the live `env.get_policy()` (at episode start).

Reward is computed only by `tau2 evaluate-trajs`, always through `benchmark/scripts/grade.py`
— interactively as `make grade`, by the batch target into the round's `graded/`, and by the
held-out round's muted grading stage into the vault.

## One experiment, one freeze

`results/` carries one level above generations: `results/experiment_<id>/generation_NNN/<run>/`.
The id derives from `benchmark_lock.yaml` — `experiment.seq` (zero-padded to three digits) plus
`experiment.name`, e.g. `001_bm25-sonnet46` — the lock defines the freeze, so the lock names the
experiment — and the runner refuses any `results/` path outside the lock's experiment directory,
before `--overwrite` could delete anything. Changing models, retrieval config, splits or trial
counts is a new experiment (bump `seq`), never a new value under the old one; the name is a
configuration nickname and may repeat — a later `002_bm25-sonnet46` would be a second,
distinct freeze of the same configuration.

Once the lock stops being `PROVISIONAL`, the first run into an experiment writes
`experiment.yaml` beside its generations — a fingerprint of the parsed freeze (lock values plus
split manifest) — and every later run must match it. Values are compared, not file bytes, so a
comment edit never trips the check while a re-decided frozen value refuses the run with
"start a new experiment". `results/experiment_dummy/` was the pre-freeze bring-up bucket
(`PROVISIONAL` runs landed there, unenforced and unreportable); it was removed from the
working tree on 2026-08-13 and lives in git history.

**The experiment numbering was reset on 2026-08-13**, and the sequence has since been
exercised: the pre-reset bring-up freeze that originally held the id `001_bm25-sonnet46`
closed without a graded round and lives only in git history. In the working tree,
`results/experiment_001_bm25-sonnet46/README.md` is a different record — seq 1 froze the
debug experiment and was **voided at H0** the same day on a τ-side user-simulator defect
no harness mutation can reach (tau2-bench#470). Seq 2 re-froze with the poisoned task
excluded, ran the debug experiment to completion, and is revealed; seq 3 is the
powered run (`003_powered-bm25-luna56`, G=5/B=8/T=28 per plan D11), cut PROVISIONAL
over a fresh 76-task pool — no task the seq-2 loop was tuned on, or whose result the
reveal exposed, appears anywhere in it; the full-scale run defers to seq 4. Reused
ids are disambiguated by freeze fingerprints. Two values were
decided the hard way and the decisions carry forward:

- `retrieval_config: bm25` is the deliberate freeze — originally forced by a dead OpenAI key,
  then pinned knowingly, and it stays pinned now that the key is live (2026-08-14): re-deciding
  retrieval is a new experiment, never a quiet upgrade. It is not a comparability
  footnote: on `bm25`, whether one task passes can turn on whether `KB_search` returns a single
  document — one trial queried that document's card by name and did not get it — so no number
  under this freeze is comparable with published τ-Knowledge results, and none claims to be.
- Per-episode reward is a draw: ten runs of one task under one frozen configuration returned
  1.0 six times and 0.0 four times — τ's `--seed` seeds τ's sampling, not Pi's, so the agent is
  not reproducible episode to episode. The retired bring-up freeze (the pre-reset
  `001_bm25-sonnet46`, in git history) froze `num_trials: 4` against this; the
  evaluation protocol instead freezes one trial per task and pools variance across the
  held-out set, treating generation deltas inside the binomial noise band (±17 pp at the
  debug T=8; ±9 pp at the powered T=28; ±7 pp at T=47) as noise (`SIA_EVALUATION_PLAN.md`
  D2, bands per D11).

The model pair settled on 2026-08-15 after three re-decisions in two days
(`SIA_EVALUATION_PLAN.md` D12–D14): **both halves run `openai/gpt-5.6-luna`**. D12
chose luna for inference cost; a platform sandbox defect then 400'd every `openai/*`
model (the sandbox serialized any thinking level as OpenAI's retired
`reasoning.level` parameter), D13 ran `anthropic/claude-haiku-4-5` as the interim
pair — restoring, briefly, the user-sim `temperature: 0.0` determinism knob — and
D14 restored luna when the platform fix shipped. The recipe now uses the modern
`ai:` spelling (validated by the cloud validator and, since CLI 0.27.1, locally)
and deliberately omits `thinking_level`: the lock asserts the absence, and the
sandbox's injected default (medium) is the effective level. The user simulator runs
`reasoning_effort: medium` with no temperature — luna rejects `0.0`, and D2's
task-pooling absorbs the stochasticity. End-to-end verification (2026-08-15): local
smoke and 28-task pilot green (baseline 25%, $0.038/local episode); platform episode
graded **reward 1.0 at $0.0157/episode** with zero seam incidents. The haiku detour
is archived with its own pilot at `results/experiment_003_powered-bm25-haiku45/`.
