# Calibration pilot — haiku-H0 on the 28 non-partition tasks (2026-08-14)

Pre-freeze pilot for the D13 re-cut (`003_powered-bm25-haiku45`): both halves moved
to `anthropic/claude-haiku-4-5` while the platform sandbox's OpenAI serializer defect
blocks every `openai/*` model (`.ai-state/UPSTREAM_ISSUES.md`); D12's luna pair
returns via its own re-cut when that fix ships. Same design as the luna pilot
(`../experiment_003_powered-bm25-luna56/CALIBRATION_PILOT.md`): the 28 tasks in
nobody's partition (8 stratification leftovers + 20 seq-2-burnt), local lane,
`--max-concurrency 10`, PROVISIONAL lock, arm `6cd7ce7` = the re-anchored
`h0-baseline`. Diagnostic, never reportable. Total cost **$6.22**.

One D13 bonus measured on the way in: `claude-haiku-4-5` **accepts
`temperature: 0.0`** (HTTP 200, verified) — the user-simulator determinism knob that
Sonnet 5 and luna both rejected is restored, so the frozen `user_llm_args` return to
τ's own doctrine (`temperature: 0.0, timeout: 60`). Anthropic's API rejects
`temperature: 0.0` when extended thinking is enabled (HTTP 400, verified), which is
why the user simulator carries no thinking argument: determinism for the
environment, `thinking_level: medium` for the agent under test.

## Results (n=28, one trial each, graded by `tau2 evaluate-trajs` via `grade.py`)

| measurement | haiku-H0 | luna-H0 (D12 pilot) | Sonnet pair (seq-2 actuals) |
|---|---|---|---|
| baseline pass | **3/28 = 10.7%** (Wilson 95%: 4–27%) | 7/28 = 25.0% | 3/8 held-out H0; ~27–37% pooled |
| cost / episode (local) | **$0.283 mean / $0.252 median** (max $0.733) | $0.038 / $0.026 | $0.62 / $0.53 |
| duration / episode | 113 s mean | 94 s | 168 s |
| messages / episode | 49 mean | 55 | ~52 |

Haiku passes: task_001, task_017, task_035. Agreement with luna on the same 28:
22/28. Sonnet overlap (n=20, mixed H0–H2 harnesses): sonnet 5/20 vs haiku 2/20.

## Verdict — D11's G=5, B=8, T=28 stands; the new watch-item is diagnostic, not statistical

- **No saturation risk whatsoever** — ~89% headroom. The weak-baseline direction of
  D8 is the live one instead: at p≈0.107 a batch of 8 reads **0/8 with probability
  ≈ 0.40**, so 0/B viability reads will be routine and are a *decision gate*, not a
  stop (exactly as seq 2 exercised at 0/4). Expect most diagnoses to run without
  in-batch successful controls, leaning on near-miss action-match profiles — seq 2's
  fallback becomes the norm.
- **Power re-checked at the measured regime** (`power_sim.py` scenarios, mixture
  shifted to its ~15% floor, bracketing the 10.7% measurement from above; power is
  monotone-better as baseline falls): G=5/T=28 reads dir 0.97 / ≥2-task 0.95 /
  trend@.05 0.86 under the optimistic scenario, 0.82/0.71/0.44@trend.05 moderate;
  null calibrated at 5%/10%. Lower baseline shrinks binomial variance, so the
  design is slightly *better* powered than at the Sonnet or luna baselines.
  **G=5, B=8, T=28 confirmed; partition unchanged.**
- **Budget re-priced:** powered local side ≈ 168 × $0.28 ≈ **$48**; platform batches
  ≈ 40 × ~$0.22 (measured haiku conversation billing) ≈ **$9** ⇒ experiment
  ≈ **$55–65** plus screens. Between luna (~$10–20) and Sonnet (~$150) pricing.
- **H0 competence caveat, stated honestly:** 10.7% is above zero but thin — the
  comparative method has few successful controls anywhere, and the protocol's
  "H0 must show basic competence" concern (lock note) is live. The B1 read remains
  the formal guard; if the loop struggles to diagnose against an almost-all-failing
  batch, strengthening H0 (or returning to luna when unblocked) re-opens per D8.

## Operational constraint measured on the way out

The org's Anthropic rate limit for `claude-haiku-4-5` is **20,000,000 prompt bytes
per hour** (named verbatim in the 429 the post-pilot platform re-check hit, and
still saturated 30+ minutes later — an hourly window, not a per-minute one). The
pilot's 28 long-context episodes at 10-wide consumed it in ~9 minutes, which prices
an episode at ≳0.7 MB of prompt bytes. Consequence for every haiku round: a
held-out round (28 episodes) or two batch rounds inside one hour can saturate the
cap mid-round, and the overflow surfaces as τ infra retries — exactly the noise a
diagnosis round must not carry. Pace haiku rounds accordingly (lower
`--max-concurrency`, or space rounds across hour windows), or raise the org cap
before the experiment. Sonnet and luna carry separate limits; this is
D13-pair-specific.

## Provenance

- Run: `generation_000/calibration_pilot/` under this experiment id (manifest,
  results, pi_sessions, run_metadata), arm `6cd7ce7`, PROVISIONAL banner recorded.
- Comparators: the luna pilot beside this one; seq-2 values from
  `experiment_002_bm25-sonnet46` (held-out H0 column + batch graded results).
- Power re-check: `benchmark/scripts/power_sim.py` scenario machinery with the
  harder-pool shift mechanism at its mixture floor; 8,000 sims/cell.
- Platform control for this model: graded clean episode with zero seam incidents
  and $0.218 conversation billing (recorded in `.ai-state/UPSTREAM_ISSUES.md`,
  Anthropic-control update).
