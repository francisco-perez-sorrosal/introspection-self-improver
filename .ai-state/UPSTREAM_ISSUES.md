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
