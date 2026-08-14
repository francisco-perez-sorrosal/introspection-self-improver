# Per-generation procedure

Written 2026-08-14 from the debug experiment that actually ran (seq 2,
`002_bm25-sonnet46`: three accepted generations, revealed) — per the repo's
written-from-what-ran doctrine. The design this instantiates is
`self_improving_agent_evaluation_protocol.md`; the permission envelope is
`constraints.md`; frozen values live in `benchmark/benchmark_lock.yaml`. Where this
file and the code disagree, the code wins and this file gets fixed.

## 0. Freeze (once per experiment)

1. **Screen the pool** before any partition exists (no firewall applies yet):
   `benchmark/scripts/screen_user_sim.py` drives τ's own orchestrator over every pool
   task with a scripted LLM-free agent — real user-sim, real user tools, crash
   verdicts only. Where the screen cannot reach a failure class (real-agent-conditioned
   crashes), probe suspects directly with τ's stock agent (`tau2 run … --agent
   llm_agent`), pre-partition. Seq 2 exists because seq 1 died at H0 on exactly such a
   defect (task_034; upstream tau2-bench#470).
2. **Partition**: `propose_split.py --write --exclude <crashers> --note <why>`;
   `--verify` must pass. Exclusions are documented in the manifest header, evidence
   committed beside it (`benchmark/data/user_sim_screen.json`).
3. **Freeze**: set `experiment.seq`, protocol block (G/B/T), flip `frozen.status` to
   FROZEN; `make reset_h0` (byte-identity to `h0-baseline`); commit; `make gate_a0a`
   (blocking) and commit the PASS record — the first run writes the freeze snapshot
   that every later run must match.

## Per generation g (H_g is current, tagged; g starts at 0)

1. **Hidden measurement of H_g**: `make heldout GEN=generation_00g`. Local lane only,
   sealed vault, completeness-only terminal (counts, seam incidents, failure classes —
   never rewards). If INCOMPLETE, rerun the same target: τ resumes missing pairs and
   replaces `infrastructure_error` placeholders; completed episodes are never re-spent.
   The round refuses a dirty recipe tree and verifies byte-identity to H_g's tag.
2. **Improvement batch**: `make batch B=<g+1> GEN=generation_00g` (platform lane,
   `--max-concurrency 2` for sandbox-quota cleanliness). Check the manifest: every row
   should be `evidence_complete`, `arm_sha_ok`, with only benign `stream_reattaches`.
   The graded read is visible by design; state it as n/B. On B1 it doubles as the D8
   viability read: 0/B or B/B → surface to the user before proceeding.
3. **Diagnose (`operate` skill)**: export all B conversations
   (`introspection conversations get --ids-file …`), read them in full, and read the
   graded `action_checks`/`db_check` from `batch_NN/graded/updated_results.json` —
   field-level diffs for near-misses. Try the observation harvest
   (`introspection events list --event-name introspection.observation`) after the
   ~40-min window; when it returns nothing, say so and use the full-population
   transcript read as the (stronger, at B=4) fallback. Open-code failure modes;
   prevalence is n/B by enumeration. Never read anything held-out.
4. **Decide with the user**: present the batch read, the modes with prevalence and
   conversation ids, and a recommended single mechanism. The user picks proceed /
   identity / halt, and the mechanism.
5. **Mutate (`improve` skill)**: one coherent mechanism, on branch
   `gen-00<g+1>/<slug>`, touching mutable surface only (seq 2: `SYSTEM.md`
   `<instructions>`; the `<policy>` block is frozen benchmark text). `make check` must
   pass. Push; open a PR citing conversation ids, prevalence, predicted effect, and
   what is deliberately not targeted. Return the work tree to `main` (it must keep
   serving H_g until the merge).
6. **Record as it happens**: `scripts/improvement_record.py --scaffold g --write`,
   fill evidence/signals/counterevidence/hypothesis/change; verify. Conversation ids
   come from the manifest — never from memory.
7. **Human gate**: the user reviews and merges (or declines) the PR. The agent never
   merges on its own authority. On merge: tag the merge commit `exp<seq>-g00<g+1>`
   (annotated, pushed), set the record's `outcome: accepted` + `candidate_commit`,
   re-verify, commit. On decline: `outcome: rejected` (or `identity`), H_{g+1} = H_g,
   the next held-out round is skipped and the result carries forward at reveal.

## Close (after the final transition)

1. Final hidden measurement: `make heldout GEN=generation_00G` against the final tag.
2. `make reveal` — the one sanctioned read of the vault: copies rounds verbatim,
   computes progression/matrix/transitions/retention, stamps `held_out_result` into
   every record, writes `summary.md` with the scale-aware noise band. Refuses a
   missing final tag, a mixed-fingerprint curve, or a measurement for an identity
   generation.
3. Walk protocol §29 and record it (`GUARDRAIL_WALK.md` beside the summary), including
   the §27 artifact inventory and the loop-mechanics verdict.
4. Numbers are always labelled with their set and N; batch reads are diagnosis
   evidence, not the progression metric; effects inside the band are directional only.

## What seq 2 measured about the procedure itself

The loop ran end to end with zero mid-run mechanics patching: freeze → 4 hidden
measurements → 3 batches → 3 diagnoses → 3 user-gated PRs → 3 tags → reveal, seam
incident-free throughout. Wall-clock ≈ 3.5 h including review latency; spend ≈ $11
(32 local + 12 platform episodes + screens/probes). The endpoint at T=8 was
directional-negative (−1 task, inside ±18 pp): the debug scale demonstrates the
loop, not the claim — T=47 carries the claim (plan D10 caveat, restated wherever the
curve renders).
