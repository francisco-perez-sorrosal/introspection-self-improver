# Improvement backlog — experiment 005_fixedb-bm25-luna56

Approved mutation targets, ranked. Opened at the g=0 decision point (2026-08-15) from
`batch_01`'s own conversations. `protocol.generations: 2`, so there are exactly **two
mutation slots** (gen 001, gen 002); `batch_03` is H2's endpoint round and consumes no
transition. Approving more targets than slots is stated here, not hidden.

**Batch-mode caveat.** `protocol.batch_mode: fixed`. `batch_01` is this experiment's
pre-mutation baseline, but the 8 tasks were **hand-chosen from seq-4 known-fails**
(partition manifest header), so it is not an unbiased sample of the pool and its floor
reading is by construction. From `batch_02` on, every batch number additionally measures a
set the loop has been tuned on — every digest, diagnosis and record must say so.

**Evaluator properties, not failure modes.** Two carry-forwards were applied while
open-coding and are not backlog items: `call_discoverable_*_tool` payloads are compared as
JSON *strings* (parsed before counting any handover miss), and seven of eight tasks grade on
a `DB` basis so their action-check misses cost no reward.

---

## T1 — Write-call arguments are filled from priors, not from the source that defines them

**Status:** consumed-by-gen-001 · **Owning layer:** harness (retrieval usage + tool-contract reading)
**Prevalence:** 6/8 tasks (`task_014`, `task_026`, `task_065`, `task_070`, `task_072`, `task_096`)

The agent grounds the customer's subject matter competently and then supplies the *tool
argument* from its own priors. The defining source is available and unconsulted in every
witnessed case:

- `task_072` — `credit_type: "rebate_credit"` where gold is `"fee_refund"`, **3/3**, with both
  credit amounts correct in 2/3. The distinction is in the tool's own docstring
  (`'rebate_credit' for missing rebates, 'fee_refund' for incorrect fee charges`), delivered
  to the agent in the unlock response it had already received. Sole cause of failure here.
- `task_070` — opened `Hunter Green` (t1), `Cobalt Blue` (t2), nothing at all (t0); gold is
  `Sky Blue`. **Zero of 28 KB queries across the three trials contain "promotion"**, although
  which of two promotions is currently active is the task's entire decision rule.
- `task_014` — wrong `reason` code 2/3. The tier list is `doc_bank_accounts_bank_accounts_(general)_042`,
  retrieved in **0/3 trials including the one that scored 1.0** — the passing trial guessed.
- `task_065` — wrong `account_class` 2/3 (`Bluest`/`Bronze`/`Blue` vs gold `Evergreen`/`Green`).
- `task_096` — `amount: 7.5` vs gold `15.00`, `expected_apy: 6.7` vs gold `6.85` (t0, the only
  trial that acted).
- `task_026` — `new_rewards_earned` values wrong on the one trial that reached the updates.

**Why this target and not the others:** terminal blocker on the most tasks; unambiguously
mutable surface (retrieval *usage* and tool-contract reading, never the frozen retrieval
backend or policy text); and it does not compete with the frozen policy, which is the failure
pattern seq 4 recorded three times. Named in seq 4's closure as the mode the batches kept
pointing at that never got a slot.

---

## T2 — Transfers to a human while actionable work remains

**Status:** pending (slot-2 candidate) · **Owning layer:** harness, contested — see counterevidence
**Prevalence:** 4/8 tasks, 9/24 episodes (`task_082` 3/3, `task_026` 2/3, `task_028` 2/3, `task_096` 2/3)

`transfer_to_human_agents` appears in **no** DB-basis task's gold. `task_082` is the extreme
and the most reproducible cell in the batch: the user's opening line is "I need to speak to a
human agent", and the agent transfers on turn one after a single KB search, with no identity
verification and no attempt, **identically in all three trials** (8 messages each) against 20
gold actions.

The frozen `<policy>` already covers this without ambiguity: transfer "only if you absolutely
have to, and you are sure that there are no potential actions you can take as specified in the
knowledge base, or in your policy. Do not transfer without asking the user first."

**Standing counterevidence (prior-experiment context, seq 4, prose only).** Seq 4 spent three
of five generations on transfer guidance; each correction left room for its mirror image
(gen-002 forbade a policy-*required* transfer, gen-003 licensed a policy-*forbidden* one,
gen-005 deleted the guidance and deferred to the policy). Any T2 mutation must therefore be a
*procedural* precondition rather than a restatement of when transfer is appropriate, or it
repeats a failure already paid for.

---

## T3 — Fabricated discoverable-tool name

**Status:** pending (low priority) · **Prevalence:** 1/8 tasks, 2/24 episodes

`task_028` calls `call_discoverable_user_tool` with `discoverable_tool_name: "submit_dispute"`
(t1) and `"dispute_submission"` (t2) instead of the unlocked `submit_cash_back_dispute_0589`.
Plausibly a sub-case of T1 (an argument filled from priors rather than from the tool surface
the agent was handed); re-rank against `batch_02` before treating it as independent.

---

## T4 — Volunteered optional argument mutates DB state — NOT APPROVED

**Status:** retired-as-target, recorded as a finding · **Prevalence:** 1 witness

`task_065` t2 issued **exactly the three gold write calls with the correct account classes**
and still failed `db_match`. It passed `reason: "customer requested closure"` to
`close_bank_account_7392`, whose default is `"Customer requested closure"`; the tool executes
`account["closure_reason"] = reason`, so a capitalisation difference in a volunteered optional
argument becomes a DB difference.

**Not approved, with the reason recorded:** the only lever that reliably helps is matching the
default string, which is grader-gaming against a frozen evaluator rather than a capability
improvement — the same judgment the seq-4 closure reached about the nested-JSON string
comparison. One witness. Kept here so a future batch that reproduces it is read against a
recorded prior rather than diagnosed fresh.

---

## Slot accounting

| Slot | Generation | Target | Status |
|---|---|---|---|
| 1 | gen-001 | T1 | consumed |
| 2 | gen-002 | T2 (candidate, re-rank against `batch_02`) | open |
| — | — | T3, T4 | carried / retired |

Two slots, four targets opened. T3 and T4 cannot be reached under `generations: 2` and are
recorded rather than dropped.
