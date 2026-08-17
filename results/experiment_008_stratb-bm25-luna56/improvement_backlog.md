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

---

## Re-ranking against `batch_02` (H1, 2026-08-17)

`batch_02` measures a set gen-001 was tuned on. Round health clean: 24/24, `arm_sha_ok` on
every row, one episode carrying `sandbox_seam_unclassified=2` / `sandbox_tool_errors=2`
(`task_096` t1, disclosed rather than rounded to "zero incidents"). Graded read **13/24
episodes, 4/8 tasks (54.2%)**, up from `batch_01`'s 10/24 (41.7%). Anchors held 3/3 and 3/3.

### ERRATUM against the gen-001 record — the round's most important finding

The gen-001 record's first signal states that `task_096` "unlocked neither" remediation tool
in 3/3 trials, and counts its three episodes toward T1's 6/24 prevalence. **That is wrong**,
and scoring C1's prediction against `batch_02` is what exposed it. Re-derived from
`generation_000/batch_01/graded/updated_results.json`: in 2 of 3 trials `task_096` **did**
unlock and call both `apply_savings_account_credit_6831` and
`submit_interest_discrepancy_report_7294`, and failed on the argument **values**; only t0
never reached them.

Consequences, recorded rather than quietly absorbed:

- **T1's true population is `task_026` alone — 3/24 episodes, not 6/24.**
- `task_096`'s dominant mode is value resolution and belongs to **T4**, which is re-ranked
  upward below.
- **C1 was justified on evidence half of which no amount of name salience could address**,
  which is the most likely reason its prediction was denied. C1 is reverted at gen-002 (D1).
- The record itself is left as written — the schema refuses unknown fields, and rewriting a
  verified record would erase the error rather than record it. This is the durable home.

The lesson generalizes past this experiment: an aggregated miss list is not a mechanism.
`task_026` (never unlocked) and `task_096` (unlocked, called, wrong values) presented
identically at the level of "gold action missing" and are different defects with different
owning layers. Prevalence must be counted on the mechanism, not on the symptom.

### gen-001's predictions, scored

- **C1 — DENIED.** Unlock rate on the target tasks did not move (`task_026` 0/3 → 0/3,
  `task_096` 2/3 → 2/3). The hook **did** run: the fetched platform conversation for
  `task_096` t0 carries 8 occurrences of its output, so this is a denied mechanism, not a
  change that failed to reach the episode. No harm measured — both anchors 3/3, `task_076`'s
  unlock count identical at 5, no new invalid calls. The two degenerate episodes this round
  were inspected and neither is the hook's doing (`task_096` t1 read the customer record
  successfully and then asserted "I'm unable to access the customer information system right
  now" before transferring — an over-escalation witness, filed under T3).
- **C2 — CONFIRMED, and the per-clause falsifiers resolved which half works.** `task_057`
  0/3 → **3/3**, with the gold `call_discoverable_user_tool(deposit_check_3847)` going
  1/3 → **3/3**, exactly as predicted.
  - Clause 1 ("with the tool name alone") — **falsifier FIRED**: 7 of 10 grants still carry
    an `arguments` key. And `task_057` t0 passed *with* payload-bearing grants. **Clause 1 is
    not the operative half.**
  - Clause 2 ("give the user that exact tool name") — **this is the mechanism.** Assistant
    messages naming `deposit_check_3847` went 0/1/1 → 4/1/1, always inside the handover, and
    the user's calls went from inventing `deposit_check`, `mobile_check_deposit`,
    `check_deposit` to calling the exact name in 3/3.
  - Clause 3 (the precondition) — **falsifier FIRED**: grant-using episodes 6 → 5, and
    `task_026` t2 made zero grants where it previously made 13. The precondition did suppress
    the behaviour in one episode, exactly the E2 mode the clause was written to watch.
  - **Attribution caveat (D22).** C1 could also have surfaced `deposit_check_3847`, so the
    composite set cannot separate them from this round alone. Reverting C1 at gen-002 makes
    `batch_03` the discriminating test.

### T4 RE-RANKED UP and re-specified — and one half of it retired

`task_072` 0/3 → 1/3 (first pass). Reading t0 in full re-specifies the target and **kills the
mechanism a slot would otherwise have been spent on**:

- The amounts are **not an arithmetic slip**. The agent's own arithmetic is internally
  consistent — "10 out-of-network withdrawals, first 4 free, remaining 6 × $1.50 = $9.00,
  charged $20.00, so $11.00 refund" — and gold is 3.50. It applies the wrong fee **rule**
  (the transactions are tiered *foreign* ATM fees). An extension-tool calculator, the obvious
  D24 surface, would compute the same wrong number. **Seq 6 landed prose arithmetic (G2) and
  scored 0/18; this round establishes that a calculator would have failed too, for a
  different reason.**
- **The `credit_type` enum half is RETIRED with cause.** The `unlock_discoverable_agent_tool`
  response already enumerates the legal values *with their semantics*: "'rebate_credit' for
  missing rebates, 'fee_refund' for incorrect fee charges". The agent read that correctly and
  applied it correctly by its own reasoning ("I applied a $14.00 missing-rebate credit" →
  `rebate_credit`), and gold classifies the same correction as `fee_refund`. The information
  was in hand and correctly used; the disagreement is with the gold labelling. This is the
  `task_070` class from seq 6 — bounded by frozen surfaces, not harness surface. Surfacing
  the enum would change nothing, because it was already surfaced.

What remains of T4 is genuine and unaddressed: **which bank rule governs a correction** is a
retrieval-usage question, and it is the same mechanism seq 6's D1 confirmed. Held this
generation because gen-002's slot is spent on a better-evidenced target.

### T3 CONSUMED (gen-002 D2), on a mechanism that finally meets seq-6 T4's condition

The transfer tool's own description says the reason enum "can be found in the knowledge base:
search it before calling this tool to select the proper applicable reason", and `reason`
carries a hard enum of 19 values. The agent does not track whether it has looked:

- Across `batch_01` and `batch_02`, **6 of 18 transfer-carrying episodes** issued a
  transfer-reason query.
- On `task_014`, whose gold action IS a transfer and whose gold compares `reason` exactly:
  **every pass (2/2) issued the lookup**; the one trial that transferred without it chose
  `kb_search_unsuccessful_customer_requests_transfer` — a legal member of the enum, and the
  wrong one. The lookup is necessary and not sufficient (`batch_02` t2 queried and then
  refused to transfer at all).
- `task_032`, the anchor, passes 3/3 **without** the lookup — its gold transfer carries
  `compare_args: []`, so the reason is not compared and the anchor is insensitive to this
  change by construction. That is what makes it a safe falsifier.

Seq 6's T4 demanded "a mechanism that is procedural and counted rather than a judgment about
when transfer is appropriate", and recorded that no such mechanism existed. One exists now,
and only because the `context` hook was measured this generation: D2 reports whether the
lookup has happened. It states a fact and gives no instruction, so it has no escape clause by
construction.

### T5 held, T2 not touched

T5 (verification without remediation) had its single witness on `task_057` t0, which now
passes 3/3 — the target is plausibly resolved as a side effect of C2 and is left to settle
rather than touched while it is moving. T2 is confirmed and survives untouched; clause 1 is
known to be inert but removing it would perturb a working change for tidiness.

<!-- transition: gen_001_to_002 -->

---

## Re-ranking against `batch_03` (H2, 2026-08-17)

Clean round, all four sandbox seam counters zero. **11/24 episodes, 45.8%** (curve: 41.7 →
54.2 → 45.8). Anchors held 3/3 and 3/3 for the third consecutive round.

**gen-002's changes, scored.**

- **D1 (revert C1) — worked as intended, and the attribution is now settled.** `task_057`
  held **3/3 with C1 removed**, user calling the gold `deposit_check_3847` in all three
  trials. **C2 owns gen-001's win outright; C1 never contributed to it.**
- **D2 — prediction DENIED, mechanism CONFIRMED, and the gap between them is the finding.**
  `task_014` queries 1/3 → 1/3 and reward 1/3 → 0/3; but `task_032`'s transfer-reason queries
  went **0/3 → 3/3**. Fetching the platform conversations settles it: the note is absent from
  `task_014` t0/t2 and present in `task_032` t0. **In 2 of 3 `task_014` trials the customer's
  explicit request arrives as the terminal `###TRANSFER###` message, so there is no
  subsequent LLM call for a `context` hook to act in.** The deciding moment has no turn.
  D2 is **kept, not reverted** — and the rule this experiment is now applying is worth stating
  once: *a denied prediction is not by itself a revert trigger; a denied MECHANISM is.* C1's
  mechanism moved nothing anywhere and its evidence was misattributed; D2's moves a counter
  0 → 3 exactly as designed.
- **A factual note can still be read as a gate.** Transfer-carrying episodes fell 9/24 →
  6/24, concentrated on the two over-escalating tasks, where no suppression was requested.
  D2 states a fact and gives no instruction, and the rate moved anyway. This sharpens the
  standing lesson past wording: **it is not only escape clauses — any injected statement about
  a missing precondition can be read as a bar to acting.** Carried forward as a standing risk
  for every future state-report change, including E1's.

## T3 — RETIRED for `task_014`, with cause

Its prediction has now been denied under the one mechanism that met seq-6 T4's pre-registered
condition, and the reason is structural rather than a wording problem: the request that
decides the task arrives as the terminal message. No hook can act after it. The remaining
transfer evidence (over-escalation on `task_026`/`task_096`) is a *symptom* of those tasks'
real failure — the agent escalates when its own analysis stalls — not an independent target.
Seven mutations across four experiments have now moved the transfer rate; none has moved
discrimination. **The task stays in the batch; the target is closed.**

## T6 — A write the agent already made is made again

**Status:** consumed-by-gen-003 (E1) · **Owning layer:** harness (state tracking)
**Prevalence:** 2/72 episodes across three rounds — and 2/2 of them failed

`task_076`'s failing trials call `log_verification` **twice**; its passing trials call it
once. Every other call is identical — same account opened, same class, same arguments, same
tools unlocked. A duplicate row in the verification records is a database difference, and the
task grades on `DB`.

This is the finding the stratification was frozen in to make possible. `task_076` is a
*reliable marginal*: it passes most of the time, so a passing trial and a failing trial of the
same task under the same harness sit side by side and the difference is readable. An
all-known-fail batch has no such pair, which is why seq 5 and seq 6 could not have produced
this class of finding at all.

**`surfaces_considered`:** `extension-hook` (`tool_result`) — **chosen**; the only legal lever,
because a `tool_call` hook cannot block the second write (τ executes it regardless and the two
histories diverge, recipe-growth trap 4), so the intervention must land on what the model
reads after the FIRST call succeeds. `instructions` — a sentence about not repeating writes is
the shape that has failed repeatedly, and this defect is mechanical rather than judgemental.
`extension-tool` — the model would have to choose to call it, which is the step that fails.

## What bounds the remaining slots

Recorded so the closure reads it with the curve. Three of the eight tasks are stuck at 0/9
across three harnesses, and each is stuck for a *different* identified reason:

- **`task_026` (0/9)** — gold requires correcting the rewards ledger via
  `update_transaction_rewards_3847`; the agent has never unlocked it, including under C1 which
  surfaced that exact name in the KB text it read. Its activity has also collapsed (104/98/88
  messages at H0 → 22/76/44 at H2): the task is doing less, not more.
- **`task_096` (0/9)** — dominant mode is value resolution, not discovery (the gen-001
  erratum).
- **`task_072` (1/9)** — the governing-rule half survives; the enum half was retired last round
  as frozen-surface-bounded.

None of the three has a mechanism with evidence strong enough to justify a slot on this
round's data. That is why gen-003 lands one change rather than two.

<!-- transition: gen_002_to_003 -->

## Slot accounting

| Slot | Generation | Target(s) | Status |
|---|---|---|---|
| 1 | gen-001 | T1 (C1, extension-hook) + T2 (C2, instructions) | consumed — C1 denied and reverted at gen-002; C2 confirmed, clause 2 identified as the operative half |
| 2 | gen-002 | C1 revert (D1) + T3 transfer-reason lookup (D2, extension-hook) | consumed — D1's attribution test settled task_057 on C2; D2 denied on its target, mechanism confirmed on the anchor, KEPT |
| 3 | gen-003 | T6 duplicate verification write (E1, extension-hook) | in flight |
| 4–6 | — | T4 (governing-rule half), T1 (task_026 only), T5 | open |

Six targets opened, four consumed, **one retired with cause** (T3 for `task_014` — the
deciding request arrives as the terminal message, so no hook can act after it; seven transfer
mutations across four experiments have moved the rate and none the discrimination) and **one
half-retired with cause** (T4's `credit_type`
enum half — the legal values are already enumerated with their semantics in the unlock
response and were read correctly; the disagreement is with gold's labelling, which is frozen
surface, not harness surface).

**Surface concentration (D26 flag):** 0 prior `instructions` mutations in this experiment,
so the flag has not fired. The set nonetheless leads with a structural change, because the
standing prior across three closed experiments is that 17 of 18 slots went to one
`SYSTEM.md` paragraph and the loop did not improve.

<!-- transition: gen_000_to_001 -->
