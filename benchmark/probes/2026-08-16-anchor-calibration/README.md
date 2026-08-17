# 2026-08-16 anchor calibration — measuring the incumbent H0 on candidate batch tasks

Run between seq 6 (REVEALED) and the seq-8 freeze, to satisfy plan **D25 rule 1** (a fixed
batch spans empirical strata **measured under the incumbent H0**) and `contract/protocol.md`
§ 0 step 2. Seq 5/6's batch was eight hand-picked known-fails; five of the eight never passed
once in 168 episodes, so the pre-registered endpoint test reduced to one task's day-to-day
variance (`results/experiment_006_fixedb-bm25-luna56/BATCH_TASK_DIFFICULTY.md` § 5). This
probe buys the measurement that lets seq 8's batch carry an **anchor** tier — reliably
passing tasks whose job is to make a regression visible.

**Pre-partition and pre-freeze**: no seq-8 partition existed when these ran, so no firewall
applied. Every task probed here is a *candidate batch* task — fully observable by design —
and none is a member of the 28-task held-out set carried into seq 8.

- **Harness**: the incumbent H0, `target-agent/` byte-identical to tag `h0-baseline`
  (commit `b76f274`, the D27 scaffold anchor). `git diff h0-baseline -- target-agent/` empty
  at run time; every `run_metadata.json` here records `arm.sha = c36c7f8`, `dirty_paths: []`.
- **Lane**: local (`pi --recipe … --mode rpc`), the work-tree-faithful lane — protocol step
  4b and probe P3 (`../2026-08-16-surface-probes/`).
- **Configuration**: the seq-6 lock, unchanged — `banking_knowledge` / `bm25` /
  `openai/gpt-5.6-luna` on both halves / `num_trials: 3` / seed 300 / max_steps 200 /
  max_errors 10 / timeout 600 — i.e. exactly the configuration seq 8 freezes. Reward from
  τ's own `run_domain` grading, never recomputed here.
- **Cost**: **$0.9712** over 69 episodes (56 completed). Zero seam incidents in passes 2–3.
- **Run directories**: written under the then-current lock's tree
  (`results/experiment_006_.../generation_000/anchor_calib_probe{,2,3}`) with non-colliding
  suffixes, evidence copied here, run directories deleted — the convention in `../README.md`
  (a closed experiment's tree must not accrete post-closure runs).

## Passes

| pass | tasks | episodes | outcome |
|---|---|---|---|
| `pass1_partial` | 8 first-choice candidates | 24 (11 completed) | **degraded** — 13 episodes died `infrastructure_error`; `make weather` was not run first. Kept as evidence, used only as corroboration. |
| `pass2_clean` | the same 8 | 24 (24 completed) | clean; `make weather` 6/6 immediately before |
| `pass3_singletrial_passers` | 7 tasks whose only prior graded attempt (seq-4 batch, 1 trial) passed | 21 (21 completed) | clean |

Candidate selection for pass 3 was mined from every committed `results/**/results.json`
outside `held_out/`: tasks with a recorded pass, not in the seq-8 held-out 28, not in seq
5/6's batch, not in seq 1/2's partition. `task_043` and `task_056` qualified but were dropped
— both sit in seq 1's held-out list (a voided freeze, never spent), and using them would
manufacture a `batch_from_held_out` declaration for no instrument gain.

## Results — per-task pass counts under H0

`pass2` and `pass3` are the decisive reads (three trials each, clean). `pass1` is
corroboration only, with its completed-trial denominator stated.

Prior history is counted from every committed `results/**/results.json` outside `held_out/`,
**excluding this probe**. It is weaker evidence than it looks: seq-4 batch rows are single
trials, and the seq-3 pilot rows span the haiku detour as well as luna, so a pilot-derived
rate is not a clean read of the incumbent model pair. That is why the probe was run.

| task | pass1 (completed) | pass2 | pass3 | probe combined | prior graded | stratum verdict |
|---|---|---|---|---|---|---|
| task_006 | — | — | **3/3** | **3/3** | 1/1 (seq-4 batch_05) | **anchor** |
| task_037 | — | — | **3/3** | **3/3** | 1/1 (seq-4 batch_04) | **anchor** (reserve) |
| task_032 | 1/1 | **3/3** | — | **4/4** | 1/1 (seq-4 batch_04) | **anchor** |
| task_057 | — | — | 2/3 | 2/3 | 1/1 (seq-4 batch_02) | marginal |
| task_076 | — | — | 2/3 | 2/3 | 1/1 (seq-4 batch_03) | marginal |
| task_001 | 2/2 | 1/3 | — | 3/5 | 11/16 (smoke/pilot/canary workhorse, mixed pairs) | marginal, high variance |
| task_002 | 1/2 | 2/3 | — | 3/5 | 2/4 (pilots, mixed pairs) | marginal |
| task_004 | 1/2 | 2/3 | — | 3/5 | 3/4 (pilots, mixed pairs) | marginal |
| task_023 | 0/1 | 2/3 | — | 2/4 | 1/1 (seq-4 batch_01) | marginal |
| task_063 | 1/1 | 1/3 | — | 2/4 | 1/1 (seq-4 batch_05) | marginal |
| task_047 | 0/1 | 1/3 | — | 1/4 | 1/1 (seq-4 batch_02) | low marginal |
| task_089 | 1/1 | 0/3 | — | 1/4 | 2/3 (seq-2 batch_03 + pilots) | low marginal |
| task_024 | — | — | 1/3 | 1/3 | 1/1 (seq-4 batch_02) | low marginal |
| task_015 | — | — | 0/3 | 0/3 | 1/1 (seq-4 batch_02) | headroom |
| task_062 | — | — | 0/3 | 0/3 | 1/1 (seq-4 batch_03) | headroom |

## Findings

1. **Three anchor-grade tasks exist outside the held-out set**: `task_006`, `task_032`,
   `task_037`, each 3/3 in a clean three-trial pass and each with a passing prior attempt.
   Seq 8 freezes `task_006` and `task_032` as its anchors and records `task_037` as the
   verified reserve. `task_032` is `reward_basis: ACTION` with `transfer_to_human_agents` in
   its gold action set, so it is a direct regression detector for the transfer dial — the
   scalar six mutations across three experiments moved without ever moving discrimination.
   `task_006` is a one-gold-action DB write, the floor detector for basic execution.
2. **A single-trial pass is weak evidence for reliability.** Seven tasks whose only prior
   graded attempt passed were re-measured at three trials: two reproduced 3/3
   (`task_006`, `task_037`), two landed 2/3 (`task_057`, `task_076`), one 1/3 (`task_024`),
   and **two scored 0/3** (`task_015`, `task_062`). Anchors picked from seq-4 single-trial
   history without re-measurement would have been wrong roughly a third of the time — the
   same failure D25 rule 1 exists to prevent, one level up.
3. **The named marginal candidates are below the marginal band under H0.**
   `BATCH_TASK_DIFFICULTY.md` § 5 lists `task_065` (≈0.10) and `task_072` (≈0.10) as
   marginals on *lifetime* rate across mutated harnesses; under the incumbent H0 both scored
   0/3 in seq-6's `batch_01`. The 1/3–2/3 band where three trials resolve movement is
   populated instead by `task_057` and `task_076` (2/3 each, measured here) and by
   `task_014` (2/3 under seq-6's H0). Seq 8's composition follows the measurement; the
   reasoning is recorded in `benchmark/split_manifest.yaml`'s header and plan decision D28.
4. **The provider-weather class is real and cheap to avoid.** Pass 1 lost 13 of 24 episodes
   to the luna user-simulator empty-completion signature; passes 2 and 3, run after a clean
   `make weather`, lost none. `make weather` before every round is operationally load-bearing,
   not ceremonial.

## Raw evidence

`pass1_partial/`, `pass2_clean/`, `pass3_singletrial_passers/` — each with
`episode_manifest.jsonl` (per-episode reward, cost, incident counters, `arm_sha`),
`run_metadata.json` (freeze fingerprint, launcher argv, toolchain, incident totals), and
`reward_extract.json` (per-task trial rewards and termination reasons, extracted from the
4 MB `results.json` the run directory carried).
