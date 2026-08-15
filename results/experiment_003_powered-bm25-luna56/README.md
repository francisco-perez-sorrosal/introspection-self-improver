# experiment_003_powered-bm25-luna56 — powered bring-up (not a reportable experiment)

Seq 3 is an **odd** sequence number: under the parity convention (plan D15,
2026-08-15) even seqs are stable, reportable experiments and odd seqs are
experimentation. This directory is the powered experiment's bring-up and
calibration archive; **the reportable powered run is
`results/experiment_004_powered-bm25-luna56/`** (same freeze values, renumbered
while PROVISIONAL with no snapshot and zero enforced episodes).

What lives here, and stays here — evidence paths are never rewritten:

- `CALIBRATION_PILOT.md` — the D12/D14 luna pilot (n=28 non-partition tasks,
  baseline 7/28 = 25%, $0.038/local episode). **Superseded as calibration of record
  by plan D16**: its arm (`2ea2475`) carried the seq-2 SYSTEM.md mutations, so it
  measured H0+g1–g3; the corrected-H0 pilot lives at
  `../experiment_004_powered-bm25-luna56/CALIBRATION_PILOT.md`. Kept sealed as the
  measurement it was.
- `generation_000/mock_smoke/` — the seam smoke on the mock domain under the
  luna pair and CLI 0.27.1 (reward 1.0).
- `generation_000/concurrency_smoke/` — the 4-wide platform concurrency
  validation (2026-08-15): four sandboxes provisioning concurrently, zero seam
  incidents; the evidence behind `make batch --max-concurrency 4` and the
  start-gate early-release note in `contract/constraints.md`.

The sibling `experiment_003_powered-bm25-haiku45/` is the D13 interim detour's
archive (its own pilot, baseline 3/28 = 10.7%), kept for the same reason.

None of the numbers in this directory are labelled results of any experiment:
they are diagnostics and calibration, cited by the seq-4 freeze's provenance.
