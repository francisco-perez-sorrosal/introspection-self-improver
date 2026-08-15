# Self-Improving Agent --- Evaluation Protocol

## Agent-Ready Experimental Design for Measuring Harness Improvement on τ-Knowledge

**Status:** Adopted, and exercised end to end — the debug-scale experiment
(`002_bm25-sonnet46`, revealed 2026-08-14) ran this protocol in full\
**Benchmark:** τ-bench / τ-Knowledge `banking_knowledge`\
**Purpose:** Measure whether successive Introspection target-agent
harness generations generalize better to a fixed held-out set after
learning from small, disjoint batches of execution experience.

> **As-built note (2026-08-14).** Sections 1–30 are the design as adopted; the repo
> cites them as "protocol §N", so their numbering is stable and they are not edited
> to track implementation. What each concept became in code is the §3 mapping table
> of `SIA_EVALUATION_PLAN.md`; refinements were adopted through that plan's decisions
> D1–D11, never by rewriting a section here. Three experiment tiers now exist where
> §3–§4 sketched two: **debug** G=3/B=4/T=8 (plan D10 — ran as seq 2), **powered**
> G=5/B=8/T=28 (plan D11 — seq 4, sized by a power analysis on the debug run's own
> data, with a pre-registered trend test as the primary significance instrument), and
> the **full** default below, G=5/B=10/T=47 (deferred to seq 6; plan D15's parity
> convention reserves even seqs for stable experiments, odd for experimentation).
> What the execution taught about the design itself is §31.

------------------------------------------------------------------------

# 1. What This Experiment Is Trying to Evaluate

The objective is **not** to reproduce or directly compare against the
published τ-Knowledge leaderboard results.

Our target agent runs through a custom Introspection/Pi-based harness
and integration layer, so the primary research question is internal and
longitudinal:

> **Can Claude Code, acting as the Improvement Orchestrator through the
> Introspection plugin, progressively improve a simple target-agent
> harness by analyzing execution evidence from small batches of
> τ-Knowledge tasks, such that successive harness generations solve more
> tasks in a fixed unseen held-out set?**

The experiment evaluates **harness evolution**.

The target model, benchmark, evaluator, user simulator configuration,
task partition, and relevant execution configuration remain fixed. The
intended changing variable is the target-agent harness.

Conceptually:

``` text
H0 → H1 → H2 → ... → HG
```

where each transition is driven by a fresh batch of improvement
experiences:

``` text
B1, B2, B3, ... BG
```

and every harness generation is independently measured against the same
hidden held-out set:

``` text
T
```

The principal question is therefore:

`R_T(H_G) > R_T(H_0)` ?

and, more generally, what does the progression

`R_T(H_0), R_T(H_1), ..., R_T(H_G)`

look like?

------------------------------------------------------------------------

# 2. Important Metric Clarification

This experiment does **not** require running every held-out task four
times.

τ-bench's `pass^k` metrics concern repeated trials of the same task.
They are useful for measuring reliability under stochastic execution,
but they are not the metric we need to describe generations of harness
improvement.

For the default self-improvement experiment, run each held-out task
**once per generation** unless an experiment configuration explicitly
requests repeated trials.

The primary metric is simply:

`HeldOutSuccess(H_g) = (held-out tasks passed by H_g) / (number of held-out tasks)`

Always report both the count and percentage.

Example:

``` text
H3: 29 / 47 tasks passed = 61.7%
```

Do not describe generations using `pass^5`, `pass^G`, or another τ
`pass^k` term.

If repeated trials are later enabled for a separate reliability study,
τ-style `pass^k` metrics may be reported as additional metrics, but they
are **not part of the default progression experiment**.

------------------------------------------------------------------------

# 3. Default Experiment Configuration

The default full experiment assumes the current `banking_knowledge` task
pool contains 97 tasks.

Default partition:

``` text
97 tasks
│
├── Improvement pool: 50
│   ├── B1: 10
│   ├── B2: 10
│   ├── B3: 10
│   ├── B4: 10
│   └── B5: 10
│
└── Held-out set T: 47
```

This produces:

``` text
Initial harness: H0

5 improvement generations:
H0 → H1 → H2 → H3 → H4 → H5
```

Each improvement batch is disjoint. A task used in one improvement batch
must not appear in another batch or in the held-out set.

------------------------------------------------------------------------

# 4. Experiment Size Must Be Configurable

The numbers above are **defaults, not architectural constants**.

Every experiment must configure at least:

``` yaml
experiment:
  generations: 5
  improvement_tasks_per_generation: 10
  held_out_tasks: 47
  held_out_trials_per_task: 1
```

The required number of benchmark tasks is:

`N = (G × B) + T`

where:

-   `G` = number of improvement generations;
-   `B` = improvement tasks per generation;
-   `T` = held-out tasks.

For the default:

`(5 × 10) + 47 = 97`

For a debugging experiment:

``` yaml
experiment:
  generations: 3
  improvement_tasks_per_generation: 3
  held_out_tasks: 5
  held_out_trials_per_task: 1
```

which requires:

`(3 × 3) + 5 = 14`

tasks.

This permits fast end-to-end debugging of:

-   τ integration;
-   Introspection execution;
-   trace ingestion;
-   `operate`;
-   `improve`;
-   approval flow;
-   generation creation;
-   held-out isolation;
-   result collection.

A debugging run is not intended to produce statistically meaningful
conclusions.

------------------------------------------------------------------------

# 5. Generation Semantics

`H0` is the original minimal target-agent harness.

For generation (g):

``` text
Hg
 │
 ├── evaluate on hidden T
 │
 └── execute fresh improvement batch B(g+1)
        ↓
     analyze
        ↓
     propose improvement
        ↓
     human approval
        ↓
      H(g+1)
```

Therefore:

``` text
H0 has learned from 0 improvement tasks.
H1 has learned from B1.
H2 has learned from B1 + B2.
...
H5 has learned from B1 + ... + B5.
```

The harness accumulates modifications across generations. `Hg+1` is
based on the latest accepted target-agent commit from `Hg`, not on `H0`.

------------------------------------------------------------------------

# 6. Step 1 --- Establish Generation 0

Create the intentionally simple initial target-agent harness:

``` text
H0
```

Freeze its exact repository commit and runtime configuration.

Run H0 against the complete held-out set `T`.

For the default experiment:

``` text
47 tasks × 1 trial = 47 evaluation episodes
```

Record:

``` text
R0 = passed / 47
```

These runs establish the baseline.

**The Improvement Orchestrator must not analyze these executions.**

------------------------------------------------------------------------

# 7. Step 2 --- Run the First Improvement Batch

Run H0 on:

``` text
B1
```

Default:

``` text
10 tasks
```

These executions are intentionally available for learning.

They should produce the complete legitimate evidence available through
Introspection, including where available:

-   conversations;
-   target-agent traces;
-   user-agent traces if instrumented;
-   retrieval activity;
-   tool calls and results;
-   observations;
-   patterns;
-   metrics;
-   τ objective outcomes.

------------------------------------------------------------------------

# 8. Step 3 --- Claude Discovers Improvement Signals

Claude Code acts as the Improvement Orchestrator.

Using the Introspection plugin's `operate` workflow, Claude analyzes the
executions from the current improvement batch.

It should:

1.  inspect failures and successes;
2.  compare failed trajectories with successful controls;
3.  inspect tool/retrieval/conversation evidence;
4.  look for recurring behavioral phenomena;
5.  estimate prevalence where possible;
6.  open-code evidence rather than starting from a human-provided
    failure taxonomy;
7.  identify the earliest meaningful divergence;
8.  seek counterexamples;
9.  distinguish plausible causes from correlations;
10. distill one or more actionable improvement hypotheses.

The improvement batches provide the learning signal.

The held-out set does not.

------------------------------------------------------------------------

# 9. Step 4 --- Claude Proposes a Harness Change

Claude hands the evidence-grounded hypothesis into the `improve`
workflow.

The proposed intervention should identify:

``` text
evidence
    ↓
discovered signal
    ↓
hypothesis
    ↓
owning harness layer
    ↓
proposed mechanism
    ↓
predicted effect
```

Prefer one coherent mechanism per generation where practical.

Examples of possible mutable surfaces include:

-   target-agent prompt;
-   skills;
-   tool descriptions;
-   retrieval behavior;
-   orchestration;
-   context management;
-   verification logic.

These are possible surfaces, not a predefined improvement taxonomy.

------------------------------------------------------------------------

# 10. Step 5 --- Human Approval Creates the Next Generation

Claude proposes the modification to the user.

No target-agent harness change becomes the next generation until the
user approves it.

After approval:

``` text
Hg → H(g+1)
```

Record:

-   previous commit;
-   new commit;
-   diff;
-   hypothesis;
-   evidence;
-   expected effect.

The new commit defines the next target-agent generation.

------------------------------------------------------------------------

# 11. Step 6 --- Evaluate the New Generation on the Same Held-Out Set

Run `H(g+1)` against exactly the same held-out set `T`.

For the default experiment:

``` text
47 tasks
```

Record:

``` text
R(g+1)
```

For example:

``` text
H0: 13 / 47 = 27.7%
H1: 17 / 47 = 36.2%
```

The desired phenomenon is increasing generalization performance as the
harness accumulates improvements.

However, **monotonic improvement is not required**.

A valid experimental trajectory might be:

``` text
27.7 → 36.2 → 34.0 → 42.6 → 48.9 → 57.4
```

The important endpoint hypothesis is:

`R_T(H_G) > R_T(H_0)`

Failed improvements and regressions are legitimate experimental results.

------------------------------------------------------------------------

# 12. Step 7 --- Held-Out Evidence Firewall

Held-out executions must be isolated from the Improvement Orchestrator.

Claude must not receive:

-   held-out task definitions during optimization;
-   held-out conversations;
-   held-out traces;
-   held-out user-agent traces;
-   held-out per-task rewards;
-   held-out failure descriptions;
-   held-out aggregate score.

This restriction applies to **every generation**, including H0.

The system may execute and record held-out evaluations after each
generation, but their results remain hidden from Claude until the final
generation is frozen.

This prevents the held-out set from becoming an implicit validation set.

The strongest experimental claim is:

> **No held-out task, trajectory, reward, or aggregate held-out
> performance signal was exposed to the Improvement Orchestrator during
> harness optimization.**

------------------------------------------------------------------------

# 13. Step 8 --- Continue with Fresh Improvement Batches

After evaluating H1 privately:

``` text
H1 + B2
    ↓
Claude analyzes B2
    ↓
proposes ΔH1
    ↓
human approval
    ↓
H2
    ↓
hidden T evaluation
```

Then:

``` text
H2 + B3 → H3
H3 + B4 → H4
H4 + B5 → H5
```

Each batch must contain previously unused improvement tasks.

Claude may retain knowledge learned from earlier batches through the
evolving harness and experiment records, but it receives fresh task
evidence each generation.

------------------------------------------------------------------------

# 14. Step 9 --- Improvement Tasks Are Fully Observable

The information policy is deliberately asymmetric.

``` text
IMPROVEMENT BATCHES
        ↓
fully observable to Claude

HELD-OUT SET
        ↓
opaque to Claude
```

For improvement tasks, expose all legitimate execution evidence needed
for diagnosis.

The objective is not to prevent Claude from learning from these tasks.
They are explicitly the system's experience.

They play a role analogous to training experience, although the process
modifies the harness rather than model weights.

------------------------------------------------------------------------

# 15. Step 10 --- Optional Within-Batch Verification

After Claude proposes and implements a change based on `Bg`, it may be
useful to rerun some or all of `Bg` to determine whether the intended
mechanism actually changed behavior.

If enabled, classify this as:

``` text
within-batch intervention verification
```

not generalization.

Conceptually:

``` text
Bg before improvement
    = discovery evidence

Bg after improvement
    = intervention verification

B(g+1)
    = fresh improvement experience

T
    = held-out generalization evaluation
```

Within-batch verification must never replace the held-out evaluation.

For a maximally simple initial MVP, this feature may be disabled.

------------------------------------------------------------------------

# 16. Step 11 --- Stratify Task Assignment

Do not blindly shuffle the 97 tasks and assume five random groups of ten
plus 47 held-out tasks will be comparable.

Where task metadata permits, construct the partition so that:

``` text
B1 ≈ B2 ≈ ... ≈ BG ≈ T
```

with respect to relevant task characteristics.

Potential stratification dimensions include:

-   banking workflow;
-   knowledge requirements;
-   tool requirements;
-   retrieval characteristics;
-   task complexity.

Task metadata may be used to construct the partition.

Task solutions and held-out execution evidence must not be exposed to
Claude.

Persist the exact assignment in a split manifest so every generation
uses the same partition.

------------------------------------------------------------------------

# 17. Step 12 --- Freeze Experimental Variables

The main experiment attempts to attribute performance changes to:

``` text
Δ target-agent harness
```

Therefore freeze as much else as possible.

At minimum record and freeze:

``` text
τ-bench version/commit
banking_knowledge task definitions
τ evaluator
task partition
target model/provider/version
target sampling configuration
user-agent implementation
user-agent model/provider/version
user-agent prompt/configuration
user-agent sampling configuration
retrieval corpus
relevant execution budgets
integration adapter semantics
```

The current τ-bench v1.0.1 release changed `banking_knowledge` grading
and task data, so results before and after that grading boundary are not
directly comparable. Pin an exact version/commit for the experiment.

Only the approved target-agent harness should evolve.

------------------------------------------------------------------------

# 18. Step 13 --- Primary Progression Metric

For every generation calculate:

`S_g = (held-out tasks passed by H_g) / T`

Report:

``` text
generation
improvement tasks seen
tasks passed / T
success percentage
```

Example:

  Generation     Improvement tasks seen   Held-out result
  ------------ ------------------------ -----------------
  H0                                  0     12/47 = 25.5%
  H1                                 10     16/47 = 34.0%
  H2                                 20     19/47 = 40.4%
  H3                                 30     23/47 = 48.9%
  H4                                 40     26/47 = 55.3%
  H5                                 50     30/47 = 63.8%

These numbers are illustrative only.

The main visualization should plot:

``` text
held-out success
        ↑
        │
        │
        └──────────────→ improvement tasks seen
```

or equivalently generation number on the x-axis.

Because 47 tasks is a finite sample, always report the raw count as well
as the percentage.

------------------------------------------------------------------------

# 19. Step 14 --- Task-Level Gain and Regression Metrics

Aggregate success alone can hide capability movement.

For every transition:

``` text
Hg → H(g+1)
```

calculate:

``` text
FAIL → PASS     gain
PASS → PASS     retained
PASS → FAIL     regression
FAIL → FAIL     unresolved
```

Example:

  Transition     Gains   Retained   Regressions   Unresolved   Net
  ------------ ------- ---------- ------------- ------------ -----
  H0→H1              6         11             1           29    +5
  H1→H2              5         15             2           25    +3

These numbers are illustrative.

This distinguishes:

``` text
stable cumulative improvement
```

from:

``` text
capability redistribution
```

A generation that gains ten tasks but loses eight is qualitatively
different from one that gains two tasks with no regressions.

------------------------------------------------------------------------

# 20. Step 15 --- Capability Retention Diagnostic

Track two related quantities:

``` text
currently solved
ever solved
```

For generation `Hg`:

``` text
currently solved:
tasks passed by Hg

ever solved:
tasks passed by at least one generation H0...Hg
```

If:

``` text
H5 currently solved: 31/47
ever solved:          41/47
```

then the system has demonstrated capability on many tasks that the final
harness no longer retains.

If:

``` text
H5 currently solved: 38/47
ever solved:          39/47
```

then improvement has been much more cumulative.

This is a diagnostic for capability retention, not a τ-bench leaderboard
metric.

------------------------------------------------------------------------

# 21. Step 16 --- Task × Generation Matrix

Persist the binary result of every held-out task for every generation.

Conceptually:

``` text
             H0 H1 H2 H3 H4 H5

task_001      0  0  1  1  1  1
task_002      1  1  1  1  1  1
task_003      0  0  0  1  1  1
task_004      1  1  0  1  1  1
task_005      0  0  0  0  0  1
...
```

This matrix should be a first-class result artifact.

It makes visible:

-   when capabilities emerge;
-   whether they persist;
-   where regressions occur;
-   whether the final harness accumulates or merely shifts capability.

------------------------------------------------------------------------

# 22. Step 17 --- Stochasticity

A single trial per task does not prove that a task has been permanently
"solved."

Agent execution may be stochastic.

Therefore interpret:

``` text
0 → 1
```

as:

> the later generation passed this evaluation instance

rather than automatically claiming a deterministic capability
acquisition.

For the MVP, one trial per held-out task per generation is acceptable
because the primary objective is to visualize harness progression while
controlling evaluation cost.

If stronger reliability evidence is later required, configure:

``` yaml
held_out_trials_per_task: 2
```

or more.

Repeated trials are an optional extension of the protocol, not a
requirement for the basic self-improvement curve.

------------------------------------------------------------------------

# 23. Step 18 --- Optional Endpoint Reliability Study

If budget permits, H0 and the final harness HG may be evaluated more
extensively after the self-improvement experiment is complete.

For example:

``` text
H0 × 4 trials/task
HG × 4 trials/task
```

This can answer a secondary question:

> Did the final harness improve repeated-trial reliability as well as
> the one-trial progression metric?

If this extension is performed, legitimate τ-style repeated-trial
metrics may be reported.

It is explicitly separate from the default generation metric.

Do not require four trials for H1...H(G-1) unless the experiment is
specifically studying reliability across the entire trajectory.

------------------------------------------------------------------------

# 24. Step 19 --- Improvement Records Are Part of the Result

For every transition:

``` text
Hg → H(g+1)
```

persist:

``` text
improvement batch IDs
evidence inspected
signals discovered
counterevidence
hypothesis
owning harness layer
proposed change
human approval
source commit
candidate commit
diff
expected effect
held-out result (kept hidden from Claude during optimization)
```

The resulting research artifact is therefore not merely:

``` text
25% → 34% → 40% → ...
```

It is:

``` text
experience
   ↓
discovered signal
   ↓
hypothesis
   ↓
harness intervention
   ↓
new generation
   ↓
hidden generalization result
```

This causal/evidential history is central to demonstrating
self-improvement through Introspection.

------------------------------------------------------------------------

# 25. Step 20 --- What Constitutes Experimental Success

Do not require:

`R_0 < R_1 < R_2 < ... < R_G`

Self-improvement can contain unsuccessful hypotheses and regressions.

The primary endpoint is:

`R_T(H_G) > R_T(H_0)`

A stronger result shows a broadly upward trajectory.

The most convincing demonstration combines:

1.  a clear H0 → HG improvement on the fixed held-out set;
2.  task-level gains and regressions;
3.  evidence that capabilities are increasingly retained;
4.  evidence → signal → hypothesis → change records for every
    generation;
5.  fixed benchmark/model/user-simulator configuration;
6.  no held-out information reaching Claude during optimization.

The desired final claim is:

> **The Improvement Orchestrator progressively extracted generalizable
> harness improvements from small, disjoint batches of execution
> experience, while remaining blind to a fixed held-out evaluation set,
> and the resulting target-agent generations showed increasing ability
> to solve unseen τ-Knowledge tasks.**

------------------------------------------------------------------------

# 26. Configurable Experiment Schema

A concrete configuration should be persisted with every run.

Example full experiment:

``` yaml
experiment:
  name: tau-banking-self-improvement-full

  generations: 5
  improvement_tasks_per_generation: 10
  held_out_tasks: 47
  held_out_trials_per_task: 1

  allow_within_batch_verification: false

  holdout_visibility:
    expose_tasks_to_orchestrator: false
    expose_traces_to_orchestrator: false
    expose_per_task_results_to_orchestrator: false
    expose_aggregate_score_to_orchestrator: false

  require_human_approval: true
```

Example debugging experiment:

``` yaml
experiment:
  name: tau-banking-self-improvement-debug

  generations: 3
  improvement_tasks_per_generation: 3
  held_out_tasks: 5
  held_out_trials_per_task: 1

  allow_within_batch_verification: false

  holdout_visibility:
    expose_tasks_to_orchestrator: false
    expose_traces_to_orchestrator: false
    expose_per_task_results_to_orchestrator: false
    expose_aggregate_score_to_orchestrator: false

  require_human_approval: true
```

The implementation must validate:

`(G × B) + T ≤ N_{available tasks}`

and must guarantee disjoint task assignment.

------------------------------------------------------------------------

# 27. Required Result Artifacts

Every experiment should produce at minimum:

``` text
results/<experiment-id>/
│
├── config.yaml
├── split_manifest.yaml
├── benchmark_lock.yaml
│
├── generations/
│   ├── H0/
│   ├── H1/
│   ├── H2/
│   └── ...
│
├── improvement_records/
│   ├── H0_to_H1.yaml
│   ├── H1_to_H2.yaml
│   └── ...
│
├── held_out/
│   ├── results_by_generation.csv
│   └── task_generation_matrix.csv
│
└── summary.md
```

The held-out artifacts must be inaccessible to the Improvement
Orchestrator until the configured experiment is complete.

------------------------------------------------------------------------

# 28. Interpretation Boundary

This protocol evaluates:

> **Whether the self-improvement process improves this target harness
> under this fixed experimental configuration.**

It does not by itself establish:

-   leaderboard comparability;
-   superiority to published τ-Knowledge systems;
-   deterministic mastery of a task from a single pass;
-   model-weight learning;
-   generalization beyond the selected benchmark/domain.

Those can be studied separately.

The purpose of this experiment is narrower and cleaner:

fresh experience → Introspection evidence → Claude diagnosis →
approved harness change → hidden generalization measurement

repeated across configurable generations.

------------------------------------------------------------------------

# 29. Implementation Guardrails

An implementation agent must preserve the following invariants:

1.  Improvement batches and held-out tasks are disjoint.
2.  Improvement batches are disjoint from one another.
3.  The held-out partition is fixed before H0 evaluation.
4.  Claude cannot inspect held-out evidence during optimization.
5.  Claude cannot receive aggregate held-out scores during optimization.
6.  The target model is fixed during the main experiment.
7.  The user simulator is fixed during the main experiment.
8.  The τ evaluator and task definitions are fixed.
9.  The benchmark version/commit is pinned.
10. Integration code must not introduce task-specific intelligence.
11. Only approved target-harness changes define a new generation.
12. Every generation maps to an exact source commit/runtime version.
13. Every held-out result maps to the generation that produced it.
14. The default metric is held-out tasks passed / held-out tasks.
15. `pass^k` terminology must not be used for harness generations.
16. Failed/rejected improvement attempts must not be silently discarded
    from the research record.
17. Debug configurations must obey the same isolation rules as full
    experiments.
18. Task assignment must be reproducible from the persisted split
    manifest.
19. Held-out results may be revealed only after the final configured
    generation is frozen.
20. The experiment should remain configurable without changing these
    methodological invariants.

------------------------------------------------------------------------

# 30. Short Form for Agents

> Partition the pinned τ-Knowledge `banking_knowledge` tasks into a
> fixed hidden held-out set `T` and `G` disjoint improvement batches of
> size `B`. The default full experiment is `G=5`, `B=10`, `T=47`; a
> debug run may use values such as `G=3`, `B=3`, `T=5`. Create a minimal
> target harness H0. Evaluate every generation H0...HG once on the same
> held-out set, but never expose held-out tasks, traces, per-task
> results, or aggregate scores to Claude during optimization. For each
> generation, run the current harness on the next fresh improvement
> batch, expose those executions fully through Introspection, let Claude
> Code use `operate` to discover actionable signals and `improve` to
> propose a coherent harness change, require human approval, and commit
> the accepted change as the next generation. The primary metric is
> simply held-out tasks passed / total held-out tasks, reported as both
> count and percentage. Also track FAIL→PASS gains, PASS→FAIL
> regressions, capability retention, and a task×generation result
> matrix. Do not call generations `pass^k`; τ `pass^k` concerns repeated
> trials and is optional here. The principal hypothesis is that the
> final harness HG outperforms H0 on the fixed unseen held-out set while
> all non-harness experimental variables remain frozen.

------------------------------------------------------------------------

# 31. Lessons Learned (As-Built Addendum, 2026-08-14)

Recorded after the debug-scale experiment ran this protocol end to end
(seq 2, `002_bm25-sonnet46`) and after the seq-3 sizing analysis.
Appended without renumbering §§1–30; each refinement below was adopted
through a plan decision (`SIA_EVALUATION_PLAN.md` D1–D11), and the
operational counterparts live in that plan's §9.

1.  **The protocol held under execution.** One full cycle — freeze, four
    hidden measurements, three batches, three diagnoses, three
    human-gated mutations, reveal — ran with zero mid-run mechanics
    patching, and all twenty §29 guardrails held
    (`results/experiment_002_bm25-sonnet46/GUARDRAIL_WALK.md`).
2.  **§4's warning is not decorative.** The debug run's endpoint
    (−1 task, inside the ±18 pp band at T=8) produced exactly the
    situation §4 anticipates: a loop demonstrated, no statistical
    conclusion available. The directional-only language did its job.
3.  **Sizing needs a power analysis, not intuition.** A mutation moves
    the curve only if its failure mode has witnesses in T — at T=8 a
    ~10-task mode goes unwitnessed 40% of the time. The powered tier
    (G=5/B=8/T=28, plan D11) was derived from the debug run's own data
    by Monte Carlo
    (`results/experiment_002_bm25-sonnet46/SIZING_ANALYSIS.md`), and
    §25's endpoint question gained a pre-registered companion: a
    one-sided trend test over all G+1 curve points, fixed α, computed
    only at reveal.
4.  **§12's firewall is implementable structurally, not just
    procedurally.** Running held-out episodes on a lane that produces no
    platform evidence at all, with outputs sealed out of tree and a
    single sanctioned reveal, is stronger than the access restriction
    the section asks for — the platform holds nothing to leak.
5.  **§22 named the dominant noise source correctly.** Measured: one
    frozen configuration split 6/10 across ten trials of one task, and
    3 of 8 held-out tasks flipped between identical-harness
    measurements. Pooling across tasks (one trial each) is the
    load-bearing choice; §23's reliability study became a *conditional*
    post-reveal addendum rather than a default.
6.  **A carried result is not a new measurement.** §11's per-generation
    evaluation meets rejected mutations (identity generations) in
    practice; the curve carries the predecessor's result forward, and
    any statistic over the curve must exclude carried columns rather
    than count one draw twice.
7.  **The pool needs screening the protocol did not specify.** A task
    that deterministically crashes the frozen user simulator voids the
    experiment from inside the frozen surface (observed: task_034,
    upstream tau2-bench#470). Pre-partition screening with a real agent
    is now freeze step 0 (`contract/protocol.md`), and pool exclusions
    are documented in the split manifest.
8.  **Tasks are consumable.** Once a loop has tuned on a batch task, or
    a reveal has exposed a held-out task, that task is burnt for future
    held-out use. Successive experiments on one domain therefore compete
    for a shrinking fresh pool — a constraint §16 never had to face and
    the seq-3 partition obeys (fresh-pool discipline, plan D11).
9.  **§24's records earned their place, plus one addition.** The
    evidence chain was written as it happened and audited at reveal; the
    one structure the protocol lacked was an *improvement backlog* for
    the case where a single batch surfaces more approved targets than
    one generation may land (one-coherent-mechanism rule) — adopted in
    `contract/protocol.md` step 4.
