# Improvement backlog — experiment 010_adopt-bm25-luna56

Mutation targets, ranked. Opened at the g=0 decision point (2026-08-17) by open-coding
`batch_01`'s 36 episodes — τ's graded `action_checks` re-read under a **normalized**
comparison, plus full transcripts for the decisive cases — before any taxonomy was
imposed. `protocol.generations: 8` with `identity_generations: [1]`, so there are **seven
mutation slots** (gen-002…gen-008); `batch_09` is H8's endpoint round and consumes no
transition.

**Autonomy.** `protocol.require_human_approval` is frozen **false** for seq 10 (plan D34,
re-registering D23's envelope): target approval and set composition are the orchestrator's,
delegated by the user. Every decision below is recorded with its reasoning so it can be
audited exactly as a human gate would have been.

**Batch-mode caveat.** `protocol.batch_mode: fixed` — the SAME twelve tasks every round.
`batch_01` is the pre-mutation baseline and `batch_02` is the pre-registered A/A round
under an identical harness. **From `batch_03` on, every batch number measures a set the
loop has been tuned on**, and every digest, diagnosis and record says so.

**Composition caveat.** The twelve span two anchors (`task_006`, `task_032`, 3/3 each at
H0) and ten marginals measured 1/3–2/3 by the pre-partition screen. There is **no headroom
tier and no walled task** — every non-anchor task is one H0 demonstrably passes sometimes.
Two consequences for diagnosis: **anchor cells are the regression channel**, so every
change's falsifier must name what it would do to `task_006` and `task_032`; and a mode
observed here has always been observed on a task this harness can pass, which is the
opposite of seq 5/6/8's situation.

---

## The reading correction that bounds every prevalence figure below

τ compares `call_discoverable_*_tool` payloads as JSON **strings**, so a semantically
identical call registers as a miss on whitespace alone (seq 8 measured 39 of 85 misses
formatting-only). Every figure here is computed against a **normalized, three-way**
comparison, because "never called it" and "called it wrong" are different defects with
different owning layers and τ's miss list cannot tell them apart:

| verdict | meaning | `batch_01` |
|---|---|---|
| MATCH | gold action performed, arguments semantically identical | **111** |
| ARGS | same tool, arguments differ semantically | **27** |
| ABSENT | the gold action was never performed | **9** |

**The dominant H0 failure mode of this batch is argument-value resolution, three to one
over discovery.** That is a different dominant mode from seq 8's (discovery/unlock), and
it is the mode a marginal-only batch was always going to surface: these tasks reach the
right tool and then fill it in wrong.

---

## T1 — A bank-defined product class is chosen without resolving the rule that selects it

**Status:** pending (gen-001 is the pre-registered identity round) · **Owning layer:**
harness (retrieval usage → value resolution)
**Prevalence:** 3/12 tasks, **8/36 episodes**, and it is the round's single most prevalent
mechanism

The agent picks the wrong member of a bank-defined catalogue — a credit-card type or an
account class — and everything downstream is then wrong. The tool is right, the customer
data is right, the class is wrong.

- **`task_003` — 3/3, deterministic.** Gold `card_type: "Silver Rewards Card"`; the agent
  applied for **`"Gold Rewards Card"` in all three trials**, with `annual_income` 180000
  and `rho_bank_subscription: true` both correct. It spent 1–4 `KB_search` calls before
  deciding (3–6 tool calls total, 10–16 messages). Convs
  `01a01239-cf39-7637-892d-63919a43bb95`, `01a01270-e27b-71df-8861-c212a58e5edb`,
  `01a01242-8ad7-7108-b039-2e2a191ebeb8`.
- **`task_023` — 2/3 fail.** Gold `card_type: "Diamond Elite Card"`; t0 applied for
  `"Silver Rewards Card"`, t2 never applied at all and transferred instead. t1 passed.
- **`task_055` — 3/3, and the transcript shows the causal chain end to end.** Gold opens a
  savings account with `account_class: "Silver Plus Account"`; the agent opened
  **`"Green Account"` (t0), `"Silver Account"` (t1), `"Platinum Plus Account"` (t2)**.
  Because the wrong account was created, **every downstream identifier was then wrong** —
  which is why `call_discoverable_user_tool`'s `account_id` never matches gold's
  `7e48bf3b0589cfad`. Conv `01a0123a-4657-7543-9891-4a553131df01`.

**The consolidation matters more than the count.** The account-id mismatch on `task_055`
looks like an independent identifier defect and is not: it is T1's symptom one step later.
Seq 8 paid a generation for the inverse mistake — counting `task_026` (never unlocked) and
`task_096` (unlocked, wrong values) as one target because they presented identically in the
miss list. **Prevalence is counted on the mechanism, not the symptom.**

**`surfaces_considered`** (written at open time, per D26):
- `extension-hook` (`tool_result`) — **the leading candidate.** `KB_search` results are the
  place a catalogue's selection rule is stated; a deterministic post-processing step that
  surfaces the eligibility/benefit fields the returned documents carry would put the rule
  in front of the model at the moment it chooses, without stating the answer. Enabler:
  measured functional on this domain, and `event.input` carries the query. Blocker: must
  not encode which class is correct — that is answer-hardcoding (trap 5).
- `extension-tool` — **live and never exercised**, certified by this experiment's
  suppression canary. A deterministic "compare these candidates against these stated
  rules" tool is exactly the shape prose has failed at three times. Adoption-first
  applies, and the tool may bundle its minimal usage instruction (D29).
- `instructions` — available and cheap, and this is the shape seq 4/5/6 measured failing
  four times: a sentence telling the model to compare more carefully competes with a
  frozen policy that already says to search the knowledge base.
- `sub-agent` — no stable contract for this; the job is one bounded comparison.

---

## T2 — The user is handed a display fragment where the tool needs the exact string

**Status:** pending · **Owning layer:** harness (handover precision)
**Prevalence:** 3/12 tasks (`task_055`, `task_057`, `task_089`), **7/36 episodes**

Gold has the *user* call a discoverable tool with exact arguments. In every failing episode
the user's call carries a mangled identifier, an invented tool name, or the wrong argument
key — and in each case the agent's own handover message is the source.

- **The identifier.** `task_055` t0: the agent told the customer the tool was "configured
  for your Green Account (savings) **ending in 9d4e**", and the user then called with
  `account_id: "9d4e"` — the display fragment, verbatim. The agent noticed and corrected
  ("The full account ID … is `36bec7cd2319d4ae`. Please retry"), which is the proof that
  the fragment was the cause. Other trials produced `"643"`, `"42ffb7bed6fb345b3"` (one
  character too many) and `"42ffb7bed6fb345b"` (one too few).
- **The tool name.** Users called `mobile_check_deposit` and `deposit_check` where gold
  requires `deposit_check_3847` — `task_057` and `task_089` both.
- **The argument key.** Users called with `amount` where the KB document says
  `check_amount` — `task_055`, `task_057`, `task_089`.
- **The KB states all three explicitly.** `doc_bank_accounts_bank_accounts_(general)_011`:
  "give them the `deposit_check_3847` tool. Have the user call
  `deposit_check_3847(account_id, check_amount)`". Nothing here needs domain knowledge; it
  needs the retrieved contract to reach the customer intact.
- **The agent instead pre-fills a machine payload.** Every grant carried an `arguments`
  block the user never sees, while the prose beside it abbreviated the id.

**`surfaces_considered`:**
- `instructions` — **the leading candidate**, and unusually well-evidenced for prose: this
  is a rule about *how to write one call*, not a judgment about when to act, so it has no
  scope to over-generalise into. It is also the one instruction shape a prior experiment
  measured working rather than failing.
- `extension-hook` (`tool_result`) — could rewrite the grant confirmation the model reads
  to restate the exact contract. Legal and measured, but closer to the adapter repairing
  the agent.
- `extension-tool` / `sub-agent` — wrong shape; the failing step is what the agent *says*,
  not a computation it could delegate.

---

## T3 — The transfer reason is a legal enum member and the wrong one

**Status:** pending · **Owning layer:** harness (retrieval usage → value resolution)
**Prevalence:** 1/12 tasks (`task_014`), **2/36 episodes** — low prevalence, high
diagnostic value

`task_014` grades on `ACTION` with `compare_args: ["reason"]`, so the transfer itself is
correct and only the code is wrong. Gold `unconfirmed_external_communication`; the agent
chose `kb_search_unsuccessful_customer_requests_transfer` (t1) and
`customer_demands_after_unavailable_offer_refusal` (t2) — both legal members of the
19-value enum. t0 passed.

This is T1's mechanism (a value chosen from a catalogue without resolving the rule) on a
different catalogue, which is why it is filed separately rather than merged: if a T1 change
moves `task_014` too, the mechanism generalizes; if it moves only the product classes, it
does not. **Deliberately unconsumed at the first slot** — two episodes is one witness
above noise, and the anchor `task_032` also carries a gold transfer, so a change here has a
regression channel pointed straight at it.

**`surfaces_considered`:** `extension-hook` (`context`) — a deterministic, counted report
of whether the reason lookup has happened; this is the shape a prior experiment measured
moving a counter 0/3 → 3/3 on this exact task. `instructions` — refused for now on the
standing evidence that prose about *when* to transfer has moved the rate eight times across
four experiments and discrimination once. `extension-tool` — a checkable enum resolver;
legal, unexercised, plausible.

---

## T4 — The procedure stops after the first of the customer's two requests

**Status:** pending, low priority · **Prevalence:** 2/12 tasks, **4/36 episodes**

- **`task_063` t0/t2** (0/3 overall): 21 tool calls, almost all `KB_search`, ending after
  `apply_for_credit_card` — `log_verification`, the unlock and the savings-account open all
  ABSENT. t1 performed **every gold action semantically** (6/6 MATCH) and still scored 0.0
  on the `DB` check, so `task_063` carries a second, distinct defect in state the gold
  actions do not capture — unresolved, and worth a transcript read before any slot.
- **`task_005` t0**: transferred after 5 calls with both gold actions ABSENT; t1 and t2
  passed.
- **`task_023` t2**: transferred instead of applying.

Held: the shape overlaps T1 (an agent that cannot resolve a value stalls and escalates) and
the seq-8 standing lesson that over-escalation has never been moved by any of eight
mutations. **Re-rank against `batch_02`**, which measures the same harness and will say
which of these cells are noise.

---

## Slot accounting

| Slot | Generation | Target(s) | Status |
|---|---|---|---|
| — | gen-001 | **pre-registered identity** (D30 rule 2) | H1 = H0; `batch_02` is the A/A noise measurement |
| 1 | gen-002 | TBD against `batch_02` | open |
| 2–7 | gen-003…gen-008 | — | open |

**Surface concentration (D29, surface-general):** 0 mutations in this experiment, so the
flag has not fired. The **project-scope surface ledger** is what actually bears on the
first set, and it is asymmetric by construction:

| surface | ever exercised in a graded round, ANY experiment | measurement status | current blocker |
|---|---|---|---|
| `instructions` | yes — ~18 slots across seq 4/5/6/8 | live | none; the standing prior is that it fails for judgment and works for call-shape rules |
| `extension-hook` | yes — 6 changes in seq 8 | `before_agent_start`, `tool_result`, `context` all measured functional on the real domain | none |
| `extension-tool` | **never** | suppression measured end-to-end (mock lane probe P6) **and now on the platform lane** — this experiment's `gates/suppression_canary.json`, 3/3 episodes, `pi_local_calls` 1 each, no leak | **none — the blocker is discharged.** First use is adoption-first |
| `sub-agent` | **never** — no episode has ever run one on this seam | same seam path as extension tools; latency and the started-not-finished contract unmeasured | first use must probe latency inside τ's frozen `timeout_seconds` |
| declared skill | n/a | measured **inert** on this seam (probe P2) | not a delivery surface; skill-shaped content ships via a hook |

Ties between candidate surfaces break toward the best-measured one **unless the digest
names that asymmetry out loud** — and it is named here: hooks are the best-instrumented
surface and the one seq 8 spent every slot on. Seq 10 carries an experiment-level
**surface-exercise obligation**: by close, at least one generation lands a registered
Pi-local surface change in a graded round under an adoption-first prediction, or the
backlog records why none of the open targets' mechanisms fit. **T1's leading alternative is
an extension tool, and that is the obligation's most natural home.**

<!-- transition: gen_000_to_001 -->

---

## Re-ranking against `batch_02` (H1, the pre-registered identity round, 2026-08-18)

Clean round: 36/36, all four sandbox seam counters zero, `pi_local_calls` 0. A first pass of
this round was VOIDED for seam contamination and preserved at
`generation_001/batch_02_seam_incident/`; it is used below as a third identical-harness draw
and as evidence for nothing else.

### The noise floor — the number gen-001 was pre-registered to buy

On a **byte-identical harness** (`batch_01` → `batch_02`):

| | |
|---|---|
| round total | **20/36 → 20/36, +0.0 pp** |
| task rates moved | **6 of 12**, every one by exactly ±1 |
| trial cells flipped | **14 of 36 (39%)** |
| anchors | `task_006` 3/3 → 3/3, `task_032` 3/3 → 3/3 |

With the voided pass as a third draw: `task_008` 3/2/0 (**range 3**), `task_089` and
`task_014` range 2, nine tasks range ≤1, and `task_006`/`task_032`/`task_076` stable at 9/9.

**The aggregate is a far better-behaved statistic than any single cell** — gains and losses
cancel almost exactly. The operational rule for the seven mutation slots, stricter than the
prior experiment's 2-cell version:

> A one-cell task movement is noise. Two is suggestive. **No single-task movement is
> attributable without its own mechanism counter moving in the predicted direction.**

gen-001's pre-registered expectation ("no systematic movement; both anchors hold 3/3") is
**CONFIRMED**.

### T1 REPRODUCES and consumes gen-002 (C1)

`task_003` applied for the Gold Rewards Card against gold's Silver in **6/6 episodes across
both rounds**, with `annual_income` and `rho_bank_subscription` correct every time — the
tool and the customer data are right, only the class is wrong. `task_023` chose Silver
against gold's Diamond Elite in 4/6. The counterfactual is measured: **`task_055` t0 passed
in `batch_02` precisely because it opened the `Silver Plus Account` gold requires**, where
every `batch_01` trial opened Green, Silver or Platinum Plus.

`task_003`'s customer states the selection rule in words — hard requirements, then "the one
with the smallest annual fee", then "the highest cash back". That is filtering and ordering
over retrieved values, not domain judgment, which is why it goes to a deterministic surface.

**Surface decision, and the ladder's obligation discharged at the first slot.** The
project-scope ledger above records `extension-tool` as never exercised in a graded round of
any experiment, with its blocker discharged by this experiment's platform suppression
canary. C1 is therefore **adoption-first**: the prediction targets `pi_local_calls` and
correct invocation, the reward prediction is deferred to `batch_04`, and the tool bundles
its minimal usage instruction as one mechanism (D29). Preflight (6 local episodes,
`generation_001/g002_preflight/`) confirmed the tool is called 3/3 on `task_003` with
well-formed multi-candidate arguments, and 0/3 on `task_023` whose customer never asks to
choose. **A preflight verifies a change runs, never that it works** — no behavioural number
from it is provenance.

The preflight did move the diagnosis a layer, and it is recorded here as the live risk: the
model supplied Gold at a flat 2.5% cash back against Silver's *"cash back outside top
categories"* 1.0% while the customer's stated spend is travel. **The ranking is correct on
the values supplied; the values are what is incomplete.** If the true defect is attribute
selection rather than ordering, C1 moves the failure one layer up rather than removing it —
which is a legitimate adoption-first outcome and precisely what `batch_03` reads.

### T2 THINS and waits for gen-003

`batch_01` gave the exact-string handover mode 3 tasks / 7 episodes; `batch_02`'s clear
witness is `task_057` t2 alone (the user calling `mobile_check_deposit` with an `amount` key
where the KB document states `deposit_check_3847(account_id, check_amount)`). The `ARGS`
verdicts on `give_discoverable_user_tool` in `task_057`'s *passing* trials are duplicate
grants and benign. Under D22's "the weaker-evidenced one waits", T2 is re-ranked against
`batch_03`. It is **parked, not retired** — one round of thinner evidence is not a
retirement, and the retirement bar is witnesses from ≥2 rounds or a mechanism-level
impossibility.

### T3 and T4 held

T3's `task_014` went 1/3 → 2/3, a one-cell movement that the floor measured this round
absorbs entirely. T4's `task_005` lost a cell and `task_063` gained one, likewise inside the
floor; `task_063` t1 again performed every gold action semantically and still failed the DB
check, so its second defect stands unexplained and is worth a transcript read before any
slot is spent on it.

### Slot accounting

| Slot | Generation | Target(s) | Status |
|---|---|---|---|
| — | gen-001 | **pre-registered identity** | consumed as designed — noise floor measured, baseline pooled |
| 1 | gen-002 | T1 (C1, **extension-tool**, adoption-first) | in flight — scored by `batch_03` |
| 2–7 | gen-003…gen-008 | T2 parked, T3/T4 held | open |

**Surface concentration:** 1 mutation, on `extension-tool`. The flag is nowhere near firing,
and the experiment-level surface-exercise obligation is **discharged at the first slot**
rather than deferred to the end — the failure mode the prior experiment demonstrated when
six of six changes landed on the one surface that had a template.

<!-- transition: gen_001_to_002 -->

---

## Re-ranking against `batch_03` (H2, 2026-08-18)

Clean round: 36/36, all four sandbox seam counters zero, $0.95. **Third round over the same
twelve tasks — from `batch_02` on, every batch number measures a set the loop has been tuned
on.**

### gen-002's prediction, scored

**C1 — ADOPTION CONFIRMED on every clause.** `pi_local_calls` **0 → 39**, in 18 of 36
episodes across 6 of 12 tasks; `task_003` called it 3/3 against a predicted ≥2/3; arguments
well-formed multi-candidate payloads; no episode hit τ's timeout. This is the project's
**first graded use of a Pi-local surface** — the D24 path three closures named as the live
hypothesis for why the loop could not improve is usable, not assumed.

**C1's reward is DEFERRED, not denied,** per its pre-registration. The round fell to 17/36
(47.2%) against the pooled H0 baseline 40/72 (55.6%). Anchors held 3/3. Per task against its
own identity-draw range: `task_057` 4/6 → 0/3 (outside), `task_076` 9/9 → 2/3 (outside),
`task_055` 1/6 → **2/3** (outside, a gain), `task_014` 3/6 → 0/3 (inside range, and it never
called the tool), `task_003` 0/6 → 0/3 (called 3/3, unmoved).

**C1 is not reverted.** The bar is a denied *mechanism*; its mechanism was confirmed and its
reward prediction has not come due. Reverting on a deferred prediction would be the exact
error the prior experiment's counterfactual warned about.

### T2 RE-OPENED and consumed by gen-003 (C2)

`task_057`'s collapse is not the tool. All three trials fail on the handover: the user calls
`mobile_check_deposit`, `mobile_deposit`, `deposit_check`, `mobile_deposit_check` with an
`amount` key where the retrieved KB document states
`deposit_check_3847(account_id, check_amount)` — **three invented names per episode**,
against `batch_02`'s single witness.

T2 was **parked** at gen-002 when its evidence thinned. That was right, and so is the
reopening: *one round's thin evidence is no more grounds for dismissal than for retirement*.
Two rounds of witnesses now exist, and the target is consumed on the **counted mechanism**
(invented names, enumerated) rather than on the cell movement, which the measured floor
cannot support on its own.

Preflight (`generation_002/g003_preflight/`, 6 local episodes): all three `task_057` trials
now carry `deposit_check_3847` and `check_amount` in the user's call, invented names gone.
The remaining failure there is `account_class` — **T1's** mechanism, not T2's. A preflight
verifies a change runs, never that it works.

### The open question `batch_04` must answer

The tool was called on four tasks that are **not** product-selection tasks (`task_057`,
`task_063`, `task_076`, `task_006`), and two of those fell. That is consistent with
over-application costing turns, and equally consistent with the measured noise plus T2 firing
independently. **`task_076` is the sharpest test available**: 9/9 across three
identical-harness draws, now 2/3. If it does not recover in `batch_04` with T2 repaired, C1's
usage instruction needs narrowing to selection contexts — and that, not a revert, is the
proportionate response to a confirmed mechanism with a scope problem.

### T1 stands, unmoved and now better understood

`task_003` called the tool 3/3 and stayed 0/3. The preflight at gen-002 already showed why:
the model supplies Gold at a flat 2.5% against Silver's *"cash back outside top categories"*
1.0% while the customer's stated spend is travel. **The ranking is correct on the values
supplied; the values are what is incomplete.** T1's remainder is therefore *attribute
selection*, not ordering — a re-specification, recorded here rather than treated as a fresh
target.

### Slot accounting

| Slot | Generation | Target(s) | Status |
|---|---|---|---|
| — | gen-001 | pre-registered identity | consumed as designed |
| 1 | gen-002 | T1 (C1, extension-tool, adoption-first) | adoption CONFIRMED; reward deferred to `batch_04`; KEPT |
| 2 | gen-003 | T2 re-opened (C2, instructions) | in flight — scored by `batch_04` |
| 3–7 | gen-004…gen-008 | T1 re-specified (attribute selection), T3, T4 | open |

**Surface concentration:** 2 mutations — one `extension-tool`, one `instructions`. No class
is at 3; the flag is not near firing, and the ladder's obligation was discharged at slot 1.

<!-- transition: gen_002_to_003 -->

---

## Re-ranking against `batch_04` (H3, 2026-08-18)

Clean round: 36/36, all four seam counters zero, **every episode `user_stop` with zero
`max_steps`**, $0.98. Fourth round over the same twelve tasks — a set the loop has been
tuned on.

### gen-003's prediction, scored

**C2 — CONFIRMED on its counter, exactly.** `task_057` t0/t1 went from *three invented
user-tool names per episode* (`mobile_check_deposit`, `mobile_deposit`, `deposit_check`,
`mobile_deposit_check`, all with an `amount` key) to **exactly one call, `deposit_check_3847`
with `check_amount`**. `task_055` went from a spurious `amount`-key call alongside the
correct one, to one correct call in all three trials. **Zero invented names round-wide.**
`task_089` made no user call in either round — that third target is **unobservable**, not
confirmed.

### The round rose, and the honest attribution is smaller than the rise

**26/36 (72.2%)**, up from 17/36, against the pooled H0 baseline 40/72 (55.6%). Anchors
3/3 for the fourth round running.

**`task_014` contributed 3 of the 9-cell rise and neither change can act on it** — no
user handover for C2 to shape, and it called the tool in neither round. Its identity-draw
range was already 2. Recorded before any narrative is built on the total. What is defensibly
attributable: C2's counter, `task_003` 0/6 → **1/3** (its first pass of the experiment,
tool called 3/3), and `task_076` 2/3 → **3/3**, recovering the fall named at gen-003 as the
sharpest available test.

### C1's scope problem — measured, and consuming gen-004 (C3)

The tool is called hardest where it does not belong: `task_055` 9 → **15** calls,
`task_057` 5 → **11**, `task_063` 9 → 9 **while still 0/3 across all four rounds**.

| | H0 (`batch_01`/`02`) | H2 (`batch_03`) | H3 (`batch_04`) |
|---|---|---|---|
| mean msgs/episode | 37.3 / 36.2 | 41.5 | 42.1 |
| mean tool msgs | 11.9 / 11.6 | 14.6 | 14.4 |
| round cost | $0.64 / $0.63 | $0.95 | $0.98 |

Plus H3's held-out round carrying this experiment's **first `max_steps` termination**
(1 of 108 — a completeness fact; no held-out reward was read) where H0's and H2's carried
none. **Step exhaustion is a harness cost to fix** (user direction, 2026-08-18), not a
budget to raise: `max_steps` is frozen, and raising it mid-experiment would let a later
generation improve by being allowed to do more.

gen-004 narrows the **usage instruction**, not the tool — the tool ranks what it is given,
correctly. **This is not a revert**: C1's mechanism was confirmed, and a confirmed mechanism
with a scope problem earns a narrowing.

### T1's remainder is isolated, and T5 opens

`task_003` reached 1/3 — its first pass — but what still fails is **attribute selection**,
not ordering: the model supplies a flat cash-back figure for one candidate against a
category-qualified figure for another, while the customer's stated spend sits in that
category. Carried as the leading gen-005 candidate.

**T5 — turn efficiency, opened as a first-class target** by user direction. The measurable
is the episode profile above plus `max_steps` terminations, and C3 is its first change.

**`task_063` is the experiment's hardest cell**: 0/12 episodes lifetime, calling the tool 9
times a round, and its `batch_01` t1 performed every gold action semantically yet failed the
DB check. That second defect is unexplained and no slot has been spent on it. It needs a
transcript read before it earns one — parked with the reason recorded, not retired.

### Slot accounting

| Slot | Generation | Target(s) | Status |
|---|---|---|---|
| — | gen-001 | pre-registered identity | consumed as designed |
| 1 | gen-002 | T1 (C1, extension-tool, adoption-first) | adoption CONFIRMED; kept; scope problem found |
| 2 | gen-003 | T2 (C2, instructions) | **CONFIRMED** on its counter |
| 3 | gen-004 | T5 turn cost / C1 scope (C3, instructions) | in flight — scored by `batch_05` |
| 4–7 | gen-005…gen-008 | T1 re-specified (attribute selection), T3, T4, `task_063` | open |

**Surface concentration:** 3 mutations — 1 `extension-tool`, 2 `instructions`. The
`instructions` class reaches 3 at the next instructions change, which arms the D29 ladder:
the set after that must include a change on a class this experiment has not exercised
(`sub-agent`, or a hook), or record a `surface_exhausted` finding citing a probe or measured
fact per unexercised alternative. Recorded now so it is not discovered late.

<!-- transition: gen_003_to_004 -->
