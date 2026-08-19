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

---

## Re-ranking against `batch_02` (H1, the pre-registered identity round, 2026-08-18)

Clean round: 78 episodes, 77 graded, all four sandbox seam counters zero, zero stall
warnings, `pi_local_calls` 0, $1.19. **The same cell was lost as in `batch_01` — `task_003`
trial 0, identical user-simulator signature.** Twice in two rounds on exactly one (task,
trial) pair makes it **deterministic for that cell**, not weather; trials 1 and 2 complete
normally, so `task_003` carries 2 graded trials per round. Recorded, not investigated: it is
frozen-surface behaviour, and it is not the seq-1 class of defect, which killed every trial
of its task.

### The noise floor — the number gen-001 was pre-registered to buy

On a **byte-identical harness** (`batch_01` → `batch_02`):

| | |
|---|---|
| round total | **26/77 → 28/77, +2.6 pp** |
| task rates moved | **13 of 26** |
| rates that moved TWO cells | 3 — `task_005` 3/3→1/3, `task_014` 2/3→0/3, `task_063` 0/3→2/3 |
| rate-equivalent trial cells flipped | 16 of 77 |

**The floor is not uniform across strata, and that is the most useful thing this round
found:**

| stratum | `batch_01` | `batch_02` | movement |
|---|---|---|---|
| anchor (3 tasks) | 4/9 | 7/9 | **+3 cells** |
| marginal (12 tasks) | 19/35 | 18/35 | −1 cell, 9 of 12 rates moved |
| **headroom (11 tasks)** | **3/33** | **3/33** | **ZERO — 8 of 11 tasks 0/3 twice** |

So this batch has two attribution regimes. A change whose target tasks are **headroom** has
a channel with **no measured ambient noise**; a change whose targets are marginal or anchor
has the noisiest channel this project has instrumented. Every set from here says which
regime it is playing in.

`batch_01`'s worrying anchor reading — `task_063` at 0/3 against Phase 0's local-lane 3/3 —
**resolves itself**: it came back at 2/3. It was a draw, not a composition defect, and the
freeze's anchor stratum is intact.

> **The operational rule, this experiment's own:** a one-cell task movement is noise — half
> the batch does it on an identical harness. Two cells is inside the measured range too.
> **Nothing at the reward level is attributable without its own mechanism counter moving in
> the predicted direction.** The headroom stratum is the single exception: movement there is
> signal.

gen-001's pre-registered expectation ("no systematic movement") is **CONFIRMED** on the
round total (+2.6 pp, inside every prior identity measurement) and the per-cell churn is
larger than any of them.

### Counters, committed

`benchmark/scripts/mech_counters.py` lands with this transition so both rounds and every
later round are scored by the same code rather than by a re-derivation:

| counter | `batch_01` | `batch_02` |
|---|---|---|
| KB_search / episode | 5.87 | 6.09 |
| distinct query strings / episode | **5.87** | **6.09** |
| distinct KB documents / episode | 33.04 | 32.94 |
| new documents per search | 5.63 | 5.41 |
| tool calls / episode | 12.34 | 12.86 |
| messages / episode | 37.43 | 37.79 |

**Distinct queries per episode equals KB_search per episode exactly, in both rounds.** The
agent never repeats a query — it rephrases. That single line re-specified T1: the defect is
query *formulation*, not query *volume*, and it is why C3 targets the wording of the query
rather than the number of them.

### T2 REPRODUCES EXACTLY and consumes gen-002 (C1)

`close_bank_account_7392` carrying `reason` and/or `waive_early_closure_fee` — keys its own
unlock text marks `(optional)` and gold's payload omits — appears in **9 episodes / 10 calls
in `batch_01` and 9 episodes / 10 calls in `batch_02`**, on the same three tasks each time.
All three are headroom, all 0/3 in both rounds: the clean regime.

The counter was **tightened before landing**. A naive "volunteered optional argument" count
also catches `task_037`, whose own tools mark `reason` **required** and which passes 3/3 then
2/3. So the scored counter is specific to `close_bank_account_7392`, and `task_037`'s general
count becomes the over-generalisation falsifier rather than part of the target.

### T4 REPRODUCES EXACTLY and consumes gen-002 (C2)

5 episodes / 3 tasks in `batch_01`, the **same** 5 episodes / 3 tasks in `batch_02`.
Round-wide catch-all/specific split 9/12 then 7/14.

### T1 REPRODUCES and consumes gen-002 (C3) — query formulation only

Sole cause in 11 ep / 6 tasks then 7 ep / 5 tasks. **Only the query-formulation half lands.**
The second half — *do not commit while a stated requirement is unverified for the option you
are about to name* — has the stronger transcript evidence (both decisive conversations show
the agent recording the gap in words and answering anyway) and is **held back deliberately**:
it is the missing-precondition framing measured to suppress unasked actions, and Phase 0's
own expert harness regressed five tasks H0 passes, two of them by early stopping. It waits
for evidence that the retrieval half alone is insufficient.

### T3 REPRODUCES but is deliberately NOT consumed

Sole cause in 5 then 4 episodes. Held because it acts on the **same call** as C1 on
`task_060` and `task_061`; landing both would make neither attributable. First candidate for
gen-003.

### A process slip, recorded rather than hidden

C1's commit `c3f24a2` swept `batch_02`'s round data and `mech_counters.py` in alongside its
three-line `SYSTEM.md` change, because the round outputs were untracked when the branch was
cut. C2 (`7303bee`) and C3 (`f79c2f5`) are clean single-file commits. The commit is supposed
to be the unit of selective revert, so the capability is preserved explicitly instead:
**a C1 revert is `git revert -n c3f24a2 -- target-agent/SYSTEM.md`**, path-scoped, which
leaves the committed round evidence in place. Later branches are cut from a clean tree.

### Slot accounting

| Slot | Generation | Target(s) | Status |
|---|---|---|---|
| — | gen-001 | **pre-registered identity** | consumed as designed — noise floor measured, baseline pooled |
| 1 | gen-002 | T2 (C1), T4 (C2), T1 (C3) — all `instructions` | in flight — scored by `batch_03` |
| 2–6 | gen-003…gen-007 | T3 next; T5 held | open |

**Surface concentration — THE FLAG ARMS WITH THIS SET.** Three `instructions` mutations
land together, so under D29 the **gen-003 set may not be confined to `instructions`**: it
must include a change on a class this experiment has never exercised, or record a
`surface_exhausted` finding citing a probe or a measured fact per unexercised class.

That obligation is already **half-discharged by measurement**. The step-4b probe
(`generation_000/subagent_probe/VERDICT.md`, run at g=0 as required) settled `sub-agent`:
delegation is reachable and cleanly suppressed (`pi_local_calls` 2 per episode, 3/3
episodes, zero occurrences in τ's graded trajectory), but **a child cannot use τ's tools at
all** — every `mcp_tau_KB_search_*` call died at `MCP daemon: Timeout` after 120 s without
reaching the bridge, and all three episodes collapsed to 6 messages and reward 0.0. So the
project-scope ledger now reads:

| surface | exercised ever | measurement status | blocker |
|---|---|---|---|
| `instructions` | yes | live | none |
| `extension-hook` | yes | all three events measured functional on the real domain | none — **unexercised in THIS experiment** |
| `extension-tool` | yes | reachable, correctly invoked; usefulness unmeasured | none — **unexercised in THIS experiment** |
| `sub-agent` | **yes, as of this experiment's g=0 probe** | delegation works; **child cannot reach τ's tools** (120 s daemon timeout, never reaches the bridge) | `surface_exhausted` for every retrieval-shaped target, cited to the probe |
| declared skill | n/a | measured inert on this seam | not a delivery surface |

`sub-agent` is therefore **not** a candidate for T1/T3 — both need a child that can search
the knowledge base, and a child cannot. The reserved slot is discharged by that measurement
rather than spent on a change that could not have worked, and gen-003's ladder obligation
falls to `extension-hook` or `extension-tool`.

<!-- transition: gen_001_to_002 -->

---

## Re-ranking against `batch_03` (H2, 2026-08-18)

**The cleanest round so far**: 78/78 episodes, every row `evidence_complete` and
`arm_sha_ok`, all four sandbox seam counters 0, zero stall warnings, `pi_local_calls` 0,
zero incomplete episodes, $1.35. **Third round over the same twenty-six tasks — from here on
every batch number measures a set the loop has been tuned on.**

**A correction to the previous entry:** `task_003` trial 0 completed this round. It failed
the same cell in `batch_01` and `batch_02` and then did not, so "deterministic for that
cell" is **downgraded to high-rate weather**. Recorded as a correction rather than left
standing.

**Round: 29/78 (37.2%)** against the pooled H0 baseline 54/154 (35.1%). The round total is
**not** evidence — the identity pair moved +2.6 pp on a byte-identical harness.

### gen-002's predictions, scored

| change | counter | predicted | measured | verdict |
|---|---|---|---|---|
| C1 | `close_bank_account_7392` with an optional key | 9 → ≤2 ep | **9 → 9 ep, 10 → 10 calls** | **mechanism DENIED** |
| C2 | catch-all `reason` calls | 7 → ≤3; transfers not −4 | **7 → 3**; specific 14 → 21; transfers 19 → **21** | **CONFIRMED, both halves** |
| C3 | distinct KB docs / episode | +≥3; `KB_search` ≤7.3; msgs ≤41.6 | **32.94 → 35.90 (+2.96)**; 6.28; 40.18 | **directional, 0.04 short; cost falsifiers unfired** |

**C1 is a mechanism denial, not a denied prediction.** Its counter sat at 9 episodes / 10
calls in *three consecutive rounds* — `batch_01` and `batch_02` before the instruction
existed, `batch_03` after it. The change moved nothing anywhere it could fire, and the
pre-registered clause-1 adversarial reading is now measured rather than hypothesised: the
customer states a motive for closing the account, so *"only if the customer's request calls
for it"* reads as permission.

**C2 is confirmed twice over.** The counter moved as predicted, and the sole-cause
enumeration — computed by different code — moved with it: `REASON`-only failing episodes
5 → 2, task count 3 → 1.

**C3's cost hazard did not reproduce.** The prior experiment's +31% `KB_search` blowout came
in here at **+3.1%**, and gold-actions-ABSENT held at 12, so the "agent stopped looking"
falsifier did not fire either.

### The zero-noise stratum moved, and it moved on C3's tasks

| stratum | `batch_01` | `batch_02` | `batch_03` |
|---|---|---|---|
| anchor | 4/9 | 7/9 | 5/9 |
| marginal | 19/35 | 18/35 | 18/36 |
| **headroom** | **3/33** | **3/33** | **6/33** |

Movers: `task_002` (0/6 pooled → **2/3** — C3's own decisive transcript task), `task_055`
(0/6 → 1/3), `task_056` (0/6 → 1/3). All three are T1 tasks, in the one stratum that showed
**zero** movement across the byte-identical A/A pair.

**Stated with its limits**, because the noise floor exists to stop selective reading: three
cells is three cells; a stratum that has never moved has had its variance *bounded loosely*,
not estimated; and the **anchors fell 7/9 → 5/9 over the same step**. Reading the rise while
ignoring the fall would be the error this ledger is built to prevent.

### T3 REPRODUCES, widens, and consumes gen-003 (C5)

Counting every failing episode in which a gold discoverable-tool name was never unlocked or
called, T3 reaches **8 tasks / 12 episodes** — `task_015` `task_046` `task_055` `task_056`
`task_057` `task_060` `task_061` `task_094`. `task_046` is deterministic: 3/3 this round,
and **0 of 9 lifetime** ever unlocking `get_user_dispute_history_7291`. It was held out of
gen-002 only because it collided with C1 on the same call; C1's prose is gone, so is the
collision.

### T1's remainder is isolated, and gen-002's stated condition is met (C6)

The wrong-named-class mechanism is **still the largest sole cause at 8 episodes / 5 tasks**
even though C3's retrieval counter moved and its stratum moved with it. **Retrieving more was
necessary and is not sufficient** — which is exactly the evidence gen-002's record said it
would require before landing C3's second half. C6 lands it, worded as a *completed-state
check with a search as its remedy* rather than a missing-precondition bar, and carries a
safety falsifier that is scored **before** its own counter.

### T2 moves to a structural surface (C4) — a controlled experiment, with its limit stated

C1's rule is re-delivered as a `tool_result` hook that names the unlocked tool's own
parameters, parsed from the unlock text τ just returned, at the moment the agent reads it,
with no licensed alternative attached. The prose is removed **as part of the substitution,
not as a revert** — C1's mechanism was never tested, because the keys were never removed.

**What this can and cannot settle**, recorded now so a positive result is not over-claimed:
the hook's content is *near*-identical to C1's, not identical (it names concrete parameters
and drops the escape clause), so a win is consistent with either "structure beats prose" or
"the escape clause was the whole problem". What a **null** would settle is sharper — if the
counter stays at 9 with the parameters named explicitly at the point of use and no
alternative licensed, the surface is not the axis and the content is.

Injection verified before any behavioural number: present in **3/3** preflight Pi sessions
with correctly parsed tool names, absent from all **119** τ-trajectory messages
(`generation_002/g003_preflight/`, 3 local episodes on the burned non-partition `task_026`).

### T5 is now the largest bucket, and is deliberately not consumed

Gold actions never performed: 12 episodes / 11 tasks. Held because it is heterogeneous,
because it overlaps the over-escalation shape no prior mutation has moved, and because **C6
could plausibly increase it** — which would confound any change aimed at it. Its counter
serves this set as the shared safety falsifier instead.

### Slot accounting

| Slot | Generation | Change(s) | Status |
|---|---|---|---|
| — | gen-001 | pre-registered identity | consumed as designed |
| 1 | gen-002 | C1 instructions, C2 instructions, C3 instructions | C1 **DENIED**; C2 **CONFIRMED**; C3 directional |
| 2 | gen-003 | C4 **extension-hook**, C5 instructions, C6 instructions | in flight — scored by `batch_04` |
| 3–6 | gen-004…gen-007 | T5 held; T1/T2/T3 remainders | open. **Reverts used: 0 of 2** |

**Surface concentration — THE LADDER IS DISCHARGED, by landing rather than by argument.**
gen-002's three `instructions` mutations armed it; C4 lands on `extension-hook`, a class this
experiment had not exercised. The project-scope ledger is now complete — **every surface
class this repo can name has been exercised in a graded round or measured by probe**:

| surface | exercised in THIS experiment | status |
|---|---|---|
| `instructions` | yes — C1, C2, C3, C5, C6 | live |
| `extension-hook` | **yes — C4** | injection verified present, zero τ leak |
| `extension-tool` | not yet | live, unblocked, no current target whose shape fits |
| `sub-agent` | probed at g=0 | **`surface_exhausted` for every retrieval-shaped target** — a child cannot reach τ's tools (120 s daemon timeout, never reaches the bridge) |
| declared skill | n/a | measured inert on this seam |

<!-- transition: gen_002_to_003 -->

---

## Re-ranking against `batch_04` (H3, 2026-08-18) — **the futility turn**

78 episodes, 77 graded (one lost to the user-sim signature), one stall warning, 274 benign
`stream_reattaches`, seam counters otherwise clean. **30/77 (39.0%)**; curve 33.8, 36.4,
37.2, **39.0%**.

### gen-003's predictions, scored — all three denied

| change | counter | predicted | measured | verdict |
|---|---|---|---|---|
| C4 required-args as a **hook** | `close_bank_account_7392` with an optional key | 9 → ≤3 ep | **9 → 8 ep, 10 → 8 calls** | **DENIED** |
| C5 procedure-named tool | failing eps, gold tool never unlocked | 12 → ≤7; `task_046` ≥1/3 | **12 → 14**; `task_046` **0/3** | **DENIED, wrong direction** |
| C6 requirement coverage | wrong-named-class sole-cause eps | 8 → ≤4 | **8 → 7**; **cost falsifier FIRED** | **DENIED** |

### C4 is the most valuable result this experiment has produced

**The hook fired on the graded platform lane** — verified in the episode itself before any
verdict was written (conv `01a01740-509b-7710-8bfa-c5de19ce9db9`, `task_060` t0), which
injected, twice, verbatim:

> *Argument set for close_bank_account_7392 — required: account_id. The remaining parameters
> (reason, waive_early_closure_fee) are optional; this call sends the required arguments and
> nothing else.*

The agent read that and sent both optional keys anyway.

**The counter across four rounds: 9, 9, 9, 8.** Two rounds with no instruction, one with the
rule as prose, one with the rule as a point-of-use structural injection naming the concrete
parameters with no escape clause. **The surface is not the axis for this defect.**

That contradicts the standing project intuition — carried in `contract/protocol.md` step 4
and in the sia skill — that judgment/scope/verification/arithmetic mechanisms should prefer a
structural surface. The refinement this round supports: **the intuition survives for
mechanisms that need STATE the model cannot hold, and does not survive for mechanisms that
need the model to withhold something it wants to emit.**

What this does *not* license: "hooks don't work" — this experiment's own hook demonstrably
reached the model. The negative is the unambiguous branch, and gen-003's record named it as
such before the data existed.

### C6's safety falsifier did NOT fire — a finding about wording

ABSENT failing episodes 12 → 15 against a ≥4 threshold; transfers 21 → 22 against the same.
The **completed-state** framing did not produce the suppression the **missing-precondition**
framing is measured to produce, and which the ceiling probe reproduced inside its own expert
harness by regressing five tasks H0 passes. Landing the safe variant of a known-dangerous
shape and measuring that it is safe is worth more than C6's target counter was.

### Strata — both halves recorded

| stratum | b1 | b2 | b3 | b4 |
|---|---|---|---|---|
| anchor | 4/9 | 7/9 | 5/9 | **3/9** |
| marginal | 19/35 | 18/35 | 18/36 | 19/35 |
| **headroom** | 3/33 | 3/33 | 6/33 | **8/33** |

The headroom stratum — zero movement across the byte-identical A/A pair — is up five cells
from baseline. The anchors are down from a 7/9 peak to 3/9, which is larger than the three
cells they moved on no change at all, and is **not** dismissed here.

### THE FUTILITY CHECK FIRES — the primary is declared dead

| | |
|---|---|
| accumulated delta (`batch_04` vs pooled `batch_01`+`batch_02`) | **+3.9 pp** (34.6% → 38.5%, Σ +1.000, permutation p = 0.2997, CMH z = 0.695) |
| required at α (committed power envelope) | **11.4 pp** |
| gap | 7.5 pp |
| largest single-generation gain actually produced | 1.8 pp |
| slots remaining incl. gen-004 | 4 |
| 1.8 × 4 | **7.2 pp < 7.5 pp** |

**It fires narrowly**, and the sensitivity is the point: a 2.0 pp estimate instead of 1.8
would leave the primary alive at 8.0 pp. Declared as firing because the rule says to use the
largest gain the experiment has *actually produced*.

**This is not "the loop found nothing."** The correct statement is that the **endpoint test
cannot reach α from here**. The remaining slots now buy knowledge, and gen-004 is the first
set composed under that rule.

### gen-004 — two changes, and the deviation is deliberate

- **C7 reverts C6** (revert **1 of 2**). Both a harness repair and a measurement: if
  `KB_search`/episode falls back below 7.0, C6 was the cost driver and the +20.7% is
  attributed; if it does not, the rise belongs to C5 or to drift, and the experiment learns
  its cost attribution was wrong.
- **C8 lands `track_requests`**, an **extension-tool** — the last surface class this
  experiment had not exercised — against the largest remaining mechanism (15 failing episodes
  / 10 tasks losing reward to a gold action never performed). **Chosen as a tool because of
  C4's null**: two channels that *tell the model something it must remember* have now failed
  on one counter, so this one **holds the state** instead. **Adoption-first**; reward deferred
  to `batch_06` and stated as deferred.

The 3–5 composition policy is deviated from deliberately: adding a third instruction sentence
to a harness whose cost falsifier just fired would confound exactly the measurement C7 exists
to make.

**C5 is left in place** despite being denied and moving the wrong way — only one revert
remains, and a second removal this round would confound C7's measurement.

### Preflight, and a methodological slip recorded

6 local episodes on burned non-partition tasks. Adoption confirmed: `pi_local_calls`
28/13/10 (form A), 25/4/15 (form B), well-formed, none near the 600 s ceiling. Form A showed
the over-application signature, so form B bounds the usage instruction.

**The A/B comparison is uninterpretable and was not used**: the two forms ran on *different
tasks*, so their message counts are confounded by task and neither task has a baseline. Form
B was selected on the prior — over-application is a measured hazard of a first tool — not on
these numbers.

### Slot accounting

| Slot | Generation | Change(s) | Status |
|---|---|---|---|
| 1 | gen-002 | C1, C2, C3 (instructions) | C1 **DENIED**; C2 **CONFIRMED**; C3 directional |
| 2 | gen-003 | C4 (hook), C5, C6 (instructions) | **all three DENIED**; C6's safety falsifier held |
| 3 | gen-004 | C7 revert, C8 **extension-tool** | in flight — scored by `batch_05` |
| 4–6 | gen-005…gen-007 | knowledge mode | open. **Reverts used: 1 of 2** |

**Every surface class this repo can name has now been exercised in this experiment** except a
declared skill, which is measured inert on this seam. No concentration flag is outstanding.

<!-- transition: gen_003_to_004 -->

---

## Re-ranking against `batch_05` (H4, 2026-08-18)

78 episodes, 76 graded (two lost to `infrastructure_error`), zero stall warnings, $1.69.
**33/76 (43.4%)** — the best round of the experiment. Curve 33.8, 36.4, 37.2, 39.0, **43.4%**.

### gen-004's predictions, scored

| change | counter | predicted | measured | verdict |
|---|---|---|---|---|
| C7 revert C6 | `KB_search`/ep; msgs/ep | <7.0 and <41.5 | **7.58 → 7.05**; **42.78 → 41.21** | msgs **CONFIRMED**; `KB_search` **missed by 0.05**, reported as missed. Both fell — C6 was a cost driver |
| C8 `track_requests` | `pi_local_calls` | 0 → ≥20 on ≥6 tasks | **0 → 578**, 76 of 78 episodes, all 26 tasks | **ADOPTION MASSIVELY CONFIRMED** |

C8's reward prediction is **deferred to `batch_06`** by design and was not read. Risk
falsifiers held: msgs/ep 41.21 (ceiling 47), zero `max_steps`, no episode near the 600 s
timeout, zero `track_requests` occurrences in τ's graded trajectory.

### THE gen-004 FUTILITY DECLARATION IS REFUTED — by the very next round

| | at gen-004 | now |
|---|---|---|
| accumulated delta | +3.9 pp | **+7.7 pp** (34.6% → 42.3%, Σ +2.000, p = 0.1112, CMH z = 1.386) |
| gap to α | 7.5 pp | **3.7 pp** |
| largest single-generation gain | 1.8 pp | **3.8 pp** |
| largest × slots remaining | 7.2 pp → **dead** | 3 × 3.8 = 11.4 pp → **REACHABLE** |

It fired on a margin of **0.3 pp** and the next round overturned it.

> **The process finding, and it outlives this experiment:** a futility check computed from
> *"the largest gain the experiment has actually produced"* is **unstable while the experiment
> has produced few gains** — the statistic it depends on is updated by the very round that
> would refute it. Declaring it out loud is what made the refutation visible; a loop that had
> quietly drifted into knowledge mode would never have noticed it was wrong.

### The rise is dominated by the noisiest stratum, and the quiet one fell

| stratum | b1 | b2 | b3 | b4 | b5 |
|---|---|---|---|---|---|
| anchor | 4/9 | 7/9 | 5/9 | 3/9 | **7/9** |
| marginal | 19/35 | 18/35 | 18/36 | 19/35 | 20/34 |
| **headroom** | 3/33 | 3/33 | 6/33 | 8/33 | **6/33** |

The A/A pair already moved the anchors 3 cells on a byte-identical harness, so +4 there is
inside measured noise — while the stratum that moved **zero** cells across that pair went
**backwards**. No claim in this transition rests on the round total.

### THE SHAPE HYPOTHESIS — six measurements, and it composed gen-005

The changes separate by the **shape of the demand**, not by delivery surface:

| verdict | changes | what they ask the model to do |
|---|---|---|
| **confirmed / directional** | C2, C3 | make a **positive choice among alternatives already visible** |
| **denied** | C1, C4 | **withhold** something it wants to emit — denied through prose **and** a verified structural injection |
| **denied** | C5 | rest on a **precondition** the model can decline to find satisfied |
| **denied** | C6 | **verify** before committing |

Recorded honestly as **post-hoc**: it is a grouping of this experiment's own verdicts, not a
pre-registration, and **C9 is its first prospective test**.

### gen-005

- **C9** (instructions) — apply the selection rule the KB states to the candidates
  retrieved. Built deliberately in the confirmed shape. `task_056` is the clean case: 0/3 in
  every round, having *retrieved* an active promotion notice stating the recommendation
  priority and then not applied it. Prediction: wrong-named-class sole-cause 5 → ≤2, **and**
  `task_056` opens "Cobalt Blue" in ≥1 of 3 against **0 of 15** lifetime.
- **C10** — **revert C5** (revert **2 of 2**). Counter **12 → 14 → 16**: wrong direction,
  two rounds of witnesses, `task_046` 0 of 15 lifetime.

**No revert remains.** gen-006 and gen-007 carry whatever they land into the endpoint
harness, and both will be composed on that basis — favouring changes whose falsifiers can
fire within a single round.

C8 is deliberately untouched so its deferred reward prediction can be scored cleanly at
`batch_06`; that is why this set is two changes rather than three.

### Slot accounting

| Slot | Gen | Change(s) | Status |
|---|---|---|---|
| 1 | 002 | C1, C2, C3 | C1 DENIED · **C2 CONFIRMED** · C3 directional |
| 2 | 003 | C4 (hook), C5, C6 | all DENIED; C6's safety falsifier held |
| 3 | 004 | C7 revert, C8 **tool** | C7 CONFIRMED (msgs) · **C8 adoption CONFIRMED**, reward due `batch_06` |
| 4 | 005 | C9, C10 revert | in flight — scored by `batch_06` |
| 5–6 | 006, 007 | — | open. **Reverts used: 2 of 2** |

<!-- transition: gen_004_to_005 -->

---

## Re-ranking against `batch_06` (H5, 2026-08-18)

78/78 graded, zero incomplete. **32/78 (41.0%)**; curve 33.8, 36.4, 37.2, 39.0, 43.4, **41.0%**.

### gen-005's predictions, scored

| change | counter | predicted | measured | verdict |
|---|---|---|---|---|
| C9 apply the retrieved rule | wrong-named-class sole-cause | 5 → ≤2 | **5 → 8** | **DENIED, wrong direction** |
| C10 revert C5 | never-unlocked-gold-tool | ≤16 | **16 → 15** | **CONFIRMED** — the rise stopped |
| C8 (deferred reward, due) | ABSENT failing episodes | — | **15 → 13 → 10** over its two rounds | **mechanism CONFIRMED, reward NOT** |

### An error in my own prediction, recorded rather than dropped

C9's second clause named `task_056` as *"0 of 15 across every round so far"*. The record shows
**1 of 15** — it passed 1/3 at `batch_03`. It went 0/3 → 1/3 this round, exactly what it had
already done once *without* C9. **The clause fired on a pre-existing condition and diagnoses
nothing** — the level-versus-delta error the composition policy warns about, committed in a
record that quotes the rule. C9's verdict rests on its first clause alone, which is denied.

### THE SHAPE HYPOTHESIS FAILED ITS FIRST PROSPECTIVE TEST

gen-005 proposed, from six measurements, that changes succeed when they ask for a **positive
choice among alternatives already visible** and fail when they ask the model to withhold,
verify, or rest on a precondition it can decline. **C9 was built deliberately in the confirmed
shape and was denied, counter moving the wrong way.** It was recorded as post-hoc when
proposed; one out-of-sample test refutes it.

What survives is the narrower, better-evidenced statement underneath: **instruction-shaped
demands on this harness have now been denied five times running (C1, C4, C5, C6, C9), across
two delivery surfaces.**

### C8's deferred reward comes due, and splits

| | |
|---|---|
| its own mechanism counter (ABSENT failing episodes) | **15 → 13 → 10** across both rounds carrying the tool |
| round total over the same step | 43.4% → 41.0% |

**Mechanism confirmed; reward not.** This reproduces a prior experiment's central finding on a
different tool and a different mechanism, and sharpens it: *adoption is not improvement — and a
moving mechanism counter is not improvement either.*

### gen-006 — one change, deliberately

- **C11** (`extension-tool`) — a per-episode tool holding candidates × stated requirements and
  returning the pairs not yet retrieved. Targets wrong-named-class, which has resisted C3
  (partial), C6 (denied, reverted) and C9 (denied). **Rationale**: the only pattern confirmed in
  this experiment's back half is *a tool that holds state the model cannot silently lose*; the
  decisive transcripts show the agent articulating the gap and then losing it, so computing it
  back is the one delivery never tried for this mechanism. C9's sentence is **replaced**, not
  reverted (none remains).

**Preflighted twice, and the second one carried the information.** `task_038`: called **0**
times — ambiguous between "not applicable" and "not registered", so **not** treated as a
verdict. `task_056`, where the mechanism demonstrably applies: **43–46 invocations/session**,
`pi_local_calls` 47/47/48. Cost checked against **the same task's own baseline** (66/66/66 at
b5, 70/90/76 at b6, preflight 60/61/73) rather than the round mean — no inflation.

**No revert remains**, so C11 ships whatever `batch_07` says about it. The pre-committed
reading, written now so it cannot be avoided later: **if C11's counter moves and reward does
not — the C8 pattern — the conclusion is that these mechanism counters are not the binding
constraint on this objective, not that the next tool will work.**

### Slot accounting

| Slot | Gen | Change(s) | Status |
|---|---|---|---|
| 1 | 002 | C1, C2, C3 | C1 DENIED · **C2 CONFIRMED** · C3 directional |
| 2 | 003 | C4 (hook), C5, C6 | all DENIED; C6's safety falsifier held |
| 3 | 004 | C7 revert, C8 tool | C7 CONFIRMED · **C8 adoption CONFIRMED**, mechanism CONFIRMED, reward NOT |
| 4 | 005 | C9, C10 revert | C9 **DENIED** · C10 **CONFIRMED** |
| 5 | 006 | C11 tool | in flight — scored by `batch_07` |
| 6 | 007 | — | last slot. **Reverts used: 2 of 2** |

Primary still reachable: accumulated **+6.4 pp**, gap 5.0 pp, 3.8 × 2 = 7.6 pp.

<!-- transition: gen_005_to_006 -->
