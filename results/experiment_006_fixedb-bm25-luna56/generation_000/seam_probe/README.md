# Seam probe — which growth surfaces the bridge actually permits

Run 2026-08-16 at the g=0 transition, before composing gen-001's improvement set. Not a
mutation, never merged: a throwaway branch (`probe/extension-seam`, deleted) added one Pi
extension registering one trivial tool, and ran `make smoke` (mock domain, local lane).

## The question

`skills/sia/references/recipe-growth.md` states that extension tools and sub-agents "are
Pi-local: they never traverse the bridge, consume no τ steps". Seq 4's and seq 5's closures
both name the unused growth surfaces as the live hypothesis for why the loop fails, so seq 6
was going to spend a generation on one. Reading the seam first said the opposite:
`transport_local._assistant_turn` forwards **every** `toolCall` block in a Pi assistant
message, and `pi_agent._to_tau_message` passes an unmapped name through "as-is so τ reports
it as the invalid call it is."

## The answer — the reference is wrong

τ's trajectory for the probe episode (`probe_results.json`, message indices 2–3):

```
2 assistant calls=['probe_note']
3 tool      err=True :: Error: Tool 'probe_note' not found.
```

**A Pi-local extension tool call reaches τ as an invalid tool call.** It costs a τ step and
one of the episode's ten `max_errors`. The task still scored 1.0 — the probe was harmless at
one call per episode — but ten calls end the episode, and every one of them is recorded in
the graded trajectory.

## What this rules out, and what it leaves

| Surface | Verdict |
|---|---|
| Extension **tool** (`registerTool`) | **Illegal here.** Every call is a τ invalid-call + error. Measured above. |
| **Sub-agent** | **Illegal here.** Delegation goes through the auto-generated `agent` tool — a Pi tool call, so the same path. Not separately measured; same mechanism. |
| `tool_call` **blocking** of a τ tool | **Worse than illegal.** Pi blocks locally, but the call is still forwarded, so **τ executes the write anyway** while the agent is told it was stopped. Agent and grader histories diverge — the exact failure class seq 5 hit through in-flight POST loss. Inferred from the same forwarding mechanism the probe confirms; not run, because running it means letting τ execute a write the harness believed it had prevented. |
| Pi **skill** | Name + description reach the system prompt; the body loads on demand via `read`, which this agent deliberately does not have (`tools: []`). Inert for its body — the pre-existing trap #1, unchanged by this probe. |
| Extension **hooks that add no tool call** — `before_agent_start` (system prompt), `tool_result` (transform what the model sees after a τ tool returns), `context` (inject messages) | **Legal.** No toolCall block, nothing extra reaches τ. This is the structural surface seq 6 actually has. |
| `SYSTEM.md` `<instructions>` | Legal, as always. |

## Why this is recorded rather than fixed

Making Pi-local tool calls invisible to τ is **seam work**, not a harness mutation: it changes
what the adapter forwards, and the adapter's semantics are frozen for the experiment (root
`CLAUDE.md` invariants; `recipe-growth.md` trap 4). It is also not obviously desirable — the
current behaviour is deliberate ("τ reports it as the invalid call it is"), and hiding agent
tool calls from the graded trajectory is precisely the kind of adapter helpfulness that makes
a harness unmeasurable. So seq 6 works inside the constraint and the finding stands as a
result in its own right.

**It also re-reads two prior closures.** "The recipe's three growth surfaces remain unused"
was taken as evidence that the loop lacked ambition. Two of those three were never available.
