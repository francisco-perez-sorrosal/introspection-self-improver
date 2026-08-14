# Guardrail walk — experiment 002_bm25-sonnet46 (protocol §29, walked at close, 2026-08-14)

Each item states the enforcing mechanism and the verdict for this experiment.

| # | Guardrail | Mechanism | Verdict |
|---|---|---|---|
| 1 | Batches ∩ held-out = ∅ | `propose_split.py --verify` at freeze; partition re-verified pre-spend by every round | HELD |
| 2 | Batches pairwise disjoint | same verify | HELD |
| 3 | Held-out fixed before H0 | partition committed at the `c1f6ecc` freeze, inside the freeze fingerprint, before the first H0 episode | HELD |
| 4 | No held-out evidence during optimization | local-lane-only held-out (no platform evidence exists); vault out of tree; muted wrapper prints counts and failure classes only (reward-free asserted by test); zero vault reads during seq 2 — the seq-1 diagnostic reads belong to the voided experiment and are accounted in its closure README | HELD |
| 5 | No aggregate held-out scores during optimization | aggregates computed at reveal and at no other time (`reveal.py` is the only reader) | HELD |
| 6 | Target model fixed | `frozen.agent_model` in the fingerprint; runner refuses recipe/lock disagreement; all three mutations touched `SYSTEM.md` only | HELD |
| 7 | User simulator fixed | `frozen.user_llm` + args in the fingerprint | HELD |
| 8 | τ evaluator + task definitions fixed | vendored pinned checkout, never edited; the pool screen used τ's own code read-only | HELD |
| 9 | Benchmark commit pinned | `fc0055dc` (v1.0.1), verified by bootstrap on every run | HELD |
| 10 | No task-specific intelligence in integration code | harness fixes (held-out resume, failure capture) and all mutations are task-agnostic; no mutation names a task id or answer | HELD |
| 11 | Only approved changes define generations | PRs #1–#3, each reviewed and merged by the user; the agent merged nothing on its own authority | HELD |
| 12 | Generation ↔ exact commit | annotated tags `exp2-g001..003` on merge commits; held-out rounds verify the recipe byte-identical to the measured tag; `run_metadata.json` records `freeze_fingerprint` | HELD |
| 13 | Held-out result ↔ generation | vault keyed by `generation_NNN`; reveal cross-checks fingerprints and refuses mixed curves | HELD |
| 14 | Metric = held-out passed / T | as revealed: 3/8, 3/8, 2/8, 2/8 | HELD |
| 15 | No `pass^k` for generations | summary states the ±18 pp band; no `pass^k` anywhere in the revealed artifacts | HELD |
| 16 | Failed/rejected attempts preserved | no mutation was rejected; both D8 halt decisions, the not-targeted failure modes, and the seq-1 void are first-class records | HELD |
| 17 | Debug obeys full isolation | identical machinery to the full experiment (same runner, vault, reveal) | HELD |
| 18 | Task assignment reproducible | committed `split_manifest.yaml` (screen exclusion documented in header); rounds select tasks from the manifest only | HELD |
| 19 | Reveal only after the final generation | `reveal.py` refuses without the final tag; ran after `exp2-g003` | HELD |
| 20 | Configurable without changing invariants | `protocol:` block in the lock; D10 re-sizing happened by editing values, not machinery | HELD |

## §27 artifact inventory

`experiment.yaml` (+ value-copies of `benchmark_lock.yaml` and `split_manifest.yaml`)
satisfy §27's `config.yaml`; `generation_000..003/` realize `generations/H0..H3/`;
`improvement_records/gen_00N_to_00M.yaml` realize `H{N}_to_H{M}.yaml`;
`held_out/results_by_generation.csv` and `task_generation_matrix.csv` present, plus
`transitions.csv` and `retention.csv` beyond the minimum; `summary.md` present. The
held-out artifacts were inaccessible until this reveal (guardrails 4/5/19 above).

## Phase 4 validate criterion: loop mechanics

Under seq 2 the loop ran with zero manual patching mid-run. The two harness fixes
found by seq 1 (held-out resume of a measured-but-incomplete round `ce10da7`;
root-cause capture `9787585`) landed before the seq-2 freeze and are part of its
machinery, not mid-run patches.
