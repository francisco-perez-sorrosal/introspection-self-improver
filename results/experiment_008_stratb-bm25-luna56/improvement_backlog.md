# Improvement backlog — experiment 008_stratb-bm25-luna56

Mutation targets, ranked. Opened at the g=0 decision point (2026-08-16) by open-coding
`batch_01`'s own 24 conversations and the graded `action_checks`/`db_check` before any
taxonomy was imposed. `protocol.generations: 6`, so there are **six mutation slots**
(gen 001…006); `batch_07` is H6's endpoint round and consumes no transition.

**Autonomy.** `protocol.require_human_approval` is frozen **false** for seq 8 (plan D28,
re-registering D23's envelope): target approval and set composition are the orchestrator's,
delegated by the user. Every decision below is recorded with its reasoning so it can be
audited exactly as a human gate would have been.

**Batch-mode caveat.** `protocol.batch_mode: fixed` — the SAME eight tasks every round.
`batch_01` is the pre-mutation baseline. **From `batch_02` on, every batch number measures
a set the loop has been tuned on**, and every digest, diagnosis and record says so.

**Stratified-batch caveat, new in seq 8.** The eight span measured strata (anchors /
marginals / headroom — `benchmark/split_manifest.yaml` header). Two consequences for
diagnosis: a mode observed only on headroom tasks has never been observed on a task this
harness can pass, and **anchor cells are the regression channel** — every change's
falsifier must name what it would do to `task_006` and `task_032`, not only what it would
fix.

---

## Two reading corrections that bound every target below

Recorded first because both change what the graded artifacts mean.

**1. `action_checks` misses are dominated by JSON-string formatting on this domain.**
`call_discoverable_*_tool` payloads are compared as JSON *strings*, so gold's
`{"user_id": "lj82d4f1a9"}` and the agent's `{"user_id":"lj82d4f1a9"}` register as a MISS
while being the identical call. Enumerated over `batch_01`: of **85** gold-action misses,
**39 are formatting-only** — the call was made, semantically identical to gold — leaving 46
genuinely absent. Every prevalence figure below is computed against a
**whitespace-normalized** comparison, never the raw miss list. Seven of the eight tasks
grade on `DB` basis, where action misses cost no reward directly — only the resulting
database state does — so the normalized diff is a diagnostic instrument, not the metric.

**2. The seq-6 structural finding that bounded that experiment's targets is OBSOLETE.**
Seq 6's backlog opened with "a Pi-local extension-tool call reaches τ as an invalid tool
call, so two of the three growth surfaces were never available". Under **D24** (decided
between experiments, `contract/constraints.md` divergence 6) a registry-declared Pi-local
call is executed by Pi and suppressed from τ — no step, none of the ten `max_errors`, fully
logged. Extension tools and sub-agents are live surfaces for the first time in this
project, and the no-tool-call hooks (`before_agent_start`, `tool_result`, `context`)
remain live. A *declared skill* is still measurably inert on this seam (probe P2), so
skill-shaped judgment ships as hook injection. **Prose is no longer the default by
elimination**, and the D26 concentration flag is a positive obligation.

---

## T1 — A tool the knowledge base names is retrieved and then never used

**Status:** consumed-by-gen-001 (C1) · **Owning layer:** harness (retrieval usage → action)
**Prevalence:** 2/8 tasks (`task_026` 3/3, `task_096` 3/3), **6/24 episodes**

The decisive mode of the round, and the one whose evidence is strongest, because the
counterfactual is measured rather than argued: **in 6 of 6 episodes the exact gold
remediation tool name appeared in the text `KB_search` returned, and the agent never
unlocked it.**

- **`task_026` — 3/3.** Gold requires `unlock_discoverable_agent_tool` +
  4× `call_discoverable_agent_tool` on `update_transaction_rewards_3847`. That name is in
  the returned KB text at query #3 (t0), #1/#4/#5 (t1) and #4 (t2). The agent never
  unlocked it in any trial. It performed the customer-facing half — handing over
  `submit_cash_back_dispute_0589`, whose four gold user-calls all match semantically — and
  then (t0, t1) transferred citing `technical_system_error`.
- **`task_096` — 3/3.** Gold requires `apply_savings_account_credit_6831` and
  `submit_interest_discrepancy_report_7294`. **Both names are returned by query #1 and
  query #2 in every trial.** The agent then spent 9–10 queries on APY rate details, unlocked
  neither remediation tool, and transferred in 3/3.

**This is not a retrieval-backend limit.** Seq 6 retired its T1 for `task_070` on the
finding that `bm25` never surfaced the gold answer; here `bm25` surfaced the tool name
early and repeatedly. The gap is between *retrieved* and *acted on*, which is harness
surface by the project's own definition (retrieval **usage**).

**Shape of the mode:** the agent completes what the customer asked about and omits the
bank-side remediation the knowledge base prescribes for that situation — the customer
asked about a cash-back discrepancy, not about correcting the rewards ledger; about an
APY shortfall, not about applying an interest correction.

**`surfaces_considered`** (written at open time, per D26):
- `extension-hook` (`tool_result`) — **the chosen home, pending step-4b measurement.**
  Deterministic post-processing of every `KB_search` result to surface the discoverable-tool
  names the returned documents mention. No judgment, no task knowledge, no answer. Enabler:
  hooks introduce no tool call and are live in every seam configuration. Blocker to clear:
  `tool_result` is *inferred* legal, never measured on this seam — probe required.
- `instructions` — available and cheap, but this is the exact shape three experiments
  measured failing: a sentence telling the model to notice something competes with the
  frozen policy, which already says "You must search the knowledge base to find tools that
  you can unlock." Restating it is the T4/T5 mistake of seq 6.
- `extension-tool` — legal under D24 but wrong shape: the model would have to choose to call
  it, which is the very step that is failing.
- `sub-agent` — no stable contract; the job is one deterministic extraction.

---

## T2 — A user-discoverable tool is handed over without its exact name

**Status:** consumed-by-gen-001 (C2) · **Owning layer:** harness (tool-contract reading)
**Prevalence:** 2/8 tasks (`task_026`, `task_057`), **6/6 episodes that use the tool**

Gold calls `give_discoverable_user_tool` with the tool **name alone**. In every episode
that used it, the agent supplied an extra `arguments` payload instead — and on `task_057`
that is the measured cause of the failure chain.

- **`task_057` — 3/3, and the mechanism is visible end to end.** Gold: the agent grants
  `deposit_check_3847` bare, the user then calls it with `{account_id, check_amount}`.
  Actual t0: the agent granted `deposit_check_3847` **with a pre-filled payload** and
  described the action in prose ("use it to photograph the front and endorsed back of the
  check"); the user narrated compliance and **called nothing**; the agent then checked the
  account, found no transaction, and advised the customer to check the app. Actual t1 and
  t2: the user did attempt the call — with **invented names** `deposit_check`,
  `mobile_check_deposit`, `check_deposit` — never `deposit_check_3847`. The gold user call
  therefore occurs 0/3.
- **`task_026` — 3/3 with the opposite outcome, which is what makes the mechanism legible.**
  The agent granted 13–18 times, once per transaction, each with a payload — and the user's
  calls *did* carry the exact name, matching gold semantically 4/4. Repetition kept the
  exact string in front of the user; a single payload-bearing grant did not.

The frozen `<policy>` already requires "Provide the exact tool name as specified in the
knowledge base" and to explain "what arguments to provide" — so this target is **not** a
restatement: the policy says what to tell the user, and the observed defect is *where the
name goes* (into a machine payload the user never sees, rather than into the handover).

**`surfaces_considered`:**
- `instructions` — **chosen.** One clause about the shape of one call. This is the shape
  seq-6's C3 landed successfully for a different tool (confirmed 3/3, survived to the final
  harness): a rule about *how to write a call*, not a judgment about when to act. It has no
  scope to over-generalise into, which is the property all four failed transfer mutations
  lacked.
- `extension-hook` (`tool_result`) — could strip the payload deterministically, but that
  would be the adapter repairing the agent one level in, and it would hide a real,
  PR-fixable harness defect from the objective.
- `extension-tool` / `sub-agent` — no.

---

## T3 — Transfer discrimination: the same harness over-escalates and under-escalates

**Status:** pending, deliberately unconsumed · **Prevalence:** 3/8 tasks, **7/24 episodes**

For the first time this project can measure transfer *discrimination* rather than transfer
*rate*, because the stratified batch holds tasks on both sides of the dial.

- **Under-escalation — `task_014` 2/3 (the gold action IS a transfer,
  `reason: unconfirmed_external_communication`).** The customer asks in plain words to be
  transferred and the agent **refuses**: t0 "I'm unable to transfer this request because the
  offer cannot be verified in the available official program information"; t2 "I can't
  transfer this request because the offer cannot be verified in Rho-Bank's documented
  referral programs." The frozen policy says the opposite — guideline 5 makes a transfer the
  response to an issue outside the agent's capability once the user asks. t1 searched twice
  more and transferred: pass.
- **Over-escalation — 5/24 episodes** transfer where gold has none (`task_026` t0/t1,
  `task_096` 3/3), in every case after the agent's own analysis failed to resolve.
- **Correct — `task_032` 3/3** (anchor; gold includes the transfer) and `task_014` t1.

Round-wide: **9/24 transfer-carrying episodes**, of which 4 are gold-correct.

**Not targeted at gen-001, and the reason is the strongest evidence this project owns.**
Six mutations across seq 4, 5 and 6 moved the transfer *rate* — 9 → 11 → 10 → 15 → 6 → 12 →
9 per 24 — and **not one moved discrimination**; seq 6's own review calls it "a controlled
demonstration that this surface cannot express the needed distinction". Seq 6's T4 recorded
the condition for a seventh attempt: *a mechanism that is procedural and counted rather than
a judgment about when transfer is appropriate*. That condition is carried forward here
unchanged. A prose sentence would also put the `task_032` anchor at risk, which is exactly
what anchors were frozen in to detect.

**`surfaces_considered`:** `instructions` — available, and refused on six witnesses of
prior failure. `extension-hook` (`context` or `before_agent_start`) — the live candidate: a
deterministic, counted precondition rather than a judgment sentence. `extension-tool` — a
checkable "may I close this out" gate, legal under D24, unexplored. **Re-rank against
`batch_02`.**

---

## T4 — Computed amounts and enum values on a prescribed write are wrong

**Status:** pending · **Prevalence:** 1/8 tasks (`task_072` 3/3), 3/24 episodes; latent on
`task_096`, which never reaches the write

`task_072` performs the right tool with the right account ids and the wrong values:
gold `amount: 14.0 / credit_type: "fee_refund"` and `amount: 3.5 / "fee_refund"`; the agent
supplied `16.0 / "rebate_credit"` and `6.5 / "fee_refund"` (t0). t2 got the second pair
**exactly right** and the first wrong — the same never-both-in-one-trial signature seq 6
recorded for this task.

Two components that may be separable and are **not** separated yet: the arithmetic
(16.0 vs 14.0) and the enum (`rebate_credit` vs `fee_refund`, a bank-defined value with a
legal set).

**Held at gen-001 for two reasons.** It is latent behind T1 on `task_096` — if T1's change
gets the agent to the remediation write, `batch_02` shows whether the values are then wrong
there too, which is what separates "arithmetic" from "this one task". And seq 6 landed prose
arithmetic (G2) and scored **0/18** with its own falsifier anticipating it. **Re-rank
against `batch_02`.**

**`surfaces_considered`:** `extension-tool` — the honest home for arithmetic, live under
D24 and unexplored; the model calls a deterministic calculator instead of computing in
prose. `extension-hook` (`tool_result`) — could append an exact computation over returned
transaction rows. `instructions` — refused for the arithmetic half on seq-6's G2 evidence;
possibly legitimate for the enum half, which is value resolution rather than computation.

---

## T5 — Verification without remediation

**Status:** pending, low priority · **Prevalence:** 1/8 tasks, 1/24 episodes
(`task_057` t0)

The agent checked the account after the handover, observed that the deposit had **not**
posted, said so accurately, and responded with advice ("check the app's deposit history")
rather than re-issuing the handover. The verification step worked; the response to its
result did not.

Held: one witness, and it is plausibly downstream of T2 — if the handover carries the exact
name, there may be nothing left to remediate. Re-rank against `batch_02`; if T2 lands and
this persists, it is a distinct target.

---

## Slot accounting

| Slot | Generation | Target(s) | Status |
|---|---|---|---|
| 1 | gen-001 | T1 (C1, extension-hook) + T2 (C2, instructions) | in flight |
| 2–6 | — | T3, T4, T5 re-ranked against each new batch | open |

Five targets opened, two consumed, none retired.

**Surface concentration (D26 flag):** 0 prior `instructions` mutations in this experiment,
so the flag has not fired. The set nonetheless leads with a structural change, because the
standing prior across three closed experiments is that 17 of 18 slots went to one
`SYSTEM.md` paragraph and the loop did not improve.

<!-- transition: gen_000_to_001 -->
