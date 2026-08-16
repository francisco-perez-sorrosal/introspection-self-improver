# Surface probes — pre-freeze measurement runs

Home for probe evidence produced **between experiments**, when no open freeze provides a
`generation_00g/` to land it in (the in-experiment home; see `contract/protocol.md` step 4b).
The runner ignores paths outside `results/` (`tau_adapter/experiment.py`), so nothing here is
an experiment record: probes are throwaway-branch measurements whose *evidence* is committed
from `main` after the branch is deleted.

Conventions:

- One directory per probe day/campaign: `<YYYY-MM-DD>-<slug>/` with a `README.md` stating
  design, runs, verdicts, and the ids of every episode spent.
- Probe mutations live on `probe/<slug>` branches, never merged, deleted after evidence
  extraction (precedent: seq-6's `probe/extension-seam`).
- Probe runs that use the τ runner write into the *current lock's* experiment tree; give
  every run a `SUFFIX` that cannot collide with a committed run directory, copy the evidence
  here, and delete the run directory (a closed experiment's tree must not accrete
  post-closure runs — and `make smoke` writes to the committed `mock_smoke/` path, so never
  leave its output behind).
- Platform-lane caveat (measured, see `2026-08-16-surface-probes/`): the platform runner
  pins the recipe to **pushed main**; `--allow-dirty` runs pushed main's recipe and marks
  rows `arm_sha_ok=false`. The local lane is the work-tree-faithful lane for probing recipe
  changes.
