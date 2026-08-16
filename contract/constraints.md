# Permission envelope

The rules. `benchmark/benchmark_lock.yaml` holds the values, and every value there is asserted
mechanically before a run — this file exists to say *why*, and to record the boundaries that no
assertion can express.

The project-level invariants live in `CLAUDE.md` and are not restated here. What follows is
specific to how this repository enforces them.

## What the improvement loop may change

Only `target-agent/`, and inside it only the harness:

| Surface | Status | Enforcement |
|---|---|---|
| `SYSTEM.md` `<instructions>` block | mutable | — |
| `SYSTEM.md` `<policy>` block | **frozen** | hash vs lock (pre-commit + CI); region vs live `env.get_policy()` (episode start) |
| `agents/agent.yaml` `model.name`, `model.thinking_level` | **frozen** | `assert_recipe_matches_lock` before every run |
| `agents/agent.yaml` `tools`, `skills`, `subagents` | mutable — `tools:` entries (plus `agent` when `subagents:` is non-empty) double as the D24 Pi-local suppression registry (divergence 6); a declared skill is measurably inert on this seam (`benchmark/probes/2026-08-16-surface-probes/`) | — |
| `package.json` `pi.skills`, `pi.extensions` | mutable — extension tools and no-tool-call hooks are live growth surfaces under D24 | — |
| `package.json` `pi.mcp` | **frozen** | tool catalogue vs live environment before every run |
| `benchmark/`, `contract/`, `.introspection/` | **frozen** | branch protection; the `frozen surfaces` workflow additionally warns (advisory, not blocking) on `benchmark/tau_adapter`, `benchmark/scripts`, the lock, the split manifest, and `contract/` |

The model is frozen even though it lives in a mutable file, because a generation that raised its
own model or thinking level would post a better score without improving the harness — the single
cheapest way to make the whole experiment meaningless.

## The monorepo cannot express the permission split

A GitHub installation token cannot be scoped to a sub-path. Granting the agent
`contents: write` on this repository so it can propose changes to its own Recipe therefore also
grants it the benchmark adapter, the lock, and the split manifest.

So the boundary is **detected and blocked at merge**, not made impossible:

1. branch protection with required review — the agent opens pull requests and cannot merge;
2. the `frozen surfaces` workflow — the policy-region hash gate fails the check, and any diff
   touching `benchmark/` or `contract/` is surfaced as a warning on the pull request;
3. the runtime assertions — a frozen value that changed anyway stops the next run rather than
   silently grading against something new.

The durable fix is to split `target-agent/` into its own repository, which the one-way path
dependency keeps available as a `git subtree split`. Until then, treat every pull request that
touches the benchmark lane as a human decision.

## Why the frozen policy lives inside a mutable file

τ's domain policy has to reach the agent as a system prompt, and a Recipe's system prompt can
only come from committed files — Pi ignores `--append-system-prompt` under `--recipe`. The three
options were:

- **a region of `SYSTEM.md`** (chosen): in the commit, so runtime↔commit lineage is exact; never
  compacted, because a system prompt is not part of the conversation; identical placement to
  stock τ, which keeps the graded surface faithful to the benchmark's own design.
- materialising a temp Recipe per run: works locally and nowhere else. `introspection dev` serves
  the git work-tree and a deployed runtime serves an immutable commit, so neither leaves an
  injection point — and it severs lineage.
- folding the policy into the first user turn: survives every lane, but puts ~1.5k tokens of
  frozen text where Pi's auto-compaction can summarise it away mid-episode. Banking episodes read
  many of 700 documents, so context will fill. That is a silent, episode-length-correlated
  corruption of the objective.

Diagnostic runs against a non-locked domain are the one case that materialises a Recipe copy, and
their results are marked unreportable for exactly that reason.

## Why the adapter never repairs the agent

τ rejects an assistant message that carries both text and tool calls. Pi narrates freely, so this
happens often. The adapter forwards such messages unaltered.

The reason is not fidelity for its own sake. Every place the adapter silently corrects the agent
is a place the harness cannot be measured, and therefore cannot be improved. Dropping narration
would hide a real, harness-owned, pull-request-fixable defect from the objective — which is
precisely the failure mode of "a defect that changes grades while leaving the evaluator
untouched". The platform's own guidance names this class as the flagship self-improvement
capability: ambiguous instructions, missing skills, misleading tool descriptions.

G0 is nevertheless *told* not to mix them, in the mutable region, because τ's own stock agent is
told the same thing and the baseline needs to clear its floor. Withholding the instruction to
manufacture a discoverable bug would be planting the answer in reverse.

Consistently applied, the same rule settles the smaller cases: Pi `thinking` blocks are dropped
because τ has nowhere to put them (stock agents lose them too), and Pi provenance goes into
`raw_data`, which τ ignores when grading.

## Known adapter divergences from a stock τ run

Recorded rather than hidden. Each is constant across generations, so none can bias a
cross-generation comparison. Comparability with published τ numbers was dropped with the bm25
freeze and is no longer a goal; what remains bounded is cross-lane comparability, measured on
demand by `make fidelity` (`SIA_EVALUATION_PLAN.md` D4).

1. **Tool names the model sees are mangled.** Recipes rewrites them to
   `mcp_<server>_<tool>_<sha256[:10]>`. The trajectory carries τ's canonical names — the reverse
   map is built forwards and verified byte-for-byte against the JS implementation — but the
   *prompt* the model reads does not.
2. **τ's canned opening greeting is recorded but not replayed** into the agent session, which
   starts empty. A stock agent's message list contains it.
3. **The agent's model is set by the Recipe, not `--agent-llm`.** τ requires the flag, so the
   lock records it as declared-and-unused and keeps it equal to the real value.
4. **Platform-lane divergences** (`TRANSPORT=platform` only, so they bound cross-lane comparison
   rather than cross-generation comparison):
   - **Narration and tool calls are reassembled into the one message Pi produced.** Pi emits a
     single assistant message that can carry narration *and* a tool call; the platform streams
     the parts as distinct AG-UI event groups. Forwarding that split hands τ's floor to the
     user simulator on the narration alone while the sandbox sits parked on the bridge — the
     first A.0b run observed exactly that (3 of 12 platform episodes at τ's 600 s ceiling with
     5–6 rendezvous stalls each; verdict preserved in git history:
     `git show 984c598^:results/experiment_bm25-sonnet46/generation_000/gates/a0b.json`).
     The transport therefore buffers a run's narration and attaches it to that run's first
     tool call, flushing text-only runs at RUN_FINISHED — *reconstructing* the shape the host
     produced (the platform's own GenAI spans record one message with
     `[thinking, text, tool_call]`), never inventing one, while the call still surfaces the
     instant it exists. Adopted by operator decision at the A.0b gate, 2026-08-13. Both lanes
     now present the same mixed message, and `enforce_communication_protocol` governs them
     identically.
   - **Reasoning is streamed and dropped.** `REASONING_*` events are discarded for the same reason
     the local lane drops Pi's `thinking` blocks: τ's `AssistantMessage` has nowhere to put them.
   - **Per-message cost and usage are absent**, because AG-UI events carry none. τ's own cost
     metric comes out `nan`; the real numbers live on the conversation record and are copied into
     `run_metadata.json`'s `platform.accounting`.
   - **The system prompt differs by one line.** Pi appends `Current working directory: /workspace`
     after `</policy>` in the sandbox, against the recipe path locally. Outside the frozen region,
     so the hash gate is unaffected.
   - **The rendezvous stall class is fixed and self-naming.** Serial CLI startup (~5.5 s per
     `introspection` invocation, paid for the prompt and then the stream) burned a third of
     the sandbox MCP daemon's ~30 s per-request budget before τ could see a call, so parked
     calls could be abandoned while the episode still graded on answers already landed. The
     stream attach now overlaps the prompt (run-id filtering plus a single reattach make the
     early attach safe); a clean episode answers every call in ~250–350 ms, and
     `STALL_WARN_SECONDS` names any recurrence. A platform score is never a substitute for a
     local one — the lanes serve different roles by design: platform episodes supply
     improvement evidence, local episodes the held-out measurement (`SIA_EVALUATION_PLAN.md`
     D1).

5. **The agent is not reproducible from τ's `--seed`.** The seed reaches τ's own sampling; Pi owns
   the agent's, and τ's `llm_args_agent` never reach it. This is not a divergence the fidelity
   instrument can close, and it is not constant across episodes — it is the reason a single
   episode's reward is a draw (measured: six runs of one task returned 1.0 five times and 0.0
   once; ten runs returned 1.0 six times and 0.0 four times). The remedy changed with the
   evaluation protocol (2026-08-13): repeated trials are no longer the instrument. Generations
   are compared on a fixed held-out set at one trial per task, pooling variance across tasks
   instead of within one — binomial noise ≈ ±17 pp at the debug T=8, ≈ ±9 pp at the
   powered T=28, ≈ ±7 pp at T=47,
   stated wherever the curve renders;
   `pass^k` is retired for generations; the endpoint reliability study (H_0 and H_G ×
   extra trials, after reveal) is the named upgrade path, conditional since D11
   (`SIA_EVALUATION_PLAN.md` D2, D11).
6. **Pi-local tool calls are suppressed from τ (D24, 2026-08-16 — user-directed, decided
   between experiments, never mid-freeze).** A tool call whose name is in the recipe's
   Pi-local registry — `agents/agent.yaml` `tools:` entries, plus `agent` when `subagents:`
   is non-empty (`tau_adapter/pi_local.py`) — is executed by Pi and never forwarded to τ: it
   costs no τ step and none of the ten `max_errors`. Before D24 every such call reached τ as
   an invalid call (measured, `results/experiment_006_fixedb-bm25-luna56/generation_000/
   seam_probe/`), which made extension tools and sub-agents unusable growth surfaces; three
   closures named that as the live hypothesis for why the loop failed. Semantics and bounds:
   suppression is registry-membership only, never a heuristic — a name neither τ nor Pi owns
   still forwards as the graded invalid call it is; it is a **turn-level pump**, so a
   fully-suppressed turn holds its narration for the next forwardable turn (the same
   reassembly rule the platform lane applies) and can never hand τ an empty assistant
   message; a runaway guard (32 consecutive fully-suppressed turns per τ step) resumes
   unfiltered forwarding so a pathological harness pays its own graded cost; τ's episode
   timeout still bounds wall-clock, which Pi-local work continues to spend. The
   measurability objection this file raises against adapter helpfulness ("every place the
   adapter silently corrects the agent…") is answered by construction, not waived: the
   unmeasurable case is *silent* correction, and this is declared, deterministic, gated
   (A.0a suppression tests + the fidelity `pi_local_leaks` invariant), and fully evidenced —
   every consumed turn's tool names land in the trajectory's
   `raw_data.pi_tool_names`, the suppressed subset in `raw_data.pi_suppressed_tool_names`,
   the manifest derives a per-episode `pi_local_calls`, and `run_metadata.json` records the
   registry the run resolved. Nothing is hidden from diagnosis — only from grading, which
   is the point: τ budgets meter benchmark-environment interactions, and Pi-local execution
   is harness-internal cognition, the same category as model reasoning. Consequence stated
   with the decision: results produced under D24 are not comparable to seq 4–6.

## Platform-lane concurrency

Both lanes execute `max_concurrency` through one mechanism (2026-08-13): every episode
opens its own bridge channel — its own mailbox — and what differs per lane is only how a
request finds it. Locally, episode identity is the URL: each Pi subprocess is handed its
channel's `/mcp/<token>` path through its environment. On the development lane, every
sandbox reaches the bridge through the single URL its `dev` attachment was handed — per-
episode URLs are impossible there (`--mcp` carries one URL; per-task MCP configuration
does not exist; `tasks create --metadata` is application metadata, not a platform switch)
— so episode identity rides the tunnel instead: **the platform stamps every forwarded MCP
request with `x-introspection-session-id`, the sandbox session it came from, and `tasks
get` exposes the same value as `metadata.agent_session_id`** (both observed live
2026-08-13 with the bridge's `TAU_BRIDGE_TRACE_HEADERS=1` instrument). The platform
transport binds its episode's channel to that session id — opportunistically from the
`tasks create` response, else by polling `tasks get` beside the stream — and the bridge
routes each tunneled call by its session header, falling back to the path token. An
unknown session waits a short grace for the binding poll rather than losing the race; a
session that never binds is refused after the grace — visible as tool errors, never as
crossing; a conflicting bind fails the episode loudly rather than stealing another's
calls.

Two hard-won facts bound this design and are worth not relearning:

- **The platform accepts ONE live dev attachment per Runtime.** A second named
  attachment (`dev --as`) against the same Runtime was refused server-side —
  `dev_slot_conflict: this Runtime is already connected by 'tau-w00-021d'` — retrying
  ~70s before timing out (observed 2026-08-13; no plugin doc states this cardinality,
  and the `--as` help's "two developers can share one Runtime" describes named routing,
  not attachment multiplicity from one branch and machine). An attachment-*pool* design
  built on N attachments was landed, live-refuted the same day, and retired; git history
  keeps it. One attachment is also all that concurrency needs, because of the session
  header above.
- The attachment keeps a **nonce'd `--as` name** so two concurrent runs on one machine
  cannot claim each other's dev target, and a misnamed attachment is refused at startup —
  task routing fails closed on the exact name.

`max_concurrency` itself is an operational knob, not a frozen budget (re-decided
2026-08-13): parallelism moves wall-clock, never what the agent can do inside an episode.
The lock's value is the recorded default, any run may override it with
`--max-concurrency` (1 = serial), and the effective value is recorded in
`run_metadata.json`. The practical ceilings are provider rate limits (2N Anthropic
streams; throttling surfaces as infra retries) and heavy-tailed sandbox provisioning
latency under concurrent starts (next section).

### The seam's own thread ceiling (found 2026-08-15; removed for good post-seq-5 via the call-site executor)

For a while there was a third ceiling, and it was invisible because nothing declared it.
Every `tools/call` parks **two** threads in sequence — `channel_for_request` (up to
`UNBOUND_SESSION_GRACE_SECONDS`) and then `channel.wait` (up to `RESULT_WAIT_SECONDS`) —
and until this date both drew from **asyncio's default executor**, sized
`min(32, os.cpu_count() + 4)`. On the 12-core host that is 16 threads for the whole
run-scoped bridge, i.e. a hidden ceiling near **8 concurrent episodes** that belonged to
the machine rather than to any recorded value. Past it, new MCP calls queue behind parked
ones and surface as rendezvous stalls — indistinguishable, from the outside, from a hung
agent.

Observed at `--max-concurrency 8` on a 24-episode batch round: one 300s stall
(`task_028` trial 0; τ retried and it succeeded). The same round's local-lane sibling ran
84 episodes 10-wide with zero incidents, which is consistent rather than contradictory — a
sandbox round-trip parks a bridge thread for far longer than a local call does, so the
platform lane reaches the ceiling first.

The first fix (`585ad45`) had `tool_bridge.py` build the serving loop itself and install a
dedicated executor via `set_default_executor`. It was **reverted the same day**
(`17fa493`) when the hand-built loop coincided with the disconnect regression described in
the next section, and seq 5 ran to completion on uvicorn's own path with the ceiling live
but non-binding (platform batches at 4-wide park 8 threads worst-case against 16).

The **fix-forward landed after seq 5 closed**: `ToolBridge._in_bridge_pool` replaces the
two `asyncio.to_thread` call sites with CPython's own three `to_thread` lines, the
executor named instead of `None` — identical contextvar and error semantics, zero loop
surgery, the serving loop stays uvicorn's to own. The pool is created in `start()`, sized
from the round's concurrency (`BRIDGE_THREADS_PER_EPISODE`, floor `MIN_BRIDGE_WORKERS`),
shut down in `stop()` (wait=False — teardown must not block behind a parked handler), and
recorded per round as `bridge_executor_workers`, which by contract always reports the pool
in use, never an intent. `_serve` survives only as the bisect arm for the disconnect
question.

Note what this fix does **not** explain: `batch_02`/`batch_03` counted `mcp upstream
timed out` markers at 4-wide, where the default executor could not saturate. The 2026-08-16
investigation established the actual mechanism, and it is neither starvation nor slow
rendezvous — see § The timeout class, diagnosed, below.

The lesson generalises past this bug: a seam limit that no value names will be rediscovered
as a mystery. If concurrency is raised again, the binding constraints are the two above —
provider streams and provisioning latency — and they should stay that way.

### The disconnect regression and the sandbox-failure counters (2026-08-15)

While the hand-built loop was live, platform episodes began failing with
`local MCP 'tau' is disconnected` — the sandbox's MCP daemon answering the tool call
itself because it believed the tunnel to the bridge was down. The failure is invisible to
every bridge-side detector by construction: the call never arrives, τ records no turn, the
refusal counters count nothing, `results.json` carries no trace, and the episode grades as
an ordinary agent failure. It was found by a human reading a platform conversation while
the round printed `incidents none`.

The evidence and its honest weight: 0/10 episodes with disconnects on the commit before
the loop change vs 3/10 after (Fisher's exact p ≈ 0.105 — suggestive, not significant);
the reverted probe (`generation_000/seam_probe_reverted`, n=3 on a lighter task) had ~25%
power against the runtime-image hypothesis and none against a time-varying platform
transient — the same afternoon's local H0 round logged 24 provider transport errors, so
environmental instability is a live confound. A source-level comparison of `_serve`
against the installed uvicorn 0.52.1 run path (Python 3.12, no uvloop) found **no
mechanism**: at `--max-concurrency 4` the executor swap was never even exercised, and the
loop-factory/signal/teardown deltas are inert during serving. **Causality is open.** The
revert is justified by cost asymmetry alone — the ceiling degrades throughput, the
regression degrades evidence. The decisive discriminator, deliberately kept one line away:
re-enable `_serve` on a dirty tree, run ~10 platform episodes on heavy non-partition
tasks, and read the counters — disconnects returning implicates the loop; a clean run
implicates the transient.

What the incident left behind mechanically: `run.py::_sandbox_tool_failures` counts, from
the already-fetched conversation payload, the failures only the platform conversation can
show — `sandbox_seam_disconnects` (daemon could not reach the bridge; tools denied),
`sandbox_seam_timeouts` (bridge reached but too slow; pre-existing, τ may have retried
through it), and `sandbox_seam_unclassified` (a daemon-reported error matching neither
marker — the drift net, so an upstream rewording degrades to a loud unknown instead of a
silent zero). Counters land per-episode on the manifest and print as a `⚠ sandbox` line;
episodes whose conversation could not be fetched print as `⚠ seam-blind`, because
unverified must never read as clean. The markers are substring matches over provider
text: over-counting via the agent quoting an error back is accepted, and a round that
flags uniformly after a prompt-touching mutation deserves one human read before belief.

How seq 5 resolved the question in practice: all 72 post-revert batch episodes plus every
canary ran with **zero disconnects**, so the reverted path is validated under load, while
causality for the original 3/10 remains formally open (the B′ arm — `_serve` — is retained
if the record ever needs settling). The counters earned their keep in the same rounds by
surfacing the timeout class instead (6 and 4 per 24-episode round) with the attribution
data to show it is daemon patience, not the executor.

### The timeout class, diagnosed (2026-08-16)

Seq 5's five `mcp upstream timed out` episodes (`batch_02`: task_026 t0, task_028 t0,
task_065 t0; `batch_03`: task_028 t1, task_070 t2) were investigated span-by-span against
the platform conversations, and the mechanism is **in-flight POST loss on transient
network blips**, not anything on τ's or the bridge's side:

- Every failed `execute_tool` span lasted **exactly 30.1s** — the sandbox daemon enforces
  a hard 30s per-call timeout, then answers the agent itself ("remote outcome is unknown;
  do not retry automatically", which is accurate).
- The bridge never saw those calls: zero stall warnings (25s threshold — it would have
  fired), zero refusals, at a concurrency where the executor could not queue. The POST
  died between daemon and bridge.
- The three `batch_02` failures started within one 15-second window (03:22:31–46Z), one
  per concurrently-running episode — a single interruption killing whatever POST was in
  flight. `batch_03`'s two were separate blips at 05:15:52Z and 05:26:35Z.
- **τ received and executed the killed calls anyway.** The tool-call travels to τ on the
  event stream (a separate, reattach-capable connection — the 83–103 reattaches per round
  are it recovering from the same churn), so τ ran the tool and posted a result nobody
  consumed. In task_028 t0 the agent retried and τ executed `transfer_to_human_agents`
  three times while the agent believed the first failed — **agent and grader histories
  diverge**, the class `fidelity/seam_integrity.py`'s count-drift finding now catches
  (bridge-served calls < τ tool messages).
- Two consequences worth naming: a retried identical call can consume the earlier call's
  stale mailbox result (benign for idempotent reads, real for writes); and the same
  evening's weather hit the local lane too — the H2 held-out round's console shows Pi
  provider connection errors 21:10–21:54 local, 7 tasks through all 4 τ attempts before
  the resume pass recovered them. Batch tunnel blips (20:22, 22:15, 22:26 local), local
  provider errors, user-sim empty completions: one instability window, three surfaces,
  common node the local machine's connectivity.
- Grade impact, bounded by the record: all five affected episodes sat on tasks scoring
  0.0 on every trial of every round regardless (task_065's single 1.0 was an unaffected
  trial), so the closure's batch curve stands; the caveat is per-episode and the counters
  carry it.

Nothing local fixes lost POSTs. What exists now is detection (the counters, the call log,
the integrity audit, `zero_bridge_calls`); the upstream avenue, if the class grows, is an
Introspection report — in-flight MCP calls through the dev tunnel are not recovered on
reconnect the way the event stream is, and an idempotent retry keyed by request id could
close the asymmetry.

The lesson is now mechanical in three more places. `make gate_seam` runs a platform canary
judged on these counters and records the verdict under the experiment's `gates/`;
`run.py` **refuses to start a batch round** when that verdict is missing, FAILED, or older
than the last change under `benchmark/tau_adapter` — the platform failure domain gets a
blocking gate the way A.0a covers the local one. Every episode that ends without a single
tool call reaching the bridge counts as `zero_bridge_calls` (the dead-tunnel signature
that once burned a 16-episode round). And `fidelity/seam_integrity.py` audits a round's
`bridge_calls.jsonl` against τ's record — count drift, unjoined calls, daemon-patience
parks — so payload-level seam failures stop grading as agent behaviour by default.
Provider weather on frozen surfaces is likewise named now: τ's infra placeholders are
classified per round (`infra_failure_classes` in run_metadata: user-sim empty completions,
provider connection errors), and `make weather` probes the user-sim surface directly for
cents before a round is spent.

### The sandbox-quota misdiagnosis (corrected 2026-08-14)

What was believed (from one incident at the 3.5c minitest): the org runs ~2 sandboxes
concurrently and a third queues — a plan-derived admission cap. The 2026-08-14
investigation read the org's full task history (200 task rows, 2026-08-12 →
2026-08-14T23:00Z, via `tasks list`) and refuted it:

- **Three sandboxes ran concurrently, twice**, on 2026-08-13 (02:05:31Z and 02:09:06Z UTC)
  — real graded episodes, all completed. No cap of 2 can produce that, and the vendor
  confirms no such plan limitation exists.
- The delays are **provisioning latency, not admission queueing**: created→`started_at`
  gaps run 40–90s at zero concurrency and 100–650s under concurrent starts (the two
  minitest bursts: 126/371/479s and 75/168/457/265s). The famous "2m49s queue wait"
  (168s, task created 2026-08-14T01:52:55Z) was mid-distribution for its burst — its
  sibling took 457s — and it was the *second*-created task of the burst, not the third.
- **No task was ever observed in `queued` status** (the platform's org-admission state).
  The one anomaly sat in `scheduled` (provisioning) — wedged 2h+ with `updated_at` frozen
  at creation, and uncancellable (`tasks cancel` → 409 "Run is not cancellable"): task
  `01a00219-068b-702f-bfff-32b324d5285e`, left in place as upstream bug evidence.
- Separately, 2026-08-14 21:06–22:10Z, a **platform ingress outage** ("Failed to reach
  Restate ingress: All connection attempts failed") failed 48 consecutive tasks
  pre-sandbox at every concurrency, serial preflights included; it recovered by ~22:53Z.
  An outage wears the quota theory as a disguise — read `metadata.error` on the task rows
  before inferring capacity.

Operational consequence: the binding constraint for wide platform rounds is the
provisioning tail against the transport's `QUEUE_WAIT_CEILING_SECONDS` (240s, sized to
fit inside τ's frozen 300s per-turn ceiling) — a start slower than the budget reads as
stream death and re-triggers exactly the τ-retry churn the budget was built to absorb.
`make batch` runs `--max-concurrency 4` (raised from 2 on 2026-08-15 after the 4-wide
validation below) — not because any quota moved, but because the contention the pin
guarded against did not materialise at 4. Going wider than the provisioning tail allows
needs staggered episode starts, not a larger budget (the τ ceiling is frozen) — built
2026-08-14 as the transport's **start gate**: a run-scoped bound (default 2,
`--max-concurrent-starts`, 0 disables, recorded in `run_metadata.json`) on episodes
sitting between `tasks create` and their first streamed event, so any number of episodes
run while at most K sandboxes provision and boot at once. The gate is advisory by
design — a permit that cannot be had within its ceiling lets the episode proceed ungated
and counts a `start_gate_timeouts` incident; waits land in `start_gate_wait_seconds`.

Two facts from the 2026-08-15 4-wide validation run (4 unused-pool tasks,
`--max-concurrency 4`, gate at its default 2 —
`results/experiment_003_powered-bm25-luna56/generation_000/concurrency_smoke`):

- **Four sandboxes provisioned and ran concurrently, cleanly.** All four tasks were
  created within 1.6s, their created→started windows (35–65s each) fully overlap, and
  the run finished in 78.9s with zero stall warnings, zero 409s, zero stream failures,
  zero queue waits. Direct confirmation that no >2-sandbox limitation exists, at
  provisioning latencies inside the healthy band.
- **The gate releases earlier than its design comment claims.** Permits freed ~1s after
  `tasks create` (total `start_gate_wait_seconds` 2 across the run) while boots took
  35s+ — the task's event stream yields its first envelope at attach, before the sandbox
  is provisioned, so "first streamed event" is not "runtime booted and streaming". As
  implemented the gate bounds creation bursts and stream spin-up, not concurrent
  provisioning. Harmless while provisioning behaves; if the 100–650s tail returns and the
  gate is needed as real insurance, the release trigger must move to an envelope that
  proves the run actually started (or to `tasks get` showing `started_at`).

## Why `pi` launches the recipe locally rather than `introspection local`

The standing guardrail is that the Introspection CLI is the only interface for operating the
platform. Launching a local agent process is not a platform operation, and the choice was made on
measurement rather than preference.

`introspection local --agent <a> -- --mode rpc` was verified to work: it passes everything after
`--` to Pi unchanged, keeps its own banner on stderr so stdout stays pure JSONL, and yields a
`get_state` identical to direct `pi` on model, provider, base URL and thinking level — differing
only in the session id. It additionally validates the recipe and resolves it through the
`.introspection/` Runtime manifest, which is how the development lane will resolve it.

It costs +5.5s per episode (median 7.3s to first event against 1.8s), because it starts node, then
a platform binary, then probes `pi --help` before launching. That is ~9 minutes on a 97-task sweep.
What it buys — knowing the recipe is valid — the
repository already has three other ways: the commit hook, CI, and one `introspection check` per run
inside the runner, added for exactly this reason so the default path cannot grade an invalid
harness.

So `pi` is the default and `LAUNCHER=introspection` stays exercised rather than merely documented.
Each run records which launcher produced it in `run_metadata.json`, because both produce
identically-shaped results and a score has to carry its configuration.

## Hard-won configuration corrections

Found while implementing, each one load-bearing — a plausible-looking configuration that
would have silently frozen the wrong thing:

- `--max-steps-seconds` looks like the per-episode wallclock bound, but it only configures
  audio-native runs, where it is divided by the tick duration. In text mode it has no effect. The
  real per-episode wallclock bound is `TextRunConfig.timeout`, which the lock freezes instead.
- `--task-set-name base` conflates two flags. `base` is a task *split*; the task set defaults to
  the domain's own. The lock records both separately.
- `enforce_communication_protocol` belongs on the frozen list: it decides whether a mixed
  message ends an episode at all, so flipping it moves scores with no harness change. Left at
  τ's default of `false`, which is what stock runs use.
- τ sets litellm's `num_retries` but never a request `timeout`, so a stalled provider response
  has no bound — one user-simulator call blocked for 601 s in the first banking run. The lock
  freezes `frozen.user_llm_args.timeout`, because it changes wall-clock per generation by an
  order of magnitude.
- `tau2 evaluate-trajs` cannot grade `banking_knowledge` offline. It rebuilds the environment
  through `DEFAULT_RETRIEVAL_VARIANT` (`alltools`, OpenAI embeddings) rather than the run's own
  recorded `retrieval_config`, and offers no flag to override it — so the only sanctioned path to
  a reward requires an embeddings key even for a `reward_basis: ['DB']` task. Worth reporting
  upstream. `benchmark/scripts/grade.py` — the only path `make grade` takes — closes the gap as
  a fidelity fix rather than a workaround: it injects the run's recorded `retrieval_config` into
  the evaluator's environment rebuild (refusing when it disagrees with the lock) and then calls
  τ's own `evaluate_trajectories`. No reward is computed anywhere but the evaluator, which was
  otherwise grading against a different tool surface than the run used.
- The `openai_embeddings` retrieval config originally intended was unavailable at bring-up
  (the OpenAI key then returned `429 billing_not_active`; it is live since 2026-08-14 — which
  does **not** reopen this freeze), so bring-up used the offline `bm25`
  fallback. **Resolved 2026-08-12: `bm25` is the deliberate freeze**, pinned knowingly rather
  than provisionally. The consequence is accepted, not
  deferred: `bm25` changes both the tool set and the policy text, so no number produced under
  this freeze is comparable with published τ-Knowledge results, and no comparability claim is
  made anywhere in this experiment's record. Cross-generation comparison is unaffected — the
  backend is constant by construction — and retrieval *usage* (query formulation, k, iteration,
  stopping) remains mutable harness territory. Re-deciding this value means a new experiment,
  never a new value under the old id.
- An experiment's id is *derived*, never chosen: `experiment.seq` (zero-padded to three
  digits) + `experiment.name`, giving e.g. `002_bm25-sonnet46` and the results directory
  `results/experiment_002_bm25-sonnet46/`. The sequence exists because a descriptive name can
  legitimately repeat — a second freeze of the same configuration is a different experiment
  under its own seq — so the name alone cannot be the identity. Re-deciding any frozen value
  bumps `seq`; reused ids across the 2026-08-13 numbering reset are disambiguated
  mechanically by freeze fingerprints (the reset's history: README § One experiment, one
  freeze). Platform task titles from before the reset keep their old `[exp:bm25-sonnet46]`
  suffix — records of what the platform actually displayed, never re-labeled evidence.
