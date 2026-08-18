# Experiment 012_ceiling-emb-luna56 — FROZEN 2026-08-18, unstarted

The first freeze in this project's history that knows **how much room it is playing for**.

Seq 4, 5, 6, 8 and 10 each asked *"did the score go up"* against an unknown maximum, so five
nulls left *the loop failed* and *there was nothing to find* equally alive. Phase 0 (seq 11,
PROVISIONAL — `benchmark/probes/2026-08-18-phase0-ceiling-probe/`) measured the maximum
before this lock was cut.

## The freeze

| | |
|---|---|
| generations | **G = 7**, `identity_generations: [1]` — six mutation slots |
| held-out schedule | **`heldout_generations: [0, 4, 7]`** — baseline, midpoint, endpoint |
| batch | **B = 26**, `batch_mode: fixed`, `allow_within_batch_verification: true` |
| held-out | **T = 36**, forced — the whole never-batched remainder of the pool |
| trials | 3, both lanes (D18, one knob) |
| backend | **`openai_embeddings`** (`text-embedding-3-large`, as τ² publishes it) |
| model pair | `openai/gpt-5.6-luna` on both halves |
| autonomy | `require_human_approval: false` (D23 envelope, ratified) |
| primary | `scripts/endpoint_test.py` — within-task permutation on EPISODE outcomes, `batch_08` vs pooled `batch_01`+`batch_02`, reported as **gap-closure against the measured ceiling** |
| secondary | held-out endpoint H7 − H0 against its band, with H4 as a midpoint read |

## What Phase 0 decided

| backend | H0 | H-expert | **harness headroom** |
|---|---|---|---|
| `bm25` | 28.6% | 35.2% | +6.7 pp |
| **`openai_embeddings`** | **23.8%** | **39.1%** | **+15.2 pp** |

The backend rule — freeze the larger *harness headroom*, never the larger absolute score —
earned its keep on first use: the two criteria **disagreed**, embeddings carrying the *lower*
H0 with more than twice the headroom.

**Consequence, accepted and stated wherever a number from this experiment is reported:**
`--retrieval-config` rewrites the tool set *and* the graded policy text, so seq 12's absolute
numbers **do not compare to seq ≤ 10**. Gap-closure against the measured ceiling is what
normalizes them, and is why the primary reports that way.

## The batch, and why it is 26

Composed from the probe as an **empirical reachability oracle** — a task H-expert passes is
*provably* harness-reachable, which is far stronger than reading a trajectory and guessing.

| stratum | n | tasks |
|---|---|---|
| anchor (H0 3/3) | 3 | `task_006` `task_032` `task_063` |
| marginal (1/3–2/3) | 12 | `task_001` `task_003` `task_005` `task_008` `task_010` `task_015` `task_023` `task_024` `task_029` `task_037` `task_057` `task_076` |
| headroom (H0 0/3, H-expert passes) | 11 | `task_002` `task_004` `task_014` `task_046` `task_055` `task_056` `task_058` `task_060` `task_061` `task_065` `task_094` |

**53 reachable failing cells at H0**, against seq 10's 17 and seq 8's ~5 — and the first
headroom stratum this project has admitted on *proof* rather than on a guess. No walled task.

**B = 26 rather than the designed 30**: only 26 of the 35 candidates earned a certificate, and
the pre-registered composition rule says shrink (floor 24) rather than admit a wall. One
widening, made with numbers visible: the rule's letter says "exclude any task H-expert never
passes", which would have dropped `task_063` (H0 **3/3**) and `task_010` (H0 2/3) as walled —
calling a task H0 passes every time unreachable is false, so the certificate is read as
*either arm* passing. Two tasks; no verdict changed (the strict letter gives B=24, also inside
the envelope).

## Power

`gates/power_envelope.json`: 156 baseline vs 78 endpoint episodes → SE 6.93 pp, **11.4 pp
detectable at α**, inside the measured 15.2 pp headroom → **REACHABLE**.

Recorded rather than smoothed: **80% power would need 17.2 pp**, which the headroom does not
cover. The design can detect a full-headroom effect at α; it is not powered to do so reliably.

## Gates — all PASS, all committed before any graded episode

| gate | verdict | where |
|---|---|---|
| A.0a (adapter suite + mock smoke) | PASS — 445 tests | `generation_000/gates/a0a.json` |
| platform seam canary | PASS — bridge park max 0.7 s | `gates/seam_canary.json` |
| D24 suppression canary | PASS — no findings | `gates/suppression_canary.json` |
| power envelope vs measured headroom | REACHABLE | `gates/power_envelope.json` |

The suppression canary's first attempt FAILed with 3/3 episodes dead at zero messages — *"The
connected local Recipe has no matching ready Runtime version"*. The commit was pushed but its
image was still building. An extension **load** failure is fatal before any model call and
presents identically; what separated the two was the local lane, where `pi_local_calls = 1` on
3/3 mock episodes with rewards 1.0. Retried after the build: PASS. Worth knowing, because it
looks like a seam defect and is not.

## H0

`h0-baseline` re-tagged at `f157fab` to carry the embeddings `<policy>` region. The **mutable
surface is byte-identical** to the prior anchor — `agents/agent.yaml`, `package.json`, all
three inert zero-state templates, and `SYSTEM.md`'s `<instructions>` all verified unchanged.
H0's harness did not change; only the frozen benchmark text it carries moved.
`make reset_h0` reports byte-identity.

## Status

**Nothing has been run.** The next action is H0's held-out round (`make heldout
GEN=generation_000`), then `batch_01`. The cadence is mechanical: `run.py` refuses a batch
whose generation is unmeasured, and the held-out runner refuses to measure H_N before
`batch_N` is graded and its record accepted.
