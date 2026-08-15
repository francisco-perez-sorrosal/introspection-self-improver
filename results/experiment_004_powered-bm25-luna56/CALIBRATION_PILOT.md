# Calibration pilot — corrected-H0 luna on the 28 non-partition tasks (2026-08-15)

The calibration of record for the seq-4 powered freeze, superseding
`../experiment_003_powered-bm25-luna56/CALIBRATION_PILOT.md` per plan **D16**: that
pilot ran against arm `2ea2475`, whose SYSTEM.md carried all three seq-2 mutations
(+30 instruction lines), so its numbers describe H0+g1–g3, not H0. This pilot
re-measures the same 28 tasks on the **corrected H0** — arm `2337ecf`, SYSTEM.md
byte-identical to `h0-baseline-sonnet46`'s, `ai:` luna block per D12/D14 — after
`make reset_h0` verified byte-identity against the corrected tag. Diagnostic, never
reportable: PROVISIONAL lock (banner in `generation_000/pilot_h0/run_metadata.json`),
local lane at `--max-concurrency 10`.

Task-set rationale (unchanged from the 003 pilot, stated there in full): exactly the
28 tasks in nobody's partition — the 8 eligible-but-unused leftovers plus the 20
seq-2-burnt tasks — because measuring the frozen held-out set pre-freeze would burn
it (CLAUDE.md firewall invariant).

## Results (n=28, one trial each, graded by `tau2 evaluate-trajs` via `grade.py`)

| measurement | corrected H0 (this pilot) | contaminated pilot (H0+g1–g3, 003) |
|---|---|---|
| baseline pass | **6/28 = 21.4%** (Wilson 95%: 10–40%) | 7/28 = 25.0% (Wilson 13–43%) |
| cost / episode (local) | **$0.022 mean / $0.017 median** (max $0.063; total $0.63) | $0.038 mean / $0.026 median |
| duration / episode | 63 s mean / 52 s median | 94 s mean / 75 s median |
| messages / episode | 45 mean | 55 mean |
| wall-clock (10-wide) | 282 s | ≈ 7 min |

Per-task: pass = 002, 004, 017, 035, 036, 051; fail = the other 22. Zero incidents;
all 28 episodes terminated `user_stop` and graded.

## Reading the two pilots against each other

- **The mutation effect on this set reads as ≈ −1 task and is far inside the noise**
  (both Wilson intervals span ~15 pp of overlap). Pass-set churn — common {002, 004,
  035, 036}, contaminated-only {001, 008, 089}, corrected-only {017, 051} — is the
  known per-episode stochasticity (D2), not signal. This is consistent with seq-2's
  own reveal: a flat held-out curve.
- **The mutations made episodes ~40 % longer and costlier** (55 → 45 msgs, 94 → 63 s,
  $0.038 → $0.022): the +30 instruction lines bought verification work without a
  measurable pass-rate return on this set.
- **D11 sizing is unaffected.** G=5/B=8/T=28 was powered across baselines in this
  range (a lower baseline slightly *shrinks* binomial variance — same argument as the
  D13 haiku re-check). Headroom improves: expected H0 held-out ≈ 6/28 leaves ~22
  tasks of room.
- Budget re-prices down: at $0.022/local episode the local side of the powered run
  (168 episodes) is ≈ $3.70; platform batches remain ≈ $0.016/episode (D14
  verification episode).
