# Per-generation procedure

**Not yet written.** This file will hold the generation cycle — execute, operate, hypothesise,
improve, baseline-vs-candidate, validate, record — and is deliberately absent until there is a
loop to describe. Writing it now would be describing a process nothing has run.

What exists today is the floor a generation needs, and the parts of the procedure that are
already mechanised:

| Phase | Status |
|---|---|
| Execute | `make bench` runs the locked domain; `make grade` is the only path to a number |
| Operate | **blocked**: the local transport produces no Introspection evidence at all |
| Hypothesise | — |
| Improve | the permission envelope exists (`constraints.md`); the pull-request loop does not |
| Baseline vs candidate | — |
| Validate | **blocked**: `benchmark/split_manifest.yaml` is an empty stub |
| Record | `results/<generation>/` exists; the learning-record schema does not |

## What has to land before this file can be honest

1. **The development-lane transport.** Conversations, traces, and tool-call evidence are what
   `operate` reads, and the local transport creates none of them. Until then a generation could
   be run but not diagnosed.
2. **The split.** `split_manifest.yaml` is empty, so there is no discovery/validation/test
   separation and therefore nothing that could be called a held-out result. Any number produced
   before it is populated is a smoke test, not a score.
3. **An adapter-fidelity gate.** Stock τ agent, native versus through the seam, same seed and
   task ids, scores agreeing within trial noise. Three known divergences are recorded in
   `constraints.md`; none has been measured. Until it runs, every generational number would be
   measuring the adapter as much as the harness.
4. **A real freeze.** `benchmark_lock.yaml` is marked `PROVISIONAL`. The retrieval config is on
   the offline `bm25` fallback rather than the intended `openai_embeddings`, and the model pair
   was chosen for availability.

Ordering matters: (3) gates any claim, (2) gates any generalisation claim, and (1) gates the
diagnosis half of the loop.
