# Per-generation procedure

**Not yet written.** This file will hold the generation cycle — improvement batch, operate,
hypothesise, improve, human approval, held-out evaluation, record — and is deliberately absent
until there is a loop to describe. It is written at `SIA_EVALUATION_PLAN.md` Phase 4, from the
debug-scale generation that actually runs. The design it will instantiate is
`self_improving_agent_evaluation_protocol.md`.

What exists today is the floor a generation needs, and the parts already mechanised:

| Phase | Status |
|---|---|
| Execute | `make single_task` runs one episode in either lane; `make grade` is the only path to a number. `make batch` (platform lane, frozen partition) and `make heldout` (local lane, vault) landed at plan Phase 2 |
| Operate | the evidence join landed (M2): `episode_manifest.jsonl` names every episode's τ task, trial, label, conversation id, cost and commit lineage. The observation/pattern harvest has never been exercised |
| Hypothesise | — |
| Improve | the permission envelope exists (`constraints.md`); the pull-request loop has not been exercised |
| Held-out evaluation | landed at plan Phase 2: `scripts/run_heldout.py` — local lane only, out-of-tree vault, muted grading, completeness-only terminal (plan D1/D9) |
| Record | `results/experiment_<id>/generation_NNN/` exists; the improvement-record schema landed at plan Phase 3 (`contract/improvement_record.schema.yaml`, validated by `tau_adapter/records.py`; `make reset_h0` and `make reveal` alongside it) |

Every mechanised piece above is in place; what remains is `SIA_EVALUATION_PLAN.md` Phase 4 —
the debug experiment whose actual run writes this procedure.
