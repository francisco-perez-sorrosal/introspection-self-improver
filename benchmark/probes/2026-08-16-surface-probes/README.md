# 2026-08-16 surface probes — skill declaration, `before_agent_start` hook, platform lineage

Run between seq 6 (REVEALED) and the next freeze, per the seq-6 independent review § 8.2:
buy the missing measurements so every surface verdict in
`skills/sia/references/recipe-growth.md` is measured, not inherited. Probe mutations lived on
`probe/surface-instrument` and `probe/skill-decl` (deleted, never merged). Instrument: a
recipe-declared `before_agent_start` extension (`extensions/probe-instrument.ts`) appending
one JSON record per firing — composed-prompt length/SHA-256/head, marker searches, and
`getAllTools()` — to `$TMPDIR/sia-probe-instrument.jsonl`, returning `undefined` (prompt
unchanged). Stack measured: `introspection` CLI 0.28.0, Pi 0.84.1, recipes 0.19.3, local
launcher `pi --recipe … --mode rpc`.

## P1 — `before_agent_start` hook: measured LEGAL and functional (real domain, local lane)

Runs: mock smoke (3 sims, all reward 1.0) and banking `task_001` local (trial 0 reward 1.0;
trials 1–2 died to the known user-sim empty-completion flake, unrelated — see P5).

- The hook **fired in every session** (mock: 4 records / 3 sims; banking: 14 records /
  3 sims — at least once per session and more than once during a session; every record in a
  run identical). It **saw the fully composed prompt**: banking prompt = `SYSTEM.md`
  byte-exact (6,571 chars = the 6,572-byte file minus trailing newline); mock = the
  materialized mock `SYSTEM.md` (1,116 chars). Returning `undefined` left the prompt
  unchanged (stable SHA across firings and trials).
- **Zero τ-side visibility**: trajectories carry only τ tool calls (`KB_search` ×3 +
  `apply_for_credit_card` in the graded banking trial), no errors, normal bridge traffic,
  reward 1.0.
- `getAllTools()` at hook time: Pi built-ins (`read`, `bash`, `edit`, `write`, `grep`,
  `find`, `ls`), `agent`, and the τ MCP tools as `mcp_tau_<name>_<hash>`. **Registered ≠
  model-callable** — the `tools: []` allowlist still governs what the model can invoke.
- Repo `CLAUDE.md`/`AGENTS.md` context-file discovery did **not** reach the prompt.

## P2 — declared skill: measured INERT-AS-DECLARED on this seam's local lane, overturning both prior beliefs

Declaration (probe branch): `skills/probe-skill/SKILL.md` (valid frontmatter; description
crafted to match `task_001` so any injected read-instruction would be exercised) +
`pi.skills` entry + `agent.yaml skills: [probe-skill]`; `introspection check` green.

- Banking local, read-less (`tools: []`): the effective prompt is **exactly `SYSTEM.md`** —
  no `<available_skills>` block, no skill name, no read-tool instruction (the sole "read
  tool" grep hit is `SYSTEM.md`'s own policy text). Trajectory: zero `read` attempts;
  graded trial reward 1.0.
- Mock discriminator, read **granted** (`tools: [read]`, mock domain only, throwaway
  branch): **still nothing injected** (prompt = mock `SYSTEM.md`, 1,116 chars), and the full
  Pi session file contains **zero** occurrences of `probe-skill` or `available_skills`.

**Verdict:** on this seam's local lane (recipes 0.19.3 host, rpc mode), a recipe-declared
skill reaches *nothing* — not the prompt, not the session — with or without `read`. This
overturns (a) the pre-2026-08-16 trap-1 claim that the *description* surfaces ("inert as
designed" was right about inertness, wrong about the mechanism), and (b) the 2026-08-16
upstream-code-derived correction that declaration injects an adverse read-tool instruction:
Pi-core's `formatSkillsForPrompt` behaves that way in Pi-core sessions, but the behavior does
not manifest through this host path. Skill-shaped content reaches a graded episode only via
deterministic hook injection (P1's surface). Platform-host behavior: unverified (see P3).

## P3 — platform lane pins the recipe to pushed main; `--allow-dirty` does not serve your branch

`make single_task TRANSPORT=platform` on the probe branch refused: *"HEAD (6027324…) is
ahead of origin/main (4c36b1d…), and the platform pins lineage to pushed main."* Re-run with
`--allow-dirty`: 3 episodes completed (rewards 1.0, $0.018 total) — every one carrying
`recipe_git_commit_sha = 4c36b1d` (**pushed main, pre-reset, without the probe extension**),
all rows `arm_sha_ok=false`, and the runner's closing arm assertion naming the three
conversations (`01a00bf3-3ee4-76d4-8c9e-85ccb884ad80`, `01a00bf3-ce3d-7560-803c-b2dd1233dc91`,
`01a00bf4-8705-713f-ae8b-63c8c6fe6adf`). Those episodes measured the wrong recipe and ground
no hook claim; they are kept as evidence of the lineage rule itself.

**Verdict:** pre-push platform verification of a recipe change through the τ runner is
impossible; the local lane is the work-tree-faithful probe lane. Platform-side verification
of a landed recipe change happens post-push (e.g., the seam canary). Encoded in protocol
step 4b and `recipe-growth.md` trap 7.

## P4 — ambient exposure (partial)

The local-lane tool catalog carried no ambient-registered tools in any run (repo
`.pi/extensions/traces.ts` registered nothing tool-shaped in-session); ambient *hook*
execution was not directly measured. Embedded Recipe sessions disable ambient surfaces by
default (upstream); whether the platform sandbox uses that host remains unverified. This
`pi` build offers `--no-extensions` / `--no-skills` / `--no-context-files` if lane-parity
hardening is ever wanted — adopting them is a freeze-level launcher change that must
re-verify recipe-declared surfaces still load under the flags.

## P5 — operational notes

- 2/3 local banking trials terminated `infrastructure_error` with the known user-simulator
  empty-completion signature (`UserMessage must have either content or tool_calls`) — the
  class `make weather` probes; unrelated to the instrumentation (the identical recipe's
  trial 0 was clean).
- Node's `os.tmpdir()` on macOS resolves to `$TMPDIR` (`/var/folders/...`), not `/tmp`.
- `make smoke` writes to the committed `generation_000/mock_smoke/` path — probe smokes
  clobbered it in the working tree (restored from git). Hence the SUFFIX convention in
  `../README.md`.

## Raw evidence

`probe_hook_platform/` (wrong-arm platform manifest + run metadata) ·
`probe_skill_local/` (banking local manifest, run metadata, sim extract) ·
`discriminator_mock/` (mock manifest, run metadata, instrument marker records for the
read-granted discriminator). Earlier runs' marker values are transcribed above; run
directories were removed from the closed seq-6 tree per the convention.

## P6 — D24 suppression demo: measured end-to-end (post-landing)

After the D24 seam change landed (`seam(D24)` commit), a throwaway branch
(`probe/suppression-demo`, deleted) registered one extension tool (`probe_note`),
allowlisted it in `agent.yaml tools:` (the registry), and instructed the mock-domain agent
to call it before its first τ call. Local lane, 3 sims:

- **All three episodes called `probe_note` and τ never saw it** — trajectories carry only
  τ's own tools (`get_users`, `create_task`), all rewards 1.0, no invalid calls, no
  `max_errors` spend.
- Evidence stream intact: each episode's assistant `raw_data.pi_suppressed_tool_names`
  carries the call; manifest rows derive `pi_local_calls: 1`; `run_metadata.json` records
  `pi_local_tools: ["probe_note"]`.

The exact call class that cost a τ step and one of ten `max_errors` in the seq-6 seam
probe is now invisible to grading and fully visible to diagnosis. Raw:
`suppression_demo/`.

## P7 — post-push platform canary: the D24 adapter PASSes on the real seam

After main (`36fe5ee`) and the re-anchored `h0-baseline` were pushed, `make gate_seam` ran
one platform-lane episode against the pushed arm: **PASS** — the graded trial completed at
reward 1.0 with `arm_sha_ok: true`, `recipe_git_commit_sha = 36fe5ee`, all four sandbox
seam counters zero, evidence complete, and `pi_local_calls: 0` (H0's registry is empty, so
suppression correctly never engaged — the pump path ran, nothing was suppressed). Two
trials died to the known user-sim empty-completion weather (`ValueError` ×2, τ-excluded,
non-gating — the same class as P5). The fresh verdict is preserved here
(`platform_canary/`); the closed experiment's committed `gates/seam_canary.json` and
`generation_000/seam_canary/` were restored from git per the probes convention.
Platform-side verification of suppression *engaging* (a non-empty registry) is the next
experiment's post-merge territory, per protocol step 4b and recipe-growth trap 7.
