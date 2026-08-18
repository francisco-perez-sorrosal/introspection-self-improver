# Improvement backlog — experiment 012_ceiling-emb-luna56

Mutation targets, ranked. Opened at the g=0 decision point (2026-08-18) by open-coding
`batch_01`'s 78 episodes — τ's graded `action_checks` re-read under a **normalized**
comparison (`scripts/gold_diff.py`), plus full transcripts for the decisive cases — before
any taxonomy was imposed. `protocol.generations: 7` with `identity_generations: [1]`, so
there are **six mutation slots** (gen-002…gen-007); `batch_08` is H7's endpoint round and
consumes no transition.

**Autonomy.** `protocol.require_human_approval` is frozen **false** for seq 12 (D23 envelope,
ratified in the launch directive). Target approval and set composition are the orchestrator's.
Every decision below is recorded with its reasoning so it can be audited as a human gate would.

**Batch-mode caveat.** `protocol.batch_mode: fixed` — the SAME twenty-six tasks every round.
`batch_01` is the pre-mutation baseline and `batch_02` is the pre-registered A/A round under an
identical harness. **From `batch_03` on, every batch number measures a set the loop has been
tuned on**, and every digest, diagnosis and record says so.

**Backend caveat, stated once.** `--retrieval-config` is `openai_embeddings` for the first
time in this project. **No absolute number here compares to seq ≤ 10.**

## Round health and the composition note

`batch_01`: 78 episodes, **77 graded**, all four sandbox seam counters **0**, zero stall
warnings, `arm_sha_ok` on every completed row, `pi_local_calls` 0 (correct — H0's registry is
empty), `stream_reattaches` 265 (benign). **One episode lost**: `task_003` t0,
`UserMessage must have either content or tool_calls` after 4 attempts — the luna
user-simulator empty-completion signature, frozen-surface weather, not investigated.
`run.py` refuses to resume a closed round, so the loss is **accepted and recorded** rather
than topped up; `task_003` carries 2 graded trials in `batch_01`, and the endpoint test
handles unequal per-task n by construction (it permutes within each task given that task's
own total).

**Result: 26/78 episodes (33.3%); mean per-task rate 33.3%.** Phase 0 measured H0 on exactly
this batch at 32.1% — the seam is behaving and no D8 viability read is triggered.

**Composition note, recorded now so it is not discovered at closure.** The anchor stratum is
weaker in this round than the freeze assumed. Phase 0 measured all three anchors 3/3 on the
**local** lane; `batch_01` is the **platform** lane and returns `task_006` 2/3, `task_032` 2/3,
**`task_063` 0/3**. `task_063` moving three cells is above every measured noise floor, so the
regression channel is really `task_006` + `task_032` (five of six cells) plus `task_005` and
`task_037`, which both ran 3/3 here. Every change's falsifier names those four.

---

## The reading correction that bounds every prevalence figure below

τ compares `call_discoverable_*_tool` payloads as JSON **strings**, so a semantically
identical call registers as a miss on whitespace alone. Every figure here is computed against
the **normalized, three-way** comparison, because "never called it" and "called it wrong" are
different defects with different owning layers:

| verdict | meaning | `batch_01` |
|---|---|---|
| MATCH | gold action performed, arguments semantically identical | **197** |
| ARGS | same tool, arguments differ semantically | **94** |
| ABSENT | the gold action was never performed | **26** |

**The dominant H0 failure mode of this batch is argument-value resolution, ~4:1 over
discovery.** Splitting the 94 ARGS instances finer (`scratchpad/argshape2.py` logic, re-run
per round) gives the differing key: `card_type` 7 tasks / 10 episodes, `account_class` 4 / 10,
`agent_tool_name` 5 / 9, `account_type` 2 / 5, `reason` 3 / 5, `transaction_id` 1 / 3.

### The decisive read — what stands between a failing episode and a pass

Of the **51 failing graded episodes**, per-episode enumeration of *every* unmatched gold
action gives the set of distinct miss-mechanisms in that episode. Episodes with exactly one:

| sole mechanism | episodes | tasks |
|---|---|---|
| **T1 wrong named class** (`card_type` / `account_class` / `account_type`) | **11** | `task_001` `task_002` `task_003` `task_023` `task_024` `task_058` |
| **T5 gold action never performed** | 8 | `task_006` `task_010` `task_015` `task_032` `task_055` `task_063` `task_076` |
| **T4 wrong `reason` enum member** | 5 | `task_004` `task_008` `task_014` |
| **T3 wrong discoverable tool** | 5 | `task_046` `task_063` `task_094` |

22 episodes carry two or more. T1 appears in **10 of those 22** as well, so T1 is implicated
in **21 of 51** failing episodes — by a wide margin the largest mechanism in the batch.

---

## T1 — a bank-defined named option is committed to before the attribute that selects it is retrieved

**Status:** pending (gen-001 is the pre-registered identity round) · **Owning layer:**
harness (retrieval usage → query formulation)
**Prevalence:** sole cause in **11/78 episodes across 6 tasks**; implicated in 21/51 failing
episodes across 10 tasks

The agent picks the wrong member of a bank-defined catalogue — a credit-card type, an account
class. The tool is right and the customer data is right; the class is wrong. Two transcripts
carry the causal chain end to end, and they agree on the mechanism.

- **`task_002` — 0/3, and the reasoning states the defect in words.** Gold
  `card_type: "Platinum Rewards Card"`; the agent applied for `"EcoCard"` (t0, t1) and
  `"Crypto-Cash Back Card"` (t2). Conv `01a01695-c9df-75aa-99c2-bf4ec23d82f8`: it issued
  **four `KB_search` calls and got substantially the same documents back each time** —
  `doc_credit_cards_gold_rewards_card_001` returned at rank 1 in three of them. It had the
  **complete card catalogue by name** in context the whole time (the Diamond Elite APY-bonus
  table enumerates all eight cards), and never retrieved the Platinum document. Its own
  penultimate reasoning block reads: *"if we're looking for a card with the highest overall
  flat rate and no subscription, the available data is insufficient. So, I'll recommend the
  EcoCard…"* — it records the gap and answers anyway.
- **`task_056` — 0/3, same shape on `account_class`.** Gold `"Cobalt Blue"`; the agent opened
  `"Hunter Green"` in all three trials. Conv `01a0169b-6d5c-7222-b82f-ee9c5b311920`: at its
  second search it retrieved `doc_bank_accounts_bank_accounts_(general)_013`, an **active
  promotion notice** (11/01–11/30/2025; episode time 11/14) that states the recommendation
  ordering for business checking outright — and never applied it. It also *named* Cobalt Blue
  in its own candidate prose and never retrieved that candidate's document. Its reasoning at
  the deciding step: *"ATM rebates are unclear… I might only recommend Hunter Green
  conditionally"*, then recommends it unconditionally.
- **`task_058` — 0/3.** Gold `account_class: "Silver Account"` (savings) and
  `card_type: "EcoCard"`; the agent chose `"Gold Account"` 3/3 and `"Gold Rewards Card"`.
  Note the direction reverses between tasks — `task_002` should have been Platinum and got
  EcoCard, `task_058` should have been EcoCard and got Gold — so this is not a bias toward
  one product. It is a failure to resolve the rule.

**The mechanism, stated so it can be falsified:** the agent searches by *intent* ("highest
cash back card", "green business account"), which under `openai_embeddings` returns
substantially the same high-scoring documents on every re-ask, and it commits to a named
member while a requirement-relevant attribute of that member is still unretrieved. The
candidate names are already available to it; the per-candidate attributes are not.

**The consolidation matters more than the count.** `task_055`'s wrong `account_id` on the
downstream user-tool call, and `task_056`'s wrong `destination_account_id`, are **not**
independent identifier defects: the wrong account was created, so every downstream identifier
is wrong. Prevalence is counted on the mechanism, not the symptom.

**`surfaces_considered`** (written at open time, D26):
- `instructions` — **leading candidate**, but with a named hazard. This is a *procedure* rule
  (which query to issue before committing), not a judgment about when to act, which is the
  shape prose has been measured to carry. The hazard is cost: a prior experiment raised
  `KB_search` 31% with a per-candidate instruction and paid for it in episode length, then
  reverted it. Any landing here pre-registers a `KB_search`-per-episode **delta** falsifier.
- `extension-hook` (`tool_result`) — **strong structural alternative.** `KB_search` results
  carry `N. <Title> ID: doc_… Score:` lines, so a hook can deterministically name which
  catalogue members have appeared *by title* in this episode and which of those have not yet
  had their own document returned. That is a **missing-state** note — the shape measured to
  move a counter 0/3 → 3/3 — and specifically **not** the bare list a prior experiment
  measured inert twice. Blocker: none; the surface and `event.input` are measured on this
  domain. Risk: it must not name which member is correct (answer-hardcoding).
- `extension-tool` — exercised and works, but the shape is wrong here: the defect is *which
  query is issued*, not a computation over values already in hand. A prior experiment landed
  exactly the comparison tool for this mechanism, got enthusiastic adoption, and moved no
  reward, and its own remainder was diagnosed as the retrieval gap this target names.
- `sub-agent` — never exercised; a "retrieve the attributes of these N named candidates" job
  has a stable contract and an independently checkable result, so this is a genuine fit and
  the reserved-slot's most natural home. Blocked until the step-4b probe settles whether a
  child's own tool calls spend the parent's τ step budget.

---

## T2 — the agent volunteers optional arguments the gold call does not carry

**Status:** pending · **Owning layer:** harness (call shape)
**Prevalence:** **9/9 episodes across 3 tasks** — `task_060`, `task_061`, `task_065`. Fully
deterministic: every trial of every one of those tasks.

Gold calls `close_bank_account_7392` with `{"account_id": …}` alone. The agent calls the same
tool, same account, and adds `reason` and `waive_early_closure_fee` — parameters the customer
never asked for and the gold procedure does not carry. Because the payload of a discoverable
tool is compared as a whole nested object, the extra keys are a miss.

- `task_060` t0 is the sharpest cell in the batch: it performed the unlock, opened the correct
  `"Silver Plus Account"` savings account, and its **only** remaining defect against gold is
  the two volunteered arguments on the closure call.
- 8 of the 9 instances add both keys; one adds `reason` alone.

**`surfaces_considered`:**
- `instructions` — **leading candidate, and unusually well-evidenced for prose.** This is a
  rule about how to write one call, with no scope to over-generalise into — the one
  instruction shape a prior experiment measured working rather than failing. Risk to watch:
  an over-broad reading that starts omitting *required* arguments; the falsifier is stated as
  a delta on gold-required-argument omissions, not as a level.
- `extension-hook` — cannot help: blocking or rewriting an outbound τ tool call from a
  `tool_call` hook is forbidden on this seam (τ executes it anyway and the histories diverge).
- `extension-tool` / `sub-agent` — wrong shape; the failing step is what the agent emits.

---

## T3 — the wrong discoverable tool is unlocked and called

**Status:** pending · **Owning layer:** harness (retrieval usage → procedure lookup)
**Prevalence:** sole cause in **5 episodes / 3 tasks** (`task_046`, `task_063`, `task_094`);
`agent_tool_name` differs in 9 episodes across 5 tasks once multi-mechanism episodes count.

`task_046`: gold unlocks and calls `get_user_dispute_history_7291`; the agent unlocked
`get_all_user_accounts_by_user_id_3847`, `pay_credit_card_from_checking_9182` and
`get_closure_reason_history_8293` instead — three wrong members of the discoverable-tool
catalogue, none of them the one the procedure names. `task_060` t1/t2: gold requires unlocking
`open_bank_account_4821`; the agent unlocked three other tools and never opened the account,
dropping the additive half of the customer's request entirely.

Structurally this is T1's mechanism on a different catalogue, which is why it is filed
separately rather than merged: if a T1 change moves T3's tasks too, the mechanism
generalizes; if it moves only the product classes, it does not.

**`surfaces_considered`:** `instructions` — available, and the rule ("unlock the tool the
retrieved procedure names, not one whose name resembles the goal") is procedural rather than
judgmental. `extension-hook` (`tool_result`) — could surface the tool names the retrieved
procedure document actually mentions; measured surface, same missing-state shape as T1's
alternative. `extension-tool` — a checkable "which tool does this procedure name" resolver;
legal but overlaps the hook at higher cost. `sub-agent` — no.

---

## T4 — a generic fallback enum member is chosen where a specific one applies

**Status:** pending · **Owning layer:** harness (value resolution)
**Prevalence:** sole cause in **5 episodes / 3 tasks** — `task_004`, `task_008`, `task_014`

All three grade on `ACTION` with `compare_args: ["reason"]`, so the transfer itself is right
and only the code is wrong, and every one of the three passes on at least one trial — the
value is resolvable.

| task | gold `reason` | agent chose |
|---|---|---|
| `task_004` (t0, t1) | `account_ownership_dispute` | `customer_requests_human_no_specific_reason` |
| `task_008` (t1) | `customer_demands_after_unavailable_offer_refusal` | `kb_search_unsuccessful_customer_requests_transfer` |
| `task_008` (t2) | `customer_demands_after_unavailable_offer_refusal` | `unconfirmed_external_communication` |
| `task_014` (t?) | `unconfirmed_external_communication` | `kb_search_unsuccessful_customer_requests_transfer` |

The pattern is one-directional and therefore diagnosable: the agent reaches for a **generic
catch-all** member (`…no_specific_reason`, `kb_search_unsuccessful…`) where a member naming
the actual situation exists in the same enum. `task_008` t2 is the exception that proves it —
it picked a specific member, just the wrong one.

**`surfaces_considered`:** `instructions` — a selection rule ("prefer the most specific
applicable member; a catch-all only when no specific member describes the situation"), not a
rule about *when* to transfer. The distinction matters: prose about when to transfer has moved
the rate across four prior experiments and moved discrimination once, whereas nothing has yet
been landed on which member to name. `extension-hook` (`context`) — a counted report of
whether the enum has been read this episode; legal, measured. `extension-tool` — an enum
resolver; legal, unexercised-shape overlap with T1's alternative.

---

## T5 — the procedure stops before the customer's later requests

**Status:** pending, **held** · **Prevalence:** sole cause in 8 episodes / 7 tasks, but
heterogeneous

`task_055` t2 alone contributes 8 absent gold actions; `task_063` t0/t1, `task_032` t1,
`task_076` t1, `task_010` t0/t2 (`submit_referral` never called), `task_015` t2, `task_006` t2.
Held rather than consumed: the shape overlaps T1 (an agent that cannot resolve a value stalls
and escalates), and a prior experiment measured that over-escalation was moved by none of its
eight mutations. **Re-rank against `batch_02`**, which measures the same harness and will say
which of these cells are noise.

---

## Slot accounting

| Slot | Generation | Target(s) | Status |
|---|---|---|---|
| — | gen-001 | **pre-registered identity** (D30 rule 2) | H1 = H0; `batch_02` is the A/A noise measurement |
| 1 | gen-002 | TBD against `batch_02` | open |
| 2–6 | gen-003…gen-007 | — | open, **one reserved for `sub-agent`** |

**Surface concentration (D29, surface-general):** 0 mutations in this experiment, so the flag
has not fired. The **project-scope surface ledger** is what bears on the first set:

| surface | ever exercised in a graded round, ANY experiment | measurement status | current blocker |
|---|---|---|---|
| `instructions` | yes — ~21 slots across seq 4/5/6/8/10 | live | none; standing prior is that it fails for judgment and works for call-shape rules |
| `extension-hook` | yes — 6 changes in seq 8, 1 in seq 10 | `before_agent_start`, `tool_result`, `context` all measured functional on the real domain | none; the one measured null was a **bare list**, replicated twice — do not spend a slot on one |
| `extension-tool` | yes — seq 10's C1, `pi_local_calls` 0 → 39 in one round | reachable and correctly invoked; **usefulness unmeasured** (adoption moved no reward) | none |
| `sub-agent` | **never** — no episode has ever run one on this seam, in any experiment | never probed | **step-4b probe required at g=0**; open question is whether a child's own tool calls spend the PARENT's τ step budget |
| declared skill | n/a | measured **inert** on this seam | not a delivery surface |

Ties between candidate surfaces break toward the best-measured one **unless the digest names
that asymmetry out loud** — named here: `instructions` and `extension-hook` are the
best-instrumented, and they are where a loop with these four targets will drift if nothing
holds the reservation. Seq 12 reserves one slot for `sub-agent` and the probe below is what
decides whether the reservation is spendable.

<!-- transition: gen_000_to_001 -->
