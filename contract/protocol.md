# Per-generation procedure

**Not yet written.** This file will hold the generation cycle — improvement batch, operate,
hypothesise, improve, human approval, held-out evaluation, record — and is deliberately absent
until there is a loop to describe. It is written at `SIA_EVALUATION_PLAN.md` Phase 4, from the
debug-scale generation that actually runs. The design it will instantiate is
`self_improving_agent_evaluation_protocol.md`.

What exists today is the floor a generation needs, and the parts already mechanised:

| Phase | Status |
|---|---|
| Execute | `make single_task` runs one episode in either lane; `make grade` is the only path to a number. The batch and held-out round targets land at plan Phase 2 |
| Operate | the evidence join landed (M2): `episode_manifest.jsonl` names every episode's τ task, trial, label, conversation id, cost and commit lineage. The observation/pattern harvest has never been exercised |
| Hypothesise | — |
| Improve | the permission envelope exists (`constraints.md`); the pull-request loop has not been exercised |
| Held-out evaluation | machinery lands at plan Phase 2 — local lane only, out-of-tree vault, muted grading (plan D1/D9) |
| Record | `results/experiment_<id>/generation_NNN/` exists; the improvement-record schema lands at plan Phase 3 |

The path from here to an honest version of this file is `SIA_EVALUATION_PLAN.md` Phases 1–4:
partition machinery, then runner + firewall, then the generation lifecycle, then the debug
experiment whose run writes this procedure.
