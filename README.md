# Introspection Self-Improver

A τ²-bench-evaluated agent built as an Introspection Recipe, with the seam between the two
built so that a self-improvement loop can be added on top without moving anything.

There is no improvement loop yet. What exists is the floor it needs: an immutable objective, a
minimal harness, and a frozen/mutable boundary that is enforced mechanically rather than by
convention.

```
τ²-bench  ──tasks──▶  target-agent (Introspection Recipe)  ──tool calls──▶  τ² environment
   ▲                                                                             │
   └────────────────────────── reward, via tau2 evaluate-trajs ◀─────────────────┘
```

## Quick start

```bash
make bootstrap   # pinned τ²-bench checkout + Python environment  (~715 MB, one time)
make check       # recipe validity + every frozen surface
make smoke       # one mock-domain task end to end, then grade it
make single_task # one locked-domain task, then grade it  (TASK=task_001 by default)
make bench       # the WHOLE locked split (97 tasks, serial) — long and costly

make single_task TRANSPORT=platform   # same task, agent on an Introspection dev runtime
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

The dependency runs one way — `benchmark/` reaches `target-agent/` by path, never the reverse
— so the Recipe can be split into its own repository with `git subtree split` when the agent is
eventually granted write access to it. That split matters: a GitHub installation token cannot be
scoped to a sub-path, so an agent granted `contents: write` here to edit its own Recipe can also
write the benchmark lane. Until the split, the boundary is enforced by branch protection plus
the `frozen surfaces` workflow, not by the grant.

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
bring-up and, later, for the adapter-fidelity gate on `mock`.

## Two transports

The rendezvous is driven by the bridge, not by the transport, so the same seam runs either way.

| | `TRANSPORT=local` (default) | `TRANSPORT=platform` |
|---|---|---|
| Agent host | Pi subprocess on this machine | cloud sandbox on a dev runtime |
| τ environment | in-process, loopback bridge | in-process, bridged by `introspection dev --mcp` |
| Introspection evidence | **none** | conversation, traces, spans, cost, commit lineage |
| Episode cost / wall clock | ~$0.17, ~45 s | ~$0.26, ~75 s (+~20 s one-off `dev` attach) |
| Prerequisites | none | login, pushed repo, App grant, Runtime, dev API-key agent |

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
the handler asks for it. The mailbox is keyed by name and arguments rather than by arrival order,
which is why that works.

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
the summary and hides the finished task from the default list. The label ends in `[exp:<id>]`
— the lock's experiment id — so platform evidence stays separable across experiments even when
two share a recipe commit. Archiving also settles the task:
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

Reward is computed only by `tau2 evaluate-trajs`, only via `make grade`.

## One experiment, one freeze

`results/` carries one level above generations: `results/experiment_<id>/generation_NNN/<run>/`.
The id comes from `benchmark_lock.yaml` (`experiment.id`) — the lock defines the freeze, so the
lock names the experiment — and the runner refuses any `results/` path outside the lock's
experiment directory, before `--overwrite` could delete anything. Changing models, retrieval
config, splits or trial counts is a new experiment id, never a new value under the old one.

Once the lock stops being `PROVISIONAL`, the first run into an experiment writes
`experiment.yaml` beside its generations — a fingerprint of the parsed freeze (lock values plus
split manifest) — and every later run must match it. Values are compared, not file bytes, so a
comment edit never trips the check while a re-decided frozen value refuses the run with
"start a new experiment". `results/experiment_dummy/` is the pre-freeze bring-up bucket:
`PROVISIONAL` runs land there, unenforced and unreportable.

**The lock is currently `PROVISIONAL`** — most values let the pipe move and are not an
experiment's freeze. Two values need a decision before G0:

- `retrieval_config` is on the offline `bm25` fallback rather than the intended
  `openai_embeddings`, because this machine has no working OpenAI key. This is no longer a
  comparability footnote: on `bm25`, whether one task passes turns on whether `KB_search` returns
  a single document, and one trial queried that document's card by name and did not get it.
- `num_trials: 1` is enough for a gate and not enough for a comparison. Ten runs of one task
  under one frozen configuration returned reward 1.0 six times and 0.0 four times — τ's `--seed`
  seeds τ's sampling, not Pi's, so the agent is not reproducible episode to episode.

The model pair, by contrast, is now chosen rather than defaulted, and neither half is Sonnet 5.

The **agent** runs Claude Sonnet 4.6 for experimental sensitivity, against cost: Sonnet 5 is
~13% cheaper per unit of work and stronger on agentic tasks, and that is the problem. The
harness improvements this project exists to discover — search discipline, query reformulation,
policy extraction, plan-before-write, post-action verification — are behaviours Sonnet 5 already
performs unprompted, so adding them explicitly would move its score less. A model that does not
already do them leaves the harness as the binding constraint, which is the thing being measured.

The **user simulator** stays on Sonnet 4.5 for an unrelated reason: Sonnet 5 rejects
`temperature: 0.0`, which is τ's own default for the simulator and the only knob that makes that
half of the environment reproducible.
