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
```

`make smoke` is the cheap seam gate and takes about 15 seconds. Its results are **not
reportable** — see *Two run modes* below.

## The lanes

| Directory | Role | Who may change it |
|---|---|---|
| `target-agent/` | The harness under improvement (H_n). An Introspection Recipe. | The improvement loop, via pull request |
| `benchmark/` | The objective and the seam to it. τ² pinned by commit, the adapter, the lock. | Humans only |
| `contract/` | The permission envelope the orchestrator works inside. | Humans only |
| `results/` | Per-generation record: trajectories, Pi sessions, graded outcome. | Append-only |

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

| | local (Pi RPC) | development lane |
|---|---|---|
| Agent host | subprocess on this machine | cloud sandbox on a dev runtime |
| τ environment | in-process, loopback bridge | in-process, bridged by `introspection dev --mcp` |
| Introspection evidence | **none** | task, conversation, traces, tool calls |
| Prerequisites | none | login, GitHub repo, App grant, one runtime |

Only the local transport is implemented. Nothing local contacts the cloud, so no task and
therefore no conversation exists — Pi's session file under
`results/<gen>/<run>/pi_sessions/` is the only record. The development lane needs no public
tunnel: `introspection dev` routes a declared MCP server to a local process with
`--mcp NAME=URL`, so the τ environment can stay on this machine.

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
