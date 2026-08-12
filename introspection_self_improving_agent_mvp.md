# Introspection Self-Improving Agent MVP

## Agent-Readable Research Context, Architecture, Experimental Protocol, and Implementation Direction

**Status:** MVP design\
**Date:** 2026-08-12\
**Primary goal:** Demonstrate a genuinely self-improving agent harness
using Introspection's native operational and improvement primitives,
with an external benchmark providing an immutable objective.\
**Framing:** Showcase first. The purpose is a convincing, legible demonstration
of the platform in a real vertical. Measurement is kept honest but modest, and
the scientific claim is stated at the strength the sample sizes support (§25).
Splits, freezing, and the learning-record schema are designed so that a
rigorous run later is a re-run, not a rebuild.

------------------------------------------------------------------------

## 0. Executive Summary

We want to demonstrate **self-improvement through the Introspection
framework**, not merely build a generic self-improvement loop and host
the target agent on Introspection.

The MVP uses:

-   **τ-bench / τ-Knowledge `banking_knowledge`** as the external task
    environment and immutable objective evaluator.
-   An intentionally simple **target agent implemented as an
    Introspection recipe**.
-   **Introspection** as the evidence and execution substrate: tasks,
    conversations, traces, tool calls, observations, patterns, metrics,
    judgements, and runtime lineage.
-   **Claude Code + the Introspection plugin** as the **Improvement
    Orchestrator**.
-   The plugin's **`operate`** skill for evidence gathering, signal
    discovery, and diagnosis.
-   The plugin's **`improve`** skill for hypothesis-driven modifications
    to the target agent's repository-owned harness.
-   Repeated benchmark rounds to determine whether the resulting harness
    changes improve performance on unseen tasks.

The key architectural insight is:

> **Do not predefine the useful diagnostic signals for the orchestrator.
> Let Claude discover them from benchmark outcomes plus Introspection
> execution evidence.**

The orchestrator therefore has two core responsibilities:

1.  **Learn from execution:** inspect evidence, discover recurring and
    actionable signals, compare failures against successful controls,
    identify the earliest meaningful divergence, and formulate a causal
    hypothesis.
2.  **Act on what it learned:** propose and eventually implement the
    smallest coherent harness change expected to improve the target
    agent, then validate the prediction experimentally.

The immutable τ evaluator remains the ultimate source of truth.
Diagnostic signals, observations, patterns, and even new evals/judges
may evolve, but the objective benchmark cannot.

The core loop is:

``` text
τ tasks
  ↓
Target Agent H_n
  ↓
Introspection execution evidence + τ outcome
  ↓
Claude Code + Introspection plugin
  ├─ operate  → discover evidence/signals/diagnosis
  └─ improve  → hypothesis + harness mutation
  ↓
Candidate H_(n+1)
  ↓
Validation
  ↓
accept / reject
  ↓
repeat
```

The research question is:

> **Can an LLM Improvement Orchestrator use Introspection's operational
> evidence to autonomously discover actionable failure signals,
> formulate hypotheses about an agent's behavior, and evolve its harness
> such that performance improves on unseen τ-Knowledge tasks?**

------------------------------------------------------------------------

# 1. What We Are Trying to Demonstrate

The project should demonstrate more than:

> Claude Code can edit an agent.

It should demonstrate:

> **Given an external objective and empirical execution evidence, an LLM
> orchestrator can discover what aspects of an agent are limiting
> performance, formulate an intervention, modify the agent harness
> through Introspection's repository workflow, and produce measurable
> improvement on unseen tasks.**

This distinction matters.

A weak demonstration would be:

``` text
benchmark failure
  ↓
human-defined label: "retrieval failure"
  ↓
Claude told to improve retrieval
  ↓
Claude edits prompt
```

The intended demonstration is:

``` text
benchmark failure
  ↓
raw execution evidence
  ↓
Claude investigates
  ↓
Claude discovers a recurring phenomenon
  ↓
Claude tests whether that phenomenon plausibly explains failures
  ↓
Claude formulates a hypothesis
  ↓
Claude chooses the owning harness layer
  ↓
Claude proposes a minimal intervention
  ↓
candidate is evaluated
  ↓
objective score determines whether intervention worked
```

The **discovery of the useful signal is part of self-improvement**.

------------------------------------------------------------------------

# 2. Core Design Principles

## 2.1 Introspection must be structurally essential

The target agent is an Introspection recipe.

The Improvement Orchestrator uses Introspection's own plugin and
operational surfaces to inspect the agent and propose improvements.

The project is therefore not:

``` text
generic self-improver
  ↓
Introspection used as hosting
```

It is:

``` text
Introspection Agent
  ↓
Introspection evidence
  ↓
Introspection operate/improve workflow
  ↓
Introspection recipe change
  ↓
new Introspection Agent version
```

τ-bench sits outside this loop as the independent reality check.

## 2.2 Objective and diagnostics must remain separate

There are two measurement layers.

### Immutable objective

``` text
τ-bench / τ-Knowledge reward
```

This answers:

> Did the agent actually perform the task correctly?

The orchestrator must never modify:

-   benchmark tasks;
-   gold answers/state;
-   evaluator;
-   reward aggregation;
-   held-out split;
-   benchmark adapter in a way that changes semantics.

The last of these is the one that can fail silently, because the adapter sits
between the agent and an evaluator that is itself untouched. §15, Phase A.0
turns it into a measured claim rather than an asserted one.

### Evolvable diagnostics

Examples:

-   Introspection traces;
-   tool-call evidence;
-   observations;
-   patterns;
-   aggregate metrics;
-   judge outputs;
-   custom evals;
-   discovered failure clusters.

These answer:

> What might explain the objective outcome?

The orchestrator may learn to use or eventually create/refine diagnostic
instrumentation, but diagnostics can never replace the external
objective.

Formally:

\[ `\text{Objective}`{=tex} `\neq `{=tex}`\text{Diagnostics}`{=tex} \]

and:

\[ `\text{Success}`{=tex}(H) =
`\text{immutable benchmark evaluation of }`{=tex} H \]

## 2.3 Open-code evidence before imposing a taxonomy

Do **not** begin with a hand-designed failure ontology such as:

``` text
retrieval_failure
policy_failure
tool_failure
planning_failure
communication_failure
```

These may ultimately emerge, but humans should not hand them to the
Improvement Orchestrator as its initial gradient.

The current Introspection `improve` skill explicitly instructs the agent
to **open-code the evidence before imposing a taxonomy**.

This principle is central to the MVP.

## 2.4 Keep the model fixed

For the MVP, improvement means **harness improvement**, not model
improvement.

Freeze:

-   target model;
-   model version/provider;
-   sampling configuration;
-   benchmark;
-   task splits;
-   relevant execution budgets;
-   evaluator.

Allow the orchestrator to modify the harness.

This gives the experiment a clean interpretation:

\[ `\Delta `{=tex}`\text{performance}`{=tex}
`\approx `{=tex}f(`\Delta `{=tex}`\text{harness}`{=tex}) \]

rather than:

\[ f(`\Delta `{=tex}`\text{harness}`{=tex},
`\Delta `{=tex}`\text{model}`{=tex},
`\Delta `{=tex}`\text{benchmark}`{=tex},
`\Delta `{=tex}`\text{budget}`{=tex}) \]

## 2.5 Prefer minimal, hypothesis-driven changes

Do not encourage complete rewrites after every failed round.

Preferred process:

``` text
Evidence
  ↓
Signal
  ↓
Hypothesis
  ↓
Prediction
  ↓
Small coherent mutation
  ↓
Validation
  ↓
Accept / reject
```

This improves causal interpretability and makes the evolutionary history
of the harness useful research data.

## 2.6 Name what Introspection contributes, and exercise it

§2.1 asserts that Introspection must be structurally essential. That assertion
needs a concrete answer, because τ-bench already writes complete trajectories —
every message, every tool call, every reward — to `data/simulations/`. If the
orchestrator's evidence were τ's own JSON, the platform would be doing nothing a
directory of files could not, and a viewer would rightly ask what it was for.

Five capabilities are not obtainable from τ's output, and the demonstration
should visibly use each:

-   **Observations and patterns.** The platform generates structured findings
    over completed conversations and clusters them into named recurring
    patterns, with no instrumentation written by us. τ produces per-episode
    records; it produces no cross-episode phenomenon.
-   **Population-level telemetry.** Metrics queries aggregate across conversation,
    span, event, judgement, observation, and pattern views, which is what
    separates prevalence from severity. Counting inspected conversations by hand
    does not.
-   **Judges as durable instruments.** A recurring behavioral risk becomes a
    Git-owned judge definition with a calibration dataset beside it, versioned
    with the recipe, running on live conversations.
-   **Runtime ↔ commit lineage.** Each generation H_n is an immutable runtime
    version pinned to an exact Git SHA, and any individual task can be traced
    back to the SHA that served it. Generational claims become verifiable rather
    than asserted.
-   **The repository loop.** The agent proposes changes to its own recipe —
    prompts, skills, tools — as pull requests, with branch protection as the
    enforcement boundary. This is a documented first-class platform feature, and
    it is the demonstration's strongest single artifact.

Where the MVP does *not* use a platform capability, it should say so rather than
imply it. The τ objective is computed by τ, outside the platform's own eval
machinery; that is a deliberate choice made to keep the evaluator immutable, not
an integration the demonstration is quietly claiming.

------------------------------------------------------------------------

# 3. The Four System Roles

## 3.1 τ-bench / τ-Knowledge: Task Oracle

Responsibilities:

-   provide realistic conversational tasks;
-   provide the banking environment;
-   provide knowledge documents;
-   provide transactional tools/state;
-   provide objective evaluation;
-   remain immutable from the Improvement Orchestrator's perspective.

It does **not** diagnose the target agent for Claude.

Conceptually, τ provides:

``` text
task
environment
objective outcome
```

not:

``` text
failure cause
recommended fix
```

## 3.2 Target Agent: Subject Being Improved

The target is an Introspection recipe (H_n).

It should begin intentionally simple.

Initial responsibilities:

-   interact with the simulated user;
-   retrieve relevant knowledge;
-   reason over policies/procedures;
-   use banking tools;
-   communicate the result.

Initially avoid sophisticated scaffolding such as:

-   multi-query retrieval;
-   explicit planning frameworks;
-   specialized policy compilers;
-   verification subagents;
-   elaborate retries;
-   large collections of hand-authored skills.

We want sufficient headroom for the Improvement Orchestrator to discover
useful structure.

## 3.3 Introspection: Evidence and Execution Substrate

Introspection supplies the empirical surface through which the
orchestrator understands what happened.

Relevant surfaces include:

-   tasks/runs;
-   conversations;
-   traces;
-   model calls;
-   tool calls and results;
-   observations;
-   patterns;
-   metrics;
-   costs;
-   runtime/version information;
-   feedback;
-   judgements;
-   experiments where justified;
-   repository/runtime lineage.

Introspection also supplies the repository mechanism that allows an
agent recipe to be changed through ordinary Git/PR workflows.

### 3.3.1 Evidence arrives on its own schedule

These surfaces do not all become available at the same time, and the generation
cadence has to absorb that rather than discover it:

-   **Conversations are immediate.** They carry every model call and tool call
    with arguments, results, and per-call token and cost detail. This is the
    evidence available the moment a benchmark round finishes.
-   **Observations are asynchronous.** A conversation becomes eligible for
    analysis only after roughly 30 minutes of inactivity, and background scans
    run on the order of every 10 minutes. A round that just completed has no
    observations yet.
-   **Patterns need volume.** They are clusters over many observations, scoped by
    organization, project, lens, and typically runtime group, and the cluster
    map is regenerated periodically. A single round of 25–35 tasks may not
    produce stable clusters at all.

A zero pattern count is therefore not evidence that nothing is wrong — it is
frequently evidence that analysis has not run yet. Phase B must check analysis
status before drawing that conclusion.

### 3.3.2 A simulated user distorts one lens

Observations are assigned to one of five lenses: user intent, task resolution,
user sentiment, agent struggle, and environment issue. Under τ the user is an
LLM simulator following a task persona, so **user sentiment carries no signal**
and user intent largely restates the task. The load-bearing lenses for this
experiment are task resolution, agent struggle, and environment issue.

## 3.4 Claude Code + Introspection Plugin: Improvement Orchestrator

This is the learning/control component.

**There is no additional orchestrator agent to implement.** Throughout this document, "Improvement Orchestrator" means **Claude Code operating with the Introspection plugin**. The repository's `contract/` directory constrains this orchestrator; it does not implement it.

Its contract is approximately:

\[ O(E_n, H_n) `\rightarrow `{=tex}(S_n, `\Delta `{=tex}H_n) \]

where:

-   (E_n): execution evidence from the current generation;
-   (H_n): current target harness;
-   (S_n): discovered signal/diagnosis/hypothesis;
-   (`\Delta `{=tex}H_n): proposed harness modification.

Internally:

\[ O = O\_{`\text{operate}`{=tex}} + O\_{`\text{improve}`{=tex}} \]

------------------------------------------------------------------------

# 4. Why `operate` and `improve` Are the Correct Introspection Primitives

## 4.1 `operate`: empirical investigation

The current Introspection plugin describes `operate` as the workflow for
inspecting/explaining/changing **live Introspection state without
changing the agent recipe**.

Relevant capabilities include investigation of:

-   tasks;
-   failed/stuck/cancelled executions;
-   conversations;
-   traces;
-   observations;
-   patterns;
-   metrics;
-   costs;
-   runtimes;
-   live judge state.

Important behaviors encoded in `operate`:

1.  Start task diagnosis from the task row and execution state.
2.  Only move to conversation evidence after understanding the
    task-level result.
3.  Inspect tool failures explicitly rather than assuming a conversation
    succeeded because model calls succeeded.
4.  Distinguish individual evidence from population-level prevalence.
5.  Use aggregate telemetry before claiming that a pattern is common or
    rare.
6.  Treat absence of an asynchronous pattern as insufficient proof that
    a problem does not exist.
7.  Hand behavioral recipe changes to `improve`.

For this project:

> **`operate` is the orchestrator's empirical interface.**

It answers:

-   What happened?
-   Where did it happen?
-   How frequently?
-   Which failures share a behavior?
-   How do failures differ from successful controls?
-   What evidence supports or falsifies a suspected cause?

## 4.2 `improve`: intervention

The current plugin describes `improve` as the workflow for proposing or
implementing repository-owned changes to an existing Introspection agent
recipe.

Its scope includes:

-   behavior;
-   prompts;
-   tools;
-   configuration;
-   tests;
-   evals;
-   judge definitions.

Its methodology is unusually well aligned with this experiment.

It directs the agent to:

-   begin from evidence;
-   verify that evidence and local/deployed code refer to the same
    target;
-   inspect recurring patterns and exact supporting conversations;
-   include controls;
-   seek falsifying as well as supporting evidence;
-   open-code evidence before imposing a taxonomy;
-   identify the earliest meaningful divergence;
-   identify the actual owning layer before choosing a remedy;
-   establish an unchanged baseline;
-   change one coherent mechanism at a time;
-   freeze relevant comparison configuration;
-   rerun affected cases and non-regression controls;
-   inspect traces behind score changes;
-   avoid creating an eval or experiment for every failure.

For this project:

> **`improve` is the orchestrator's intervention interface.**

## 4.3 Handoff boundary

The conceptual handoff is:

``` text
OPERATE
inspect → compare → aggregate → discover → diagnose
                         │
                         ▼
                    hypothesis
                         │
                         ▼
IMPROVE
identify owner → propose mechanism → mutate → prove
```

The distinction should remain explicit even if a single Claude Code
session drives both skills.

------------------------------------------------------------------------

# 5. Why τ-Knowledge `banking_knowledge`

The preferred MVP benchmark is the text-based `banking_knowledge` domain
from τ-bench / τ-Knowledge.

Current τ-bench documentation describes the domain as containing:

-   **97 tasks**;
-   **698 policy/procedure documents**;
-   account-management, credit-card, dispute, and transfer workflows;
-   configurable retrieval;
-   transactional tools plus knowledge retrieval.

## 5.1 Retrieval is benchmark configuration, not harness surface

The domain offers several retrieval mechanisms — BM25, embedding-backed
retrieval, grep, an LLM reranker, and agentic terminal/shell search. It is
important to be precise about what they are, because it is easy to mistake them
for an agent-side design space.

They are **mutually exclusive benchmark configurations**, selected by a single
`--retrieval-config` flag. That flag decides which tools the agent is given
**and rewrites the domain policy text** to describe them. It is a property of
the task environment, not of the target harness.

Two consequences follow, and both are binding:

1.  One configuration is pinned for the whole experiment and recorded in the
    benchmark lock. Changing it mid-experiment invalidates every
    cross-generation comparison, because both the tool surface and the policy
    the agent is graded against would have changed underneath the measurement.
2.  Retrieval **implementation** is therefore immutable, but retrieval **usage**
    is not. Query formulation, result count, iteration and stopping behavior,
    and how retrieved policy text is carried into subsequent reasoning all
    belong to the target harness and remain fully mutable.

The pinned configuration for this MVP is `openai_embeddings`: it needs one API
key, avoids the `sandbox-runtime` / ripgrep / bubblewrap dependency that the
shell-based configurations require, caches document embeddings on disk, and sits
closest to the setting under which published τ-Knowledge scores were obtained.
`bm25` is the fully offline fallback, for bring-up only.

This framing does not narrow the experiment. Target-agent failures still emerge
across several harness dimensions:

``` text
user intent
   ↓
knowledge retrieval
   ↓
cross-document reasoning
   ↓
policy/procedure interpretation
   ↓
planning
   ↓
tool selection
   ↓
tool arguments
   ↓
state transition
   ↓
communication
```

Crucially, we do **not** tell the Improvement Orchestrator that these
are the failure categories. They are only examples of phenomena it may
discover.

τ-Knowledge is preferable to a simple classification or QA benchmark
because the agent harness has real architectural surface to improve.

------------------------------------------------------------------------

# 6. τ-bench Versioning Requirement

## 6.1 Naming

Three names refer to overlapping things, and looking for the wrong one wastes
time:

-   the repository and installable package are **`tau2-bench`**
    (`sierra-research/tau2-bench`) — there is no `tau3-bench` repository;
-   the current release line is **τ³-bench**;
-   **`banking_knowledge`** is the domain; the paper calls it **τ-Banking** and
    the extension it belongs to **τ-Knowledge**.

Installation requires `uv sync --extra knowledge` and Python `>=3.12,<3.14`.

## 6.2 Pinning

Pin an exact tag or commit. Do not pin a range: `>=1.0.1` admits a future
release that changes grading again, which is the precise failure this section
exists to prevent.

Reason: v1.0.1 changed `banking_knowledge` grading and task data. The project
explicitly warns that results from versions before and after v1.0.1 are not
directly comparable, and republished affected leaderboard entries. A
`pre-v1.0.1` tag exists for reproducing the older behavior; it must not be used
here. Existing result files can be rescored against current tasks with
`tau2 evaluate-trajs --fresh-tasks`.

A self-improvement curve is meaningless if the evaluator changes during
the experiment.

Record for every run:

``` yaml
benchmark:
  repository: sierra-research/tau2-bench
  commit: "<exact SHA>"          # exact, not a range
  tag: "<exact tag>"
  domain: banking_knowledge
  retrieval_config: openai_embeddings
  task_set_name: base
  frozen:
    agent_llm: "<model@version>"
    user_llm: "<model@version>"
    num_trials: 3
    seed: 300
    max_steps: 200
    max_errors: 10
    max_steps_seconds: 600
    max_concurrency: "<value>"
```

------------------------------------------------------------------------

# 7. Why Not Use Harbor as the First Benchmark?

Harbor is highly relevant but is not the preferred first task
environment.

Harbor is a framework for:

-   evaluating arbitrary agents;
-   creating benchmarks/environments;
-   running isolated environments at scale;
-   generating rollouts for RL/optimization.

It becomes valuable later as a **benchmark portability layer**.

A terminal/SWE benchmark has a much larger failure surface:

-   repository navigation;
-   shell interaction;
-   planning;
-   coding;
-   testing;
-   dependency management;
-   debugging;
-   environment issues.

That makes early causal interpretation harder.

Recommended progression:

``` text
MVP:
Introspection + τ-Knowledge

Later:
same Improvement Orchestrator
        │
        ├── τ-Knowledge
        ├── Harbor / Terminal tasks
        └── custom benchmarks
```

There is a second reason to keep Harbor in view. The Introspection plugin treats
Harbor as a first-class evaluation layer — `improve` bootstraps it directly and
runs baseline-versus-candidate comparisons through it. This MVP deliberately
does not use that path: the τ objective is computed by τ, outside the platform's
own eval machinery, which is what keeps the evaluator immutable and unarguable.
The cost is that `improve`'s native measurement step is not what decides a
generation here. Wrapping a τ episode as a Harbor task would close that gap and
make the loop fully native — which is a strong later step, and too much for a
first implementation.

A later research question becomes:

> Does the same Introspection-based improvement process generalize
> across agent domains?

------------------------------------------------------------------------

# 8. What We Borrow from SIA

SIA provides an important conceptual reference.

SIA separates roles around:

-   meta/feedback agent;
-   target/task agent;
-   benchmark feedback;
-   successive generations.

It explores both:

-   harness updates;
-   weight updates.

For this MVP we deliberately choose only:

``` text
HARNESS UPDATES
```

and hold weights/model fixed.

What we borrow:

1.  **Generational improvement.**
2.  **External benchmark signal.**
3.  **Separation between target agent and improvement logic.**
4.  **Preservation of per-generation artifacts.**
5.  **Evaluation of whether improvements generalize rather than merely
    fit observed cases.**

What we do **not** initially borrow:

-   weight updates;
-   RL/post-training;
-   simultaneous model and harness evolution.

This keeps the result attributable to the Introspection
harness-improvement process.

------------------------------------------------------------------------

# 9. What We Borrow from Prime Agent

Prime Agent is useful conceptually because its refinement philosophy
favors incremental changes grounded in trajectory evidence rather than
uncontrolled rewrites.

The relevant principle for this MVP is:

> **Prefer the smallest harness mutation that follows from the evidence
> and has a testable predicted effect.**

The orchestrator should not respond to:

``` text
score = 42%
```

with:

``` text
rewrite the entire agent
```

It should instead produce reasoning of the form:

``` text
Observation:
A recurring behavior appears in failed trajectories.

Control:
Successful trajectories differ at a specific point.

Hypothesis:
Mechanism X plausibly explains the divergence.

Intervention:
Change one harness mechanism.

Prediction:
Specific cases should improve without regressions in controls.

Validation:
Run unchanged baseline and candidate.

Decision:
Accept or reject.
```

------------------------------------------------------------------------

# 10. What We Borrow from SquareDiff

SquareDiff's public philosophy is highly aligned with the project:

``` text
define → improve → run → evolve
```

Its platform describes autonomous experimentation across prompts,
models, and tools using evaluation performance and traces.

The main connection is **autonomous harness experimentation**.

Our MVP differs by deliberately emphasizing:

-   an external research benchmark;
-   a fixed model;
-   interpretable generational changes;
-   open evidence-to-hypothesis records;
-   Introspection as the native evidence and modification substrate.

------------------------------------------------------------------------

# 11. The Final MVP Architecture

``` text
                    IMMUTABLE OUTER REALITY
              ┌───────────────────────────────┐
              │           τ-BENCH             │
              │                               │
              │ banking_knowledge tasks       │
              │ environment / user simulator  │
              │ objective evaluator           │
              └───────────────┬───────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │    TARGET AGENT     │
                   │                     │
                   │ Introspection H_n   │
                   └──────────┬──────────┘
                              │
                           executes
                              │
                              ▼
             ┌──────────────────────────────────┐
             │          INTROSPECTION           │
             │                                  │
             │ tasks / conversations / traces   │
             │ tool calls / results             │
             │ observations / patterns          │
             │ metrics / feedback / judgements  │
             │ runtime + repository lineage     │
             └────────────────┬─────────────────┘
                              │
                           evidence
                              │
                              ▼
       ┌────────────────────────────────────────────┐
       │          IMPROVEMENT ORCHESTRATOR          │
       │          Claude Code + Plugin              │
       │                                            │
       │  ┌──────────────────────────────────────┐  │
       │  │ OPERATE                              │  │
       │  │                                      │  │
       │  │ inspect                              │  │
       │  │ compare failures / successes         │  │
       │  │ measure prevalence                   │  │
       │  │ open-code evidence                   │  │
       │  │ discover actionable signal           │  │
       │  │ identify earliest divergence         │  │
       │  └───────────────────┬──────────────────┘  │
       │                      │                     │
       │               learning record              │
       │                      │                     │
       │                      ▼                     │
       │  ┌──────────────────────────────────────┐  │
       │  │ IMPROVE                              │  │
       │  │                                      │  │
       │  │ determine owning layer               │  │
       │  │ formulate causal hypothesis          │  │
       │  │ predict expected effect              │  │
       │  │ propose minimal mutation             │  │
       │  │ baseline → candidate → validation    │  │
       │  └───────────────────┬──────────────────┘  │
       └──────────────────────┼─────────────────────┘
                              │
                              ▼
                            H_n+1
                              │
                              └──────────► next round
```

## 11.1 The seam between τ and Introspection is undecided

The arrow from τ-BENCH down to TARGET AGENT in the diagram above hides the one
component this MVP has not designed, and it carries nearly all of the
implementation risk. Nothing downstream in this document may assume a particular
answer.

### The mismatch

τ and Pi have opposite control flow for tool execution.

τ constructs the agent with the tools and the policy
(`HalfDuplexAgent.__init__(tools, domain_policy)`), the agent returns an
`AssistantMessage` that may contain tool calls, and **the orchestrator executes
those calls** against the environment and returns the results. A Pi agent, by
contrast, executes its own tools inside its own sandbox and returns only text.

Something has to reconcile that. §14.1 forbids the orchestrator from changing
the "benchmark semantic adapter" — this is that adapter, and a defect in it
silently changes grades without changing the evaluator.

### Confirmed constraints

-   Endpoint bindings accept **public DNS names over HTTPS only**; IP addresses
    and localhost are rejected. A deployed runtime cannot reach a τ environment
    running on a laptop.
-   `introspection dev --mcp NAME=URL` can repoint a **declared MCP server** at a
    local process for the duration of the command. Recipe extensions cannot be
    repointed this way. If the τ tool surface is to be relocatable per
    environment, it must be an MCP server rather than an extension.
-   Recipes may declare Python dependencies (`pi.runtime`, with a `pyproject.toml`
    and a committed `uv.lock`), so vendoring τ into the sandbox is not excluded
    on packaging grounds.
-   τ supports custom agents as a first-class extension point: implement
    `HalfDuplexAgent`, register a factory, select it with `--agent`. Runnable
    starting points live in `examples/agents/` (`custom_agent_eval.py`,
    `minimal_text_agent.py`).

### Candidates

| Candidate | Mechanism | Trade-off |
|---|---|---|
| **MCP shim + `introspection dev`** | τ's live environment wrapped as a declared MCP server, repointed at the local process with `--mcp` | Fastest loop, no public infrastructure, and because the shim wraps the orchestrator's actual environment object, `reward_basis: DB` needs no reconstruction. Runs in the development lane only, so generations get no immutable version pin |
| **MCP shim + public tunnel** | The same shim behind a public HTTPS endpoint binding | Generations run on real staging runtimes with full runtime ↔ commit lineage. Costs a tunnel and a session-keyed multi-tenant environment service |
| **τ vendored into the sandbox** | tau2 plus the banking data shipped inside the recipe, environment running in-process | No network infrastructure at all. Heaviest recipe, and the trajectory must be reconstructed for grading, which is the highest-risk part to get right |

### Spike

Timeboxed, and it runs before any further work on this MVP. It exits when all
four hold:

1.  one τ `banking_knowledge` task completes end-to-end through the seam;
2.  the full trajectory is visible as a single Introspection conversation, with
    tool calls and their arguments;
3.  `tau2 evaluate-trajs` grades the result — the reward is never recomputed by
    us;
4.  the adapter fidelity gate (§15, Phase A.0) passes on the `mock` domain.

The spike's outcome is recorded here, and the chosen candidate becomes the
design. Until then this section is the design.

------------------------------------------------------------------------

# 12. Experimental Dataset Split

Do not use a simple train/test split if we want the orchestrator to
investigate failures repeatedly without contaminating the final
evaluation.

Use three sets.

``` text
                     τ task pool
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      DISCOVERY      VALIDATION        TEST
          D              V              T
```

Suggested initial sizes depend on implementation cost, but a reasonable
MVP could begin around:

``` text
Discovery:   25–35 tasks
Validation:  10–20 tasks
Test:        15–25 tasks
```

The exact split should preserve task diversity.

## 12.0 The split is configuration, not structure

τ selects tasks by identifier (`--task-ids`), so a split is nothing more than
three lists of IDs. They live in `benchmark/split_manifest.yaml` and are frozen
per experiment by §14.1 — but resizing them between experiments costs an edit,
not a redesign.

That matters, because the sizes above are small relative to the variance this
domain exhibits (§17.2), and the test split in particular carries the strongest
claim in §25 on the fewest tasks. Two consequences to hold in view:

-   The remainder of the 97 tasks is not discarded. Tasks outside the three
    splits are unused during optimization and are available for the full-domain
    checkpoint runs described in §17.1.
-   If a generation's accept/reject decision turns on a difference smaller than
    the split can resolve, the honest response is to record the result as
    directional and say so in the learning record — not to reach for a number
    the sample cannot support.

## 12.1 Discovery set

Claude may inspect:

-   task outcome;
-   conversation;
-   trace;
-   model calls where available;
-   retrieval/tool calls;
-   observations;
-   patterns;
-   metrics;
-   relevant diagnostic judgements.

This is the dataset from which the orchestrator learns.

## 12.2 Validation set

Used to decide whether a candidate change generalizes beyond the cases
that motivated it.

Prefer limiting information returned to the orchestrator.

At minimum provide aggregate/objective outcomes.

If candidate diagnosis requires additional evidence, define a controlled
policy for exposing validation failures rather than silently turning
validation into more discovery data.

## 12.3 Test set

The Improvement Orchestrator must not inspect test tasks or trajectories
during optimization.

Use only at predetermined checkpoints or final evaluation.

This is the strongest evidence that the harness genuinely improved.

------------------------------------------------------------------------

# 13. Baseline Target Agent

Generation 0 should be intentionally simple but legitimate.

Conceptual architecture:

``` text
simulated user
     ↓
target LLM
     ↓
knowledge-search capability
     ↓
banking documents
     ↓
target LLM
     ↓
banking transactional tools
     ↓
response / state
```

The baseline should have only enough instruction to perform the task:

-   act as a banking support agent;
-   use available knowledge when needed;
-   follow policies;
-   use available banking tools when appropriate;
-   communicate results accurately.

Avoid prematurely giving it:

-   query decomposition;
-   synonym expansion;
-   explicit retrieve-plan-execute loops;
-   specialized policy extraction;
-   self-verification;
-   multi-agent decomposition;
-   learned failure-specific rules.

Those are candidate structures the Improvement Orchestrator may
discover.

(Reranking is deliberately absent from that list. It is a `--retrieval-config`
suffix, so it is not something the baseline could be given or the orchestrator
could add — see §5.1.)

## 13.1 The baseline needs a floor, not just a ceiling

"Intentionally simple" has a lower bound, and it follows from the method this
document adopts rather than from taste.

Both §15 and the `improve` workflow diagnose by **comparing failed trajectories
against successful controls** and locating the earliest point at which they
diverge. That method requires successes to compare against. A baseline weak
enough to pass almost nothing does not merely score badly — it destroys its own
diagnostic comparator, and the orchestrator is left open-coding a pile of
failures with nothing to contrast them with.

This is a real risk here rather than a hypothetical one. Frontier models with
high reasoning budgets reach only about 25.5% pass on this domain, so a
deliberately naive G0 can land in single digits.

Therefore:

-   **Target ≥20–25% pass on the discovery split at G0.** Below that, the run
    yields too few controls to support the method.
-   If G0 falls below the floor, the correct response is to **strengthen G0** —
    give it enough instruction to perform the task competently — and rerun the
    baseline, not to proceed and hope the orchestrator copes.
-   Strengthening G0 to reach the floor is not the same as pre-supplying the
    structures listed above. The floor is about basic task competence: use the
    search tool, read the policy, call the transactional tools, report what
    happened.

------------------------------------------------------------------------

# 14. Mutable vs Immutable Surfaces

## 14.1 Immutable during an experiment

The Improvement Orchestrator must not modify:

``` text
τ evaluator
τ task definitions
gold states/answers
objective reward aggregation
benchmark semantic adapter
held-out/test data
dataset split (benchmark/split_manifest.yaml)
```

Nor any of the following, each of which is a comparison variable named by its
actual τ flag so that "frozen" is checkable rather than aspirational:

``` text
--domain              banking_knowledge
--task-set-name       base
--retrieval-config    openai_embeddings      # tools AND policy text (§5.1)
--agent-llm           pinned model@version   # the target model
--agent-llm-args      sampling configuration
--user-llm            pinned model@version   # user simulator: also a variable
--user-llm-args       sampling configuration
--num-trials          fixed across generations
--seed                300
--max-steps           200
--max-errors          10
--max-steps-seconds   600
--max-concurrency     fixed
tau2-bench commit     exact SHA, not a range (§6.2)
```

Two of these are easy to overlook and both have bitten comparisons before. The
**user simulator model** is as much a determinant of an episode's outcome as the
agent model, and it is not the same knob — a provider change there moves scores
with no harness change at all. And the **execution budgets** (`--max-steps`,
`--max-errors`, `--max-steps-seconds`) are exactly how a later generation can
"improve" by simply being allowed to do more.

## 14.2 Mutable target-agent harness

Potentially mutable:

``` text
system prompt
agent instructions
skills
tool descriptions
retrieval usage        # query formulation, k, iteration, stopping
policy application     # how retrieved policy text is carried forward
planning/orchestration logic
retry logic
context management
verification logic
tests
diagnostic eval definitions
diagnostic judge definitions
```

The exact permission envelope should be explicit.

Note what is deliberately **not** on this list. Earlier drafts included
"retrieval implementation" and "reranking". Both are `--retrieval-config`
selections: they change the agent's tool set *and* the policy text it is graded
against, so they belong in §14.1 and are frozen. What remains mutable is how the
agent *uses* the retrieval tools it was given — which is a large and genuinely
improvable surface, and the one where §5.1 expects most of the headroom to be.

## 14.3 Important distinction: diagnostic evolution

The orchestrator may discover that a recurring behavioral risk deserves
permanent instrumentation.

For example:

``` text
G0:
τ reward only

experience:
Claude discovers recurring retrieval mismatch

G1:
target harness changes how it queries and triages retrieval results
(never which retrieval mechanism it has — see §5.1)

possibly:
a retrieval-quality diagnostic eval is introduced
```

This is allowed because the τ objective remains unchanged.

The system can therefore co-evolve:

\[ (H_n, E_n) \]

where:

-   (H_n): target harness;
-   (E_n): diagnostic/instrumentation model.

But only (H_n)'s performance under the immutable external objective
determines success.

------------------------------------------------------------------------

# 15. One Improvement Generation

A complete generation should be treated as an empirical cycle.

## Phase A.0 --- Adapter fidelity gate

This runs once before G0, and again whenever the adapter changes. It is a
blocking precondition, not a formality.

§2.2 claims the τ evaluator is immutable. The evaluator is only half of what
determines a score: the adapter that carries messages and tool calls between τ
and the Introspection runtime determines what the evaluator *sees*. A defect
there changes grades while leaving the evaluator untouched, and it does so
silently. The claim is therefore worth nothing unless it is measured.

Procedure:

1.  Run τ's **stock `LLMAgent`** natively via `tau2 run`.
2.  Run the **same stock agent through the adapter path**.
3.  Hold everything else identical: same model, same `--seed`, same
    `--task-ids`, same `--num-trials`, same retrieval config.
4.  Compare. The two must agree within trial noise.

Notes:

-   Run the gate on the **`mock` domain** during development. It costs a
    fraction of `banking_knowledge` and tests exactly the same thing — the
    adapter, not the experiment. Repeat it once on `banking_knowledge` before
    G0.
-   Grade **only** with `tau2 evaluate-trajs`. The reward function is never
    reimplemented, reproduced, or approximated on our side; that is what keeps
    §2.2 true by construction rather than by assertion.
-   A failed gate blocks the experiment. Divergence means the adapter is
    changing outcomes, and every downstream generational number would be
    measuring the adapter as much as the harness.

## Phase A --- Execute

Run the current target harness (H_n) on the selected discovery cases.

Capture:

-   τ objective results;
-   Introspection task identifiers;
-   conversations;
-   traces;
-   retrieval/tool activity;
-   relevant metrics;
-   observations/patterns.

## Phase B --- Operate

Claude invokes the `operate` workflow.

Required behavior:

1.  Resolve the exact target runtime/version.
2.  Inspect objective failures.
3.  Inspect corresponding Introspection task rows.
4.  Inspect conversations/traces/tool evidence.
5.  Inspect successful controls.
6.  Use aggregate telemetry to estimate prevalence.
7.  Open-code observed phenomena.
8.  Search for the earliest meaningful divergence.
9.  Distinguish correlation from plausible cause.
10. Seek counterexamples/falsifying evidence.

Timing constraint (see §3.3.1): steps 3–5 can run as soon as the round finishes,
because conversations are immediate. Steps 6–7 cannot. Observations require
roughly 30 minutes of conversation inactivity plus a background scan, and
patterns need enough observations to cluster at all. Phase B therefore either
waits for analysis or proceeds on conversation evidence alone and says which it
did. An empty pattern list queried five minutes after a round is not a finding.

Output: one or more candidate actionable signals.

Example:

``` text
Observed:
Failed cases frequently retrieve policy documents that match
the user's literal vocabulary but not the operational banking
concept required by the task.

Controls:
Successful cases often contain vocabulary overlap with the
correct policy document.

Candidate signal:
Surface-vocabulary mismatch between user language and policy
terminology may be suppressing relevant-document retrieval.
```

Notice that the human never supplied the label "retrieval failure."

## Phase C --- Hypothesis

The orchestrator converts evidence into a testable hypothesis.

Example:

``` text
If the target agent reformulates user language into likely
banking-policy terminology before retrieval, relevant-document
recall should improve on the affected class of tasks without
degrading unrelated tasks.
```

The hypothesis should include:

-   evidence;
-   counterevidence;
-   owning layer;
-   expected affected cases;
-   expected non-regressions;
-   confidence;
-   predicted measurable effect.

## Phase D --- Improve

Hand off to `improve`.

The orchestrator determines the narrowest appropriate mutation.

Examples that may emerge:

-   prompt clarification;
-   new skill;
-   retrieval query reformulation;
-   result-triage or stopping discipline over retrieved documents;
-   improved tool description;
-   prerequisite validation;
-   plan-before-action step;
-   post-action verification;
-   deterministic test;
-   justified diagnostic eval.

Do not prescribe these categories to the orchestrator upfront.

## Phase E --- Baseline and Candidate

Preserve an unchanged baseline.

Then create candidate (H'\_n).

Freeze comparison variables.

Run:

``` text
baseline H_n
vs.
candidate H'_n
```

on the same relevant evaluation protocol.

Three disciplines make that comparison mean something at this domain's variance:

-   **Pair it.** Run baseline and candidate over the identical `--task-ids`, not
    over independent samples. A paired comparison on the same tasks resolves a
    far smaller effect than two independent rates at these sample sizes.
-   **Repeat it.** `--num-trials` at 3 or more. τ-Knowledge documents reliability
    degrading sharply over repeated trials, so a single trial per task measures
    luck as much as harness.
-   **Interleave it.** Run baseline and candidate in the same batch rather than
    reusing the baseline number recorded in an earlier generation. Provider
    behavior drifts, and a stale baseline turns that drift into an apparent
    improvement.

## Phase F --- Validation

Evaluate candidate on validation tasks.

Possible result:

``` text
candidate improves:
accept → H_(n+1)

candidate does not improve:
reject/revert → retain H_n
```

Inspect traces behind score changes. A higher aggregate score alone is
not sufficient evidence that the intended mechanism improved.

## Phase G --- Record

Persist the complete learning record.

------------------------------------------------------------------------

# 16. Learning Record Schema

Every attempted mutation should produce a machine-readable artifact.

Example:

``` yaml
generation: 3
candidate: query-reformulation-v1

target:
  recipe_commit: "<sha>"
  runtime_version: "<id>"
  model: "<fixed-model>"

objective_before:
  discovery_pass1: 0.47
  discovery_pass_k: 0.31
  validation_pass1: 0.43
  validation_pass_k: 0.28

evidence_examined:
  failed_tasks: 16
  successful_controls: 8
  task_ids:
    - ...
  conversations:
    - ...

discovered_signal:
  description: >
    Failed cases frequently retrieve documents matching
    surface terminology while missing the operational
    banking concept required by the policy.
  prevalence: "<measured, not guessed>"
  supporting_cases:            # Introspection task/conversation IDs (§22.9)
    - ...
  counterexamples:
    - ...
  previously_published: false  # does the τ-Knowledge literature already name
                               # this? honest answer, not a suppressed one

earliest_divergence:
  layer: retrieval
  description: >
    ...

hypothesis:
  statement: >
    Reformulating user language into domain-policy terminology
    before retrieval should increase relevant-document recall.
  confidence: "<calibrated qualitative or numeric value>"
  expected_effect:
    - "improve affected discovery cases"
    - "improve validation pass rate"
  expected_non_regression:
    - "no increase in invalid banking tool calls"

proposed_change:
  owner: target-agent-harness
  mechanism: "<description>"
  files:
    - ...

comparison:
  frozen: "<the full §14.1 set, by τ flag name>"
  paired: true                 # identical --task-ids for baseline and candidate
  interleaved: true            # same batch, not a reused earlier baseline
  num_trials: 3

results:
  discovery_before: ...
  discovery_after: ...
  validation_before: ...
  validation_after: ...
  pass_k_before: ...
  pass_k_after: ...
  effect_resolvable: true      # false => record as directional (§12.0)
  cost_before: ...
  cost_after: ...
  walltime_minutes: ...

trace_review:
  intended_mechanism_observed: true
  regressions_observed: []

decision: accept
reason: >
  ...
```

This artifact is part of the research output, not incidental logging.

------------------------------------------------------------------------

# 17. Metrics

## 17.1 Primary metric

Start with the native τ objective.

Primary:

``` text
pass^1 / task success rate
```

Do not initially create a complicated composite objective.

### 17.1.1 Report two numbers at checkpoints, and label both

At G0 and at the final generation, report both of the following. Neither is
sufficient alone, and presenting one without the other is misleading in opposite
directions.

| Number | What it is | How to label it |
|---|---|---|
| **Held-out test score** | The configured test split (§12.3), never inspected during optimization | The generalization claim. Always with its N and an interval — a 15–25 task split moves in coarse quanta and the interval is wide |
| **Full 97-task `base` score** | The whole domain, the number the leaderboard reports | The recognizable, externally comparable number. Explicitly labelled as **including tasks the orchestrator inspected**, so it is not a generalization claim |

The reason for carrying both is that they answer different questions. The
held-out score is the honest one but is small and noisy; the full-domain score
is large and comparable to published results but is contaminated by discovery.
Reporting only the first understates what was built; reporting only the second
overstates what was shown. Reporting both, correctly labelled, is accurate.

Run the full-domain number at G0 and at the final generation only. It is not a
per-generation metric — it is expensive, and running it every round would leak
test tasks into the optimization loop.

## 17.2 Reliability

Where budget allows, repeated trials measure reliability rather than
single lucky successes. Relevant concepts from τ-bench include pass^k-style
reliability, and `--num-trials` is the native mechanism.

This is not an optional refinement here. τ-Knowledge reports that on this domain
"reliability degrad[es] sharply over repeated trials" even for frontier models —
which means two things at once. Single-trial pass¹ is a noisy estimator, so
trials are needed for the comparison to resolve anything. And reliability is
plausibly *where the headroom is*: a harness change that makes an already-
achievable task achievable consistently may move pass^k substantially while
barely moving pass¹.

Report pass^k alongside pass¹ from G0 onward, so that an improvement of this
shape is visible rather than invisible.

## 17.3 Efficiency metrics

Track but do not necessarily optimize initially:

``` text
tokens/task
model calls/task
retrieval calls/task
tool calls/task
latency
cost/task
conversation turns
```

### 17.3.1 Budget the generation before running it

The MVP needs a cost and wall-clock estimate per generation, produced before the
first full round rather than discovered during it. The inputs are known:

-   episode length and retrieved-context volume, measured from a pilot run
    rather than assumed — the domain is 700+ documents and tasks routinely
    require reading many of them, so context grows substantially within an
    episode;
-   each generation runs **baseline and candidate**, over **discovery plus
    validation**, multiplied by **`--num-trials`**;
-   checkpoint generations additionally run the full 97-task domain (§17.1.1).

Two throughput ceilings bind independently of cost. τ's own `--max-concurrency`
limits simultaneous simulations, and **Introspection queues tasks per
organization** according to plan limits, with no user-configurable setting —
queued work proceeds when slots free, and retrying only lengthens the queue.
Whichever is lower sets the real wall-clock per round, and §3.3.1's analysis
latency is added on top before Phase B can complete.

Record actual cost and wall-clock per generation in the learning record from G0
onward. §17.4's "cost per accepted improvement" is not computable otherwise.

## 17.4 Improvement-process metrics

These are especially interesting for this project:

``` text
candidate acceptance rate
validation gain per accepted mutation
regression rate
cost per accepted improvement
generations to improvement
number of files/mechanisms changed
diagnostic signals discovered
diagnostic signals that led to successful interventions
```

A useful meta-measure is:

\[ P(`\Delta `{=tex}R \> 0 `\mid `{=tex}S_n
`\rightarrow `{=tex}`\Delta `{=tex}H_n) \]

Informally:

> How often does a discovered signal lead to an intervention that
> actually improves objective performance?

------------------------------------------------------------------------

# 18. What Counts as Self-Improvement Here?

The human supplies:

``` text
goal
benchmark
environment
permission boundaries
```

The Improvement Orchestrator discovers:

``` text
failure structure
useful signals
causal hypotheses
owning harness layer
intervention
validation evidence
```

This is stronger than a system in which humans label every failure and
tell the meta-agent which component to optimize.

The target agent itself does not necessarily execute the improvement
reasoning. The self-improving **system** consists of:

``` text
Target Agent
+
Introspection evidence substrate
+
Improvement Orchestrator
+
mutable target recipe
+
objective feedback loop
```

The critical property is closure:

\[ `\text{experience}`{=tex} `\rightarrow`{=tex}
`\text{diagnosis}`{=tex} `\rightarrow`{=tex}
`\text{harness mutation}`{=tex} `\rightarrow`{=tex}
`\text{new experience}`{=tex} \]

with minimal human specification of the intermediate diagnosis.

------------------------------------------------------------------------

# 19. Repository and Permission Architecture

Prefer strict separation.

Conceptually:

``` text
Repository A — target agent recipe
  orchestrator: read/write through approved workflow

Repository B — benchmark integration
  orchestrator: read-only where possible

Benchmark/evaluator
  orchestrator: immutable

Held-out test data
  orchestrator: inaccessible during optimization
```

Introspection's repository model is directly relevant.

Its documentation states that a recipe is a repository and can be
explicitly granted to an agent. With elevated `contents` and
`pull-requests` permissions, an agent can propose changes to the
prompts, skills, and tools defining its own behavior.

Important security principle:

> Agent repository write access is a code-execution capability.

The platform documents two controls for exactly this loop, and they are
complementary rather than alternatives:

-   **required-review branch protection** — the agent opens pull requests but
    cannot merge its own work;
-   **a pinned production lane** — merges land on the branch, but production
    stays on its pinned version until advanced deliberately.

For an initial research MVP, use PRs and branch protection.

Recommended first workflow:

``` text
Claude discovers improvement
  ↓
Claude proposes recipe diff
  ↓
PR
  ↓
review / controlled acceptance
  ↓
candidate runtime
  ↓
benchmark
```

A later stage can close more of the loop automatically.

------------------------------------------------------------------------

# 20. Human-in-the-Loop vs Fully Closed Loop

The current `improve` skill is explicitly human-in-the-loop and requires
confirmation before repository edits/PR work.

Therefore distinguish:

## MVP-A: research loop with approval

``` text
run
↓
operate
↓
diagnose
↓
improve proposal
↓
human approval
↓
edit / PR
↓
candidate
↓
evaluate
```

This already demonstrates automated signal discovery and automated
improvement design.

## MVP-B: progressively closed loop

After the experimental protocol is trustworthy, automate additional
transitions.

Potential later loop:

``` text
run
↓
operate
↓
diagnose
↓
propose candidate
↓
candidate branch
↓
automatic validation
↓
accept/reject under explicit policy
↓
next generation
```

Do not weaken Introspection's current permission/confirmation boundaries
merely to claim full autonomy.

------------------------------------------------------------------------

# 21. Expected Evolution --- Hypotheses, Not Instructions

We expect that the target harness **might** evolve along dimensions such
as:

``` text
baseline
  │
  ├─ better retrieval discipline
  │
  ├─ query reformulation
  │
  ├─ policy extraction
  │
  ├─ prerequisite checking
  │
  ├─ plan-before-write behavior
  │
  └─ post-action verification
```

Every item above is harness-side and therefore reachable: "better retrieval
discipline" and "query reformulation" mean changing how the agent uses the
retrieval tools it was given, never swapping the retrieval mechanism, which
§5.1 freezes.

But these should **not** be given to the orchestrator as a prescribed
roadmap.

They are researcher hypotheses.

The scientifically interesting result is which mechanisms the
orchestrator actually discovers from evidence.

------------------------------------------------------------------------

# 22. Threats to Validity

## 22.1 Benchmark leakage

Risk:

Claude sees held-out answers/tasks and memorizes them.

Mitigation:

-   strict discovery/validation/test separation;
-   inaccessible final test trajectories;
-   immutable benchmark repo;
-   no target-specific hardcoding.

How strongly "inaccessible" holds is the subject of §22.10 — these mitigations
are procedural unless a mechanical boundary is chosen.

## 22.2 Judge gaming / Goodharting

Risk:

The orchestrator improves diagnostic scores rather than task
performance.

Mitigation:

-   τ reward is immutable and authoritative;
-   diagnostic evals cannot redefine success;
-   final test uses external evaluator.

## 22.3 Model drift

Risk:

Provider/model changes contaminate generational comparisons. This applies to
**two** models, not one: the target agent's and the user simulator's. A change
to the simulator moves scores with no harness change at all, and it is the
easier of the two to forget.

Mitigation:

-   pin provider/model/version for both `--agent-llm` and `--user-llm`;
-   record exact configuration, including `--agent-llm-args` and
    `--user-llm-args`;
-   freeze both for the experiment;
-   interleave baseline and candidate in one batch (§15, Phase E) so residual
    drift affects both arms equally.

## 22.4 Evaluator drift

Risk:

τ-bench changes during experiment.

Mitigation:

-   pin exact τ commit;
-   use \>=1.0.1;
-   store evaluator version in every run.

## 22.5 Budget drift

Risk:

Later agents simply consume more tokens/tools.

Mitigation:

-   freeze or explicitly track budgets;
-   report efficiency metrics;
-   later introduce constrained optimization if useful.

## 22.6 Overfitting discovery tasks

Risk:

Changes improve cases Claude inspected but not unseen cases.

Mitigation:

-   validation split;
-   final hidden test;
-   preserve per-generation generalization curves.

## 22.7 Uninterpretable multi-change generations

Risk:

Claude changes prompt, retrieval, tools, and planning simultaneously.

Mitigation:

-   one coherent mechanism at a time;
-   explicit hypothesis and prediction;
-   baseline/candidate comparison;
-   inspect traces behind score changes.

## 22.8 False causal stories

Risk:

Claude produces plausible narratives that are not causally responsible
for failure.

Mitigation:

-   require successful controls;
-   require counterexamples/falsifying evidence;
-   identify earliest divergence;
-   require intervention prediction;
-   validate against unseen cases.

## 22.9 Orchestrator prior knowledge

Risk:

τ-bench is a public benchmark with a live leaderboard, and the τ-Knowledge paper
states the failure modes outright — that agents "struggle to retrieve the
correct documents from densely interlinked knowledge bases and to reason
accurately over complex internal policies." The orchestrator may reproduce those
findings from training data rather than discover them from evidence.

This threatens the central claim of §1 more directly than any other item in this
section. A signal that merely restates published knowledge, dressed in the
language of discovery, would look identical in the learning record to one
genuinely derived from trajectories.

Mitigation:

-   do not place the τ-Knowledge paper, the leaderboard, or summaries of either
    into the orchestrator's context;
-   require every entry under `discovered_signal` to cite the specific
    Introspection task and conversation identifiers it was derived from, with
    measured prevalence — §31's guardrail 8 already forbids a signal that is not
    grounded in inspected executions, and this is where that bites;
-   note in each learning record whether the signal is one the published
    literature already names, and report that honestly rather than suppressing
    it. A signal can be both independently derived and previously known; what
    cannot be claimed is discovery without grounding.

This threat is mitigated, not eliminated. Say so in the writeup.

## 22.10 Held-out enforcement is honor-system

Risk:

§12.3 asserts that test tasks and trajectories are inaccessible during
optimization. But the Improvement Orchestrator is Claude Code running on a
machine with shell access to the repository, the τ checkout, and
`data/simulations/`. Nothing structurally prevents it from reading the test
split; the constraint currently rests on instruction-following.

For a showcase this may be acceptable — but only if stated. An unstated
honor-system boundary presented as an enforced one is a misrepresentation of the
result.

Mitigation, in increasing order of strength:

-   state plainly that the boundary is procedural, and that §22.1's leakage
    mitigation depends on compliance;
-   keep test task IDs and test simulation output outside the working tree the
    orchestrator operates in;
-   run test evaluations from a separate session, project, or credential, so the
    orchestrator that proposed the change is not the process that scores it.

The third is the only one that is actually a boundary. Choose deliberately and
record which was used.

------------------------------------------------------------------------

# 23. Suggested Project Layout

There is **no separately implemented orchestrator agent in this MVP**.

**Claude Code itself is the Improvement Orchestrator**, using the Introspection plugin. In particular:

```text
Claude Code
    +
Introspection Plugin
    │
    ├── operate  → inspect live evidence, discover signals, diagnose
    ├── improve  → propose/implement repository-owned harness changes
    └── deploy   → activate a changed recipe/runtime when deployment is required
```

Therefore, the repository must not contain an `orchestrator/` directory that could be mistaken for another agent implementation.

The project should instead separate:

1. the **target agent** being improved;
2. the **benchmark integration** providing the external objective;
3. the **contract** defining the immutable rules and permission boundaries under which Claude operates;
4. the **results/artifacts** produced by successive improvement generations.

Conceptually:

```text
introspection-self-improver/
│
├── target-agent/
│   ├── <Introspection recipe files>
│   ├── prompts/
│   ├── skills/
│   ├── tools/
│   └── tests/
│
├── benchmark/
│   ├── tau_adapter/          # the seam (§11.1) — shape decided by the spike
│   ├── fidelity/             # Phase A.0 gate: stock LLMAgent, adapter vs native
│   ├── split_manifest.yaml   # three --task-ids lists (§12.0)
│   └── benchmark_lock.yaml   # exact commit + every frozen flag (§6.2, §14.1)
│
├── contract/
│   ├── protocol.md
│   ├── constraints.md
│   └── learning_record.schema.yaml
│
├── results/
│   ├── generation_000/
│   ├── generation_001/
│   └── ...
│
└── README.md
```

Do not invent exact Introspection recipe filenames until implementation checks the current platform specification.

## 23.1 Why `contract/`, not `orchestrator/` or `experiment/`

`orchestrator/` is incorrect because it suggests that the repository contains another software agent responsible for self-improvement.

It does not.

The Improvement Orchestrator is:

```text
Claude Code + Introspection Plugin
```

`experiment/` is also less precise because the directory does not primarily contain experimental runs or results. Those belong under `results/`.

`contract/` contains the **experimental and operational contract** that constrains Claude's improvement process.

It defines things such as:

```text
TARGET
- Improve the banking-support target agent.

OBJECTIVE
- Improve performance under the immutable τ-Knowledge evaluator.

FIXED
- target model and version
- user-simulator model and version
- retrieval config (tools AND policy text)
- τ-bench exact commit
- evaluator
- benchmark adapter
- discovery/validation/test split
- comparison budgets (--max-steps, --max-errors, --max-steps-seconds)
- seed and trial count

DISCOVERY
- Claude may inspect discovery trajectories and Introspection evidence.
- Claude may use the Introspection operate workflow to investigate them.

VALIDATION
- Validation is used to test whether a candidate generalizes.
- Validation must not silently become unrestricted discovery data.

TEST
- Test tasks and trajectories are inaccessible during improvement.
- Test is used only at predetermined checkpoints/final evaluation.

MUTABLE
- target recipe
- prompts
- skills
- tools/tool descriptions
- retrieval usage (query formulation, k, iteration, stopping)
- policy application
- orchestration
- tests
- justified diagnostic evals/judges

FORBIDDEN
- modifying the τ evaluator
- modifying benchmark tasks or gold state
- recomputing reward outside `tau2 evaluate-trajs`
- changing the target or user-simulator model during the main experiment
- changing --retrieval-config
- changing the task split
- changing execution budgets
- hardcoding benchmark answers
- redefining the external objective
```

These are not instructions implementing another meta-agent. They are invariants supplied to **Claude Code**, which is already the Improvement Orchestrator.

The relationship is:

```text
                   contract/
                       │
               defines boundaries
                       │
                       ▼
             ┌──────────────────┐
             │   Claude Code    │
             │        +         │
             │ Introspection    │
             │     Plugin       │
             └────────┬─────────┘
                      │
             Improvement Orchestrator
                      │
          ┌───────────┴────────────┐
          ▼                        ▼
       operate                  improve
          │                        │
          ▼                        ▼
  Introspection evidence      target-agent/
                                   │
                                   ▼
                              candidate recipe
```

## 23.2 Avoid duplicating the Introspection plugin

The contract should **not reimplement or unnecessarily duplicate the methodology already encoded by the Introspection plugin**.

For example, the current `improve` workflow already provides methodological guidance around:

- beginning from evidence;
- checking controls;
- seeking falsifying evidence;
- open-coding before imposing a taxonomy;
- finding the earliest meaningful divergence;
- determining the owning layer;
- establishing a baseline;
- changing one coherent mechanism at a time;
- freezing comparison configuration;
- inspecting traces behind score changes.

Those behaviors should remain owned by the plugin.

The `contract/` directory should contain only **project-specific invariants, goals, permissions, benchmark boundaries, and reproducibility requirements** that the generic plugin cannot know.

This separation is important:

```text
Introspection plugin
    = HOW Claude investigates and improves agents

contract/
    = WHAT Claude is allowed/required to optimize in this experiment

τ-bench
    = WHETHER the resulting target agent actually improved
```

## 23.3 `operate`, `improve`, and `deploy`

The inner loop should also distinguish recipe modification from deployment.

Conceptually:

```text
operate
   ↓
understand evidence
   ↓
improve
   ↓
modify/propose target recipe
   ↓
candidate recipe/version
   ↓
deploy, only when activation is required
   ↓
execute candidate
   ↓
operate
   ↓
inspect resulting evidence
```

`improve` should not be treated as synonymous with production deployment.

If the MVP can evaluate a candidate recipe directly without activating it as a production runtime, `deploy` does not need to participate in every inner-loop iteration.

Whether it can is decided by the seam spike (§11.1), not here. The development-attachment candidate keeps `deploy` out of the inner loop entirely but gives up per-generation version pinning; the endpoint-binding candidate puts `deploy` in every generation and buys that pinning back. Do not assume either until the spike reports.

Use deployment only when required by the actual Introspection execution path.

# 24. Generation Artifact Layout

Each generation should be reproducible.

Example:

``` text
results/generation_003/
│
├── manifest.yaml
├── benchmark-results/
│   ├── discovery.json
│   └── validation.json
├── evidence/
│   └── introspection-identifiers.json
├── learning-record.yaml
├── candidate/
│   ├── base_commit.txt
│   ├── candidate_commit.txt
│   └── diff.patch
└── decision.md
```

The exact raw Introspection evidence can remain in Introspection; local
artifacts should retain stable identifiers/URLs necessary to recover it.

------------------------------------------------------------------------

# 25. MVP Success Criteria

The MVP succeeds if all of the following are demonstrated.

## Functional

0.  The seam spike (§11.1) reaches its exit criteria, and the adapter fidelity
    gate (§15, Phase A.0) passes — first on `mock`, then on
    `banking_knowledge`. Nothing below counts until this does.
1.  τ `banking_knowledge` tasks execute against the Introspection target
    agent.
2.  Objective τ outcomes are captured, graded only by `tau2 evaluate-trajs`.
3.  Introspection captures useful execution evidence.
4.  Claude Code can use `operate` to inspect that evidence.
5.  Claude discovers at least one nontrivial actionable signal without
    being given its failure category.
6.  Claude uses `improve` to formulate a repository-owned harness
    change.
7.  The candidate can be evaluated under the same frozen configuration.
8.  The change can be accepted/rejected from validation evidence.
9.  The process can repeat for multiple generations.

## Scientific

The framing of this MVP is **showcase first** (§0). These criteria are stated at
the strength the sample sizes actually support; claiming more would not survive
contact with §12.0 and §17.2.

1.  At least one accepted change improves validation performance.
2.  Final harness outperforms G0 on held-out test tasks, reported with its N and
    an interval, alongside the full 97-task `base` score at both checkpoints and
    labelled per §17.1.1.
3.  The improvement cannot be attributed to model, user-simulator, evaluator,
    retrieval-config, or budget drift — each of which §14.1 freezes by flag
    name.
4.  Every accepted change has an evidence → hypothesis → mutation →
    result record, with every signal citing the Introspection task and
    conversation identifiers behind it.
5.  At least some discovered signals are predictive of successful
    interventions.
6.  Where an effect is smaller than the split can resolve, it is reported as
    directional rather than as a measured gain.

## Showcase

A viewer should be able to understand:

``` text
what the target did
↓
what Claude observed
↓
what Claude inferred
↓
what Claude changed
↓
why it expected improvement
↓
what happened on unseen tasks
```

------------------------------------------------------------------------

# 26. Recommended Initial Experimental Sequence

## Generation -1 --- seam spike and fidelity gate

Before any target agent exists:

-   run the seam spike to its exit criteria (§11.1);
-   record the chosen candidate back into §11.1;
-   pass the adapter fidelity gate on `mock`, then on `banking_knowledge`
    (§15, Phase A.0);
-   pin `benchmark_lock.yaml` and write `split_manifest.yaml`.

If the gate does not pass, the experiment does not start.

## Generation 0 --- baseline

-   create minimal Introspection target recipe;
-   freeze the full §14.1 set, target and user-simulator models included;
-   integrate τ `banking_knowledge` through the chosen seam;
-   run discovery baseline;
-   check it against the control-set floor (§13.1) — below ~20–25% pass on
    discovery, strengthen G0 and rerun rather than proceeding;
-   run validation baseline;
-   run the full 97-task `base` score once, as the G0 checkpoint number
    (§17.1.1);
-   preserve final test.

## Generation 1+

For each generation:

1.  Run current harness on discovery tasks.
2.  Give Claude the objective outcomes plus access to Introspection.
3.  Invoke `operate`.
4.  Require evidence gathering and controls.
5.  Let Claude discover the highest-value actionable signal.
6.  Produce a learning record.
7.  Handoff to `improve`.
8.  Require one coherent proposed mechanism.
9.  Preserve unchanged baseline.
10. Create candidate after approval.
11. Evaluate baseline and candidate **paired** on identical `--task-ids`,
    **interleaved** in one batch, at `--num-trials` ≥ 3.
12. Evaluate on validation the same way.
13. Inspect traces behind the score delta, and report pass^k alongside pass¹.
14. Accept or reject — or record as directional when the effect is below what
    the split resolves.
15. Record the decision, with cost and wall-clock.
16. Repeat.

Run hidden test only at predetermined checkpoints, not after every
speculative mutation. Run the full 97-task `base` score only at G0 and at the
final generation (§17.1.1).

------------------------------------------------------------------------

# 27. Later Experiments

These are explicitly **not MVP requirements**.

## 27.1 Cross-model transfer

After obtaining (H_0 `\rightarrow `{=tex}H_k), freeze (H_k) and change
the target model.

Compare:

\[ M_A + H_0 `\quad `{=tex}`\text{vs.}`{=tex} `\quad `{=tex}M_A + H_k \]

then:

\[ M_B + H_0 `\quad `{=tex}`\text{vs.}`{=tex} `\quad `{=tex}M_B + H_k \]

Question:

> Did the orchestrator discover general harness engineering knowledge or
> model-specific tricks?

## 27.2 Human-designed vs self-improved harness

Compare:

``` text
A. minimal baseline
B. human-engineered strong agent
C. autonomously improved agent
```

with the same model and benchmark.

## 27.3 Improvement-budget scaling

Measure:

\[ `\text{performance}`{=tex} =
f(`\text{meta-agent improvement budget}`{=tex}) \]

Examples:

-   meta-agent tokens;
-   number of candidate experiments;
-   wall-clock time;
-   dollar cost.

## 27.4 Harbor transfer

Reuse the same Improvement Orchestrator protocol on a Harbor benchmark.

Question:

> Does evidence-driven Introspection harness improvement transfer beyond
> knowledge-grounded customer support?

## 27.5 Weight evolution

Only after harness-only behavior is understood, consider SIA-like
model/weight updates.

At that point separate:

\[ `\Delta `{=tex}H \]

from:

\[ `\Delta `{=tex}W \]

and their interaction.

------------------------------------------------------------------------

# 28. Research Questions

Primary:

> **Can an LLM Improvement Orchestrator use Introspection's operational
> evidence to autonomously discover actionable failure signals,
> formulate hypotheses about an agent's behavior, and evolve its harness
> such that performance improves on unseen τ-Knowledge tasks?**

Secondary:

1.  What signals does the orchestrator discover without a human-defined
    failure taxonomy?
2.  Which discovered signals lead to interventions that generalize?
3.  Which harness layers are modified most often?
4.  Does harness complexity monotonically increase, or does the
    orchestrator also remove unnecessary scaffolding?
5.  How often do plausible diagnoses fail experimental validation?
6.  How many generations are required before improvements saturate?
7.  Do improvements raise pass¹ while reducing or increasing
    reliability?
8.  What is the cost/performance frontier across generations?
9.  Do discovered diagnostic evals become useful predictors of objective
    τ performance?
10. Do learned harness improvements transfer across target models?
11. Do they transfer across benchmarks/domains?

------------------------------------------------------------------------

# 29. Conceptual Contribution

The project is not simply:

> "Use Claude to optimize a prompt."

The intended contribution is:

> **An evidence-driven self-improvement loop in which an LLM
> autonomously learns both what is wrong with an agent and how to change
> the harness, using Introspection as the empirical and intervention
> substrate and an external benchmark as the immutable objective.**

There are effectively two coupled learning processes:

\[ H_0 `\rightarrow `{=tex}H_1 `\rightarrow `{=tex}H_2
`\rightarrow `{=tex}`\dots`{=tex} \]

and:

\[ E_0 `\rightarrow `{=tex}E_1 `\rightarrow `{=tex}E_2
`\rightarrow `{=tex}`\dots`{=tex} \]

where (H) is the target harness and (E) is the orchestrator's evolving
diagnostic model/instrumentation.

The external objective remains fixed:

\[ R\_`\tau`{=tex}(H_n) \]

This lets us distinguish:

-   **learning how to act**;
-   **learning how to diagnose**;
-   **actually improving according to external reality**.

------------------------------------------------------------------------

# 30. References and Source Material

## Introspection

-   Documentation: https://docs.introspection.dev
-   Work with repositories / self-improving agents:
    https://docs.introspection.dev/guides/work-with-repositories
-   Introspection plugin:
    https://github.com/introspection-org/introspection-plugin
-   `operate` skill source:
    https://github.com/introspection-org/introspection-plugin/blob/main/skills/operate/SKILL.md
-   `improve` skill source:
    https://github.com/introspection-org/introspection-plugin/blob/main/skills/improve/SKILL.md

Key verified facts from current plugin/docs:

-   `operate` owns inspection of live Introspection state and explicitly
    hands repository behavior changes to `improve`.
-   `improve` owns repository changes to behavior, prompts, tools,
    configuration, tests, evals, and judge definitions.
-   `improve` explicitly says to open-code evidence before imposing a
    taxonomy.
-   `improve` asks for falsifying as well as supporting evidence.
-   `improve` calls for an unchanged baseline and one coherent mechanism
    at a time.
-   Introspection recipes are repositories; explicit repository write
    grants can allow an agent to propose changes to its own prompts,
    skills, and tools.
-   Repository write access should be treated as a security-sensitive
    capability and normally gated through review/branch protection. The
    documented controls are required-review branch protection and a pinned
    production lane.
-   Endpoint bindings accept public DNS names over HTTPS only; IP addresses and
    localhost are rejected. Credentials are applied at the egress boundary and
    never enter the sandbox.
-   `introspection dev --mcp NAME=URL` repoints a declared MCP server at a local
    process for the life of the command; recipe extensions cannot be repointed.
-   Recipes may declare Python dependencies via `pi.runtime` with a
    `pyproject.toml` and a committed `uv.lock`.
-   Observations are generated automatically after roughly 30 minutes of
    conversation inactivity, with background scans on the order of every 10
    minutes; patterns are clusters over many observations and are regenerated
    periodically.
-   Tasks queue per organization according to plan limits, with no
    user-configurable concurrency setting.

## τ-bench / τ-Knowledge

-   Repository: https://github.com/sierra-research/tau2-bench (package
    `tau2-bench`; current release line τ³-bench — there is no `tau3-bench`
    repository)
-   τ-Knowledge paper: https://arxiv.org/abs/2603.04370
-   Agent Developer Guide:
    https://github.com/sierra-research/tau2-bench/blob/main/src/tau2/agent/README.md
-   Knowledge retrieval configs:
    https://github.com/sierra-research/tau2-bench/blob/main/src/tau2/knowledge/README.md
-   Current `banking_knowledge` domain: 97 tasks over 700+ knowledge documents,
    with two data sources — a `TransactionalDB` for user/account state and a
    `KnowledgeBase` for retrieval. Per-task averages of ~18.6 documents and
    ~9.52 tool calls are reported secondhand and should be confirmed against the
    domain data before being used to size a budget.
-   Reported difficulty: frontier models with high reasoning budgets reach only
    **~25.5% pass**, with reliability degrading sharply over repeated trials.
    Documented failure modes are retrieval from densely interlinked knowledge
    bases and reasoning over complex internal policies — see §22.9 for why this
    matters to the discovery claim.
-   `--retrieval-config` selects the agent's tool set **and** the domain policy
    text. Offline configs need no API keys; `terminal_use` / `alltools` require
    Anthropic `sandbox-runtime` plus ripgrep (and bubblewrap and socat on Linux).
-   Custom agents are a supported extension point: implement `HalfDuplexAgent`,
    register a factory, select with `--agent`; runnable examples in
    `examples/agents/`.
-   Splits are expressible as `--task-ids`; `--seed` defaults to `300`;
    `--max-steps` `200`, `--max-errors` `10`, `--max-steps-seconds` `600`.
-   v1.0.1 contains `banking_knowledge` grading/task corrections;
    pre-v1.0.1 and \>=v1.0.1 scores are not directly comparable. A `pre-v1.0.1`
    tag exists for reproducing the old behavior, and `tau2 evaluate-trajs
    --fresh-tasks` rescores old result files.
-   Installation requires `uv sync --extra knowledge` and Python
    `>=3.12,<3.14`.

## SIA

-   Repository: https://github.com/hexo-ai/sia
-   Paper: https://arxiv.org/abs/2605.27276
-   Relevant concept: generational self-improvement using a
    feedback/meta-agent, with harness updates and model-weight updates.
    This MVP isolates harness updates.

## Harbor

-   Repository: https://github.com/harbor-framework/harbor
-   Relevant concept: portable agent evaluation and optimization
    environments; useful as a later benchmark abstraction.

## Prime Agent

-   Article: https://www.primeintellect.ai/blog/prime-agent
-   Relevant concept: trajectory-grounded incremental harness refinement
    and keeping changes focused enough to validate.

## SquareDiff

-   Platform: https://www.squarediff.com/platform
-   Thesis: https://www.squarediff.com/thesis
-   Relevant concept: autonomous harness experimentation using
    evaluation performance and agent traces.

------------------------------------------------------------------------

# 31. Implementation Guardrail for Coding Agents

When implementing this specification:

1.  **Read the current Introspection documentation and plugin skill
    sources first.** Do not assume APIs, CLI syntax, recipe layout, or
    permission behavior from this document when current upstream
    documentation differs.
2.  **Pin τ-bench before generating results.**
3.  **Do not expose held-out test data to the Improvement
    Orchestrator.**
4.  **Do not pre-label benchmark failures with a human-created
    taxonomy.**
5.  **Do not let the orchestrator modify the immutable
    objective/evaluator.**
6.  **Do not change the target model during the main MVP experiment.**
7.  **Preserve stable identifiers linking every conclusion to actual
    Introspection evidence.**
8.  **Never fabricate an observed signal.** A signal must be grounded in
    inspected executions.
9.  **Require controls and counterevidence before promoting a
    correlation into a causal hypothesis.**
10. **Prefer one coherent harness mutation per candidate.**
11. **Run an unchanged baseline under the same configuration before
    claiming improvement.**
12. **Inspect trajectories behind score changes.**
13. **Record rejected hypotheses and failed mutations as first-class
    research results.**
14. **Treat recipe repository write access as privileged.**
15. **Keep the first implementation simple enough that the origin of
    performance changes remains interpretable.**
16. **Pass the adapter fidelity gate before producing any result.** Stock
    `LLMAgent`, adapter path versus native, same seed and task IDs. Grade only
    with `tau2 evaluate-trajs`; never reimplement the reward.
17. **Do not change `--retrieval-config`.** It rewrites the tool set and the
    policy text, so a change there invalidates every cross-generation
    comparison. Improve how retrieval is *used*, never which retrieval exists.
18. **Freeze the user-simulator model and the execution budgets**, not just the
    target model — both move scores with no harness change at all.
19. **Label every reported score with its split and its N**, and never present
    the full-domain number as a held-out result.

------------------------------------------------------------------------

# 32. Short Form

If an agent needs the project reduced to one paragraph:

> Build a minimal knowledge-grounded banking support agent as an
> Introspection recipe and evaluate it on a pinned subset of τ-bench
> `banking_knowledge`. First decide the seam between τ and Introspection by
> spike, then prove it: run τ's stock agent through the adapter and natively,
> and require the scores to agree before producing any result. Grade only with
> `tau2 evaluate-trajs`. Freeze the target model, the user-simulator model, the
> retrieval config, the execution budgets, the benchmark commit, the task
> splits, and the evaluator. Use Claude Code plus the Introspection plugin as an
> Improvement Orchestrator. Claude first uses `operate` to inspect τ failures
> and Introspection tasks, conversations, traces, tool calls, observations,
> patterns, and aggregate metrics — waiting for asynchronous analysis rather
> than reading an empty pattern list as a finding; it must discover useful
> failure signals from evidence rather than receive a predefined failure
> taxonomy, and every signal must cite the executions behind it. It then uses
> `improve` to identify the owning harness layer, formulate a falsifiable
> hypothesis, and propose one coherent change to the target recipe's prompts,
> skills, tools, retrieval *usage*, or orchestration — never to which retrieval
> mechanism exists, which is benchmark configuration. Compare the unchanged
> baseline with the candidate paired on identical task IDs, interleaved in one
> batch, over several trials; inspect traces behind score changes; report pass^k
> alongside pass¹; and accept, reject, or record as directional when the effect
> is below what the split resolves. Keep a hidden test set inaccessible during
> optimization, and report both the held-out score with its N and the full
> 97-task score labelled as contaminated. Preserve an evidence → signal →
> hypothesis → mutation → result record for every generation. The τ evaluator is
> immutable and remains the ultimate measure of success; Introspection
> diagnostics may evolve but cannot redefine the objective.
