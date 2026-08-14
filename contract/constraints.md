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
| `agents/agent.yaml` `tools`, `skills`, `subagents` | mutable | — |
| `package.json` `pi.skills`, `pi.extensions` | mutable | — |
| `package.json` `pi.mcp` | **frozen** | tool catalogue vs live environment before every run |
| `benchmark/`, `contract/`, `.introspection/` | **frozen** | branch protection + the `frozen surfaces` workflow |

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
     the parts as distinct AG-UI event groups. The transport's first design forwarded that
     split, on the view that merging would invent a message shape — and recorded the latent
     consequence here rather than fixing it: narration taken alone hands τ's floor to the user
     simulator while the sandbox sits parked on the bridge. The A.0b gate then observed exactly
     that (first run 2026-08-13; the verdict now lives in git history —
     `git show 984c598^:results/experiment_bm25-sonnet46/generation_000/gates/a0b.json`):
     3 of 12 platform episodes hit τ's 600 s
     ceiling, each with 5–6 rendezvous stalls — the sandbox's MCP daemon abandoning parked
     calls at ~15 s ("MCP daemon: Timeout; remote outcome is unknown"), Pi's tool executor
     erroring at 120 s, the agent retrying against phantom failures while the trajectory
     recorded valid results. Example conversations: `019ffbcd-cacd-…` (graded 0 on timeout)
     and `019ffbeb-01e4-…` (an attempt τ retried past; kept as an orphan). The platform's own
     GenAI spans settle whose shape is real: the model's output is one message with
     `[thinking, text, tool_call]`. The remedy — buffering a run's narration and attaching it
     to that run's first tool call, flushing text-only at RUN_FINISHED — therefore
     *reconstructs* the shape the host produced rather than inventing one, and the call still
     surfaces the instant it exists, so the parked sandbox is answered while its daemon is
     listening. Adopted by operator decision at the A.0b gate, 2026-08-13. Consequence: both
     lanes now present the same mixed message, `enforce_communication_protocol` governs them
     identically, and the two-compliant-messages divergence this bullet used to record no
     longer exists.
   - **Reasoning is streamed and dropped.** `REASONING_*` events are discarded for the same reason
     the local lane drops Pi's `thinking` blocks: τ's `AssistantMessage` has nowhere to put them.
   - **Per-message cost and usage are absent**, because AG-UI events carry none. τ's own cost
     metric comes out `nan`; the real numbers live on the conversation record and are copied into
     `run_metadata.json`'s `platform.accounting`.
   - **The system prompt differs by one line.** Pi appends `Current working directory: /workspace`
     after `</policy>` in the sandbox, against the recipe path locally. Outside the frozen region,
     so the hash gate is unaffected.
   - **The intermittent rendezvous failure is diagnosed and fixed.** A `tools/call` could park
     15–30 s and be abandoned by the sandbox's MCP daemon, while the episode still graded 1.0 on
     the answers that had already succeeded. The cause was never the rendezvous: each
     `introspection` CLI invocation pays ~5.5 s of startup, and the transport paid the prompt's
     and the stream's serially before τ could see a call — burning a third of the daemon's ~30 s
     per-request budget per turn. The stream attach now overlaps the prompt (run-id filtering
     plus a single reattach make the early attach safe), and a clean episode answers every call
     in ~250–350 ms with zero span errors. `STALL_WARN_SECONDS` stays, so any recurrence names
     itself. A platform score is never a substitute for a local one — under the evaluation
     protocol the lanes serve different roles by design: platform episodes supply improvement
     evidence, local episodes supply the held-out measurement (`SIA_EVALUATION_PLAN.md` D1).

5. **The agent is not reproducible from τ's `--seed`.** The seed reaches τ's own sampling; Pi owns
   the agent's, and τ's `llm_args_agent` never reach it. This is not a divergence the fidelity
   instrument can close, and it is not constant across episodes — it is the reason a single
   episode's reward is a draw (measured: six runs of one task returned 1.0 five times and 0.0
   once; ten runs returned 1.0 six times and 0.0 four times). The remedy changed with the
   evaluation protocol (2026-08-13): repeated trials are no longer the instrument. Generations
   are compared on a fixed held-out set at one trial per task, pooling variance across tasks
   instead of within one — binomial noise ≈ ±7 pp at T=47, stated wherever the curve renders;
   `pass^k` is retired for generations; an optional endpoint reliability study (H_0 and H_G ×
   4 trials, after reveal) is the named upgrade path (`SIA_EVALUATION_PLAN.md` D2).

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
streams; throttling surfaces as infra retries) and the org's plan-derived sandbox limit,
which queues rather than refuses.

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
a platform binary, then probes `pi --help` before launching. That is ~9 minutes on a 97-task sweep,
and a generation runs baseline and candidate. What it buys — knowing the recipe is valid — the
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
- The `openai_embeddings` retrieval config originally intended is unavailable on this machine
  (the OpenAI key returns `429 billing_not_active`), so bring-up used the offline `bm25`
  fallback. **Resolved 2026-08-12: `bm25` is the deliberate freeze**, pinned knowingly rather
  than provisionally. The consequence is accepted, not
  deferred: `bm25` changes both the tool set and the policy text, so no number produced under
  this freeze is comparable with published τ-Knowledge results, and no comparability claim is
  made anywhere in this experiment's record. Cross-generation comparison is unaffected — the
  backend is constant by construction — and retrieval *usage* (query formulation, k, iteration,
  stopping) remains mutable harness territory. Re-deciding this value means a new experiment,
  never a new value under the old id.
- An experiment's id is *derived*, never chosen: `experiment.seq` (zero-padded to three
  digits) + `experiment.name`, giving `001_bm25-sonnet46` and the results directory
  `results/experiment_001_bm25-sonnet46/`. The sequence exists because a descriptive name can
  legitimately repeat — a second freeze of the same bm25 + Sonnet 4.6 configuration is
  `002_bm25-sonnet46`, a different experiment — so the name alone cannot be the identity.
  Re-deciding a freeze bumps `seq`. The pre-rename directory
  `results/experiment_bm25-sonnet46/` was migrated to `results/experiment_001_bm25-sonnet46/`
  (snapshot id and fingerprint refreshed, recorded `experiment` fields rewritten); platform
  task titles from before the rename keep their old `[exp:bm25-sonnet46]` suffix — they are
  records of what the platform actually displayed, not re-labeled evidence.
