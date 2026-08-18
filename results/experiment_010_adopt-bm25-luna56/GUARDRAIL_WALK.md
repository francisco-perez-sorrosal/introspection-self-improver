# §29 guardrail walk — experiment 010_adopt-bm25-luna56

Walked 2026-08-18 at close, after `make reveal`. Each of the twenty implementation guardrails
in `self_improving_agent_evaluation_protocol.md` §29 is answered with the artifact that
settles it, not with an assertion.

**Autonomy note, stated once.** `protocol.require_human_approval` was frozen **false** by plan
D34 (user-delegated, re-registering D23/D28's envelope), so guardrail 11's human gate is
satisfied by a pre-registered delegation rather than by a per-PR human review. That is a
*frozen* deviation, recorded in the lock before the first episode was spent — not a waiver
applied afterwards. Branch protection and the four required CI checks stayed on throughout;
all seven mutation PRs (#25–#31) plus the two canary PRs (#23, #24) merged green.

| # | Guardrail | Verdict | Evidence |
|---|---|---|---|
| 1 | Batches and held-out disjoint | **HELD** | `benchmark/split_manifest.yaml`; `propose_split.py --verify` passed at freeze and `make check` re-verified on every commit. The 12 batch tasks and the 36 held-out tasks share no member. |
| 2 | Batches disjoint from one another | **N/A by design** | `batch_mode: fixed` — the same twelve tasks under every generation. The manifest's `verify` enforces the *identity* of the nine lists rather than their disjointness. |
| 3 | Held-out partition fixed before H0 | **HELD** | Partition frozen and committed at `6965f74`, before any H0 episode. Freeze snapshot `experiment.yaml` (`sha256:50553b93…`) written by the first non-PROVISIONAL run and matched by every later run. |
| 4 | No inspection of held-out evidence during optimization | **HELD** | All nine held-out rounds ran on the local lane into `~/.sia_vault`, out of tree. No `results/**/held_out/` path existed until `make reveal`. Every diagnosis cites `generation_NNN/batch_NN/` artifacts or platform conversation ids; none cites a vault path. |
| 5 | No aggregate held-out scores during optimization | **HELD** | The held-out runner's terminal prints completeness only — counts, manifest rows, incident and failure classes. Every round's terminal is in the session record and none carries a reward. Two rounds reported an incomplete count (H2 `infrastructure_error=2`, H3 `max_steps=1`, H5 `infrastructure_error=1`); those are failure *classes*, which the runner is designed to surface, not results. |
| 6 | Target model fixed | **HELD** | `openai/gpt-5.6-luna`, asserted against `agents/agent.yaml` before every episode. One freeze fingerprint across every `run_metadata.json`. |
| 7 | User simulator fixed | **HELD** | `openai/gpt-5.6-luna`, `reasoning_effort: medium`, `timeout: 60`, unchanged for the whole experiment. Screen currency confirmed at freeze against the 2026-08-15 luna screen (97/97). |
| 8 | τ evaluator and task definitions fixed | **HELD** | No diff under `benchmark/vendor/`; `immutable-paths` passed on every PR. Reward computed only by `tau2 evaluate-trajs` via `scripts/grade.py`. |
| 9 | Benchmark commit pinned | **HELD** | `fc0055dc4e0a316c3f83133267fbd6faaa770992`, in the lock and the freeze snapshot. |
| 10 | No task-specific intelligence in integration code | **HELD** | Two extensions landed. `compare-options.ts` encodes no product, threshold, document id or gold value — every candidate and attribute comes from the caller. `search-index.ts` (later reverted) echoed only ids the episode had already received and could not name an unseen document. Both reviewed per change in their PRs and records. |
| 11 | Only approved harness changes define a generation | **HELD, by frozen delegation** | Seven mutation PRs (#25–#31), each merged green, each tagged `exp10-g002…g008`; gen-001 was the pre-registered identity and lands no PR by design. Approval authority was the orchestrator's by pre-registered freeze (D34); every decision is recorded with its reasoning in `improvement_records/` and `improvement_backlog.md`. |
| 12 | Every generation maps to an exact commit | **HELD** | Tags `h0-baseline` (`28ec38c`) and `exp10-g002…g008`; each record names `source_commit` and `candidate_commit`. Every batch round's manifest carries `arm_sha_ok: true` — 324/324 rows. |
| 13 | Every held-out result maps to its generation | **HELD** | `make heldout GEN=generation_00N` refuses a recipe not byte-identical to that generation's tag, and refuses to measure H_N before batch_N is graded with an accepted record. It refused `batch_07` outright when H6's round had not completed — the cadence gate firing in anger, not in theory. `held_out_result` was stamped by `make reveal` and by nothing else. |
| 14 | Default metric is held-out passed / held-out total | **HELD** | `summary.md` reports expected count and percentage per generation with the ±5 pp band stated. |
| 15 | No `pass^k` for generations | **HELD** | The term appears nowhere in this experiment's records, backlog, summary or closure. Per-task cells are pass rates over three trials (D18). |
| 16 | Failed and rejected attempts kept in the record | **HELD** | Two changes were reverted as first-class changes (C5 at gen-007, C4 at gen-008), each with its own commit, record and reasoning. C5 is recorded as **measured inert**, with its inertness confirmed by its removal (`KB_search`/episode 11.6 both with and without it) rather than asserted. One provisional harm attribution (C5 → `task_003`) was **retracted** at gen-008 when the task did not recover. One falsifier is recorded as **mis-specified** (C3 clause 1, keyed on an absolute level rather than a delta). |
| 17 | Debug configurations obey the same isolation | **N/A** | No debug configuration ran on the locked domain. Probes and preflights ran with the frozen config, their evidence committed under `generation_00N/<probe>/`, and none is cited as record provenance. |
| 18 | Task assignment reproducible from the manifest | **HELD** | `split_manifest.yaml` carries the nine identical batch lists, the held-out 36, the stratum of every batch task, every drop-and-reason, and the pre-partition-information disclosure. `--verify` passes. |
| 19 | Reveal only after the final generation is frozen | **HELD** | `make reveal` ran after `exp10-g008` was tagged and pushed and after H8's held-out round completed 108/108; it refuses a missing final tag, a mixed-fingerprint curve, a measurement for an identity generation, or a pre-registered identity generation whose record says otherwise. |
| 20 | Configurable without changing the invariants | **HELD, with one recorded exception** | No invariant, adapter *semantic* or contract file was edited. One change did land under `benchmark/tau_adapter/` mid-experiment — the D35 round-resume contract fix — recorded as a plan decision row rather than a quiet commit, judged non-semantic (it changes only when a rerun into an existing round directory is permitted; nothing about trajectory construction, tool forwarding, D24 suppression, step accounting or grading), and gated by the runner's own staleness rule, which invalidated the seam canary and forced both `gate_a0a` and `gate_seam` to re-run and re-pass before the next round. |

**Twenty guardrails: eighteen HELD, one N/A by design (2), one N/A for absence (17), one
HELD by frozen delegation (11), one HELD with a recorded exception (20). None waived.**

## D33 attestation

**No in-loop session of this experiment opened held-out artifacts of any experiment.** Every
diagnosis in the nine transitions cites `generation_NNN/batch_NN/` artifacts, platform
conversation ids, committed probe evidence, or the domain's own knowledge-base documents.
Prior-experiment memory was read once at experiment start and consisted of
`improvement_records/` and `improvement_backlog.md` only — the batch-derived memory D33
permits. No `held_out/`, `summary.md`, trend or fragility artifact, task×generation matrix,
or per-task held-out section of any closure or review was opened at any point before
`make reveal` on 2026-08-18.

Recall digests named their sources at every generation boundary. One disclosure is recorded
in the manifest header rather than left implicit: while ranking pre-freeze screen candidates,
the freeze-time session read `experiment_004/generation_000/pilot_h0/graded/` — a pre-freeze
calibration pilot, outside every vault — whose 28-task list includes 8 tasks that became part
of this experiment's held-out 36. That is pre-partition screening information of the class
`contract/protocol.md` § 0 step 1 explicitly sanctions and D33 § 3 permits for freeze-time
design; it sized nothing and steered nothing, and no in-loop session consulted it.

## §27 artifact inventory

| artifact | present |
|---|---|
| `benchmark_lock.yaml`, `split_manifest.yaml`, `experiment.yaml` freeze snapshot | ✅ one fingerprint `sha256:50553b93…` |
| `generation_000…008/batch_01…09/` with manifests, bridge logs, graded results | ✅ 324 platform episodes |
| `held_out/generation_000…008/` | ✅ 864 local episodes, copied verbatim at reveal |
| `improvement_records/gen_000_to_001 … gen_007_to_008.yaml` | ✅ eight, all schema v4, all validating |
| `improvement_backlog.md` with a `<!-- transition: … -->` stamp per transition | ✅ eight stamps |
| `gates/a0a.json`, `gates/seam_canary.json`, `gates/suppression_canary.json`, `gates/power_envelope.json` | ✅ all PASS/REACHABLE, recorded before the first graded episode |
| pre-partition screen | ✅ `benchmark/probes/2026-08-17-seq10-screen/` — 38 candidates × 3 trials, 114 episodes |
| preflights | ✅ `generation_00N/g00M_preflight*/`, five sets, none cited as provenance |
| voided round preserved | ✅ `generation_001/batch_02_seam_incident/` with its own README |
