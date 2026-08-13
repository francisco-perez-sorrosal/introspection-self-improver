# PLAN — Milestones to the Demonstrated Self-Improving Loop

**Status:** living tracker. Check boxes (with dates) as items land; where this file and
the code disagree, the code wins and this file gets fixed.\
**Specification:** `introspection_self_improving_agent_mvp_v2.md` (v2). The milestones
below are v2 §4's dependency-ordered workstreams grouped into four checkable stages; this
file owns milestone tracking only and introduces no design of its own. Invariants live in
`CLAUDE.md`, frozen values in `benchmark/benchmark_lock.yaml`, the seam mechanism in
`README.md`, and the per-generation procedure in `contract/protocol.md` — written at M4
from what actually ran, not before (v2 §4 W7).\
**Created:** 2026-08-12, against repo state verified the same day.

**Done means:** M4 closed — one complete evidence → signal → hypothesis → mutation →
result generation, accepted **or cleanly rejected**, recorded under
`results/experiment_<id>/generation_001/`, with `contract/protocol.md` written from the
generation that ran. That is the MVP.

------------------------------------------------------------------------

## Recorded decisions

| Decision | Value | Consequence |
|---|---|---|
| H1 — retrieval config (v2 §4 H1) | **`bm25`, pinned knowingly** | Comparability with published numbers is dropped; the caveat is recorded in the lock and `contract/constraints.md` at M1. Once bm25 is the *deliberate* freeze, retrieval-**usage** findings (query formulation, k, iteration, stopping) are attributable harness territory — the v2 §3.2 quarantine lifts because the backend is constant by choice. |
| Agent hosting | **Dev lane only** | `introspection dev` serves the recipe from a clean committed work-tree on the `target-agent` dev Runtime; no `deploy` anywhere in MVP scope (v2 §8). Staging pins remain the named upgrade path. |
| H2 — freeze scale (v2 §4 H2) | **Decided 2026-08-13**: `num_trials: 4`; full-domain checkpoint ×1; `experiment.id: bm25-sonnet46`; held-out enforcement procedural + outputs out of tree (v1 §22.10 level 2) | G0 ≈ $70 / ~6.5 h serial — the checkpoint's 97 episodes ≈ $25 and its number is labeled single-trial wherever reported. Each generation ≈ $60–90 / 5–7.5 h. Basis: v2 §3.3. |

## Operating model (summary — design detail is v2 §5)

Claude Code **is** the orchestrator: it runs make targets via Bash (multi-hour rounds in
the background, resume as the safety net), reads manifests/lock/split, drives the
`introspection` CLI for evidence, invokes the plugin skills `operate` (diagnosis → answer)
and `improve` (mutation → PR), and authors PRs with git + `gh`. It never merges and never
touches frozen surfaces — machinery enforces both. The **human** owns exactly: the M1
freeze values, PR review/merge, accept/reject sign-off, and budget go/no-go at
checkpoints. Artifacts are the interface between sessions (v2 §5.1): a generation session
starts from episode manifests, the lock, the split manifest, and prior learning records —
never from ambient conversation state. The τ-Knowledge paper, the leaderboard, and
anything test-split stay out of the orchestrator's context.

Per generation (~1 day wall clock serial, v2 §5.10):

1. **Round** — pre-flight (lock assertions, clean tree at the arm SHA, no connected `tau`
   binding) → background round → `make grade` → manifest completeness assertions.
2. **Diagnose** — harvest 1 immediately (outcome table, within-task divergent pairs as
   primary controls, trajectories, open codes); harvest 2 after the ~40-min eligibility
   window (observations, patterns, prevalence via `metrics query`) → signal + hypothesis
   → learning-record draft.
3. **Propose** — `improve`: one mechanism inside the mutable table → branch
   `gen-NNN/<slug>` → PR citing conversation ids, prevalence, predicted effect → human
   review (the approval gate).
4. **Validate & decide** — both arms paired and adjacent, arm SHA asserted per
   conversation → trace review → accept / reject / directional → record → close out.

------------------------------------------------------------------------

## M1 — Freeze the experiment (v2: W0 + H1 + H2 + W2)

Decisions plus documentation truth. No new machinery.

Tasks:

- [x] **W0 truth pass** — five stale items, each fixed to read true against the code (2026-08-13):
  - [x] `contract/protocol.md` — dropped the claim that Operate is blocked on a missing
        dev-lane transport; the honest blocker is now the W3 evidence join (M2), and the
        fidelity item carries v2 §4 W4's re-specification.
  - [x] `results/experiment_dummy/generation_000/README.md` — delete-at-close replaced
        with retitle-and-archive (`transport_platform.py:237`); the platform row and
        detail table refreshed against the run actually on disk (reward 0.0, $0.2520,
        conversation `019ff93b…`, sha `e366b828…`).
  - [x] `contract/constraints.md` — "not worked around here" replaced with the truth:
        `scripts/grade.py` injects the run's recorded retrieval config into the
        evaluator's environment rebuild; the reward function stays τ's.
  - [x] `benchmark/benchmark_lock.yaml` — per-episode-bridge-port comment fixed: one
        run-scoped bridge, single-episode-safe (`run.py`).
  - [x] `target-agent/README.md` — `ai.model` → the legacy `model.name` spelling actually
        used; phantom `session` mutable-key reference removed.
- [x] **H1 executed as decided** (2026-08-13) — `retrieval_config: bm25` re-commented as
      the deliberate freeze; comparability-dropped caveat recorded in the lock and
      `contract/constraints.md`; `gen_policy_region.py --check` confirms the policy
      region regenerates unchanged from bm25.
- [x] **H2 decided** (2026-08-13) — `num_trials: 4`, checkpoint ×1, budget approved;
      `max_concurrency` stays 1, `seed` stays 300; experiment named `bm25-sonnet46`;
      `frozen.status` → `FROZEN` with every value re-decided or re-affirmed.
- [x] **W2 split** (2026-08-13) — `tau_adapter/split.py` + `scripts/propose_split.py`
      (stratified over `reward_basis` 88 DB / 9 ACTION, dominant required-document
      category, doc count; seed 20260812) proposed 30/15/20; frozen into
      `benchmark/split_manifest.yaml` with the enforcement strength in the header;
      `--verify` is the standing mechanical check; 16 tests in
      `benchmark/tests/test_split.py`.

Exit criteria:

- [x] `grep -c PROVISIONAL benchmark/benchmark_lock.yaml` → 0, and the experiment id derives
      to `001_bm25-sonnet46` (`experiment_id.py --dir` → `experiment_001_bm25-sonnet46`)
      (2026-08-13; frozen as `experiment.id: bm25-sonnet46`, renamed the same day to the
      seq+name scheme — `experiment.seq: 1` + `experiment.name: bm25-sonnet46`, results
      migrated to `results/experiment_001_bm25-sonnet46/`).
- [x] `benchmark/split_manifest.yaml` holds three disjoint lists (30/15/20), ACTION tasks
      in 3/1/2 — `scripts/propose_split.py --verify` passes (2026-08-13).
- [x] The five W0 items read true against the code (2026-08-13).
- [x] `make check` passes and the 92-test suite is green locally (2026-08-13).
      **CI pending**: both GitHub workflows must go green on the commit that lands M1 —
      the box that closes M1 for good.

## M2 — Evidence spine and gates: make a platform sweep trustworthy (v2: W3 + W5 + W4)

Build tasks (W3 + W5):

- [x] **Sweep-safe episode labels** (2026-08-13) — post-run retitle pass in `run.py`:
      every platform task renamed `τ²-bench <domain> <task_id> trial<k> gen<NNN>
      [exp:<id>]` from τ's own record once it exists (the factory never learns its
      simulation, so ground truth beats threading — v2 §4 W3.1).
- [x] **`episode_manifest.jsonl`** (2026-08-13) — `tau_adapter/manifest.py`, pure
      derivation from `results.json` + recorded accounting/incidents, emitted beside
      `run_metadata.json` by every runner (seam and stock anchor alike).
- [x] **Clean-tree assertion + post-round arm assertion** (2026-08-13) — platform runs
      refuse a dirty served surface (`target-agent/`, `.introspection/`) unless
      `--allow-dirty` marks every row `arm_sha_ok: false`; after any platform round every
      conversation's `recipe_git_commit_sha` is asserted against the arm SHA, exit 1 on
      mismatch (W3.3–W3.4).
- [x] **Queue-tolerant accounting** (2026-08-13) — N from τ's simulation rows
      (infrastructure placeholders included); every created platform task registered by
      the transport, orphans (created-but-unreferenced: τ retried past them) counted in
      `run_metadata.json` (W3.5).
- [x] **Resume + incident accounting** (2026-08-13) — τ's own checkpoint/resume adopted
      (`auto_resume`, keyed (trial, task, seed); the completion sentinel distinguishes
      interrupted-resume from completed-refuse); stall/409/prompt/stream counters ride a
      per-episode sink from bridge + transport into the manifest (W5.2); interrupted runs
      archive their in-flight task at teardown instead of idling the sandbox (W5.3).
- [x] **Round make targets** (2026-08-13) — `discovery` / `validation` / `checkpoint`
      (platform-lane by default, `ARM=`-aware, resume-friendly), plus `gate_a0a`,
      `fidelity_gate`, `anchor_stock`. `--split test` deliberately does not exist — the
      runner offers no button for the held-out split; test tasks run only inside the
      checkpoint.

Gate runs (W4 — run under the M1 freeze; blocking gates re-run for any new experiment):

- [x] **A.0a — pipe semantics** (blocking) — PASS 2026-08-13: 110-test adapter suite +
      mock smoke (4/4 completed), verdict at `generation_000/gates/a0a.json`.
- [ ] **A.0b — cross-lane consistency** (blocking): `make fidelity_gate` — task_004 +
      task_001 + task_003 (ACTION + 2×DB from discovery) × 4 trials × both lanes.
      **First run 2026-08-13: FAIL, recorded at `generation_000/gates/a0b.json`** — the
      aggregate agreement held (pass¹ 0.083 local vs 0.25 platform, overlapping Wilson
      intervals) but 3/12 platform episodes ended in `timeout` with 5–6 rendezvous stalls
      each, versus 12/12 clean locally. Diagnosis: the pre-registered platform divergence
      (`contract/constraints.md` §platform-lane 4a) observed for the first time —
      narration-then-call inside one run hands τ's floor to the user simulator while the
      sandbox is parked on the bridge; Pi's 120s tool timeout × ~5 retries eats the 600s
      episode budget. Remedy (transport-level reassembly) in flight; gate re-runs after.
- [ ] **A.0c — stock-agent anchor** (informational): `make anchor_stock` — staged,
      fires on user go (≈ $15–25 / 1.5–2 h). Under bm25 it anchors the scaffold delta,
      not published comparability.

Exit criteria:

- [x] A deliberately interrupted sweep resumes without re-spending completed episodes
      (2026-08-13: mock round interrupted at 2/4 trials — no completion sentinel — rerun
      skipped every done (trial, task, seed) pair, ran only the remainder, closed with a
      4-row manifest and `resumed: true`).
- [x] The manifest joins every episode → named conversation + commit, with completeness
      flags (2026-08-13: live 4-trial platform round — 4/4 rows joined with
      `arm_sha_ok: true`, `evidence_complete: true`, per-episode cost; retitles 4/4
      applied, labels on the platform task rows and in the local dashboard's episode
      table; the round also caught a real τ retry — 5 tasks created / 4 referenced /
      1 orphan — with its 409 + settle-timeout + stall counters in the record).
- [ ] A.0a and A.0b PASS recorded; A.0c numbers recorded. Gate cost ≈ $30–50 actual.

## M3 — G0: graded baseline + first harvest (v2: W6)

Tasks:

- [ ] Discovery round (30 × trials) and validation round (15 × trials) on the platform
      lane; grade; manifests emitted; completeness asserted per v2 §5.2 post-flight.
- [ ] **Competence floor check** — ≥20–25 % pass¹ on discovery. Below it: strengthen the
      G0 recipe's basic competence (v1 §13.1) and rerun. **Do not proceed to M4 below
      the floor.**
- [ ] Full-domain checkpoint at the H2-decided trial count.
- [ ] **First observation/pattern harvest**, including the explicit dev-lane analysis
      verdict: an `introspection.observation` event for a platform conversation ≥40 min
      after episode end. If the assumption fails, harvest 2 degrades to
      metrics-over-spans + manual clustering and the generation proceeds with its
      evidence tier stated (v2 §5.4 fallback).

Exit criteria:

- [ ] pass¹ and pass^k per split, N stated, recorded under
      `results/experiment_<id>/generation_000/`.
- [ ] Floor verdict recorded; dev-lane analysis-assumption verdict recorded.
- [ ] Budget actuals vs v2 §3.3 appended. (Estimate at the decided scale — trials=4,
      checkpoint ×1: ≈ $70 / ~6.5 h serial.)

## M4 — G1: one full improvement generation, then write the protocol (v2: W7)

Tasks:

- [ ] Execute the operating-model loop end to end once: operate → signal (measured
      prevalence, cited conversation ids, within-task pairs) → learning record →
      improve → PR `gen-001/<slug>` → human review → paired validation, both arms →
      trace review → accept / reject / directional →
      `results/experiment_<id>/generation_001/`.
- [ ] `contract/learning_record.schema.yaml` lands, instantiated from v2 §5.6.
- [ ] `contract/protocol.md` written **from what actually ran** — only after the
      generation closes.

Exit criteria:

- [ ] One accepted or cleanly rejected candidate with the complete evidence → signal →
      hypothesis → mutation → result chain, every claim traceable to conversation ids.
- [ ] Schema committed; `protocol.md` no longer says "Not yet written".
- [ ] **The loop is demonstrated — MVP complete.** Cost ≈ $60–90 / 5–7.5 h actual.

------------------------------------------------------------------------

## After M4 — steady state (not a milestone)

Repeat the M3/M4 generation shape for G2+ at ~$60–90 and ~1 day each. Final-generation
full-domain checkpoint; generation curves (pass¹/pass^k per split per generation) in the
dashboard at close-out. MVP-B — the target agent holding write access to its own recipe —
stays deliberately out of scope (v2 §8).

## Conventions

- One milestone in flight at a time; if a milestone's scope grows mid-flight, stop and
  re-plan rather than silently expanding.
- Check a box by appending the landing date: `- [x] … (2026-08-15)`.
- Budget figures above are §3.3 estimates until replaced by recorded actuals at M3/M4.
