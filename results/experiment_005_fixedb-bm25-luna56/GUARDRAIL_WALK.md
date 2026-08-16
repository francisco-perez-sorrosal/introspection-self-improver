# Protocol §29 guardrail walk — experiment 005_fixedb-bm25-luna56

Walked at close, 2026-08-16, after `make reveal`. Each of the twenty invariants is
reported as **HELD**, **WAIVED** or **VIOLATED** with the evidence that settles it.
One is waived and one carries a recorded exposure; the rest held.

| # | Invariant | Verdict |
|---|---|---|
| 1 | Improvement batches and held-out tasks are disjoint | **HELD** |
| 2 | Improvement batches are disjoint from one another | **N/A by design — `batch_mode: fixed`** |
| 3 | The held-out partition is fixed before H0 evaluation | **HELD** |
| 4 | Claude cannot inspect held-out evidence during optimization | **HELD, with a recorded exposure** |
| 5 | Claude cannot receive aggregate held-out scores during optimization | **HELD** |
| 6 | The target model is fixed during the main experiment | **HELD** |
| 7 | The user simulator is fixed during the main experiment | **HELD** |
| 8 | The τ evaluator and task definitions are fixed | **HELD** |
| 9 | The benchmark version/commit is pinned | **HELD** |
| 10 | Integration code must not introduce task-specific intelligence | **HELD** |
| 11 | Only approved target-harness changes define a new generation | **WAIVED — see below** |
| 12 | Every generation maps to an exact source commit/runtime version | **HELD, after a corrected error** |
| 13 | Every held-out result maps to the generation that produced it | **HELD** |
| 14 | The default metric is held-out tasks passed / held-out tasks | **HELD** |
| 15 | `pass^k` terminology must not be used for harness generations | **HELD** |
| 16 | Failed/rejected attempts must not be silently discarded | **HELD** |
| 17 | Debug configurations obey the same isolation rules | **HELD** |
| 18 | Task assignment reproducible from the persisted split manifest | **HELD** |
| 19 | Held-out results revealed only after the final generation is frozen | **HELD** |
| 20 | The experiment remains configurable without changing these invariants | **HELD** |

---

## The two that are not a plain HELD

### 11 — human approval: **WAIVED BY EXPLICIT USER INSTRUCTION**

`protocol.require_human_approval: true` in the lock, and it was **not** satisfied as
written. For this run the user explicitly waived the human review-and-merge gate and
delegated both the merge and the step-4 mutation-target selection to the orchestrator
("this is a test so I can delegate to you"). The orchestrator opened PR #9 and PR #10 and
merged both on that delegated authority.

Reported as **waived, not HELD** — deliberately, because a waived gate that reports as
held is the failure this walk exists to prevent. What the user *did* decide directly:
the proceed/identity/halt call at both decision points, and the decision to keep the
seam-contaminated `batch_02` round rather than re-run it.

Both PRs did pass CI's three required status checks before merge; branch protection was
not bypassed. (PR #10's first merge attempt was *rejected* by branch protection because
CI had not finished — see guardrail 12.)

### 4 — held-out firewall: **HELD, with one recorded exposure**

No held-out task, trajectory, per-task reward or aggregate was read by the orchestrator
before `make reveal`. Held-out rounds ran on the local lane with outputs sealed in the
out-of-tree vault; the terminal reports completeness only.

Two exposures are on the record and neither is silent:

1. **The D19 standing caveat.** The held-out set reuses seq 4's T=28 verbatim, and the
   orchestrator has seen seq 4's *revealed* per-task results for those tasks. This is why
   the batch curve, not the held-out lane, was pre-registered as seq 5's primary.
2. **One per-task held-out datum was disclosed by the user in chat during the H0 round.**
   One value, at H0. It was not repeated anywhere, and it informed no diagnosis and no
   mutation. Both improvement records carry this.

**Vault reads.** `heldout.py` asks that any read of the sealed console be recorded. During
the H0 round the console was grepped for **infrastructure lines only** (retry and
exhaustion counts) — never graded output. No vault console read occurred during the g=1
transition or afterwards until reveal.

---

## Guardrail 12, and the error it caught

**HELD at close**, but only after a real error was found and corrected mid-run, which is
worth recording precisely because the guardrail is what caught it.

`exp5-g002` was first created pointing at `0548f8f` — the `batch_02` commit, which does
**not** contain the gen-002 mutation. Cause: the tag command was chained with `;` after a
`gh pr merge` that branch protection had just rejected (CI incomplete), so the tag ran
despite the merge failing. The bad tag was pushed.

Fix: the tag was deleted locally and on the remote, PR #10 was merged once its three
required checks passed, and the tag was recreated at the merge commit — then **verified by
reading `target-agent/SYSTEM.md` at the tag** and confirming the mutation text is present.

Final state, verified:

| tag | commit | mutation present at tag |
|---|---|---|
| `exp5-g001` | `1e7b792` | yes |
| `exp5-g002` | `18351a5` | yes |

Every batch round additionally records its arm sha in `run_metadata.json`, with
`arm_sha_ok` per episode in the manifest: `batch_01` `51e59e4`, `batch_02` `c669207`,
`batch_03` `6580164`, zero `arm_sha_mismatches` across all 72 episodes, no dirty paths.

---

## Guardrail 2 — why it reads N/A rather than HELD

Seq 5 is the loop-reliability experiment (plan D17). `protocol.batch_mode: fixed` measures
**one** hand-chosen batch of 8 tasks under every generation, by design, to ask whether the
loop can fix what it directly observes. Batch disjointness is therefore not merely
unsatisfied — it is deliberately inverted, and `allow_within_batch_verification: true` in
the lock records the inversion. The lock refuses the contradictory combination.

The cost this incurs is stated wherever a batch number is quoted: `batch_01` is the only
round measuring a set the loop has not been tuned on, and even it is not an unbiased
sample of the pool, because its 8 tasks were hand-picked from seq-4 known-fails.

---

## Guardrail 16 — what was recorded rather than discarded

- **gen-002 failed, and its record says so before the result was known.** The record
  pre-registered `task_014` as the falsifier and committed in advance to reading a
  regression there as over-reach "exactly as seq 4's gen-002 did". `batch_03` produced
  exactly that. The record was not edited afterwards to soften it.
- **gen-001's denied prediction is recorded as denied** (`task_070`, zero
  promotion-directed queries across three trials, both rounds).
- **gen-001's cost is recorded against it**: `task_072`'s amounts destabilised while its
  enum was fixed.
- **The rejected target is recorded with its reason.** Backlog item T4 was explicitly
  *not approved*, because its only direct lever is matching a default string, which is
  grader-gaming against a frozen evaluator. It was then resolved as a side effect of
  gen-001 — recorded as an unpredicted win, not claimed as a plan.
- **T3 is recorded as never reachable** under `generations: 2` rather than dropped.
- **Seam contamination is recorded in full**, including that the `batch_02` count was
  revised from three cells to four after the dashboard was taught to surface the
  `sandbox_*` counters — i.e. the user's keep-the-round decision was made on an
  undercount, and the record says so.

## Guardrails 14 and 15 — metric discipline

The reported metric is held-out tasks passed / T, with `num_trials: 3` making per-task
cells pass **rates** (D18): H0 5.3/28, H1 4.3/28, H2 5.3/28. Every number in this
experiment's artifacts carries its set and its N. `pass^k` is used nowhere for
generations; τ's own `pass^1/2/3` appears only inside per-round τ output.

## Frozen surfaces, mechanically checked

The freeze fingerprint `sha256:7ea86d87…f15e9b` is asserted by the runner before every
round against `experiment.yaml`; no round ran under a different one. The frozen `<policy>`
region (5733 chars) is asserted by `make check`, the pre-commit hook and CI on every
commit, and by the adapter against the live `env.get_policy()` at episode start. Both
mutations touched only the `<instructions>` block. `make gate_a0a` PASSed before the first
episode was spent (323 tests + mock smoke) and its verdict attests the adapter sha that
actually ran.
