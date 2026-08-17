# 2026-08-17 seq-10 batch candidate screen — measuring the incumbent H0 on 38 candidates

Run between seq 8 (REVEALED) and the seq-10 freeze, to satisfy plan **D34** (a batch
composed to hold **≥15 reachable failing cells at H0**), plan **D30** rule 3
(reachability-screened strata) and `contract/protocol.md` § 0 step 2. Seq 8's batch held
roughly five reachable failing cells and saturated by round 5 with a null primary; this
screen exists to make that impossible for seq 10.

**Pre-partition and pre-freeze**: no seq-10 partition existed when these ran, so no
manifest guard was armed and the exclusion was the screen's own responsibility. Verified
before launch and again here: **none of the 38 candidates is a member of the intended
held-out 36** (the legacy 28 + seq-2's 8 never-batched tasks), none is `task_034` (the
frozen-surface user-sim crasher), and none is a proven-walled task
(`task_026`, `task_028`, `task_070`, `task_072`, `task_082`, `task_096`). Every candidate
comes from **burned batch stock** — tasks some prior experiment already read in full as
batch evidence — plus the 8 seq-3/4 pilot tasks, which have never been in any partition.

- **Harness**: the incumbent H0, `target-agent/` byte-identical to tag `h0-baseline`
  (the D31 growth-parity scaffold anchor). `make reset_h0` reported "the recipe already
  was H0" immediately before the run; every manifest row carries
  `arm_sha 1a95cad7b06688cc4036185e60c9de8c700b4d0b`, `arm_sha_ok true`, `dirty_paths []`.
- **Lane**: local (`pi --recipe … --mode rpc`), the work-tree-faithful lane.
- **Configuration**: the seq-8 lock, unchanged — `banking_knowledge` / `bm25` /
  `openai/gpt-5.6-luna` on both halves / `num_trials: 3` / seed 300 / max_steps 200 /
  max_errors 10 / timeout 600 — i.e. exactly the configuration seq 10 freezes. Reward from
  τ's own grading via `scripts/grade.py`, never recomputed here.
  Freeze fingerprint of the run: `sha256:fea4ae1c…`.
- **Cost / wall-clock**: **$2.5742** over **114 episodes** (38 tasks × 3 trials), 18.2 min
  at `--max-concurrency 8`. **114/114 completed**; `make weather` 6/6 immediately before.
- **Incidents: none.** stall_warnings 0, zero_bridge_calls 0, all four sandbox seam
  counters 0, `infra_failure_classes` empty, `pi_local_calls` 0 (H0's registry is empty,
  as it must be).
- **Run directory**: written under the then-current lock's tree
  (`results/experiment_008_stratb-bm25-luna56/generation_000/seq10_screen`) with a
  non-colliding suffix, evidence copied here, run directory deleted — the convention in
  `../README.md`: a closed experiment's tree must not accrete post-closure runs.

## Why 38 candidates and not the runbook's ~24

Recorded as a deliberate deviation, per the D28 precedent that composition deviates from a
candidate list **by measurement**. Phase 5.10 budgets ~24 candidates ≈ $1.5; this screen
took 38 ≈ $2.6. The extra $1.1 buys the selection the whole experiment rests on: D34 names
batch composition as the load-bearing repair of precondition (a), and the 2026-08-16
anchor calibration measured that **single-trial history mispredicts a task's stratum
roughly a third of the time** (7 single-trial passers re-measured at 3 trials: two 3/3,
two 2/3, one 1/3, **two 0/3**). Under-screening is how seq 5, 6 and 8 each admitted tasks
with no dynamic range. The candidate set is the full burned-batch stock filtered to the
productive complexity band (2–9 gold actions, where every task ever measured in the
marginal band sits), plus the three previously-verified anchors.

## Results — per-task pass counts under H0, three clean trials each

| task | H0 rate | band | prior graded (batch-side only) |
|---|---|---|---|
| task_002 | **3/3** | anchor-grade | 1/1 seq-4 pilot; 3/5 anchor-calib |
| task_004 | **3/3** | anchor-grade | 1/1 seq-4 pilot; 3/5 anchor-calib |
| task_006 | **3/3** | **ANCHOR (frozen in)** | 22/22 lifetime; 3/3 anchor-calib |
| task_032 | **3/3** | **ANCHOR (frozen in)** | 22/22 lifetime; 4/4 anchor-calib |
| task_005 | 2/3 | marginal | 0/1 seq-4 batch |
| task_023 | 2/3 | marginal | 1/1 seq-4 batch; 2/4 anchor-calib |
| task_037 | 2/3 | marginal | 1/1 seq-4 batch; **3/3 anchor-calib** |
| task_076 | 2/3 | marginal | 20/22 lifetime (seq-8 batch) |
| task_003 | 1/3 | marginal | 0/2 (seq-2 batch + seq-4 pilot) |
| task_008 | 1/3 | marginal | 0/2 (seq-2 batch + seq-4 pilot) |
| task_014 | 1/3 | marginal | 23/52 lifetime (seq-5/6/8 batch) |
| task_055 | 1/3 | marginal | 0/1 seq-4 batch |
| task_057 | 1/3 | marginal | 17/22 lifetime (seq-8 batch) |
| task_063 | 1/3 | marginal | 1/1 seq-4 batch; 2/4 anchor-calib |
| task_089 | 1/3 | marginal | 1/2 (seq-2 batch); 1/4 anchor-calib |
| task_010 task_015 task_020 task_024 task_027 task_029 task_038 task_040 task_046 task_047 task_058 task_060 task_061 task_062 task_064 task_065 task_066 task_069 task_071 task_083 task_094 task_101 task_102 | 0/3 | zero | 23 tasks, none selected |

Pool-wide: **27/114 episodes (23.7%)**, 4 tasks at 3/3, 11 tasks in the 1/3–2/3 band,
23 tasks at 0/3.

## Findings

1. **The marginal band filled every slot, so the 0/3 tier was never needed.** Eleven tasks
   landed in 1/3–2/3 against ten open slots. D34's composition rule reads "marginal band
   preferred, reachability-classified 0/3 tasks **fill**" — with no fill required, seq 10's
   batch admits **no headroom tier and no walled task at all**. This discharges the D30
   reachability obligation by construction rather than by trajectory reading: *a task the
   incumbent H0 passes in at least one of three trials is demonstrably harness-reachable*,
   which is a stronger certificate than any classification of a never-passing task's
   terminal step. The 23 zeros were therefore **not** individually classified — the
   classification exists to decide admission, and none was admitted.
2. **The reserve anchor was not an anchor.** `task_037` measured 3/3 in the 2026-08-16
   calibration and **2/3** here, one day later, on a byte-identical harness. It is recorded
   as a marginal, not frozen in as a third anchor, and it is the clearest live instance of
   the standing lesson that a task's stratum is a measurement with a noise band — not a
   property. The two frozen anchors (`task_006`, `task_032`) reproduced 3/3 for the second
   consecutive screen and hold 22/22 lifetime each.
3. **Two new anchor-grade tasks exist** (`task_002`, `task_004`, both 3/3). They are
   recorded as verified reserves and deliberately **not** frozen in: every added anchor
   removes one movable task from the primary's power envelope (movable = B − anchors −
   walled), and D34 pins the anchor count at two for exactly that reason.
4. **Transfer discrimination is measurable on both sides again, and more cheaply than in
   seq 8.** Gold-transfer tasks now sit at three levels: `task_032` 3/3 (anchor, gold
   includes the transfer), `task_008` 1/3 and `task_014` 1/3 (`ACTION` basis, gold IS a
   transfer). Seven mutations across four experiments moved the transfer *rate*; one
   (seq 8's D2) moved *discrimination*, and only toward gold transfers. Seq 10 can watch
   both directions on three tasks instead of two.
5. **Weather discipline held.** `make weather` returned 6/6 immediately before launch and
   the round lost zero episodes to the luna user-simulator empty-completion signature —
   the class that cost pass 1 of the 2026-08-16 calibration 13 of 24 episodes.

## A disclosure about pre-partition information

Candidate ranking for this screen mined every committed `results/**/results.json`
**outside `held_out/`**. One of those files — `results/experiment_004_powered-bm25-luna56/
generation_000/pilot_h0/graded/` — is seq 4's pre-freeze calibration pilot, and its
28-task list happens to include seq-2's 8 held-out tasks, which seq 10 carries into its
own held-out 36. So single-trial, 2026-08-15-era pilot outcomes for 8 of the 36 were
visible to the session composing this freeze.

Stated rather than left implicit. It is **not** held-out-derived information: the pilot ran
before any partition contained those tasks as held-out, it lives outside every vault, and
it is exactly the class of pre-partition screening `contract/protocol.md` § 0 step 1
sanctions ("no firewall applies yet"). Plan D33 § 3 likewise permits freeze-time design to
use pre-partition and aggregate information, quarantining only per-task and trace-level
*held-out* content. The operational consequence is recorded in the seq-10 manifest header:
these numbers sized nothing and steer nothing, and no in-loop session of seq 10 consults
them.

## Raw evidence

`screen/` — `episode_manifest.jsonl` (per-episode reward, cost, incident counters,
`arm_sha`), `run_metadata.json` (freeze fingerprint, launcher argv, toolchain, incident
totals), `reward_extract.json` (per-task trial rewards, termination reasons, durations and
costs, extracted from the 22 MB `results.json` the run directory carried).
