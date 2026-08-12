# target-agent — the harness under improvement (H_n)

This Recipe is the only thing in the repository that the improvement loop is allowed to
change. Everything it needs to do its job — the banking tools, the knowledge search, the
domain policy — arrives from τ²-bench at run time. Nothing here imports or references
`benchmark/`, so the package can be split out into its own repository when the agent is
eventually granted `contents: write` on it.

## What is mutable, and what only looks mutable

| Surface | Status | Why |
|---|---|---|
| `SYSTEM.md` `<instructions>` block | **mutable** | The harness prompt. This is where a generation's change usually lands. |
| `SYSTEM.md` `<policy>` block | frozen | Verbatim `env.get_policy()` for the locked domain and retrieval config. Written by `make policy`; the pre-commit hook and CI reject any commit that alters it. |
| `agents/agent.yaml` `ai.model`, `ai.thinking_level` | frozen | Comparison variables. Raising either would improve the score without improving the harness. Checked against `benchmark/benchmark_lock.yaml` before every run. |
| `agents/agent.yaml` `tools`, `skills`, `subagents`, `session` | mutable | Genuine harness structure. |
| `package.json` `pi.skills`, `pi.extensions` | mutable | Adding a skill is a legitimate mutation, and an explicit `[]` makes it a visible diff. |
| `package.json` `pi.mcp` | frozen | The τ tool surface is benchmark configuration (`--retrieval-config` decides it). |

The split inside `SYSTEM.md` deliberately reproduces τ²'s own system prompt
(`src/tau2/agent/llm_agent.py`), which is `<instructions>` followed by `<policy>`. The
mutable/frozen boundary falls exactly where τ's template boundary already falls.

## Generation 0

Intentionally unsophisticated (§13). It is told to act as a bank support agent, to search
the knowledge base rather than answer from memory, to use the banking tools, to report what
it did, and — mirroring τ²'s own `AGENT_INSTRUCTION` — that a turn is either a message or a
tool call but never both.

It is deliberately *not* given query decomposition, synonym expansion, retrieve-plan-execute
loops, policy extraction, self-verification, or subagents. Those are structures the
improvement orchestrator may discover from evidence; handing them over up front would be
planting the answer.

`tools: []` is not minimalism for its own sake. A locally-hosted Pi session runs with this
repository as its working directory, so granting `read` or `bash` would put τ's task
definitions and gold state in `benchmark/vendor/` within the agent's reach.

## Running it

The Recipe cannot run on its own: `pi.mcp` declares `tau` as `required`, so a session fails
closed until the τ tool bridge is listening. Drive it through the benchmark instead:

```bash
make smoke     # one mock-domain task, end to end, graded by tau2 evaluate-trajs
```

See the repository README for the two transports (local Pi versus the development lane) and
what evidence each one produces.
