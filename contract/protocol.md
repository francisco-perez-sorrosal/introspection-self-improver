# Per-generation procedure

**Not yet written.** This file will hold the generation cycle — execute, operate, hypothesise,
improve, baseline-vs-candidate, validate, record — and is deliberately absent until there is a
loop to describe. It is written at M4 (`PLAN.md`), from the generation that actually ran.

What exists today is the floor a generation needs, and the parts of the procedure that are
already mechanised:

| Phase | Status |
|---|---|
| Execute | `make bench` runs the locked domain; `make grade` is the only path to a number. The development lane (`TRANSPORT=platform`) runs the same episodes on the `target-agent` dev Runtime |
| Operate | the development lane leaves per-episode platform evidence — conversation, spans, cost, usage, commit lineage. **Blocked on the evidence join**: no per-episode manifest exists, sweeps cannot name their τ task per episode, and the observation/pattern harvest has never been exercised (v2 §4 W3; `PLAN.md` M2) |
| Hypothesise | — |
| Improve | the permission envelope exists (`constraints.md`); the pull-request loop does not |
| Baseline vs candidate | — |
| Validate | gated on the frozen split (`benchmark/split_manifest.yaml`, frozen at M1) and on paired-arm execution, which does not exist yet |
| Record | `results/experiment_<id>/<generation>/` exists; the learning-record schema does not (lands at M4) |

## What has to land before this file can be honest

1. **The evidence join** (v2 §4 W3; `PLAN.md` M2). The development-lane transport landed —
   platform episodes leave conversations, spans, cost and commit lineage — but nothing joins a
   sweep's episodes to their conversations: no episode manifest, no per-task labels on sweeps,
   no clean-tree or arm-SHA assertion. Until it lands a generation can be run but not diagnosed
   at scale.
2. **The adapter-fidelity gates, as re-specified** (v2 §4 W4; `PLAN.md` M2). v1's gate — stock
   τ agent, native versus through the seam — cannot run: the seam replaces the agent host, so
   there is no "same agent, two paths" configuration. It decomposes into A.0a pipe semantics
   (the adapter test suite plus the mock smoke; exists), A.0b cross-lane consistency
   (`make fidelity`, to be extended to a task set × the frozen trial count; not yet run at that
   scale), and A.0c a native stock-agent anchor (never run). A failed blocking component stops
   the experiment.
3. **A graded G0 and one full improvement generation** (`PLAN.md` M3–M4). The cycle this file
   describes must have run once; the learning-record schema lands with it.

Ordering matters: (2) gates any claim, (1) gates the diagnosis half of the loop, and the frozen
split gates any generalisation claim.
