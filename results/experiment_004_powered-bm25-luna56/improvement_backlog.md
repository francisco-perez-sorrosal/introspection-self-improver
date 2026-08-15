# Improvement backlog — experiment 004_powered-bm25-luna56

Approved mutation targets, per `contract/protocol.md` step 4. The user approves targets as a
**set**; a generation still lands **one coherent mechanism** (protocol invariant), so the rest
carry forward here and are re-ranked against each new batch's evidence. An item later
contradicted by evidence is retired with the reason recorded, never silently dropped.

**G = 5** bounds the mutation slots, and the backlog has outrun it. See the slot accounting
under the table: two approved targets will go unconsumed. That is stated here rather than
discovered at the reveal.

Prevalence is `n/B` by full enumeration over the batch, never sampling. Conversation ids are
taken from `generation_NNN/batch_NN/episode_manifest.jsonl`, never from memory.

| id | mechanism | prevalence | status |
|---|---|---|---|
| T1 | Commits a write on an unverified KB-derived value | 3/8 (B₁) | **consumed-by-gen-001** |
| T2 | Bails to a human instead of completing an in-scope procedure | ~~3/8~~ **2/8** (B₁, re-scoped) | pending |
| T3 | Declares "no discrepancy" without performing the required comparison | 1/8 (B₁) | **retired** (see B₃) |
| T4 | Over-caution: the grounding check blocks a determinate action | 2/8 (B₂) | **consumed-by-gen-002** |
| T5 | Performs an unrequested extra write | 1/8 (B₂) | pending |
| T6 | Botches the discoverable-tool handover (omits it, or passes arguments) | **6 witnesses / 4 batches** | **consumed-by-gen-004** |
| T7 | Prohibition misreading: refuses a policy-required transfer | 1/8 (B₃) | **consumed-by-gen-003** |
| T8 | Unbounded re-search exhausts the step budget | 1/8 (B₃) + 1/8 (B₄) | pending |
| T9 | Paraphrases a KB value instead of transcribing it verbatim | 1/8 (B₄) | pending |

**Slot accounting.** G = 5. Four generations are spent (gen-001 → T1, gen-002 → T4,
gen-003 → T7, gen-004 → T6), leaving **1 slot** against **4 pending targets** (T2, T5, T8,
T9). Three approved targets will go unconsumed. The last slot is decided at the gen-005
boundary against B₅.

**Three of five generations have now been spent on the same clause** — T1 installed the
grounding check, T4 bounded its consequence, T7 repairs how that bound reads. That is a
finding about the experiment, not only about the agent: a single instruction paragraph has
absorbed 60% of the mutation budget, each fix creating the next defect. It is recorded here
so the reveal can be read with it in view.

---

## T1 — Commits a write on an unverified KB-derived value

**Approved** 2026-08-15 (batch B₁). **Status:** consumed-by-gen-001.

**Mechanism.** The agent reaches the write step of a procedure needing a specific value from
the knowledge base — an APY tier, a `credit_type` enum, a product class — and when the KB does
not yield it cleanly, it writes a plausible value anyway rather than resolving it. There is no
stopping condition between "still unsure" and "commit the write".

**Evidence** (`generation_000/batch_01/graded/updated_results.json`, all `reward_basis: ['DB']`):

- `task_096` / `01a00390-566b` — wrote `expected_apy: 3.0` (gold `3.25`) and `6.7` (gold `6.85`);
  credit amounts `11.25`/`7.5` against gold `17.50`/`15.00`. Reached only after **9** KB searches
  that never resolved the APY boost.
- `task_072` / `01a0038f-c557` — wrote `credit_type: "rebate_credit"` (gold `"fee_refund"`) and
  `amount: 10.0` (gold `3.50`), after only **2** KB searches.
- `task_055` / `01a0038f-b771` — opened the savings account as `account_class: "Green Account"`
  (gold `"Silver Plus Account"`), and deposited three times against `account_id 36bec7cd2319d4ae`
  where gold is `7e48bf3b0589cfad`.

**Why this one first.** Tied on prevalence with T2, but it is the mode closest to the reward:
in all three episodes the agent performed the *right procedure with the right tool shape* and
lost only on values — `task_072` and `task_096` match gold write-for-write in tool name and
count. That makes the predicted effect narrow and directly measurable. Search *volume* is not
the discriminator (the one pass used 5 searches; failures ranged 2–12), so the mutation targets
the **stopping condition**, not search effort.

## T2 — Bails to a human instead of completing an in-scope procedure

**Approved** 2026-08-15 (batch B₁). **Status:** pending.

**Mechanism.** Faced with a precondition it cannot immediately satisfy, the agent calls
`transfer_to_human_agents` rather than working the procedure the policy actually prescribes.

**Evidence:**

- `task_005` / `01a0038e-d3b1` — first `KB_search` for the balance-check procedure returned an
  unrelated rewards-representation doc; the agent then improvised a stricter "two matching
  details" rule from memory, refused, and transferred. Gold wanted `log_verification` +
  `change_user_email`. **Zero** write calls were made.
- `task_010` / `01a0038e-d935` — retrieved the *correct* referral doc, then transferred instead
  of submitting the referral.
- `task_088` / `01a0038f-ef30` — demanded SSN-last-4 "enhanced verification", then transferred;
  never filed the dispute, closed the card, or ordered a replacement.

Note `task_005`'s root is partly retrieval-usage (the governing procedure was never surfaced),
which overlaps T1's territory. If gen-001's T1 mutation moves `task_005`-shaped episodes, T2
must be re-scoped against the next batch before being spent as its own generation.

## T3 — Declares "no discrepancy" without performing the required comparison

**Approved** 2026-08-15 (batch B₁). **Status: RETIRED** 2026-08-15 — see
[T3 retired](#t3-retired) under batch B₃ for the reason. Kept in full below, not deleted.

**Mechanism.** The agent asserts a negative finding it did not establish, and so never enters
the write procedure at all.

**Evidence:** `task_026` / `01a0038e-d519` — reported "no discrepancy in the recorded rewards"
after reading the KB doc stating rewards are stored as points regardless of card type. Gold
expected four mis-rewarded transactions to be found, the dispute tool handed to the user, and
8 writes. Agent made **1** write (`log_verification`).

At 1/8 this is the weakest-powered target in the set; a second witness in a later batch would
strengthen it considerably.

---

## Batch B₂ (generation_001, H₁) — 4/8

**Not comparable with B₁'s 1/8.** The partition makes batches disjoint, so B₁ and B₂ are
different task sets of different difficulty. Batch reads diagnose; the progression metric is
the held-out curve, sealed until reveal. No cross-batch inference is drawn anywhere below.

### T4 — Over-caution: the grounding check blocks a determinate action

**Approved** 2026-08-15 (batch B₂). **Status:** consumed-by-gen-002. **Prevalence 2/8.**

This is gen-001's own stopping clause over-firing — the risk its PR and record both named in
advance, now visible in the agent's stated reasons rather than inferred:

- `task_094` — transferred to a human, saying: "**No correction was applied yet because the
  exact statement period and daily balances still need to be confirmed.**" Gold expected
  `apply_savings_account_credit_6831` at `amount: 140.00`.
- `task_069` — searched the knowledge base **seventeen** times, then declined: "I searched the
  personal products and found **no combination whose documentation confirms all three
  requirements** simultaneously." Gold expected two accounts opened
  (`open_bank_account_4821` × 2).

**Causation is not claimed.** B₁ and B₂ are disjoint and the held-out numbers are sealed, so
whether gen-001 helped, hurt, or did nothing is unknown until reveal. What *is* established is
mechanistic: the instruction's stopping clause is being read as licence to abandon the whole
procedure, not merely to withhold one unconfirmed value. That is a defect in the clause's
scope regardless of its net effect on score.

### T5 — Performs an unrequested extra write

**Approved** 2026-08-15 (batch B₂). **Status:** pending. **Prevalence 1/8.**

`task_046` matched **every** gold action and still failed `db_check`, because it additionally
called `pay_credit_card_from_checking_9182` with a garbled `checking_account_id: "05"` — a
payment nobody asked for. Low prevalence, but arguably the highest-severity mode seen so far:
every other mode is a failure to act, and this one is an unrequested real-money state change.
A second witness would justify promoting it above higher-prevalence targets.

### T6 — Never hands over the discoverable tool the procedure requires

**Approved** 2026-08-15. **Status:** pending. **Prevalence 2/8 across two batches.**

- `task_020` (B₂) — never called `give_discoverable_user_tool` for
  `submit_cash_back_dispute_0589`.
- `task_026` (B₁) — same omission for the same tool; previously counted under T3.

Two witnesses in different batches make this a mode in its own right rather than an aspect of
T3. T3 accordingly narrows to the *unfounded negative finding* itself.

### T2 re-scoped: 3/8 → 2/8

Applying the observation harvest's `environment_issue` on `task_088` (the declined
authorization was absent from all transaction histories, so that escalation was partly forced).
`task_005` and `task_010` remain unambiguous. Recorded as a re-scope with its reason rather
than a silent edit.

---

## Batch B₃ (generation_002, H₂) — 3/8

Not comparable with B₁ or B₂; disjoint task sets. Both findings below are **self-inflicted**
— defects this project's own mutations introduced — and both are quoted, not inferred.

### T7 — Prohibition misreading: refuses a policy-required transfer

**Approved** 2026-08-15 (batch B₃). **Status:** consumed-by-gen-003. **Prevalence 1/8**, on the
experiment's **first `reward_basis: ['ACTION']` task**, whose gold action *is* the transfer.

`task_014` — the user asked, in their own words, to "connect me with a human agent who can
verify this promotion". The agent answered:

> "I'm sorry, but **I can't transfer this request** because the promotion remains unverified in
> Rho-Bank's referral documentation."

Gold: `transfer_to_human_agents(reason="unconfirmed_external_communication")`.

Gen-002's clause says an unconfirmed value "is **never a reason to** end the conversation,
**transfer to a human**, or leave other required actions undone". The agent parsed the middle
phrase as a *prohibition on transferring* rather than as "unconfirmedness does not justify
giving up" — the exact inverse of intent. It also contradicts the **frozen policy**, which
requires helping or transferring when a user asks for a human. The instruction cannot be
allowed to override the graded policy.

Supporting but **not** decisive: transfers across B₃ were **0/8 episodes**, against 3 in B₁ and
1 in B₂. Batches are disjoint, so that trend is suggestive only; the verbatim misreading is
what carries this target.

### T8 — Unbounded re-search exhausts the step budget

**Approved** 2026-08-15 (batch B₃). **Status:** pending. **Prevalence 1/8.**

`task_064` hit `max_steps` after **28 distinct** knowledge-base searches across 201 messages, at
**$0.20** — roughly six times any other episode in the batch. Gen-001's surviving "search again
for that exact value" clause carries no bound, and this is what unbounded looks like. Distinct
from T4: the agent here never refused, it simply never converged.

### T6 promoted to top rank

Now **4 witnesses across 3 batches** — `task_026` (B₁), `task_020` (B₂), `task_028` and
`task_038` (B₃) — three of them the same `submit_cash_back_dispute_0589` tool. The
best-evidenced mode in the experiment, and still unconsumed.

### T3 retired

**Retired** 2026-08-15 with the reason recorded, per the protocol's requirement that a
contradicted item is never silently dropped. T3 (declares "no discrepancy" without performing
the comparison) narrowed to a single witness once T6 split out of it, and neither B₂ nor B₃
produced a second. It is retired for lack of evidence, not because it was disproved — a
witness in B₄ or B₅ would reopen it.

---

## Batch B₄ (generation_003, H₃) — 2/8

Disjoint from B₁–B₃; no cross-batch comparison drawn. Arm sha `ae28005` is the gate commit,
whose `target-agent/` tree was **verified** byte-identical to the `exp4-g003` tag.

### The first positive evidence in this experiment

`task_032` is a `reward_basis: ['ACTION']` task requiring a transfer, and it **passed**, with
one `transfer_to_human_agents` call. Gen-003 repaired the prohibition misreading it was
written for. One episode, on a different task from the one that motivated the fix — evidence
that the mechanism works, **not** a measurement of gain.

### Two mutations did not achieve what they were written for

`task_070` used **only `KB_search` — 20 calls, no other tool whatsoever** — and closed with
"No application has been started. You will need Brightwave Digital's formation date to
determine whether it qualifies." It abandoned the entire procedure over one unconfirmed value
without even logging verification. That is what gen-002 was written to prevent and gen-003 to
clarify, still present at H₃. Recorded as plainly as the success above.

**T1 returned under the loosened stop**, exactly as gen-002's record predicted it might:
`task_065` opened Green as *checking* and Gold as *savings* (gold: Green savings, Evergreen
checking), writing `account_class: "Green Account (checking)"` — a paraphrase, not a product
name. `task_066` applied with wrong arguments.

### The pair that reframes three generations of work

B₂'s `task_069` and B₄'s `task_065` are **different tasks that share customer `rp65a7b3c4`** —
not one scenario under two regimes; an assumption made mid-diagnosis and corrected here. The
comparison still holds: under the strict stop the agent **refused to act**; under the loosened
one it **acted and chose wrong**. The constant across both is that it cannot resolve the
correct product from bm25 retrieval. **Three generations tuned *when to stop* around a
resolution failure none of them addressed** — which is why T9 is now on the backlog.

### T6 — consumed by gen-004, and it is not what its old name said

The mode is not "never hands the tool over". `task_029` called `give_discoverable_user_tool`
for the **right** tool **four times**, each carrying a pre-filled `arguments` payload that gold
does not have, so no handover matched. Renamed accordingly. Six witnesses across four batches:
`task_026` (B₁), `task_020` (B₂), `task_028` + `task_038` (B₃), `task_029` + `task_037` (B₄) —
four of them the same `submit_cash_back_dispute_0589` tool.

### T9 — Paraphrases KB values instead of using them verbatim (new, pending)

`task_065`'s `"Green Account (checking)"` is the clearest instance: the agent has the right
word but emits its own construction rather than the exact product name from the retrieved doc.
Distinct from T1, which is about *whether* the value was confirmed; T9 is about *fidelity of
transcription* once it has been. Unconsumed, and with one slot left it will probably stay so.

---

## Observation harvest — independent corroboration, and two caveats

The `introspection.observation` harvest was attempted at diagnosis time and returned nothing
(6 minutes after the batch, against a ~40-minute eligibility window). Re-run at 05:03 UTC it
returned **59 observations across the 8 batch-1 conversations**. This is a lens that had no
access to the transcript analysis above, so it is a genuine second opinion — and it is
recorded whether or not it agrees.

**T1 is corroborated on all three of its tasks**, in the platform's own words:

- `task_096` `agent_struggle/high` — "inferred unsupported effective rates and monthly
  shortfalls from sparse transaction data, **then applied interest corrections without
  verifying** the actual daily balances"; and separately, "treated the Gold Plus credit as a
  confirmed $7.50 discrepancy even though the available records did not establish" it.
- `task_072` `agent_struggle/high` — "miscalculated the Light Green Account's November ATM
  charges and **applied a $10 refund without establishing** that this was the correct
  overcharge".
- `task_055` `agent_struggle/medium` — recommended an unaffordable product before eliciting the
  user's constraints.

**T3 is corroborated verbatim**: `task_026` `agent_struggle/high` — "Concluded that no
discrepancy existed … **without** having the user's expected cash-back figures **or a
complete, independently validated** comparison".

### Caveat 1 — part of T2's prevalence may not be harness-addressable

`task_088` carries `environment_issue/medium`: "The declined $449.99 authorization was **absent
from all account transaction histories**, so the card and decline reason could not be identified
from the available data." If the record genuinely is not there, the agent's escalation was
partly forced rather than premature. T2's harness-addressable prevalence may therefore be
**2/8 rather than 3/8**. Not retired — `task_005` and `task_010` are unambiguous, and `task_088`
still never filed the dispute or closed the card — but T2 must be re-scoped against B₂ before
being spent as a generation, and this caveat is why.

### Caveat 2 — `task_055`'s repeated writes were a tool-availability failure, not only grounding

`environment_issue/medium`: "the user-facing `deposit_check_3847` action returned an
**unavailable-tool error**"; and `agent_struggle/medium`: "The agent **retried the same deposit
action** after the user reported that it was unavailable, rather than diagnosing why". That
explains the three repeated `deposit_check_3847` calls and the invented `mobile_check_deposit`
seen in the transcript. So `task_055` is a mixed case: its wrong `account_class` is T1, but its
repeated writes are a distinct retry-without-diagnosis behaviour. T1's evidence stands on
`task_072` and `task_096`, which are clean.

### Possible new mode, not yet a target (1/8)

`task_026` `agent_struggle/medium` — the agent "logged the email and full address **discovered
from the account record** even though the user had supplied only the requested name, date of
birth, and phone number." Logging verification data the user never provided is a
verification-integrity issue distinct from T1–T3. One witness only; watch for a second in B₂
before promoting it to a target.

---

## Not a target — recorded so it is not rediscovered as one

**τ's action-check comparison under-reports agreement on discoverable-tool calls.**
`Action.compare_with_tool_call` compares argument dicts, but `call_discoverable_agent_tool` and
`call_discoverable_user_tool` carry their payload as a **nested JSON string**, so that field is
compared by string equality. The agent emits compact JSON (`{"user_id":"x"}`); gold carries
spaces (`{"user_id": "x"}`). **14 of 43 action-check misses in B₁ (33%) are semantically
identical calls differing only in whitespace.**

This costs **no reward** — every B₁ task is `reward_basis: ['DB']`, so reward comes from the
database check and action checks are informational. It is a property of the **frozen** evaluator,
not an adapter defect, and must not be "fixed": τ's evaluator, task definitions, gold state and
reward aggregation are immutable, and making the agent match gold's JSON whitespace would be
grader-gaming rather than capability.

It is recorded because it is a live trap for diagnosis: reading `action_checks` naively yields a
"fails to call discoverable tools" failure mode that **does not exist**. Any future batch read
must parse nested JSON-string arguments before counting a miss.
