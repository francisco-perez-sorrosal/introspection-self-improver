# §29 guardrail walk — experiment 008_stratb-bm25-luna56

Walked 2026-08-17 at close, after `make reveal`. Each of the twenty implementation guardrails
in `self_improving_agent_evaluation_protocol.md` §29 is answered with the artifact that
settles it, not with an assertion.

**Autonomy note, stated once.** `protocol.require_human_approval` was frozen **false** by plan
D28 (user-directed, re-registering D23's envelope), so guardrail 11's human gate is satisfied
by a pre-registered delegation rather than by a per-PR human review. That is a *frozen*
deviation, recorded in the lock before the first episode was spent — not a waiver applied
afterwards. Branch protection and the four required CI checks stayed on throughout; every one
of the six PRs merged green.

| # | Guardrail | Verdict | Evidence |
|---|---|---|---|
| 1 | Batches and held-out disjoint | **HELD** | `benchmark/split_manifest.yaml`; `propose_split.py --verify` passed at freeze and `make check` re-verified on every commit. The 8 batch tasks and the 28 held-out tasks share no member. |
| 2 | Batches disjoint from one another | **N/A by design** | `batch_mode: fixed` — the same eight tasks are measured under every generation. This is the design under study (D17/D23/D28) and the manifest's `verify` enforces the *identity* of the seven lists rather than their disjointness. |
| 3 | Held-out partition fixed before H0 | **HELD** | Partition frozen and committed at `8396739`, before any H0 episode ran. The freeze snapshot `experiment.yaml` (fingerprint `sha256:fea4ae1c…`) was written by the first non-PROVISIONAL run and matched by every later run. |
| 4 | No inspection of held-out evidence during optimization | **HELD** | All seven held-out rounds ran on the local lane into `~/.sia_vault`, out of tree. No `results/**/held_out/` path existed until `make reveal`. Every diagnosis in this experiment cites `generation_NNN/batch_NN/` artifacts or platform conversation ids; none cites a vault path. |
| 5 | No aggregate held-out scores during optimization | **HELD** | The held-out runner's terminal prints completeness only — episode counts, manifest rows, incident classes. All seven rounds' terminals are in the session record and none carries a reward. |
| 6 | Target model fixed | **HELD** | `openai/gpt-5.6-luna`, asserted by the runner against `agents/agent.yaml` before every episode; a mismatch stops the run. One freeze fingerprint across all 15 `run_metadata.json` files. |
| 7 | User simulator fixed | **HELD** | `openai/gpt-5.6-luna`, `reasoning_effort: medium`, `timeout: 60`, unchanged in the lock for the whole experiment. Not re-screened, per D19 precedent — the model pair is unchanged and the 2026-08-15 luna screen (97/97) is current. |
| 8 | τ evaluator and task definitions fixed | **HELD** | No diff under `benchmark/vendor/`; the `immutable-paths` CI check passed on all six PRs. Reward was computed only by `tau2 evaluate-trajs` via `scripts/grade.py`. |
| 9 | Benchmark commit pinned | **HELD** | `fc0055dc4e0a316c3f83133267fbd6faaa770992`, in the lock and in the freeze snapshot. |
| 10 | No task-specific intelligence in integration code | **HELD** | The three extensions landed this experiment match a naming *convention* (`[a-z_]+_\d{4}`), a phrase class for a handoff request, and one tool name (`log_verification`). None encodes a document id, a gold value, a task id, or a per-task procedure; each runs unchanged on any episode. Reviewed per change in the PRs and the records. |
| 11 | Only approved harness changes define a generation | **HELD, by frozen delegation** | Six PRs (#17–#22), each merged green, each tagged `exp8-g001…g006`. Approval authority was the orchestrator's by pre-registered freeze (D28), and every decision is recorded with its reasoning in `improvement_records/` and `improvement_backlog.md` so it can be audited as a human gate would have been. |
| 12 | Every generation maps to an exact commit | **HELD** | Tags `h0-baseline` (`b76f274`) and `exp8-g001…g006`; each record names `source_commit` and `candidate_commit`. Every batch round's manifest carries `arm_sha_ok: true` against the pushed arm — 168/168 rows. |
| 13 | Every held-out result maps to its generation | **HELD** | `make heldout GEN=generation_00N` refuses a recipe that is not byte-identical to that generation's tag, and refuses to measure H_N before batch_N is graded with an accepted record. `held_out_result` was stamped into the six records by `make reveal` and by nothing else. |
| 14 | Default metric is held-out passed / held-out total | **HELD** | `summary.md` reports it as expected count and percentage per generation, with the ±5 pp band stated. |
| 15 | No `pass^k` for generations | **HELD** | The term appears nowhere in this experiment's records, backlog, summary, or closure. Per-task cells are pass rates over three trials (D18); `pass^k` from τ's own metrics panel is never used cross-generation. |
| 16 | Failed and rejected attempts kept in the record | **HELD** | Two changes were reverted as first-class changes (C1 at gen-002, F1 at gen-005), each with its own commit, record entry, and reasoning. One measured *inert* change (F1) is recorded as such rather than quietly dropped, along with the finding that its preflight was chance. One retirement (T3) was reversed and the reversal recorded. |
| 17 | Debug configurations obey the same isolation | **N/A** | No debug configuration ran. Probes and preflights ran on the locked domain with the frozen config, and their evidence is committed under `generation_00N/<probe>/` with a note that they are never cited as record provenance. |
| 18 | Task assignment reproducible from the manifest | **HELD** | `benchmark/split_manifest.yaml` carries the seven identical batch lists and the held-out 28, with the stratum of every batch task and every drop-and-reason in its header. `--verify` passes. |
| 19 | Reveal only after the final generation is frozen | **HELD** | `make reveal` ran after `exp8-g006` was tagged and pushed and after H6's held-out round completed; it refuses a missing final tag, a mixed-fingerprint curve, or a measurement for an identity generation. |
| 20 | Configurable without changing the invariants | **HELD** | Everything that moved this experiment moved in `benchmark_lock.yaml`'s `protocol:` block and the manifest. No invariant, adapter semantic, or contract file was edited; `contract/` and `benchmark/tau_adapter/` carry no diff. |

**Twenty guardrails: seventeen HELD, two N/A by design (2, 17), one HELD by frozen delegation
(11). None waived.**

## §27 artifact inventory

| artifact | present |
|---|---|
| `benchmark_lock.yaml`, `split_manifest.yaml`, `experiment.yaml` freeze snapshot | ✅ one fingerprint `sha256:fea4ae1c…` across all 15 runs |
| `generation_000…006/batch_01…07/` with manifests, bridge logs, graded results | ✅ 168 platform episodes |
| `held_out/generation_000…006/` | ✅ 588 local episodes, copied verbatim from the vault at reveal |
| `improvement_records/gen_000_to_001 … gen_005_to_006.yaml` | ✅ six, all schema v3, all validating |
| `improvement_backlog.md` with a `<!-- transition: … -->` stamp per transition | ✅ six stamps |
| `gates/a0a.json`, `gates/seam_canary.json` | ✅ both PASS, recorded before the first episode |
| step-4b probes | ✅ `generation_000/toolresult_probe/`, `generation_001/context_probe/` |
| `summary.md`, `batch_curve.json`, `held_out/trend_test.json`, `held_out/trend_fragility.json` | ✅ |
| `README.md` closure | ✅ |

## Loop-mechanics verdict

The loop ran **six generations fully autonomously with no procedural breach**: seven held-out
rounds, seven batch rounds, six diagnoses, six PRs merged green, six tags, one reveal. Every
mechanical gate that could fire did its job — the D26 backlog-stamp gate refused a record once
and was satisfied by writing the re-ranking it demanded; the cadence gates refused nothing
because the order was kept; the freeze fingerprint matched on all 15 runs.

**Seam health:** 168 platform episodes with **zero** disconnects, **zero** timeouts and zero
stall warnings; two `sandbox_seam_unclassified` and two `sandbox_tool_errors` on a single
episode (`task_096` t1, `batch_02`), which completed with evidence intact and is disclosed
here rather than rounded to "zero incidents". `pi_local_calls` is 0 across all 168 episodes,
correctly: every change this experiment landed was a hook, and hooks are not registered tools,
so the D24 suppression registry stayed empty and suppression never engaged. **The D24 seam
change was therefore exercised in its pump path and never in its suppressing path** — a limit
of this experiment worth naming, since D24 was the groundwork that motivated it.

**Spend:** platform batch \$2.6109 over 168 episodes; local held-out \$12.0334 over 588
episodes; probes and preflights ≈ \$2.4. **Total ≈ \$17.**

## Three process failures, recorded

None breached an invariant; all three are the loop's own conduct and are in the records.

1. **An inert change consumed a generation.** gen-004's F1 keyed on message role `tool` where
   this host spells it `toolResult` — a fact recorded in this experiment's own g=1 probe. H4
   was behaviourally identical to H3.
2. **A preflight manufactured a confirmation out of noise.** F1's three-trial local run showed
   its target behaviour 3/3 against a 0/12 baseline, for a change that never executed.
   Standing rule added at gen-005: verify an injection's text in a fetched conversation before
   reading any behavioural number from it.
3. **A target was retired on one round's evidence and un-retired two rounds later.** T3 was
   retired at gen-003 on the reading that `task_014`'s deciding request is always terminal;
   `batch_04` falsified it and the target's own change then produced 3/3. The correction is
   recorded rather than absorbed.
