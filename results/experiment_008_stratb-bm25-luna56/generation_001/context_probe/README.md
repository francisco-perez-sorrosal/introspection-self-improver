# Step-4b surface probe, g=1 — the `context` hook on the real domain

Fired by protocol step 4b's second trigger: gen-002's D2 names a surface this experiment has
not exercised. `context` was the last hook `skills/sia/references/recipe-growth.md` still
listed as legal by **inference** — `before_agent_start` was measured at probe P1 and
`tool_result` at seq 8's g=0 probe, leaving this one unmeasured while a mutation slot was
about to depend on it.

Mutation lived on throwaway branch `probe/context-hook` (deleted, never merged). Lane:
local, the work-tree-faithful lane. Task: `task_014`, 3 trials, twice, the frozen
configuration. `introspection check` green before each run.

## The three questions

**1. Does `context` fire, and what shape are the messages?** **Yes — 19 firings in one
3-episode run**, once before each LLM call, with `event.messages` growing 1, 3, 5, … 15 as
the conversation extends. A session message is `{role, content, timestamp}` with `content`
an **array** of blocks. Injections do **not** accumulate: `alreadyMarked` was false on every
firing, so each call sees the unmodified list and the hook's output is per-call only.

**2. Can an APPENDED message reach the model?** The documented example only *filters*
messages, and appending is the operation D2 needs, so it was tested directly — and the first
attempt showed why a marker file is not enough: the injected text appeared **0** times in
the Pi session files, because `context` modifies the outgoing payload rather than the stored
session. Absence there proves nothing.

A second run replaced the marker with a behavioural instruction — begin the next customer
message with the token `ZANZIBAR7`. **The token appears 3 times in tau's graded trajectory,
one per episode.** The model obeyed an appended context message in 3/3 episodes. Appending
works.

**3. What reaches tau?** The injected message itself: **0 occurrences** in the graded
trajectory. Only the model's *response* to it appears — which is correct and is the
asymmetry to design against: unlike `tool_result`, a `context` injection is invisible to
grading but its **behavioural effect is fully visible**, because the agent's output is what
tau grades. That is the intended shape for a harness change, not a leak.

Rewards were 1.0 / 1.0 / 0.0 and 1.0 / 1.0 / 0.0 across the two runs — `task_014`'s ordinary
marginal spread, carrying no information about the hook, and recorded rather than read as a
finding.

## Verdict

`context` is **measured functional on the banking domain, local lane** (CLI 0.28.0 / Pi
0.84.1 / recipes 0.19.3): it fires before every LLM call, sees the full conversation
including user messages, and an appended message changes model behaviour. Every hook this
project can use is now measured rather than inherited.

Practical notes for anything built on it: derive the injected message's shape from an
observed message rather than assuming one (this probe clones the last user message and
strips `id`/`timestamp`); expect the hook to fire on every call, so make the injection
idempotent or condition it; and remember the effect is graded even though the injection is
not.

## Raw evidence

`hook_firings.json` (all firings with message counts, trailing roles, and observed message
shape), `verdict.json` (the counts above, computed from the artifacts rather than asserted),
`episode_manifest.jsonl` and `run_metadata.json` from the behavioural run. Both run
directories were deleted after extraction, per the probe convention. Run ids appear here as
probe evidence only, never as record provenance.
