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
  stock τ, which is what keeps the score comparable to published numbers.
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
cross-generation comparison; they bound comparability with published τ numbers, which is what the
adapter-fidelity gate will eventually measure.

1. **Tool names the model sees are mangled.** Recipes rewrites them to
   `mcp_<server>_<tool>_<sha256[:10]>`. The trajectory carries τ's canonical names — the reverse
   map is built forwards and verified byte-for-byte against the JS implementation — but the
   *prompt* the model reads does not.
2. **τ's canned opening greeting is recorded but not replayed** into the agent session, which
   starts empty. A stock agent's message list contains it.
3. **The agent's model is set by the Recipe, not `--agent-llm`.** τ requires the flag, so the
   lock records it as declared-and-unused and keeps it equal to the real value.
4. **The agent is not reproducible from τ's `--seed`.** The seed reaches τ's own sampling; Pi owns
   the agent's, and τ's `llm_args_agent` never reach it. This is not a divergence the fidelity gate
   can close, and it is not constant across episodes — it is the reason per-task reward has to be
   treated as a draw and `num_trials` raised before any comparison. Six runs of one task under one
   frozen configuration returned reward 1.0 five times and 0.0 once.

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

## Corrections to the MVP document

Found while implementing, and load-bearing:

- `--max-steps-seconds` is listed as a frozen comparison variable, but it only configures
  audio-native runs, where it is divided by the tick duration. In text mode it has no effect. The
  real per-episode wallclock bound is `TextRunConfig.timeout`, which the lock freezes instead.
- `--task-set-name base` conflates two flags. `base` is a task *split*; the task set defaults to
  the domain's own. The lock records both separately.
- `enforce_communication_protocol` is missing from the frozen list and belongs on it: it decides
  whether a mixed message ends an episode at all, so flipping it moves scores with no harness
  change. Left at τ's default of `false`, which is what stock runs use.
- τ sets litellm's `num_retries` but never a request `timeout`, so a stalled provider response
  has no bound — one user-simulator call blocked for 601 s in the first banking run. The lock now
  freezes `frozen.user_llm_args.timeout`, which the document's frozen list has no slot for even
  though it changes wall-clock per generation by an order of magnitude.
- `tau2 evaluate-trajs` cannot grade `banking_knowledge` offline. It rebuilds the environment
  through `DEFAULT_RETRIEVAL_VARIANT` (`alltools`, OpenAI embeddings) rather than the run's own
  recorded `retrieval_config`, and offers no flag to override it — so the only sanctioned path to
  a reward requires an embeddings key even for a `reward_basis: ['DB']` task. Worth reporting
  upstream; not worked around here, because working around it would mean computing a reward
  somewhere other than the evaluator.
- The `openai_embeddings` retrieval config the document pins is unavailable on this machine
  (the OpenAI key returns `429 billing_not_active`), so bring-up used the offline `bm25`
  fallback. This is a genuine deviation from the intended freeze and must be resolved before G0:
  `bm25` changes both the tool set and the policy text, so results on it are not comparable with
  published τ-Knowledge numbers.
