# Improvement-record craft and backlog hygiene

Schema truth: `contract/improvement_record.schema.yaml` (loaded by
`tau_adapter/records.py` — edit the schema, never that module's field list). Procedure
truth: `contract/protocol.md` steps 4 and 6–7. This file carries what neither does: how to
mine prior records at recall time, and what separates a strong record from a merely
schema-compliant one. Exemplar of the standard: pick a well-formed `gen_*.yaml` from a
**revealed** prior experiment under `results/` — its `held_out_result` is populated, so
the whole evidence-to-outcome arc is visible.

## Recall mining — what each field of a prior record yields

| Field | Mine for |
|---|---|
| `outcome` + `mutation.candidate_commit` | the actual generation chain. `identity`/`rejected` transitions mean H did not move — never attribute a batch delta to a mutation that never landed |
| `batch.task_ids` | fresh mode: which tasks are spent and can never recur as virgin evidence. Fixed mode: the same set every round — deltas are per-task pass-rate movement on a tuned-on set from B2 on |
| `signals[]` | witness accumulation: the same failure mode re-sighted across batches strengthens an unconsumed backlog target — one observed target reached six witnesses across four batches before earning its slot, out-evidencing anything a single batch showed. Fold re-sightings into the existing target's row, never open a duplicate |
| `counterevidence` | standing objections that transfer forward: disjoint-batch comparisons are suggestive only; a severity-over-prevalence ranking override was "recorded so the choice can be judged rather than assumed" — judge it now, with the new batch |
| `hypothesis` + `proposed_change` | the semantic history of each touched surface. Re-read every prior change to a sentence before touching that sentence again — an entire observed generation existed only to repair how the previous generation's wording was read |
| `owning_layer` | concentration accounting: mutations per surface; ≥3 on one surface is a recall-digest flag |
| `expected_effect` | pre-registered predictions and named risks — check each against the new batch and report confirmed / denied / unobservable in the recall digest |
| `changes[].clauses` (v3) | per-clause falsifiers of landed instruction text — score each clause's falsifier alongside the change's prediction; a firing clause falsifier makes the CLAUSE (not necessarily the whole change) the revert candidate |
| `human_approval` | provenance only; who decided, when |

## Batch modes and trials

The lock's `protocol.batch_mode` and `num_trials` change what good prevalence and recall
look like:

- **`num_trials` > 1**: label denominators explicitly — k/B tasks exhibiting a mode vs
  n/(B×trials) episodes; never leave "n/B" ambiguous. A task passing some trials and
  failing others hands diagnosis a passing and a failing transcript of the same harness
  on the same task — read them as a pair. `pass@k`/`pass^k` are within-generation
  reliability texture only, never a cross-generation description.
- **`fixed` mode**: batch reads are the training curve, not generalization evidence —
  every record and diagnosis note says so. Feed the forming per-task batch matrix (from
  each round's `batch_NN/graded/`) into the recall digest; interim `make batch_curve`
  runs are descriptive only — the endpoint test is pre-registered.
- One record per *transition*: a measurement-only endpoint round is consumed by no
  transition and gets no record.

## Writing the record (protocol step 6)

Scaffold, fill while the transition happens, verify — never reconstruct afterwards:

```bash
python3 benchmark/scripts/improvement_record.py --scaffold <g> --write   # then edit
python3 benchmark/scripts/improvement_record.py --verify \
  results/experiment_<id>/improvement_records/gen_<g>_to_<g+1>.yaml
```

(The script's `--help` wins on exact flags; `contract/protocol.md` on procedure.)

Field craft — what the exemplar does that the schema cannot require:

- **`evidence.summary`**: batch health before content (`evidence_complete`, `arm_sha_ok`,
  stalls/409s/prompt failures), the recipe commit the batch ran against, provenance of the
  graded read (`batch_NN/graded/`), and read-depth decisions with reasons ("read in full
  rather than by tail, because the decisive evidence is a sentence the agent wrote").
- **`signals[]`**: prevalence n/B by enumeration, never sampling; conversation id inline
  with each claim; backlog target ids cross-referenced; decisive vs supporting evidence
  separated explicitly ("Supporting but NOT decisive: …").
- **`counterevidence`**: argue against the chosen hypothesis for real. If the chosen
  target is not the best-evidenced, record the override and its reason (severity vs
  prevalence). "none found" is a legitimate value; a perfunctory sentence is not.
- **`expected_effect`**: falsifiable, scoped ("measured on the held-out set at H<g+1> and
  nowhere else"), with named risks for the next batch — these become the predictions the
  next recall checks. Also record what the change deliberately does not target.
- **`changes[]`** (schema v2+, plan D22): one item per change of the set, and the item's
  `expected_effect` is that change's ONLY attribution channel — write it so the next
  batch can score it mechanically, and **prefer a behavioral process counter over a bare
  pass/fail** (plan D25): the derived counters (`partial_action_reward_pct`,
  write-match, the lock-named search/transfer/discovery counts — batch rounds emit them
  too) move smoothly where the binary rate flips coins, e.g. "the named write-action
  counter reaches ≥2/3 trials on the tasks this targets". `surface` says where it
  landed (instructions | extension-hook | extension-tool | sub-agent | pi-skill |
  retrieval-usage | revert | other); `commit` names the per-change commit so a refuted
  change can be reverted alone; a prompt-only set after a concentration flag satisfies
  the positive obligation (protocol step 4: a structural change, or a probe-backed
  `surface_exhausted` finding — a paragraph alone no longer discharges it). The
  set-level `expected_effect` stays: it is what the generation curve measures.
- **`changes[].clauses[]`** (schema v3, plan D26) — the **adversarial wording review**,
  required for every `surface: instructions` change: before landing the text, enumerate
  its disjunctions, preconditions, and licensed alternatives; each becomes
  `{clause, adversarial_reading, falsifier}` with `clause` quoted **verbatim from the
  landed diff** (`git show`, never memory — a misquoted verdict propagated through
  three documents of one closed experiment) and its own falsifier the next batch scores.
  The lesson this operationalizes: the escape clause is what the model optimises
  against — one observed record falsified over-reach and left its "or explained"
  disjunction unwatched, and the harm arrived through the unwatched clause one round
  later.
- **Outcome discipline**: `accepted` names a `candidate_commit` distinct from
  `source_commit` (the merge commit, tagged `exp<seq>-g<NNN>`); `rejected`/`identity` pin
  H_(g+1) = H_g. `held_out_result` is never written by hand.

## Backlog hygiene (`results/experiment_<id>/improvement_backlog.md`)

Protocol step 4 owns approval (multi-select with the user); sia keeps the ledger honest:

- One row per approved mechanism: id `T<n>`, prevalence n/B with its batch, status
  `pending` / `consumed-by-gen-NNN` / `retired`. Retirement always carries the
  contradicting evidence — never silently dropped.
- **`surfaces_considered`, written when the target OPENS** (plan D26): which surface
  classes could carry this mechanism — one line each from {instructions,
  extension-hook, extension-tool, sub-agent, none-available}, with the blocker or
  enabler named. The surface decision belongs upstream of set composition: one closed
  experiment pre-registered a hook-shaped home for a target twice and still landed
  prose when the slot came, because nothing carried the commitment forward to the
  moment of composition.
- **The per-transition stamp** (plan D26, mechanically enforced): every transition's
  re-ranking appends `<!-- transition: gen_NNN_to_MMM -->`; a v3 record refuses to
  validate — and the next round refuses to start — without its marker. The backlog of
  one closed experiment silently froze halfway while its gated records stayed
  impeccable; only gated artifacts stay alive.
- Accounting under composite sets (plan D22): G bounds generations, not changes — a
  generation may consume any number of pending targets, and each consumed target's row
  names the change (and commit) that consumed it. What still goes unstated nowhere:
  targets left pending at the final transition are recorded as unconsumed with their
  witness counts, exactly as before.
- Record experiment-level findings (e.g., surface concentration) in the backlog prose,
  where the reveal will be read with them in view.
