# Concurrency Design — episode channels across both lanes

The record of how episode concurrency was designed, live-refuted, and finally solved
(all on 2026-08-13). It reads **chronologically** — intake adjudication (Phase 3.5),
the attachment pool and its refutation (3.5b), the session-keyed mechanism (3.5c) —
so earlier sections state beliefs that later evidence overturned; that is the point
of keeping them. **The end state is the Final chapter**; the enforced summary lives
in `contract/constraints.md § Platform-lane concurrency`, and the sizing/operational
doctrine in `SIA_EVALUATION_PLAN.md` (D7, D10).

---

## Phase 3.5 intake design note (historical)

Scope guard at the time: machinery only, frozen `max_concurrency` VALUE stays 1
(later unfrozen — see the Final chapter).

## The problem, precisely

Today's bridge has ONE `_Mailbox` per run, slots keyed `(tool_name, canonicalised
args)` with **no episode dimension**; `reset_for_episode` replaces it wholesale at
every episode start (`tool_bridge.py:263–277`), and `pi_agent.py:80–95` documents the
contract as "Safe at max_concurrency 1". At N≥2, two episodes calling the same tool
with identical arguments would cross results silently — graded contamination the
fidelity invariants might not even catch (both episodes still see *a* result). τ is
already parallel (`ThreadPoolExecutor(max_workers=config.max_concurrency)`,
vendored `runner/batch.py:810`), so the serial constraint is entirely ours.

## Adjudication: mechanism A, implemented on the single run-scoped server

**Chosen: A — per-episode URL channels.** `bridge.open_channel()` mints a channel
(own mailbox, own `/mcp/<episode-token>` path); each local episode's Pi subprocess
receives its channel URL via `TAU_MCP_URL` (the recipe already expands
`${TAU_MCP_URL}` from env — zero recipe changes).

**Rejected: B — MCP-session-keyed channels over the single run URL.** The SDK half
of B actually grounds: the installed MCP SDK 2.0.0 hands every handler a
connection-scoped `ctx.session` and the live HTTP request. But B's fatal half is the
**episode↔session binding**: with N Pi processes connecting to one URL, the bridge
sees N anonymous sessions and has no way to determine which episode each belongs to
— it would need a first-call handshake protocol, which is more machinery than A, for
the benefit of serving a platform lane that stays pinned at 1 regardless (one
`dev --mcp` URL per run). Not built speculatively.

**Implementation shape (probed live, not assumed).** A scratchpad probe against the
installed SDK proved: `streamable_http_app(streamable_http_path="/mcp/{token}")`
serves a parameterized Starlette route; two concurrent MCP client sessions on
distinct token URLs each resolve their own token inside `on_call_tool` via
`ctx.request.path_params` (the streamable-HTTP transport attaches the Starlette
`Request` to every inbound message — verified in SDK source,
`runner._make_context` ← `ServerMessageMetadata.request_context`). So:

- ONE uvicorn server, ONE `LowLevelServer`, ONE session manager, ONE port — as today.
- The route becomes `/mcp/{token}`; the bridge keeps a lock-guarded
  `token → EpisodeChannel` registry. Handlers resolve the channel per request;
  an unknown token is refused loudly (it is also still the credential: unguessable,
  loopback-bound, and nothing meaningful is served without a live channel).
- `EpisodeChannel` = token + `_Mailbox` + `on_stall` sink + `url` + `env()` +
  `post_result()` + `close()`. `_Mailbox` itself is unchanged.
- `PiRecipeAgent` binds to a **channel**, not the bridge: `get_init_state` opens it
  exactly where `reset_for_episode` sits today; `stop()` closes it. A τ retry builds
  a new agent+transport → new channel; stale results from the dead attempt sit in
  the dead channel's mailbox, unreachable **by construction** (stronger than
  today's wholesale reset).
- **Platform lane = the same mechanism at a pinned token.** `dev --mcp` is handed
  one URL before the first episode, so platform episodes open the channel at the
  run's pinned token with replace semantics — byte-for-byte today's
  `reset_for_episode` behavior. Concurrency 1 is enforced by a runner refusal (see
  increment 4), not by a separate code path.
- Degenerate case: at N=1 the local lane simply has at most one live channel.
  Existing suite must pass unchanged.

## What each increment lands (mirrors the plan checklist)

1. **Bridge episode channels.** Result-crossing minitest FIRST: two concurrent
   channels, same tool, identical args — results must not cross. Then per-channel
   stall attribution, stale-result isolation across a channel's episodes (τ-retry
   shape), channel lifecycle (unknown/closed token refused; pinned replace),
   degenerate case (existing suite green, single-channel behavior unchanged).
2. **run.py thread-safety.** `episode_transports` → lock-guarded registry;
   `launch_argv` computed once (it is identical for every episode); channel opening
   under the bridge lock; incident aggregation and `original_titles` verified
   post-run-only (they are). Factory-from-threads test.
3. **Local lane end-to-end.** Channel URL via each transport's env; per-episode
   process-group teardown re-verified under concurrency; live minitest = mock round
   (10 tasks) at `--max-concurrency 2–3` in diagnostic mode + the same round serial,
   asserting fidelity per-episode invariants (calls answered, no orphan results,
   mapped names, normal termination, τ-graded), zero rendezvous incidents, distinct
   per-episode `session_ref`s, and reporting measured wall-clock for both.
   A `--max-concurrency` runner flag is **diagnostic-mode only**: locked mode always
   reads the lock (refused otherwise) — that is how the machinery lands without a
   frozen-value change.
4. **Platform lane, investigation-complete.** The documentation pass
   (session artifact `RESEARCH_FINDINGS.md`, ephemeral, not retained; verified against the
   installed CLI) found a **native affordance**: `introspection dev --as <NAME>`
   names an attachment, N attachments can serve one Runtime concurrently, and
   `INTROSPECTION_DEV_TARGET=<NAME>` routes a task to a specific attachment,
   fail-closed. Per-task MCP config does NOT exist (`--metadata` is explicitly not
   a platform switch), and one attachment carries one `tau` URL — so platform N>1
   means N dev attachments, each `--mcp tau=<own channel URL>`.
   **Decision: pin the platform lane at 1 this phase, with the refusal citing the
   affordance as the sanctioned upgrade path.** Grounds: (a) platform N>1 cannot be
   live-exercised inside this phase's rules — diagnostic mode is local-lane-only and
   locked platform spend runs at the frozen value 1 — so N-attachment machinery
   would land untested, against the written-from-what-ran doctrine; (b) the payoff
   is in the local lane (held-out ≈ 85% of wall-clock per D7); (c) smallest
   mechanism that provably solves the problem. The seq-3 freeze decides whether to
   build the N-attachment path, with the recipe already in hand.
5. **Truth-pass.** Every "single-episode"/"run-scoped"/"max_concurrency" sentence
   the mechanism falsifies: `bridge.path` docstring, `pi_agent.py:80–95` comment,
   `run.py` bridge/sweep comments, README §How the seam works,
   `contract/constraints.md`, the lock's `max_concurrency` comment block (value
   untouched).
6. **Close.** Full suite green (baseline 208), ruff+format, `make check`,
   `make gate_a0a` PASS recorded, both mock rounds' numbers stated, plan boxes
   dated.

## Live-spend plan (go/no-go with the user)

Mock-domain diagnostic rounds only, local lane: one serial 10-task round + one
concurrent round at N=2–3. Estimate ≈ $1–3 total (mock episodes are short; measured
locked-domain episodes ran $0.10–0.51). No locked-domain live check planned; if one
becomes necessary it gets its own explicit go/no-go (≤ $2 target).

## Premortem — "it shipped and broke the experiment; why?"

Category I — cross-episode information crossing (the user-named invariant: no
conversation/task information may mix):

- **Result crossing** between concurrent episodes, same tool+args → channels remove
  the shared keyspace; the first test in increment 1 exists to prove exactly this.
- **Stale result answers a retry** (τ re-runs the same task with identical args
  after an infrastructure error) → new attempt = new channel; the stale result is
  unreachable. Test: stale-result isolation.
- **Stall/incident mis-attribution** → `on_stall` is bound per channel at open to
  that episode's transport sink; manifest rows key on per-transport `session_ref`
  (unchanged). τ-retry orphans stay attributable via the existing
  `unattributed_incidents` path — verified to be post-run single-threaded.
- **Manifest/evidence join integrity at N** → the minitest asserts distinct
  `session_ref` per episode row and (platform, later) task-id uniqueness; the join
  logic itself never keys on ordering, verified in `manifest.py`.
- **Platform lane silently running N>1** on one dev URL (all episodes one token →
  guaranteed crossing) → config-time refusal in run.py before the bridge starts,
  tested.

Category II — machinery defects:

- Channel registry races (open/close/lookup from τ workers + event loop) → one lock,
  tiny critical sections; token uniqueness asserted at insert.
- `asyncio.to_thread` pool ceiling (default ≈ min(32, cpu+4)) could park at high N —
  irrelevant at 2–3, recorded as a sizing note for the seq-3 freeze decision.
- Degenerate-case regression → serial mock round + untouched 208-test baseline are
  explicit gate items.
- Teardown at N: each transport already owns its process group; Ctrl+C's
  `os._exit(130)` (τ's own path) leaves N orphan groups instead of 1 — pre-existing
  τ behavior, unchanged, noted in constraints rather than "fixed" in the seam.

Category III — experiment integrity:

- **Frozen-value leak**: `--max-concurrency` must be impossible in locked mode —
  refusal tested; locked config keeps reading `lock.max_concurrency`.
- **Grade-surface drift** (the invisible failure class): A.0a re-proof is a gate
  item; the concurrency minitest checks the same fidelity invariants per episode.
- **Held-out/vault surfaces untouched**: `heldout.py` drives `run.py` as a child
  process and inherits whatever the lock freezes — no code change there; its tests
  must not change either.
- **checkpoint under concurrent completion**: verified in vendor source —
  `create_checkpoint_fns` guards every write with a shared lock and atomic
  tempfile+`os.replace`; resume keys on (trial, task, seed) and re-runs only
  infrastructure errors. Results order in results.json differs from serial — all
  consumers key by task/trial, none by position (checked: manifest, fidelity,
  dashboard).
- **User-simulator rate limits**: 2N concurrent Anthropic streams on one key is the
  real ceiling; validation stays at N=2–3 and τ/litellm own retries — no
  backpressure machinery built, stated in constraints.

## Traps acknowledged (from intake instructions)

(a) Phase 3.5 lands before Phase 4 by design (D7 re-decision) — grounding confirms:
the plan registers Phase 3.5 with seq 2 running the new bridge at concurrency 1
under a fresh A.0a PASS. No contradiction found. (b) Seam churn is test-first —
increment 1's result-crossing test lands before the mechanism. (c) τ mid-flight
retries create transports concurrently — covered by Category I attribution items.
(d) Held-out wrapper and vault inherit through run.py — no direct changes.

---

# Phase 3.5b addendum — the attachment pool (platform-lane concurrency)

*(Historical: this design was refuted live and later retired — see the Final chapter.)*

User-directed 2026-08-13: lift the platform pin. Design:

- **Bridge**: N *pinned slot tokens*. Slot 0 reuses `bridge.token` (N=1 ≡ today,
  one code path); others minted+registered via `mint_pinned_token`.
  `open_pinned_channel(token)` replaces `open_run_channel`; unregistered tokens
  refused. Replace semantics per slot = the 3.5 episode boundary, per attachment.
- **Pool** (`dev_lane.py`): one `dev --as <name>-<nonce>` attachment per slot, each
  started with `--mcp tau=<url_for(slot token)>`; parsed dev target asserted equal
  to the requested name (fail-closed routing depends on it). Lease/release:
  `create_agent` leases (τ's workers don't announce identity), the transport's
  `close()` releases exactly once. Per-slot warm-up, concurrent.
- **Live proof**: flag stays locked-refused, so the proof runs on a temporary
  PROVISIONAL `max_concurrency: 2` (committed, restored after). `--allow-dirty`
  removes the push precondition: rows marked `arm_sha_ok=false`, correct for a
  machinery proof that must never be cited as a score. Ad-hoc 3-task locked round.

## Premortem → test map (each row lands as a committed test or a named live assertion)

| Failure imagined | Guard |
|---|---|
| Identical calls on two slots cross results | bridge cross-slot test (FIRST) + live fidelity invariants |
| Double-release re-queues a slot → two episodes share an attachment | pool test: double release cannot duplicate a slot |
| Lease starvation looks like a hang | pool test: N+1th lease blocks, unblocks on release |
| τ retry leases the same slot with stale state | per-slot stale-isolation test (replace at slot token) |
| Attachment process died; episodes park forever | lease refuses dead attachment loudly, test with stub |
| `--as` requested ≠ dev target served → tasks route nowhere | DevAttachment start asserts parsed target, test |
| Retitle/archive CLI failure swallows the release | transport close test: release fires despite CLI errors |
| Name collision with another session's attachment | nonce suffix, construction test |
| N=1 regression | slot-0-token equivalence test + existing 222-suite |
| Org sandbox limit < N | queueing observed at live proof; documented, not built around *(later corrected — no org limit exists; see third-pass correction)* |
| Evidence mis-join at N | live proof: distinct task ids, each row's attachment named in run_metadata |

---

# Final chapter — how concurrency was actually solved (end state, 2026-08-13)

The 3.5b pool above was landed, live-refuted the same day, and retired. The record of
what actually runs now, and why, in three acts:

## Act 1 — the pool meets reality: `dev_slot_conflict`

The live N=2 proof started two named attachments against the one Runtime and the
platform refused the second server-side (`dev_slot_conflict: this Runtime is already
connected by 'tau-w00-021d'`, ~70s of retries, timeout). **One live dev attachment per
Runtime** — a cardinality no doc states; the `--as` help's "two developers can share
one Runtime" means named routing, not attachment multiplicity. The pool's fail-closed
startup did its job (every attachment stopped, ~$0 spent), and the pool's premise was
dead.

## Act 2 — the header probe: the platform already carries episode identity

Intake had rejected mechanism B (session-keyed channels) because the episode↔session
binding looked undeterminable. A ~$0.35 probe with `TAU_BRIDGE_TRACE_HEADERS=1`
(raw-stderr, because τ's per-task log context swallows loguru mid-simulation) showed
the binding was there all along, on the platform side:

- the dev tunnel stamps **every** forwarded MCP request with
  `x-introspection-session-id` — the sandbox session it came from;
- `tasks get <task>` exposes the **same value** as `metadata.agent_session_id`.

So mechanism B is clean on the platform lane specifically — the tunnel supplies the
session, the CLI supplies the binding — and no attachment multiplicity is needed at
all.

## The mechanism that ships (one code path, both lanes)

Every episode opens a **fresh channel** (own mailbox) via `bridge.open_channel()`.
Lanes differ only in how a request finds it:

- **Local**: episode identity is the URL — each Pi subprocess gets its channel's
  `/mcp/<token>` path via `TAU_MCP_URL`.
- **Platform**: ONE nonce-named `dev --as` attachment serves every concurrent task;
  the transport binds its episode's channel to the task's `agent_session_id`
  (opportunistically from the create response, else a `tasks get` poll beside the
  stream), and the bridge routes each tunneled call by its session header, path token
  as fallback. Unbound sessions wait a 30s grace; never-bound sessions are refused
  after it; a conflicting bind fails the episode loudly; a bind arriving after channel
  close is ignored (closed flag under the bridge lock — a poll can race a τ-retry's
  teardown).

Pinned tokens, the pool, lease/release — all retired with their premise. τ retries get
fresh channels and fresh sessions, so stale isolation is structural in both lanes.

**Proven live**: 3 locked banking tasks through one attachment, genuinely overlapping
windows, fidelity invariants clean on all 3, zero crossing, 3 distinct
tasks/conversations (479s, ~$3 — long episodes drive cost, not concurrency). Local
lane: 2.80× at N=3 on the 10-task mock round. A.0a PASS re-recorded after every seam
change; suite ended at 235.

## Second-pass findings (from the one failed attempt in the minitest)

- **Slow sandbox start, not a seam bug** *(diagnosis superseded — see third-pass
  correction below)*: a burst task took 2m49s to start (then read as an org ~2-sandbox
  queue), our stream read the silence as death, τ retried, and the
  abandoned attempt still burned $0.69 after finally starting. Fixed: a silent stream
  over a task with no `started_at` re-attaches within a 240s queue budget (inside τ's
  300s turn ceiling), counted as `sandbox_queue_waits`; real stream deaths after start
  fail exactly as before.
- One task = one conversation = one sandbox is the platform's model AND the evidence
  contract — sandbox reuse across episodes would contaminate the agent's context and
  break the 1:1 evidence join, and would not increase parallelism anyway (start latency
  scales with concurrent sandbox starts, not with task creation).

## Third-pass correction (2026-08-14): there is no sandbox quota

The second pass's "org runs ~2 sandboxes; a third queues" was a misdiagnosis from a
single incident. The org's full task history shows three sandboxes running concurrently
on 2026-08-13 (02:05:31Z and 02:09:06Z), no task ever in `queued` status, and
created→started gaps that are heavy-tailed **provisioning latency**: 40–90s serial
baseline, 100–650s under concurrent starts — the 2m49s incident was mid-distribution
for its burst (a sibling took 457s) and was the second-created task, not the third. The
vendor confirms no plan-derived cap. The binding constraint for wide platform rounds is
that provisioning tail against `QUEUE_WAIT_CEILING_SECONDS` (240s, inside τ's frozen
300s turn ceiling); going wider needs staggered starts, not a bigger budget. Evidence
and task ids: `contract/constraints.md` § Platform-lane concurrency.

## Operational doctrine (the knob, final form)

`max_concurrency` is **unfrozen** — an operational knob, not an execution budget:
parallelism moves wall-clock, never what the agent can do inside an episode. Lock
default **10** (a round self-caps at its episode count, so "10" means "as wide as the
round allows"); `--max-concurrency` overrides per run, `1` = serial; effective value
recorded in `run_metadata.json`. The one carve-out: **`make batch` passes
`--max-concurrency 2`** to bound concurrent-start provisioning contention (no org quota
exists — see the third-pass correction) — batch rounds are
diagnosis evidence, and start-latency-driven τ-retry churn is pollution there. Held-out rounds
run T-wide on the local lane (no sandbox constraint; 2N provider streams is the real
ceiling, τ/litellm own retries).

Sizing rides on this (D10): the debug experiment runs G=3, B=4, T=8 — T=8 gives a
fixed failure mode ~60% odds of a held-out witness (vs ~43% at T=5), halves the
per-task quantum to 12.5 pp, and dilutes identity-harness churn across an 8×4 matrix.
Held-out = one fixed task list measured at every generation; batches = G disjoint
sets, consumed once each. Debug compute ≈ 1–1.5 h concurrent (vs ~5–8 h serial); the
full experiment ≈ 5–7 h (vs 20–28 h).
