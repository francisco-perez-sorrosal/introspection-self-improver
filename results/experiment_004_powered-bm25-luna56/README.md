# Experiment 004_powered-bm25-luna56 — closure

**Status:** REVEALED 2026-08-15. **The endpoint question is not supported.** This experiment does
not demonstrate a self-improving agent.

Freeze: G=5, B=8, T=28 (plan D11), `openai/gpt-5.6-luna` on both halves, `bm25` retrieval,
tau2-bench `fc0055dc` (v1.0.1). Fingerprint `sha256:1c3a301e…`.

## Result

| generation | passed | of | % |
|---|---|---|---|
| H0 | 6 | 28 | 21.4% |
| H1 | 8 | 28 | 28.6% |
| H2 | 5 | 28 | 17.9% |
| H3 | 6 | 28 | 21.4% |
| H4 | 7 | 28 | 25.0% |
| H5 | 4 | 28 | 14.3% |

**Endpoint:** R_T(H5) − R_T(H0) = **−2 tasks (−7.1 pp)** — inside the ±9 pp band, directional only.
**Pre-registered primary (D11):** one-sided trend over H0…H5, **z = −0.85, p = 0.802** — not
significant at α = 0.05.

## What the data actually support

The honest reading is **weaker than either an improvement claim or a regression claim**, and it
corrects a stronger statement made in the reveal commit (`3595d60`), which called the mutations
"trading, not accumulating". That over-reads the evidence. Three checks say so:

**1. Gains and regressions are balanced.** Across the five transitions: **13 FAIL→PASS gains against
15 PASS→FAIL regressions.** Under the null that every generation behaves identically and each cell is
an independent single-trial draw, gains and regressions are equal in expectation. 13 vs 15 is that
null, not a trading dynamic.

**2. "No task was solved by every generation" is not a finding.** It looked like one. At the measured
base rate p = 0.214 with six independent draws, the expected number of tasks solved by all six is
**0.003** — observing zero is exactly what noise predicts, and says nothing about mutation stability.

**3. The union is consistent with task heterogeneity, not with accumulating capability.** 13 tasks
were solved by some generation; a homogeneous-p null predicts 21.4. Fewer than predicted means some
held-out tasks are simply out of reach for this harness — not that capability was being built and
lost.

So: **the data are consistent with the five mutations having no systematic effect in either
direction.** Every movement in the curve sits inside what single-trial sampling predicts. This is
precisely the exposure D2 accepted when it chose one trial per task and pooling across T over
repeated trials of one task, and this experiment is where that cost came due — the design can
detect a ~+4–5 pp/generation loop, and cannot resolve what actually happened here.

## What *is* demonstrated

**The loop runs.** Start gate → six sealed measurements (168 episodes) → five diagnosed batches
(40 episodes) → five human-gated PRs → five tags → five verified records → reveal, with **zero seam
incidents across all 208 episodes** and no mid-run mechanics patching. All twenty §29 guardrails held
(`GUARDRAIL_WALK.md`). That is a claim about machinery, and it is the only claim this data carries.

## The finding that outlives the number

**Four of five generations went into a single instruction paragraph, and two of those four were
repairs of defects the paragraph itself introduced.**

| gen | target | outcome |
|---|---|---|
| 001 | writes an unverified KB-derived value (3/8) | installed a grounding check with a stopping condition |
| 002 | that check blocks determinate actions (2/8) | bounded it — and forbade a policy-*required* transfer |
| 003 | prohibition misreading (1/8) | repaired it — and licensed a policy-*forbidden* transfer |
| 004 | botched discoverable-tool handover (6 witnesses / 4 batches) | **worked** — `task_040` in B₅ shows the clean name-only call |
| 005 | over-permission (1/8) | removed the rule; deferred to the frozen policy |

Two mutations have direct positive batch evidence (gen-003 in `task_032`, gen-004 in `task_040`).
Two demonstrably failed to do their job. The pendulum in gens 002/003/005 is the mechanism to study:
**every attempt to state *when* to transfer competed with a frozen policy that already covered the
case completely**, and each correction left room for its mirror image. Gen-005's remedy was to delete
harness guidance rather than add it.

The batches also surfaced, and never got a slot: the agent's inability to **resolve** the right
product/value from `bm25` (three generations tuned *when to stop* around it), and the failure to
unlock-and-call a required agent tool (3/8 in the final batch, witnesses across four batches).
Nine targets were opened, four consumed, four left unconsumed, one retired for lack of evidence, and
one ranking (T8) retracted when `task_063` passed with 22 KB searches.

## A methodological trap worth carrying forward

τ's `Action.compare_with_tool_call` compares argument dicts, but `call_discoverable_*_tool` carries
its payload as a **nested JSON string**, so that field is compared by string equality. The agent emits
compact JSON; gold carries spaces. Formatting-only misses grew across the run: **33% → 56% → 62% →
56% → 40%** of all action-check misses. It costs no reward under a `DB` basis, it is frozen evaluator
surface, and "fixing" it would be grader-gaming. Every batch diagnosis used a nested-JSON-aware
comparison; a naive read would have invented a "fails to call discoverable tools" failure mode that
does not exist.

## What would actually answer the question

Not a bigger T alone. The binding constraint here is **per-episode variance at one trial per task**,
which no amount of held-out width removes from the per-task cells. The protocol's own upgrade path
(§23, plan D11) is the endpoint reliability study: H0 and H5 × additional trials. D11 gates it on the
endpoint landing *positive*-but-inside-band; this endpoint is *negative*-and-inside-band, so the gate
as written does not fire — but the diagnostic value is the same, and it is the one measurement that
would separate "the mutations did nothing" from "the measurement could not see it".

## Artifacts

`summary.md` (generated at reveal) · `GUARDRAIL_WALK.md` (§29 walk, all twenty HELD) ·
`held_out/` (six rounds copied verbatim, progression/matrix/transitions/retention/trend_test) ·
`improvement_records/gen_00N_to_00M.yaml` (five, all verifying) · `improvement_backlog.md` (nine
targets with prevalence, evidence, consumption, one retirement, one retraction) ·
`generation_000..005/` (batches and gates) · `experiment.yaml` + value-copies of the lock and
partition · `CALIBRATION_PILOT.md`.
