# Guardrail walk — experiment 004_powered-bm25-luna56 (protocol §29, walked at close, 2026-08-15)

Each item states the enforcing mechanism and the verdict for this experiment.

| # | Guardrail | Mechanism | Verdict |
|---|---|---|---|
| 1 | Batches ∩ held-out = ∅ | `propose_split.py --verify` at the start gate; partition re-verified pre-spend by every round | HELD |
| 2 | Batches pairwise disjoint | same verify; confirmed in use — B₁…B₅ share no task, which is why no cross-batch prevalence comparison was ever drawn | HELD |
| 3 | Held-out fixed before H0 | partition frozen at the `bc31f80` start gate, inside the freeze fingerprint `sha256:1c3a301e…`, before the first H0 episode | HELD |
| 4 | No held-out evidence during optimization | local-lane-only held-out (no platform evidence exists to leak); vault out of tree at `~/.sia_vault`; muted runner printed episode counts and incident totals only, never a reward; **zero vault reads before `make reveal`** | HELD |
| 5 | No aggregate held-out scores during optimization | aggregates computed at reveal and nowhere else (`reveal.py` is the only reader) | HELD |
| 6 | Target model fixed | `frozen.agent_model: openai/gpt-5.6-luna` in the fingerprint; runner refuses recipe/lock disagreement; **all five mutations touched `SYSTEM.md` `<instructions>` only** — `agents/agent.yaml` byte-unchanged across the experiment | HELD |
| 7 | User simulator fixed | `frozen.user_llm` + `user_llm_args` in the fingerprint; re-screened under the active pair at the start gate (97/97 survive) | HELD |
| 8 | τ evaluator + task definitions fixed | vendored pinned checkout, never edited. Tested under pressure: the nested-JSON action-check artifact (33%→62% of misses) was diagnosed as **frozen evaluator surface and deliberately left alone** — matching gold's JSON whitespace was explicitly rejected as grader-gaming | HELD |
| 9 | Benchmark commit pinned | `fc0055dc` (v1.0.1), verified by bootstrap on every run | HELD |
| 10 | No task-specific intelligence in integration code | no mutation names a task id, tool payload, or answer; the closest call was gen-004, which names `give_discoverable_user_tool` — a **policy-documented** tool of the domain, not a task-specific fact | HELD |
| 11 | Only approved changes define generations | PRs #4–#8, each merged on the user's explicit instruction; the agent merged nothing on its own authority, and each record's `human_approval` names the instruction that authorized it | HELD |
| 12 | Generation ↔ exact commit | annotated tags `exp4-g001..005`; held-out rounds verify the recipe byte-identical to the measured tag. Exercised for real: B₄ and B₅ ran on gate commits (`ae28005`, `3434466`) rather than merge commits, and each was **verified** byte-identical to its tag before any diagnosis was drawn | HELD |
| 13 | Held-out result ↔ generation | vault keyed by `generation_NNN`; reveal cross-checks fingerprints and refuses mixed curves | HELD |
| 14 | Metric = held-out passed / T | as revealed: 6/28, 8/28, 5/28, 6/28, 7/28, 4/28 — every figure reported with its count and its N | HELD |
| 15 | No `pass^k` for generations | absent from every revealed artifact; the ±9 pp band is stated instead | HELD |
| 16 | Failed/rejected attempts preserved | no mutation was rejected, but the record preserves more than that requires: **two mutations that demonstrably failed** (gen-002's prohibition misreading, gen-003's over-permission), the T3 retirement with its reason, the four unconsumed targets, and **T8's overstated ranking retracted** when `task_063` passed with 22 KB searches | HELD |
| 17 | Debug obeys full isolation | n/a — this is the powered experiment; identical machinery to seq 2 | HELD |
| 18 | Task assignment reproducible | committed `split_manifest.yaml`; exclusions header-documented with evidence at `benchmark/data/user_sim_screen.json` | HELD |
| 19 | Reveal only after the final generation | `reveal.py` refuses without the final tag; ran after `exp4-g005` and after H₅'s round completed | HELD |
| 20 | Configurable without changing invariants | `protocol:` block carried G=5/B=8/T=28 with no machinery change from seq 2 | HELD |

**All twenty held.** One is worth naming as more than a checkbox: guardrail 8 was the one under real
pressure, because the nested-JSON artifact was a standing invitation to "fix" grading in the harness's
favour. It was declined every time it appeared, and recorded so it could not be rediscovered as a defect.

## §27 artifact inventory

`experiment.yaml` (+ value-copies of `benchmark_lock.yaml` and `split_manifest.yaml`) satisfy §27's
`config.yaml`; `generation_000..005/` realize `generations/H0..H5/`;
`improvement_records/gen_00N_to_00M.yaml` realize `H{N}_to_H{M}.yaml`, all five verifying under
`improvement_record.py --verify`; `held_out/results_by_generation.csv` and `task_generation_matrix.csv`
present, plus `transitions.csv`, `retention.csv` and `trend_test.json` beyond the minimum; `summary.md`
present. Held-out artifacts were inaccessible until the reveal (guardrails 4/5/19).

Beyond §27: `improvement_backlog.md` — the approved-target ledger the per-generation procedure
requires, carrying nine targets with prevalence, evidence pointers, consumption status, one retirement
and one retraction.

## Loop-mechanics verdict

The loop ran end to end with **zero mid-run mechanics patching**: start gate, six sealed measurements
(168 episodes), five diagnosed batches (40 episodes), five human-gated PRs, five tags, five verified
records, reveal. **Zero seam incidents across all 208 episodes** — no stalls, 409s, prompt failures,
stream failures or sandbox queue waits in any round. One operational fact was learned and recorded
rather than worked around: the platform lane pins lineage to *pushed* `main`, so a freeze or record
commit must be pushed before a batch will run; `--allow-dirty` would have started the round at the
cost of `arm_sha_ok=false` on every row and was never used.

**The machinery is sound. The mutations were not.** That separation is the experiment's honest result
and is developed in `summary.md` and the reveal commit.
