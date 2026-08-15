# Upstream Issues

Append-only log of issues this project has filed against upstream dependencies.
Grep here before recommending a new filing (`upstream-stewardship` skill).

## sierra-research/tau2-bench#470 — text-mode user-sim empty-completion crash

- **Filed:** 2026-08-13 · **Status:** open, fix PR submitted
- **URL:** https://github.com/sierra-research/tau2-bench/issues/470
- **Fix PR:** https://github.com/sierra-research/tau2-bench/pull/471 (2026-08-13) —
  retry the empty completion once with a system-prompt reminder (pointing at the
  `###STOP###` out), raise descriptively on double-empty; tests mock `generate`.
  Branch `fix/user-sim-empty-completion` on the `francisco-perez-sorrosal` fork.
- **Summary:** In text mode, a scenario instructing the simulated user to speak and
  fire a tracking-only user tool in one turn can crash the episode: the orchestrator
  routes the tool call to ENV before the agent sees the verbal half, the post-tool
  utterance comes back empty at the framework-default `temperature: 0.0`, and
  `UserMessage.validate()` books it as `infrastructure_error`. Confirmed 16/16 on
  `banking_knowledge/task_034` across the stock `llm_agent` and this project's Pi
  harness; text-mode sibling of upstream's voice fix #440; related to #234.
- **Local workaround:** `task_034` excluded from the seq-2 experiment partition
  (`benchmark/split_manifest.yaml` header documents it); failed episodes persist τ's
  recorded root cause onto their manifest row, and the held-out completeness report
  names failure classes reward-free.
- **Unblock condition:** an upstream release that survives empty user-sim completions
  (treat as pass-turn / retry / drop, per the issue's candidate resolutions) would let
  a future freeze re-admit the excluded task class.

## introspection platform — sandbox Pi sends `reasoning.level` to OpenAI `/v1/responses`

- **Reported:** 2026-08-14 (relayed to the Introspection CTO through the user; no
  public tracker) · **Status:** open, blocking the platform lane
- **Summary:** For a recipe with `model: {name: openai/gpt-5.6-luna, thinking_level:
  medium}` — the format the CTO confirmed current — the platform sandbox's Pi issues
  `{"model": "gpt-5.6-luna", "reasoning": {"level": "medium"}, "stream": true}` to
  `https://api.openai.com/v1/responses`, which OpenAI rejects with 400
  `Unknown parameter: 'reasoning.level'` (the current parameter is
  `reasoning.effort`). Every platform episode dies at the first model call
  (`termination=infrastructure_error`, 0 messages). Local Pi 0.84.1 with the
  identical recipe maps correctly (29 clean episodes: 28-task calibration pilot +
  mock smoke). Freshly-baked runtime images (same day) reproduce it, so it is the
  current sandbox stack, not a stale image.
- **Evidence:** conversations `01a00281-67ea-7131-8088-2ae87a483d5b` and the
  2026-08-14T16:40Z warm-ups (dev env, runtime `target-agent`; span item[1] carries
  the request body and `error {type: 400}`, `byok: false`). Direct API repro:
  `reasoning:{level:"medium"}` → 400; `reasoning:{effort:"medium"}` → 200 on
  `gpt-5.6-luna`.
- **Also observed:** the published agent-YAML docs (`recipes/agent-yaml`) describe an
  `ai:` vocabulary that Recipes 0.19.3 (newest compatible, per `introspection
  upgrade`/`doctor`) rejects with `agent.key_unknown` — docs ahead of the shipped
  checker; the CTO's guidance is to stay on the legacy `model:` spelling meanwhile.
- **Local workaround:** none acceptable — dropping `thinking_level` would fork the
  harness between lanes mid-experiment. The local lane (held-out rounds) is
  unaffected; improvement batches (platform lane) stay blocked.
- **Update 2026-08-14 (later):** omitting `thinking_level` from the recipe does NOT
  work around it — the sandbox applies Pi's default (medium) and serializes it through
  the same path (verified: conversation `01a002ac-996e-732a-ab50-e20c94e2a050`, request
  body identical with the field absent). The defect therefore breaks EVERY `openai/*`
  model on the platform unconditionally; no recipe-side workaround exists.
- **Update 2026-08-14 (Anthropic control):** the same recipe/runtime with
  `anthropic/claude-haiku-4-5` + `thinking_level: medium` completes a platform episode
  cleanly — graded, `evidence_complete`, `arm_sha_ok`, zero seam incidents, $0.218
  conversation billing (task `01a002d9-68a6-765c-acbd-f6eb3795440e`). The defect is
  therefore isolated to the sandbox Pi's OpenAI request path; everything else in the
  platform lane is healthy.
- **Unblock condition:** a sandbox Pi (or gateway request-shaping) release mapping
  `thinking_level` → `reasoning.effort` for OpenAI models; re-verify with
  `make single_task TRANSPORT=platform TASK=task_001`.
