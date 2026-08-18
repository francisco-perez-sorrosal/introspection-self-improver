# batch_02, first pass — VOIDED for seam contamination, preserved as evidence

Not a round of this experiment's record: `batch_02` was re-measured after this pass, and the
re-measurement is the round the noise floor and the pooled baseline are taken from. This
directory is kept because an incident that changed a decision has to stay auditable.

## What happened

Two episodes — `task_003` t0 (conv `01a0127d-88b9-706f-9b45-14449ab11885`, created
2026-08-18T01:30:16.998Z) and `task_014` t0 (conv `01a0127d-709b-7338-a37c-b9b31b87fe72`,
created 2026-08-18T01:30:11.577Z) — each recorded 2 `sandbox_seam_disconnects` and 2
`sandbox_tool_errors`, carrying the documented signature verbatim:

    MCP daemon: Error POSTing to endpoint: {"detail":"local MCP 'tau' is disconnected"};
    remote outcome is unknown; do not retry automatically.

The sandbox's MCP daemon answered the tool calls itself, believing the tunnel down. Both
episodes ran to `user_stop` and graded 0.0 with 1 and 2 bridge calls respectively — the
agent was denied its tools and the episode then graded as an ordinary agent failure, which
is precisely the failure mode `contract/constraints.md` records as invisible to every
bridge-side detector.

## Why it reads as transient connectivity, not a regression

- The two episodes were created **5.4 seconds apart at round start**; the other 34
  episodes, spanning the next ~15 minutes, were clean.
- `stream_reattaches` was **127** for this round against 83–103 for a seq-5 round and **1**
  for the canary immediately afterwards — network churn in the same window.
- The platform seam canary ran **PASS 3/3 with all counters zero** roughly an hour before
  (`gates/seam_canary.json`, pre-incident) and **PASS 3/3 again immediately after**, so the
  D35 adapter change sits between two clean canaries.
- D35 itself touches `prepare_round_dir` / `round_measured` only: round-directory
  lifecycle, executed once before any episode starts. It cannot reach the tunnel.

Causality for this class remains formally open upstream (`constraints.md` § The disconnect
regression): in-flight MCP calls through the dev tunnel are not recovered on reconnect the
way the event stream is.

## Why the round was re-measured rather than annotated

The two contaminated cells could have been declared invalid and excluded — the clean-cell
noise floor was computable (8 flips of 34 cells, 19/34 → 17/34). It was re-measured anyway,
for a reason specific to what `batch_02` is: under `identity_generations: [1]` this round is
**half the pooled H0 baseline of the pre-registered primary**, and both contaminated cells
sit on movable tasks (`task_003`, `task_014`) forced to 0.0 by a tool denial. A depressed
baseline makes a later "up" delta easier to obtain on exactly those tasks — a bias pointing
toward the experiment's own hypothesis, inside its single confirmatory statistic. $0.62 and
sixteen minutes is a cheap price for not carrying that.

τ's own resume could not have repaired it: both episodes are `completed: true` with rewards
recorded, so the (trial, task, seed) resume keyed on missing or `infrastructure_error` pairs
skips them. Re-measuring the round was the only path to clean cells.

## What this pass measured anyway, recorded because it is real

Against `batch_01` on a byte-identical harness: 9 of 36 trial cells flipped (8 on
clean-seam episodes), 7 of 12 task rates moved, round total 20/36 → 17/36. `task_008` swung
3/3 → 0/3. Both anchors held 3/3. The re-measured round is the one the experiment's noise
floor is quoted from, but this pass is a second, independent draw of the same A/A
comparison and the closure reads them together.
