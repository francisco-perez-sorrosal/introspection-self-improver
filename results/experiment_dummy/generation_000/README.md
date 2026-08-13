# generation_000 — seam bring-up

**Not a generation.** No harness change was made, nothing was compared, and no number here is a
result. This directory records that the seam works end to end and that the frozen surfaces hold.

`benchmark/benchmark_lock.yaml` was `PROVISIONAL` for both runs, and
`benchmark/split_manifest.yaml` was empty, so neither run drew from a discovery / validation /
test split. See `contract/protocol.md` for what has to land before a number counts.

## Runs

| Run | Domain | Mode | Outcome |
|---|---|---|---|
| `mock_smoke/` | `mock` | diagnostic | reward 1.0, DB match 1/1, normal stop (`user_stop`), 8 messages, 12 s, $0.0052 |
| `task_001/` | `banking_knowledge` (`bm25`) | locked | **reward 0.0**, DB match 0/1, normal stop (`user_stop`), 20 messages, 43 s, $0.1607 |
| `task_001_trials/trial_6…10/` | `banking_knowledge` (`bm25`) | locked | five trials of one task under one config: 1 × 1.0, 4 × 0.0 |
| `task_001_platform/` | `banking_knowledge` (`bm25`) | locked, **platform lane** | **reward 0.0**, DB match 0/1, normal stop (`user_stop`), 24 messages, 8 tool calls, $0.2520 |
| `task_001_sonnet5/` | `banking_knowledge` (`bm25`) | superseded config | reward 1.0, DB match 1/1, normal stop, 18 messages, $0.1283 |

`mock_smoke/`, `task_001/` and `task_001_platform/` are whatever the most recent `make smoke` /
`make single_task` (local or `TRANSPORT=platform`) produced — those targets overwrite, since a
seam gate is not a record. Each carries a
`run_metadata.json` naming the launcher, the exact launch argv, and the toolchain versions,
because two launchers produce identically-shaped results and a directory has to be able to say
which one made it.

**`task_001/` currently holds a failure, and it is kept.** Re-running until it passed would be
selecting on the outcome, which is the one thing this repository cannot afford to start doing.
The failure is also the more informative artefact — see below.

Graded by τ's own `evaluate_trajectories`, through `make grade`.

## The first episode graded on the Introspection platform

`task_001_platform/` is the same locked task with the agent running in a cloud sandbox instead of
a local subprocess, reached back to the τ environment on this machine through
`introspection dev --mcp`. It is the first result in this repository that leaves platform
evidence, and the evidence is what makes it interesting rather than the reward:

| | value |
|---|---|
| conversation / task id | `019ff93b-e92d-77dc-8e81-38bba88d57d6` |
| lineage | `recipe_git_commit_sha` = `e366b82867…`, the commit the run served |
| cost / usage | $0.2520 · 11 LLM calls · 8 tool uses · 47 spans |
| health | `has_errors: false`, `failed_tool_use_count: 0` |
| completeness | `evidence_complete: true`, 55 items |

Read it back with `introspection conversations export <id> --format trajectory`, which returns the
messages including the `<instructions>` and frozen `<policy>` the agent was actually given.

**This is not a comparison with the local lane.** One episode per lane cannot be, and per-task
reward is a draw regardless (see below). The divergences that bound any future comparison are
listed in `contract/constraints.md`.

### Two bugs this lane's bring-up found, both of which a green reward had hidden

Worth recording because both produced *correct-looking* results:

1. **A turn is not over when τ thinks it is.** τ hands the floor to its user simulator as soon as
   it holds an assistant message, but the platform run was often still streaming. Prompting then
   returns `409 Task is already processing`; τ books that as an infrastructure error and retries
   the whole episode. It presented as an episode "stuck on turn 2" — a `tools/call` parked 30s, the
   sandbox's MCP daemon gave up, the agent carried on, **and τ still graded the episode 1.0** on
   the answers that had already landed. Fixed by gating the next prompt on `RUN_FINISHED`, the
   platform's equivalent of Pi's `agent_settled`. Retries went from 1–3 per run to 0.
2. **A finished task is not a finished conversation.** The task stays `idle` on a warm sandbox
   until an inactivity timeout, so the conversation reads pending long after the reward exists, and
   a sweep would strand one warm sandbox per episode against the org concurrency limit. The
   transport now retitles the task (`τ²-bench <domain> <task>`) and archives it — never deletes
   it. Archiving settles the task immediately (the sandbox is released) while the conversation
   keeps its name, spans, cost and usage; the first design deleted the task, which preserved the
   evidence but not the name.

The second bug is the reason `evidence_complete` is recorded at all. "The episode finished" was an
inference from the reward; now it is a field that the export itself supplies.

## One task, one frozen configuration, ten different answers

`banking_knowledge/task_001` has been run ten times. Reward came back 1.0 six times and 0.0 four
times. Five of those runs are retained under `task_001_trials/` and are the citable ones; the
earlier five were overwritten before the study was deliberate, and are listed only as history.

Trials 6–10, identical locked configuration, all artefacts on disk:

| trial | reward | messages | cost | `KB_search` calls | Gold card doc retrieved |
|---|---|---|---|---|---|
| 6 | 0.0 | 20 | $0.1607 | 8 | no |
| 7 | 0.0 | 20 | $0.1680 | 7 | no |
| 8 | 0.0 | 24 | $0.1960 | 8 | no |
| 9 | **1.0** | 16 | $0.0962 | 5 | **yes** |
| 10 | 0.0 | 18 | $0.1316 | 6 | no |

History, artefacts overwritten: runs 1–5 all scored 1.0 at 28, 18, 27, 23 and 44 messages
(run 2 on Sonnet 5, run 4 through the `introspection` launcher). Ten runs, 6 × 1.0.

**τ's `--seed` cannot fix the variation, and it is worth being precise about why.** The seed is
frozen at 300 and reaches τ's own sampling; the agent's sampling belongs to Pi, which τ never
configures — the same separation that lets the agent ignore τ's `llm_args`. So the user simulator
is close to reproducible at `temperature: 0.0` and the agent is not, by construction.

The consequence is a constraint on the method: a single-trial per-task reward is a draw, and
`num_trials: 1` cannot resolve a harness improvement from noise. Raise it before G0 and report
pass^k alongside pass¹.

One thing this data cannot settle: runs 1–5 all passed and trials 6–10 went 1-for-5, which looks
like a mid-session shift. The breakpoint was chosen after seeing the outcomes, which is exactly
the way to manufacture a significant-looking split from noise, and no code change between run 5
and trial 6 touches the agent. Recorded as unresolved rather than as a regression.

## What decided the reward: one document

The reward tracks a single fact, in all six runs where the retrieved documents can be inspected:
**1.0 if `doc_credit_cards_gold_rewards_card_005` came back from `KB_search`, 0.0 if it did not.**

That document is the answer to the task. It states `Annual fee: $0.00` and `Earn 2.5% cash back
on all purchases`. The user wants a no-fee everyday-purchases card, and applying for the Gold
Rewards Card is what the graded DB state records.

In the failing trials the agent behaved correctly on the evidence it had. Its retrieved personal
credit-card documents were Platinum (10%, $200 fee), Silver (1%, $0) and Bronze (1%, $0), so it
presented those, and when pushed said — accurately, given what it had — that no no-fee card beat
1% flat, and that another institution might suit better. The user left. The DB never changed, and
`reward_basis: ['DB']` scored 0.

So this is **not** an agent that reasoned badly, and not a stopping-rule problem: the failing
trials searched *more* (6–8 calls against 5) and got *less*. Trial 7 even queried
`"Gold Rewards Card cash back rate personal"` by name and `bm25` returned savings-account APY
bonus tables and the *Business* Gold card instead.

**Which layer owns this is genuinely unsettled, and that matters more than the number.** Query
formulation is harness-owned and mutable, and the passing trials reached the document with
simpler, less enumerative queries — so there is real signal for the improvement loop. But
`retrieval_config` is frozen benchmark configuration, and it is currently on the provisional
offline `bm25` fallback rather than the intended `openai_embeddings`, because this machine has no
working OpenAI key. A retrieval backend that cannot surface a document when it is named directly
may well be most of this effect.

That ambiguity is itself the finding: **the retrieval config has to be settled before G0**, or the
first generation will attribute a benchmark-configuration artefact to the harness. Nothing is
fixed here by hand — diagnosis is `operate`'s job, and pre-labelling the failure is forbidden.

## Why a Sonnet 5 record is kept alongside the locked one

The locked configuration is Sonnet 4.6. `task_001_sonnet5/` is retained because it is the only
Sonnet 5 evidence, and a rejected alternative is a first-class result rather than something to
delete. Its 18 messages and $0.1283 are row 2 of the six-run table above.

**It supports nothing about either model's score, and the earlier reading of it was wrong.** When
only three runs existed it looked like the two Sonnet 4.6 runs clustered (28 and 27 messages,
within 2% on cost) while Sonnet 5 finished in 18 — suggesting Sonnet 5 did less work per unit of
outcome. Runs 5 and 6 broke that: the same Sonnet 4.6 configuration produced 44 messages and then
20. The apparent cluster was two draws that happened to land near each other, and 18 is inside the
4.6 spread, not below it.

The model choice in `benchmark_lock.yaml` therefore rests on its stated reasoning — that Sonnet 5
performs §21's expected discoveries natively and would mask them — and **not** on any measurement
here. Nothing in this directory could support a model comparison: one task, one trial per cell,
and a per-task reward that is demonstrably a draw.

## Do not read the model off the session file's first `model_change`

Every Pi session here emits two `model_change` events: one at boot carrying Pi's own default, and
one once the recipe's pinned model applies — both before any inference. The first is therefore not
authoritative about which model served the run.

In one earlier `task_001` run the boot event read `claude-sonnet-5` while all 11 assistant messages
ran on `claude-sonnet-4-6`. That run has since been overwritten and **no session currently on disk
shows the two disagreeing** — in all three, boot and served model match. So this is a caution
grounded in one observation, not a reproducible property; Pi's default appears to track recent use.

The point survives either way: attributing a score to the wrong model is the cheapest way to
invalidate a generation, and grepping the session file for a model id is the obvious way to do it.
The authoritative sources are the per-message `model` field in the session, or `raw_data.pi_model`
on each assistant message in `results.json`. The runner also refuses to start when
`agents/agent.yaml` and the lock disagree, so the declared model cannot drift from the served one
unnoticed.

One assistant message in each τ trajectory has no `raw_data` at all: τ's canned opening greeting,
which the orchestrator constructs and never sends to Pi.

## Where the 662 seconds went

The banking episode looked pathologically slow, so the trajectory timestamps were attributed by
the role of the message that ends each gap:

| | time | share |
|---|---|---|
| agent turns (Pi, through the bridge) | 48.5 s | 7% |
| τ environment tool execution | 0.1 s | ~0% |
| **τ's user simulator** | **613.1 s** | **93%** |

Of the user-simulator total, **601.9 s was a single call**. Every other call in the episode took
2–12 s, and the Pi session recorded only 46 s of work across its 24 messages. So the harness was
not slow; one provider request stalled.

The cause is that τ sets litellm's `num_retries` but never a request `timeout`
(`utils/llm_utils.py`), so a stalled response has no bound. `frozen.user_llm_args.timeout` is now
set to 60 s in the lock — five times the slowest healthy call — so a stall costs one retry rather
than ten minutes. This matters beyond patience: an unbounded per-call wait makes wall-clock per
generation unpredictable, and a generation runs baseline and candidate over a whole split.

`mock_smoke` is diagnostic because `mock` is not the locked domain: the committed Recipe carries
the locked domain's policy in its system prompt, so the Recipe is materialised into a throwaway
workspace at `.diagnostic-workspace/` with mock's policy substituted. Its reward is therefore not
comparable to anything at all — it exists to show the pipe moves.

## What the mock trajectory proves about the seam

Read from `mock_smoke/results.json`, and re-derivable from whatever run currently occupies it:

- **Tool calls reach τ under τ's own names.** The trajectory names `create_task`, not the
  `mcp_tau_create_task_5cab118a37` form the model actually saw. The reverse name map works, and
  `raw_data.pi_tool_names` keeps the mangled name alongside it for audit.
- **Arguments survive intact** — `{"user_id": "user_1", "title": "Important Meeting"}` arrived at
  the environment as the model wrote it.
- **τ executed the tools, not the adapter.** Each call produced a `tool` message from the real
  environment, and the final DB state matched gold.
- **Termination was normal** (`user_stop`), not an adapter timeout or an agent error.
- **Evidence linkage exists.** Every assistant message carries `raw_data.pi_session_ref` pointing
  at the Pi session under `pi_sessions/`, which is the only record of this episode — the local
  transport creates no Introspection conversation.

## Mixed messages, forwarded unaltered

Some assistant messages carry narration *and* a tool call, which τ's protocol disallows. The
adapter forwards them exactly as produced, and τ does not end the episode because
`enforce_communication_protocol` defaults to `false` — now frozen explicitly in the lock, since it
decides whether the violation is graded at all.

The rate depends on the domain, which is itself the interesting part. In the runs currently on
disk: **2 of 2** tool-calling messages are mixed in `mock_smoke`, and **0 of 6** in `task_001`. The
banking runs consistently show none — the agent puts its reasoning in `thinking` blocks there,
which τ has nowhere to put and the adapter drops, so nothing violates the protocol.

So the earlier reading — that it happens on essentially every tool call and the `SYSTEM.md`
instruction is simply not working — was drawn from mock alone and does not hold. Whatever the
mechanism, it is left as-is: fixing it now would be authoring the first improvement by hand, which
is the orchestrator's job to discover from evidence.

τ recorded the narration in the trajectory but never delivered it to the user. That is τ's own
behaviour, faithfully. The alternative — having the adapter strip the text — would have hidden a
real, harness-owned, pull-request-fixable defect from the objective.

## Grading had to be told which environment the run used

`tau2 evaluate-trajs` on a banking run fails with `429 billing_not_active` from OpenAI, even
though the run used the fully offline `bm25` config and the task's `reward_basis` is `['DB']`,
which needs no retrieval at all.

`evaluate_trajectories._build_eval_env_kwargs` passes only `read_log_allowlist` for
`banking_knowledge`, never the retrieval variant, so `get_environment` falls back to
`DEFAULT_RETRIEVAL_VARIANT` — `alltools`. The run's own `retrieval_config: bm25` **is** recorded in
the results file at `info.retrieval_config`; the evaluator does not read it, and the CLI exposes no
flag to supply it.

`benchmark/scripts/grade.py` closes that gap, and it is a fidelity fix rather than a convenience.
The evaluator was grading against a **different tool surface** than the run used — retrieval
configs expose different tool names (`KB_search` under `bm25`, `KB_search_bm25` plus
`KB_search_dense` under `alltools`) — so an `ACTION`-basis task's expected actions could silently
stop matching. The wrapper injects the config the results file recorded, which is by definition the
environment the trajectory was produced in, and refuses when that disagrees with the lock.

It calls τ's own `evaluate_trajectories`; no reward is computed here and no grading logic is
reimplemented. The patch wraps one private kwargs builder, calls the original, and adds one key —
narrow on purpose, and loud if upstream changes it. Worth reporting upstream.

## Bugs found and fixed during bring-up

Kept because they are the parts most likely to break again:

1. **The rendezvous deadlocked on a name mismatch.** The mailbox was keyed on Pi's mangled tool
   name, but Recipes' rewrite is client-side presentation only — an MCP `tools/call` arrives under
   the name the *server* advertised. Pi's 120 s daemon timeout fired first and surfaced as a tool
   error, so the agent carried on against a phantom failure. `TAU_ADAPTER_TRACE=1` prints every
   await/post pairing and made it obvious in one run.
2. **τ² resolves its data directory once, at import time.** Setting `TAU2_DATA_DIR` inside
   `main()` was too late, because the adapter imports τ² at module level. It is now set in
   `tau_adapter/__init__.py`.
3. **`save_to` is a run *name*, not a path.** `run_domain` places results under
   `TAU2_DATA_DIR/simulations/<name>/`, which would have written into the pinned vendor checkout.
   The runner uses `run_tasks` with explicit paths instead.
4. **τ² v1.0.1 is Python 3.12-only** despite declaring `<3.14`: its package `__init__` reaches
   `audioop`, removed from the stdlib in 3.13.
5. **Under `introspection local`, Pi is a grandchild, so killing the direct child hangs
   teardown.** The tree is node → platform binary → pi. `Popen.kill()` reached only node; the rest
   reparented to init and kept our stdout pipe open, so the reader never saw EOF and `close()`
   blocked forever. Fixed with `start_new_session=True` plus `os.killpg`, which also makes the
   direct-`pi` path more robust than it was.
6. **The CLI's recipe validation reads gitignore, so a materialised recipe cannot live in
   `/tmp`.** `introspection check` rejects `.pi/mcp.local.json` as local capability config shipped
   with a recipe; the committed tree satisfies it by gitignoring that file. A copy outside a work
   tree has no ignore rules to consult and fails. Diagnostic mode therefore materialises into
   `.diagnostic-workspace/` inside the repo, gitignored — the same copy under `/tmp` did not run.
