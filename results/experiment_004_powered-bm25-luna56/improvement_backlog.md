# Improvement backlog — experiment 004_powered-bm25-luna56

Approved mutation targets, per `contract/protocol.md` step 4. The user approves targets as a
**set**; a generation still lands **one coherent mechanism** (protocol invariant), so the rest
carry forward here and are re-ranked against each new batch's evidence. An item later
contradicted by evidence is retired with the reason recorded, never silently dropped.

The backlog cannot outrun the freeze: **G = 5** bounds the mutation slots. Three targets are
approved and five generations remain, so every approved target can still be reached — stated
rather than assumed.

Prevalence is `n/B` by full enumeration over the batch, never sampling. Conversation ids are
taken from `generation_NNN/batch_NN/episode_manifest.jsonl`, never from memory.

| id | mechanism | prevalence | status |
|---|---|---|---|
| T1 | Commits a write on an unverified KB-derived value | 3/8 (B₁) | **consumed-by-gen-001** |
| T2 | Bails to a human instead of completing an in-scope procedure | 3/8 (B₁) | pending |
| T3 | Declares "no discrepancy" without performing the required comparison | 1/8 (B₁) | pending |

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

**Approved** 2026-08-15 (batch B₁). **Status:** pending.

**Mechanism.** The agent asserts a negative finding it did not establish, and so never enters
the write procedure at all.

**Evidence:** `task_026` / `01a0038e-d519` — reported "no discrepancy in the recorded rewards"
after reading the KB doc stating rewards are stored as points regardless of card type. Gold
expected four mis-rewarded transactions to be found, the dispute tool handed to the user, and
8 writes. Agent made **1** write (`log_verification`).

At 1/8 this is the weakest-powered target in the set; a second witness in a later batch would
strengthen it considerably.

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
