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

The bridge multiplexes episodes over per-episode URL channels (2026-08-13): each episode
rendezvouses at its own `/mcp/<token>` path with its own mailbox, so the local lane runs N
episodes in flight without any way for their results to cross. The development lane cannot
use per-episode URLs directly — `introspection dev --mcp tau=<url>` is handed exactly one
URL for the whole attachment, and per-task MCP configuration does not exist (`tasks create
--metadata` is application metadata, not a platform switch) — so its concurrency rides the
platform's own affordance instead, verified against the installed CLI and built as the
**attachment pool** (2026-08-13, `SIA_EVALUATION_PLAN.md` Phase 3.5b): `introspection dev
--as <name>` names an attachment, N named attachments serve one Runtime concurrently, and
`INTROSPECTION_DEV_TARGET=<name>` routes a task to its attachment fail-closed.

The pool (`tau_adapter/dev_lane.py`) starts one named attachment per worker, each handed
its own pinned bridge slot's URL for the whole run; an episode leases a slot for its
lifetime and its transport releases it at close. The invariants the tests pin: a slot can
never be queued twice (two episodes on one attachment would share a rendezvous channel —
the exact crossing the channels forbid), a dead attachment is refused loudly at lease and
retired, a misnamed attachment is refused at startup (routing fails closed on the exact
name), and names carry a per-run nonce so two concurrent runs on one machine cannot claim
each other's dev target. A pool of one slot rides the bridge's own run token — the
single-attachment behavior this lane always had, one code path at every N.

**The platform caps live dev attachments at one per Runtime — observed, not documented.**
The Phase 3.5b live proof (2026-08-13) started a second named attachment against the same
Runtime and the platform refused it server-side, retrying ~70s before timing out:

    WARN introspection::dev_attach: development conflict this Runtime is already
    connected by 'tau-w00-021d' on main at f40c084d code=Some("dev_slot_conflict")

The pool's startup failed loudly and stopped every attachment — zero episodes spent. No
plugin doc states this cardinality; the CLI's `--as` help ("two developers can share one
Runtime") evidently describes named routing, not concurrent attachment multiplicity from
one branch and machine. The runner therefore refuses platform-lane `max_concurrency` > 1
before any spend (`assert_transport_supports_concurrency`), citing this observation. The
machinery stays: if the platform lifts the cap (or a future decision runs N Runtimes —
unprobed, with real platform-state and lineage implications), the pool serves N with no
code change. Until then platform rounds are serial by upstream constraint; the local lane
— ~85% of experiment wall-clock (`SIA_EVALUATION_PLAN.md` D7) — executes the frozen
`max_concurrency` in full.

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
