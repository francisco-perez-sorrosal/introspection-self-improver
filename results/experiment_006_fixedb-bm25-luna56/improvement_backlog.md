# Improvement backlog — experiment 006_fixedb-bm25-luna56

Mutation targets, ranked. Opened at the g=0 decision point (2026-08-16) by open-coding
`batch_01`'s own 24 conversations before any taxonomy was imposed. `protocol.generations: 6`,
so there are **six mutation slots** (gen 001…006); `batch_07` is H6's endpoint round and
consumes no transition.

**Autonomy.** `protocol.require_human_approval` is frozen **false** for seq 6 (plan D23):
target approval and set composition are the orchestrator's, delegated by the user. Every
decision below is recorded with its reasoning so it can be audited exactly as a human gate
would have been.

**Batch-mode caveat.** `protocol.batch_mode: fixed` — the SAME eight tasks every round.
`batch_01` is the pre-mutation baseline, but the eight were hand-picked (in seq 5) from
seq-4 known-fails, so its floor reading is by construction and it is not an unbiased sample
of the pool. **From `batch_02` on, every batch number measures a set the loop has been tuned
on**, and every digest, diagnosis and record must say so.

**Evaluator properties, not failure modes.** Carried forward while open-coding and not
backlog items: `call_discoverable_*_tool` payloads are compared as JSON *strings*, and seven
of the eight tasks grade on a `DB` basis, so their action-check misses cost no reward
directly — only the resulting database state does.

---

## The structural finding that bounds every target below

Recorded first because it changes which surfaces the targets may use. Measured this
transition (`generation_000/seam_probe/`): a Pi-local extension-tool call reaches τ as an
**invalid tool call**, costing a τ step and one of ten `max_errors`. Sub-agents use the same
path; blocking a τ tool call is worse still (τ executes the write anyway).

**So two of the three growth surfaces both prior closures named as "unused" were never
available.** What remains: `SYSTEM.md` `<instructions>`, a Pi skill's name and description
(its body needs `read`, which this agent deliberately lacks), and the extension hooks that
introduce no tool call — `before_agent_start`, `tool_result`, `context`. Any prompt-only set
this experiment lands cites this paragraph as its reason, and any structural change it lands
must come from that last row.

---

## T1 — A bank-defined value is chosen from a candidate set the agent never enumerated

**Status:** consumed-by-gen-001 · **Owning layer:** harness (retrieval usage)
**Prevalence:** 4/8 tasks (`task_065`, `task_070`, `task_082`, `task_096`), 10/24 episodes

The agent searches competently for the customer's *subject*, then picks the option whose name
best fits the customer's words — from among the options it happens to have named, never from
the bank's own list.

- **`task_070` — 3/3, and it is the clean case.** Gold opens `business_checking` with
  `account_class: "Sky Blue"`. The agent opened `Hunter Green` (t0, t1) and `Cobalt Blue`
  (t2). Across **22 KB queries in three trials, not one asks for the list of business-checking
  classes**: every query is built either from the customer's requirements ("no overdraft fees",
  "ATM fee rebates at least $15 per month") or from class names the agent already had in hand
  ("Navy Blue Cobalt Blue True Blue", "Hunter Green"). `Sky Blue` never entered the candidate
  set, so no amount of care in choosing could have reached it.
- **`task_065` — 3/3.** Gold opens `Green Account` (savings) and `Evergreen Account`
  (checking). The agent opened `Evergreen Account` ✓ + nothing (t0), `Blue Account` +
  `Silver Plus Account` (t1), `Bluest Account` (t2).
- **`task_096` — the numbers are this mode too.** Gold reports `expected_apy` 3.25 / 6.85; the
  agent supplied 2.95 (t0), 3.0 (t1), 2.7 (t2) for the same account. The APY is a value the
  bank defines in a rate table, not a quantity to estimate — and t1 got the *other* account's
  pair exactly right (6.85 / 6.55), which shows the mode is retrieval-dependent rather than
  arithmetic.
- **`task_082` t1** filed a dispute with `dispute_category: "card_not_present_fraud"` where gold
  is `card_present_fraud`, and closed the card with `reason: "fraud_suspected"` where gold is
  `"lost"` — both enums with a defined legal set.

**Why this target first:** highest prevalence among the modes that are unambiguously harness
surface; a *procedural* rule (enumerate, then choose) rather than a judgment rule, so it has no
scope to over-generalise into; and it does not touch the frozen policy, which is where four of
seven prior mutations died.

---

## T2 — The agent stops partway through the set of actions the customer asked for

**Status:** consumed-by-gen-001 · **Owning layer:** harness (procedure completion)
**Prevalence:** 4/8 tasks (`task_014`, `task_028`, `task_065`, `task_096`), 6/24 episodes

Not a value error — a coverage error. The agent does part of the work correctly and ends.

- **`task_096` 2/3** — the customer names two savings accounts; t0 and t2 credit and report on
  the Bronze account only and never touch Gold Plus. t1 acted on both.
- **`task_065` 2/3** — t0 and t2 close the checking account and open one replacement; gold
  opens **two** (savings `Green Account` *and* checking `Evergreen Account`).
- **`task_028` t2** — updates 5 of the 6 gold transactions with **exactly the gold values**
  (669, 642, 750, 2049, 1390) and omits the sixth (`txn_57ecc6da56c2`, 95). The one episode in
  the batch whose values were right failed on coverage alone.
- **`task_014` t2** — 12 messages, 2 searches, then no action at all, on a task whose t0 and t1
  passed by taking one.

**Standing counterevidence, recorded with the target.** `task_026` t1 shows the opposite
failure in the same family: told to correct four transactions, it wrote **fourteen**. A
completion rule that is not bounded to *what the customer named* converts this target into that
one. The gen-001 wording is bounded for exactly that reason and `task_026`'s write count is its
pre-registered falsifier.

---

## T3 — Optional arguments are volunteered into state-changing calls

**Status:** consumed-by-gen-001 · **Owning layer:** harness (tool-contract reading)
**Prevalence:** 1/8 tasks, 3/24 episodes — the weakest evidence in this set, and it is landed
anyway for the reason below

`task_065`'s gold closes the account with `account_id` **alone**. All three trials volunteered a
`reason` (`"customer_requested_closure"` t0, `"Customer requested a switch to a checking account
with enhanced benefits"` t2, `"Customer requested replacement with Blue Account"` t1), and t1
additionally volunteered `waive_early_closure_fee: false`. The tool writes these into account
state, so an argument nobody asked for becomes a database difference on a `DB`-graded task.

**Prior-experiment context, and why the decision differs.** Seq 5 recorded this as its item T4
and **deliberately refused to target it**, on the grounds that the only reliable lever was
matching the tool's default string — grader-gaming against a frozen evaluator. That judgment
was right about *that* lever and is not disturbed. gen-001 uses a different one: do not supply
an optional argument you were not asked for. That is a principled rule about writing state,
not a string match, and seq 5's own gen-001 produced exactly this behaviour as an unintended
side effect and flipped the task with it. Landed third, with its 1/8 prevalence stated.

---

## T4 — Transfer to a human while gold actions remain — NOT TARGETED, and this is the
## most-evidenced mode in the batch

**Status:** pending, deliberately unconsumed · **Prevalence:** 4/8 tasks
(`task_026` 2/3, `task_028` 2/3, `task_082` 2/3, `task_096` 1/3), **7/24 episodes**

`transfer_to_human_agents` appears in no `DB`-basis task's gold, and `task_082` is the extreme:
the customer's opening line asks for a human and t0 and t2 transfer at the **first** turn after
a single KB search — 8 messages against roughly twenty gold actions — while t1, under the same
harness on the same task, worked for 76 messages and filed every dispute.

**It is not targeted, and the reason is the strongest evidence this project owns.** Across seq 4
and seq 5 (prior-experiment context, prose only), **four of seven mutations were transfer
guidance and all four failed**: one forbade a policy-*required* transfer, one licensed a
policy-*forbidden* one, one deleted the guidance and deferred to the policy, and seq 5's gen-002
— written with that history in hand and with two structural guards designed against it —
suppressed transfers wholesale (9/21 → 0/21 on DB tasks) and broke `task_014`, whose gold **is**
a transfer. The frozen policy already fixes the threshold at four requests; every mutation that
has tried to add discipline on top of it has instead competed with it.

**The condition for consuming this target in a later slot:** a mechanism that is *procedural and
counted* rather than a judgment about when transfer is appropriate — and preferably one that
cannot over-generalise, which after the seam probe means a no-tool-call extension hook rather
than a sentence. Until such a mechanism exists, prevalence does not justify a fifth attempt.

---

## T5 — The user-facing discoverable tool is never handed over

**Status:** pending · **Prevalence:** 2/8 tasks (`task_026`, `task_028`), **0/6 episodes ever
did it**

Both tasks' gold requires `give_discoverable_user_tool("submit_cash_back_dispute_0589")` followed
by the user's own calls. Across six episodes the agent never once called it — `task_026` t2
searched for the tool ("submit cash back dispute tool couldn't be found") and gave up, while
other trials found *agent*-side tool names in the same knowledge base and used them freely.

**Deferred rather than consumed, with the reason.** The frozen `<policy>` already specifies this
procedure in full and at length ("Giving Discoverable Tools to Users … you must use the
`give_discoverable_user_tool(discoverable_tool_name)` function"). An instruction restating it is
the exact shape of mutation that failed four times in T4's history — competing with policy text
rather than adding discipline the policy lacks. If a later batch shows *what* fails (retrieval
never surfacing the user-tool instruction, versus surfacing it and not acting), the target
becomes attackable at that specific step.

---

## T6 — A value is computed rather than read, and the arithmetic drifts

**Status:** pending · **Prevalence:** 2/8 tasks (`task_072`, `task_096`), 5/24 episodes

`task_072`'s gold credits are 14.00 and 3.50; the agent produced 12.00/3.50 (t0), 14.00/6.50
(t1), 14.00/4.50 (t2) — **each amount correct in some trial, never both in one.** `task_096`'s
credit amounts are similar (11.39, 11.61+11.08, 4.19 against gold 17.50 and 15.00).

Held back because it is **not cleanly separable from T1** at this evidence: `task_096`'s wrong
amounts follow directly from its wrong `expected_apy`, so fixing the rate may fix the amount.
Re-rank against `batch_02` — if the rates come right and the amounts stay wrong, this is a
distinct target and the honest surface for it is deterministic (a `tool_result` hook that
appends an exact computation), not another sentence.

---

---

## Re-ranking against `batch_02` (H1, 2026-08-16)

`batch_02` measures a set gen-001 was tuned on. Round health clean: 24/24, one stray
`sandbox_tool_error` counter, no cell excluded. Graded read **1/24 episodes, 1/8 tasks**,
down from `batch_01`'s 2/24.

**gen-001's three predictions, scored.**

- **C1 — behaviour confirmed, outcome denied, and the pair is the transition's best finding.**
  `"Sky Blue"` appears in `task_070`'s queries (t1, t2) after **zero of 22** in `batch_01` —
  the gold option entered the candidate set for the first time — and the agent opened
  `Hunter Green` anyway, 3/3. `task_065` t2 enumerated five savings classes across sixteen
  queries and still opened `Blue`/`Silver Plus`. **Enumeration is not the binding constraint**,
  so T1 is re-specified below and gen-002's D1 targets the re-specification.
- **C2 — confirmed on `task_065` (both accounts 2/3, was 1/3), denied on `task_096`,
  over-reach falsifier strongly not triggered** (`task_026` writes 14 → 2/2/1) — **and it
  caused a measured harm through its escape clause.** See T7.
- **C3 — confirmed above prediction, 3/3** (`task_065` closes with `account_id` alone; the
  prediction asked for ≥1). Watch item, not yet a falsifier: `task_072` t1 emitted one call
  keyed `agent_name` instead of `agent_tool_name`, then reissued correctly. A second
  occurrence in `batch_03` makes it C3's falsifier firing.

**T1 is RE-SPECIFIED, not retired.** The mode is not "the candidate set is incomplete" but
"the agent ranks published features against the customer's stated wants, where the bank's
answer turns on a rule in force". Across six `task_070` episodes and ~65 queries in two rounds,
**no query asks which offer or rate is currently active**; `task_065`'s gold pairs `Evergreen`
checking with `Green` savings, a relation no single-product ranking reaches. Consumed by
gen-002 D1.

**T5 moved without being targeted, and it is the round's largest behavioural change.**
`give_discoverable_user_tool` went **0/6 → 6/6** episodes on `task_026` and `task_028`, almost
certainly from C2's completion check. Not yet a pass — the agent adds an `arguments` payload
gold does not carry and repeats the call per transaction where gold calls it once. **Left to
settle**: touching it now would confound a change that is already moving.

**T6 held again.** `task_072`'s amounts got *worse* (12/8, 14/16, 12/16 against gold 14.00 and
3.50) while its query count fell to 4/2/3. Still not separable from T1's mechanism — the fee
schedule is itself a bank-defined rule. Re-rank against `batch_03`.

**T4 (transfer) held again, and the reasoning is now testable rather than only historical.**
It rose to **11/24 episodes** from 9/24 — but gen-001's own C2 escape clause is a measured
cause of part of that rise, so gen-002's D2 removes the clause and `batch_03` says how much of
the mode was self-inflicted. Attacking transfer directly before that answer would confound the
two. This is the last generation that reasoning holds for: if `batch_03` still shows transfer
at or above `batch_01`'s 9/24 after the clause is gone, the mode is native and earns a slot.

---

## T7 — An instruction that offers an alternative to acting will have its alternative taken

**Status:** consumed-by-gen-002 (as a revert) · **Owning layer:** harness (the harness's own
prior generation) · **Prevalence:** 3 witnesses plus a round-wide shift

Not a property of the target agent — a property of **this loop's own output**, which makes it
the most transferable finding so far. gen-001's C2 required every named item to be *"either
acted on or explained to them."* The disjunction was meant to excuse items that legitimately
need no action. The model used it to convert action into explanation:

- `task_096` t2 covered the second account by filing a report with `expected_apy ==
  actual_apy == 6.55` and `amount_difference 0` — a null action that satisfies the check.
- `task_096` t0 transferred having acted on nothing, where `batch_01`'s t0 acted.
- `task_082` lost its only full-effort trial (`batch_01` t1: 76 messages, all four disputes
  filed, both cards closed, replacement ordered). `batch_02` has none.
- Round-wide, transfer-carrying episodes rose 9/24 → 11/24.

Generalised: seq 4 and seq 5 recorded that *an instruction does not inherit the scope its
author reasoned about*. This is the sharper form — **an instruction's escape clause is the part
the model optimises against.** gen-002's D2 ties the alternative to a retrieved finding rather
than to the agent's own narration.

---

---

## Re-ranking against `batch_03` (H2, 2026-08-16)

Clean round, zero seam counters. **3/24 episodes, 2/8 tasks — the curve's first rise**
(8.3% → 4.2% → **12.5%**), with **`task_072` passing for the first time (0/3 → 2/3)**.

**gen-002's predictions, scored.**

- **D1 — behaviour confirmed on both targets, outcome confirmed on an unpredicted third,
  denied a third time on `task_070`.** In-force queries appear for the first time
  (`task_070` t2 *"offers current in force account selection rule"*). The unpredicted win is
  `task_072`: t0 and t2 retrieved the ATM fee *policy* ("4 free, then $1.50") rather than
  comparing products, and supplied gold's 14.00/3.50 exactly. **T6 (computed amounts) appears
  resolved as a consequence of T1's re-specification** — re-read on `batch_04` before touching.
- **D2 — confirmed, and the kept half strengthened.** Transfers 11/24 → 10/24, no
  zero-difference report, and `task_065` opened both accounts **3/3** against the ≥2/3 its
  falsifier demanded. **C2 was separable into a working half and a harmful one**, which is the
  question D2 existed to answer.

**T8 opened — ordering of state changes (consumed by gen-003 E1).** `task_065` t2 chose **both
gold classes correctly** for the first time and still scored 0.0: it closed the checking
account first, and the savings open was then refused for a 14-day checking-tenure requirement.
Gold opens before it closes. **Invisible until now** — the classes were wrong in every earlier
round, so ordering never became binding. This is the fixed batch doing exactly what it is for.

**T4 CONSUMED (gen-003 E2), on the condition pre-registered at g=1 — which fired.** The
condition was: *if `batch_03` still shows transfer at or above `batch_01`'s 9/24 after the
escape clause is gone, the mode is native and earns a slot.* It shows 10/24. The shape is now
specific: the agent escalates when its own analysis fails to resolve (`task_096` t0 after 14
queries and two writes; t2 after 8; `task_070` t0 ran 9 queries and stopped acting entirely).
E2 targets that motive and states no condition for when transfer is appropriate — the property
all four failed predecessors lacked.

**T1 RETIRED for `task_070`, with the reason recorded.** Its prediction has been denied three
times while its behaviour clause was confirmed twice. The agent now enumerates, asks which
offer is in force, **retrieves `Sky Blue`'s own specification** (`batch_03` t1 Q11, t2 Q13) —
and still chooses `Hunter Green`, nine episodes running. The live reading is that the gold
answer is not derivable from what `bm25` surfaces, and **`bm25` is a deliberate freeze, not
harness surface**. A fourth rewording would be the loop repeating itself, which is the failure
mode this experiment exists to detect. Retired as a target; the task stays in the batch.

**T5 held again.** Still 6/6 with a superfluous `arguments` payload and repeated calls. Left to
settle rather than touched while it is moving on its own.

---

## Slot accounting

| Slot | Generation | Target(s) | Status |
|---|---|---|---|
| 1 | gen-001 | T1 + T2 + T3 | consumed — C1 behaviour-only, C2 mixed + harmful, C3 confirmed; resolved T5 as a side effect |
| 2 | gen-002 | T1 re-specified (D1) + T7 revert (D2) | consumed — D1 confirmed on `task_072` (first new pass), D2 confirmed and separated C2's halves |
| 3 | gen-003 | T8 ordering (E1) + T4 escalation (E2) | in flight |
| 4–6 | — | T5, T6 re-read against each new batch | open |

Eight targets opened, six consumed, one retired with cause (`task_070`'s T1 — likely bounded by
the frozen retrieval backend, not by the harness).
