# 2026-08-18 — Phase 0, the ceiling probe (plan D36, runbook Phase 5.11)

Run between seq 10 (REVEALED) and the seq-12 freeze, under a **seq 11 PROVISIONAL lock**
(`011_ceiling-probe`) because probes need a lock to run under and seq 10's is frozen with a
committed snapshot fingerprint. Nothing here is a generation, and nothing here is reportable
as a curve.

**The question no prior experiment asked.** Seq 4, 5, 6, 8 and 10 each asked "did the score
go up" against an *unknown maximum*, so five nulls left *the loop failed* and *there was
nothing to find* equally alive. This probe measures the maximum.

## Result

| backend | H0 | H-expert | **harness headroom** | reachable / 35 |
|---|---|---|---|---|
| `bm25` | 28.6% | 35.2% | **+6.7 pp** | 23 |
| **`openai_embeddings`** | **23.8%** | **39.1%** | **+15.2 pp** | 24 |

Mean per-task pass rate, 35 tasks × 3 trials per arm, graded by `tau2 evaluate-trajs` via
`scripts/grade.py` against the retrieval config each run recorded. Never recomputed here.

### The three pre-registered decisions

Written and committed in `results/experiment_011_ceiling-probe/README.md` **before the first
episode ran**, and applied unchanged afterwards.

- **(a) Backend → `openai_embeddings`.** The rule is larger *harness headroom*, not larger
  absolute score, and the two disagree here: embeddings has the **lower** H0 (23.8% vs 28.6%)
  and more than **twice** the headroom. Choosing on absolute score would have frozen bm25 and
  halved the room the loop has to move in. This is the case the rule was written for.
- **(b) GO.** 15.2 pp against a 5 pp no-go bar.
- **(c) Envelope → REACHABLE.** The episode-level primary's smallest detectable effect
  (10.6 pp at B=30, 11.4 pp at the B=26 actually frozen) sits inside 15.2 pp. No trial
  increase was needed and no softer test was considered.

### Cost and health

**$12.82** total including preflights, against ~$16 budgeted. **416 / 420 episodes**
completed; **zero** stall warnings and zero sandbox seam counters across all four arms. The
four losses are the luna user-simulator empty-completion signature (`UserMessage must have
either content or tool_calls`) — frozen-surface weather, resumed rather than investigated.
`task_064`'s single missing episode is immaterial: 0/3 in **both** embeddings arms, so the
most it could do is move headroom to +16.2 pp.

## What H-expert is, and what it is not

A harness hand-built with full access to the candidate tasks and unlimited effort, **never
shipped, never tagged, never part of any loop**, existing only to bound the range. Built on
throwaway branches, deleted after this probe; the source is preserved in `h-expert/` and the
arm commits in `h-expert/ARM_COMMITS.txt` so the ceiling is reproducible without them.

It respects every frozen surface: no `<policy>` edit, no model or thinking-level change, no
`read`/`bash` capability, no runtime reach into `benchmark/vendor/`, and **no gold values,
document ids or per-task procedure anywhere**. Two halves, because a prompt-only expert would
understate the ceiling for the reason this project has measured four times — an instruction
added to a prompt does not inherit the scope its author reasoned about:

- **`<instructions>`** — a full operating procedure: enumerate the customer's requests before
  acting; order additive actions before removals; search for the *rule* not the answer; for a
  choice among bank-defined named options retrieve the full candidate list and the
  per-candidate attributes the customer's requirements refer to, then filter-then-rank in the
  stated order; copy every exact string verbatim; hand the tool contract over in full; read
  the call back before sending.
- **a `tool_result` extension hook** — the same discipline delivered where it is used, after a
  `KB_search` return, plus a completed-state note after a state-changing call pointing at the
  customer's remaining requests. Host facts cited; injection verified present in session logs
  (69 occurrences in the first preflight) before any behavioural number was read.

### It was aimed by measurement, and re-aimed twice by measurement

Seq 10 established that **88% of gold actions at H0 were already the right tool**, with the
failures concentrated in *which value was chosen*. Three preflight rounds then found two
general, harness-reachable mechanisms that the first build got wrong:

1. **Rank on the figure that applies to THIS customer.** The expert compared candidates
   correctly and still lost, because it ranked on the headline "on all purchases" rate while
   the rate that decides sat in a second document keyed to the spending category the customer
   named. The tell is in the text the agent already had — a phrase like *outside top
   categories* says a better category rate exists somewhere.
2. **Order additive actions before removals.** On a close-an-account-and-open-another task the
   expert identified the correct account class and then declined to open it, because personal
   savings accounts need an active checking account of a given tenure and the only remaining
   checking account was ten days old — it had closed the older one first. **The closure
   destroyed the eligibility for the other half of the same request list.**

## The finding the probe did not set out to make

**H-expert regresses tasks H0 passes, and that means this ceiling is a lower bound.**

| backend | tasks improved | flat | **regressed** | gross gain | gross loss | net |
|---|---|---|---|---|---|---|
| `bm25` | 14 | 14 | **7** | +17.1 pp | −10.5 pp | +6.7 pp |
| `openai_embeddings` | 16 | 14 | **5** | +21.0 pp | −5.7 pp | +15.2 pp |

Two opposite modes, both classic over-instruction, sharpest under bm25: **over-work**
(`task_002` 2/3 → 1/3 at 24–25 tool calls against H0's 5–11) and **under-work / early stop**
(`task_015` 2/3 → 0/3 in 14–17 messages against H0's 22–43). `task_005` 3/3 → 0/3 is the
sharpest: **both** arms transfer to a human on all three trials — it is a gold-transfer task —
so the expert did not refuse to act, it transferred *differently*, which points at the
transfer-reason enum. The overall transfer rate barely moved (27% → 29%), so this is
concentrated rather than a global suppression epidemic.

Two consequences worth carrying:

- **The measured headroom understates the true ceiling.** A ceiling harness that breaks tasks
  H0 passes is measuring its author's drafting error alongside the objective's room. The
  gross-gain column is the more honest upper bound: **+21.0 pp** under embeddings.
- **The ceiling probe reproduced, inside itself, the most-replicated lesson this project
  has.** A long, carefully-reasoned instruction block does not inherit the scope its author
  reasoned about — measured here for the fifth time, now on a harness written specifically by
  someone who knew that.

Per the pre-registration, H-expert was **not** rebuilt: that repair was committed to only if
the envelope gate failed, and it passed with margin.

## The other unplanned result: a third identical-harness noise measurement

33 of the 35 candidates were screened on 2026-08-17 (`../2026-08-17-seq10-screen/`) under a
recipe whose `target-agent` tree hash is byte-identical to this probe's H0/bm25 arm and to
`h0-baseline` — `50ac0d6729e9e3a55ce51b97e977a9f85073f0ab`, verified all three. Same model
pair, same backend, same trial count, one day apart:

| | seq-10 screen | Phase 0 arm 1 |
|---|---|---|
| passing cells (33 × 3) | 26 | 29 |
| mean per-task rate | 26.3% | 29.3% |

**12 of 33 task rates moved** — 7 up, 5 down, net +3 cells, **+3.0 pp aggregate drift on no
change at all**; largest single-task swing 2 cells. This replicates seq 10's identity-round
finding (14 of 36 trial cells flipping on a byte-identical harness, round total nearly
unchanged) on a different and larger task set, with gains and losses again very nearly
cancelling. It is the third independent measurement of the floor and the largest, and it
re-earns the standing attribution rule: *one cell is noise, two is suggestive, and nothing is
attributable without its own mechanism counter moving in the predicted direction.*

## Method

- **Arms**: four, each 35 tasks × 3 trials on the local lane (work-tree-faithful; the platform
  lane pins the recipe to pushed main and cannot serve a branch). Run from committed branch
  states so `arm_sha` records real lineage.
- **Candidate pool**: the 54 batch-eligible tasks from Phase 5.11, filtered by **one
  outcome-independent criterion** — ≤ 9 gold actions, the seq-10 screen's recorded productive
  band. τ's frozen `max_steps: 200` and 600 s timeout make a 25-to-37-gold-action task a
  *budget* wall rather than a harness one, and carrying tasks where both arms fail for reasons
  no mutation can reach would deflate headroom toward a false no-go. 35 remain. Verified
  disjoint from the intended held-out 36, from `task_034`, and from the six proven walls.
- **`text-embedding-3-large`, not by preference.** τ² pins every `openai_embeddings*` variant
  to that model in its own config map; `text-embedding-3-small` is not a published retrieval
  config. Selecting it would mean editing the vendored benchmark — `--retrieval-config` is a
  frozen surface — and would forfeit the comparability with published numbers that earns
  embeddings its pre-registered tie-break. Decided with the user, 2026-08-18.
- **Backend switching** sets `benchmark.retrieval_config` and runs `make policy`, which moves
  the frozen `<policy>` region by exactly one line (the sentence naming the retrieval
  mechanism) and updates the lock's policy hash. The tool surface is unchanged at 15 tools.

## Raw evidence

`arms/<arm>/` — `episode_manifest.jsonl` (per-episode reward, cost, incident counters,
`arm_sha`), `run_metadata.json` (freeze fingerprint, launcher argv, toolchain), and
`reward_extract.json` (per-episode reward, termination, message count, db_check and
per-action match verdicts, extracted from the multi-megabyte `results.json` each run carried).
`headroom_bm25.json` / `headroom_openai_embeddings.json` — the `scripts/headroom.py` verdicts.
`h-expert/` — the ceiling harness source and its arm commits.

Run directories were written under the probe's own tree
(`results/experiment_011_ceiling-probe/generation_000/`) and deleted after extraction, per the
convention in `../README.md`: 325 MB of session logs is not a committable record.
