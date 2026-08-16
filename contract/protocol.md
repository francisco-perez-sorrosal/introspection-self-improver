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
2. **Partition**: `make propose_split` (wraps `propose_split.py`; review the printed
   proposal, then freeze with `WRITE=1`); `--verify` must pass. Exclusions are
   documented in the manifest header, evidence committed beside it
   (`benchmark/data/user_sim_screen.json`). Exclusions carry the crashers AND the
   experiment's decision-row pool discipline: seq 4 (plan D11) additionally excludes
   all 20 seq-2 tasks, so nothing a prior loop was tuned on — and nothing a prior
   reveal exposed — reappears anywhere in the new partition.
3. **Freeze**: set `experiment.seq`, protocol block (G/B/T), flip `frozen.status` to
   FROZEN; `make reset_h0` (byte-identity to `h0-baseline`); commit; `make gate_a0a`
   (blocking) and commit the PASS record — the first run writes the freeze snapshot
   that every later run must match.

## Per generation g (H_g is current, tagged; g starts at 0)

**The cadence is a guarantee, not a habit** (user-ratified 2026-08-16). An experiment of
G generations is exactly: *measure H0 on the held-out set → [batch → diagnose → improve →
merge+tag → measure H_(g+1) on the held-out set] × G → reveal* — the baseline is measured
before any learning, every harness that learned is measured, and the sequence always ends
with the latest harness's held-out measurement. Three mechanisms enforce it, so the order
cannot be lost to forgetting: **(a)** `run.py` refuses `--batch N` until H_(N-1)'s
held-out round is graded in the vault (existence of the graded artifact by path — nothing
in the vault is opened) and the recipe surface is byte-identical to H_(N-1)'s tag, both
resolved through the identity chain (an identity/rejected transition carries its
predecessor's tag and measurement forward, D5); **(b)** the held-out runner refuses a
recipe that is not byte-identical to the generation it claims to measure — and, for
H_N (N ≥ 1), refuses to measure at all until batch_N is graded and the transition record
exists with outcome accepted, so a generation cannot be measured that no learning round
produced (a skipped batch would otherwise be invisible: merge, tag, measure, cite older
evidence), and an identity generation is refused before the spend rather than at reveal;
**(c)** `make reveal` refuses to close the experiment while any non-identity generation
H0…H_G lacks its measurement — the final harness cannot go unmeasured, because without
its round there is no reveal. A skipped baseline is not merely late: once the next merge
moves the recipe, (b) makes the missed measurement unrunnable — which is why (a) exists.
Together (a) and (b) make each seam bidirectional: a batch cannot run before its
generation's measurement, and a measurement cannot run before its generation's batch.

1. **Hidden measurement of H_g**: `make heldout GEN=generation_00g`. Local lane only,
   sealed vault, completeness-only terminal (counts, seam incidents, failure classes —
   never rewards). If INCOMPLETE, rerun the same target: τ resumes missing pairs and
   replaces `infrastructure_error` placeholders; completed episodes are never re-spent.
   The round refuses a dirty recipe tree and verifies byte-identity to H_g's tag.
2. **Improvement batch**: `make batch B=<g+1> GEN=generation_00g` (platform lane,
   `--max-concurrency 2` to keep sandbox-provisioning contention out of the evidence).
   Check the manifest: every row
   should be `evidence_complete`, `arm_sha_ok`, with only benign `stream_reattaches`,
   and `pi_local_calls` consistent with the recipe (nonzero only when the registry is
   non-empty; D24).
   The graded read is visible by design; state it as n/B. On B1 it doubles as the D8
   viability read: 0/B or B/B → surface to the user before proceeding.
3. **Diagnose (`operate` skill)**: export all B conversations
   (`introspection conversations get --ids-file …`), read them in full, and read the
   graded `action_checks`/`db_check` from `batch_NN/graded/updated_results.json` —
   field-level diffs for near-misses. Try the observation harvest
   (`introspection events list --event-name introspection.observation`) after the
   ~40-min window; when it returns nothing, say so and use the full-population
   transcript read as the fallback — at these batch sizes it is the stronger evidence
   tier anyway. Open-code failure modes;
   prevalence is n/B by enumeration. Never read anything held-out.
4. **Decide with the user** — two questions with different shapes. Proceed / identity /
   halt is exclusive and stays a single choice. The detected improvements are not:
   present every mode with prevalence and conversation ids as a **multi-select**, and
   the user opts into any subset — or all — as approved mutation targets. Approved
   targets land in `results/experiment_<id>/improvement_backlog.md` (mechanism,
   evidence pointers, approval date, status: pending / consumed-by-gen / retired).
   Targets carry forward re-ranked against each new batch's evidence; an item later
   contradicted is retired with the reason recorded, never silently dropped.

   Then **compose the improvement set** (plan D22, from seq 6; decided ahead of its
   first run by user direction, to be trued up against what actually runs): the next
   generation lands **any number of changes**, drawn from the approved targets, and the
   orchestrator proposes the set it judges most likely to generalize — never a
   pick-one-of-N menu. Present it as a per-change table — mechanism, surface, evidence
   (n/B + conversation ids), its own falsifiable prediction, its risk — and the user
   opts individual changes in or out. Composition rules:
   - Each change is **one coherent mechanism** (the `improve` skill's discipline,
     held per change, not per generation) and would justify landing on its own.
   - No two changes in a set may interact on the same behavior; candidates that
     interact are either genuinely one mechanism, or the weaker-evidenced one waits.
   - The surface is part of the diagnosis, and the structural surfaces are first-class
     under D24 (Pi-local suppression, `constraints.md` divergence 6): extension tools,
     sub-agents, and the no-tool-call extension hooks are live; a *declared* skill is
     measurably inert on this seam, so skill-shaped judgment is delivered by hook
     injection (wiring and measured verdicts: sia's `recipe-growth` reference +
     `improve/capability-set`). Seq 4 + seq 5 measured that *an instruction added to a
     prompt does not inherit the scope its author reasoned about*; seq 6 added the
     sharper form (*the escape clause is what the model optimises against*) — when the
     mechanism is judgment, scope, verification, or arithmetic, prefer a structural
     surface. **After ≥3 prior prompt mutations on one surface, a prompt-text-only set
     is no longer self-certifying: the next set includes at least one
     non-`instructions` change, or records a `surface_exhausted` finding backed by a
     committed step-4b probe naming the fact that blocks each structural alternative.**
     A paragraph alone does not discharge the flag.
   - A **revert** of a prior change whose prediction the batch refuted is a
     first-class change, enabled by per-change commits (step 5).
   G bounds generations, not changes; per-change attribution inside a set is
   **mechanistic** — each prediction is scored against the next batch — while the
   statistical read stays at the generation level, and every record says so.

4b. **Probe an untried surface — one episode, evidence committed.** Required at g=0;
   afterwards whenever the concentration flag fires or a target's mechanism names a
   surface this experiment has not exercised. On a throwaway `probe/<slug>` branch,
   wire the minimal artifact and run one **work-tree-faithful** episode: `make smoke
   TRANSPORT=local` (mock) or `make single_task TRANSPORT=local` (locked domain). The
   platform lane cannot serve an unmerged branch — it pins the recipe to pushed main,
   and `--allow-dirty` runs pushed main anyway with `arm_sha_ok=false` (measured:
   `benchmark/probes/2026-08-16-surface-probes/` P3) — so platform-side verification
   of a landed surface happens post-merge. Delete the branch; commit the evidence
   (markers, manifests, verdict) under `results/experiment_<id>/generation_00g/
   <probe>/` — `benchmark/probes/<date>-<slug>/` when no freeze is open — citing run
   ids **in the probe evidence, never as record provenance** (a probe precedes its
   batch, and provenance validates against batch manifests). The verdict updates
   `recipe-growth.md`'s surface table: measured, never inherited. Probe runs reuse the
   current experiment tree only with a non-colliding suffix, and leave nothing behind
   in a closed experiment's record.
5. **Mutate (`improve` skill)**: the approved set on branch `gen-00<g+1>/<slug>`,
   **one commit per change** — each message naming the mechanism and its prediction,
   because the commit is the unit of selective revert — touching mutable surface only
   (`SYSTEM.md` `<instructions>`; recipe skills/tools/sub-agents per
   `references/recipe-growth.md`; the `<policy>` block is frozen benchmark text).
   `make check` must pass, plus `make smoke` when any change is mechanical (tools,
   sub-agents, wiring). Push; open **one PR carrying the whole set**, citing per-change
   evidence, predictions, and what is deliberately not targeted. Return the work tree
   to `main` (it must keep serving H_g until the merge).
6. **Record as it happens**: `scripts/improvement_record.py --scaffold g --write`,
   fill evidence/signals/counterevidence/hypothesis and the per-change `changes` list
   (schema v3: mechanism, surface, evidence, expected_effect, risk, commit per item,
   plus per-clause falsifiers for `instructions` changes — see step 5's adversarial
   wording review); verify, and update the backlog in the same transition (its
   per-transition marker is validated with the record). Conversation ids come from the
   manifest — never from memory; **quoted instruction text comes from `git show`
   against the landed commit — never from memory** (a verdict attributed to words the
   text does not carry propagated through three seq-6 documents).
7. **Human gate**: the user reviews and merges (or declines) the PR. The agent never
   merges on its own authority. On merge: tag the merge commit `exp<seq>-g00<g+1>`
   (annotated, pushed), set the record's `outcome: accepted` + `candidate_commit`,
   re-verify, commit. On decline: `outcome: rejected` (or `identity`), H_{g+1} = H_g,
   the next held-out round is skipped and the result carries forward at reveal.

## Close (after the final transition)

1. Final hidden measurement: `make heldout GEN=generation_00G` against the final tag.
2. **Diagnose the endpoint batch round** — any design whose final harness runs an
   observable batch round (`batch_mode: fixed` runs batch_G+1 under H_G) gives that
   round the same diagnosis pass step 3 gives every round: counters, behavioral dials,
   the final change's prediction scored — minus any mutation. Findings land in the
   closure README; a measurement-only round is consumed by no transition and gets no
   improvement record. The final harness's behavioral profile is part of the result —
   seq 6 paid 24 episodes for its endpoint and read only the reward bits, leaving its
   own last prediction unscored and its transfer dial unmeasured until the independent
   review.
3. `make reveal` — the one sanctioned read of the vault: copies rounds verbatim,
   computes progression/matrix/transitions/retention and the pre-registered trend
   test (plan D11: one-sided over measured generations, identity generations
   excluded; machine-readable at `held_out/trend_test.json`), stamps
   `held_out_result` into every record, writes `summary.md` with the scale-aware
   noise band, the trend verdict, and the trend-fragility report
   (`held_out/trend_fragility.json`: leave-one-task-out and endpoint-cell
   sensitivity — a significance that rests on one task's cells is reported as such,
   next to the p-value it qualifies). Refuses a
   missing final tag, a mixed-fingerprint curve, or a measurement for an identity
   generation.
4. Walk protocol §29 and record it (`GUARDRAIL_WALK.md` beside the summary), including
   the §27 artifact inventory and the loop-mechanics verdict.
5. Numbers are always labelled with their set and N; batch reads are diagnosis
   evidence, not the progression metric; effects inside the band are directional only.

## What seq 2 measured about the procedure itself

The loop ran end to end with zero mid-run mechanics patching: freeze → 4 hidden
measurements → 3 batches → 3 diagnoses → 3 user-gated PRs → 3 tags → reveal, seam
incident-free throughout. Wall-clock ≈ 3.5 h including review latency; spend ≈ $32
(manifest sums: $19.92 local — agent + user-sim — and $9.05 platform conversation
billing, the τ-side user-sim on that lane being manifest-invisible, plus ~$3
screens/probes; an earlier "≈ $11" note here undercounted by omitting the local
lane's manifests). The endpoint at T=8 was
directional-negative (−1 task, inside ±18 pp): the debug scale demonstrates the
loop, not the claim. The claim path was re-staged from this run's own data (plan
D11, `results/experiment_002_bm25-sonnet46/SIZING_ANALYSIS.md`): seq 4 runs the
POWERED scale — G=5, B=8, T=28, powered for a ~+4–5 pp/generation loop, with a
pre-registered one-sided trend test over H0…H5 at α=0.05 as the primary
instrument — and the full T=47 run defers to seq 6 (parity convention, plan D15).
