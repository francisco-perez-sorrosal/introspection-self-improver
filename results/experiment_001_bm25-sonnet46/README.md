# Experiment 001_bm25-sonnet46 (seq 1) — VOID (environment defect found at H0)

Closed 2026-08-13, user-ratified, before any generation ran. This freeze is the debug
experiment's first attempt (D10 sizes: G=3, B=4, T=8). It froze cleanly — partition
verified, recipe byte-identical to `h0-baseline`, lock flipped at `af0c4a8`, A.0a PASS
(254-test suite + graded mock smoke) at `generation_000/gates/a0a.json` — and then the
H0 held-out round could not complete, for a reason frozen surfaces own, not the harness.

## The defect

`task_034` deterministically crashes τ's user simulator before the agent produces a
single token. τ seeds a constant agent greeting (`DEFAULT_FIRST_AGENT_MESSAGE`) and asks
the simulator for the opening user turn; for this scenario, Sonnet 4.5 at the frozen
`temperature: 0.0` returns an empty completion, and τ v1.0.1's
`UserMessage.validate()` fails the episode as `infrastructure_error`
(`orchestrator.py:844`; `ValueError: UserMessage must have either content or
tool_calls`). Observed 12/12 across three runner invocations (τ retried ×4 each,
`failed_after_attempts: 4`), with every seam incident counter at zero and wall-clock
per invocation ~seconds — the failure precedes the agent, so no harness mutation can
ever reach it, and every generation would fail identically. Upstream fixed exactly this
class for the *voice* simulator the day before (sierra-research/tau2-bench #440, merged
2026-08-12); text mode is unfixed on `main`, so re-pinning τ would not help.

Under the protocol this is fatal: the held-out measurement must cover the full frozen
set (reveal refuses anything else), and a frozen surface (τ commit + user-sim config)
owns the crash. Re-deciding a frozen surface means a new experiment — hence seq 2.

## What survives

- Two harness fixes found by this run, kept for every later experiment: the held-out
  wrapper resumes a measured-but-incomplete round instead of sealing it (`ce10da7`),
  and failed episodes persist the root cause τ records onto their manifest row, with
  the exception class shown reward-free on the completeness report (`9787585`).
- The A.0a gate record and the freeze snapshot in this directory (citable bring-up
  record; nothing here is an experiment result).
- The remedy for seq 2: a pre-partition first-turn screen over the whole 97-task pool,
  excluding tasks whose opening user-sim completion is empty, exclusions documented in
  the split manifest.

## Firewall accounting (sanctioned reads of the seq-1 vault)

The vault (`~/.sia_vault/experiment_001_bm25-sonnet46/`) holds 7 completed graded
episodes and stays sealed permanently — this experiment will never reveal. Reads that
occurred, each deliberate and bounded:

1. Pre-void, diagnostic: termination classes of non-completed manifest rows (counts
   only, no task ids, no rewards) — established `infrastructure_error=1`.
2. Pre-void, diagnostic: the failed row's `failure` block with task ids redacted —
   established the `ValueError` and its message.
3. Post-void: the failed row's task id (`task_034`) and attempt count, to seed the
   seq-2 exclusion screen.

Per-task rewards, trajectories, and the aggregate of the 7 completed episodes were
never read and must stay unread.
