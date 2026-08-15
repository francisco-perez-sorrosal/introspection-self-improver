/* Results dashboard application. Read-only over /api/*; all dynamic text via textContent. */

import { lineChart, sparkline, tooltip } from "./charts.js";

const state = {
  experiments: [],
  current: null,
  filters: { split: "all", transport: "all" },
  selectedGen: null,
  heatSort: "id",
  curveAsTable: false,
  openRounds: new Set(),
};

const CAT_COLOR_COUNT = 4; // --cat-0 … --cat-3 in style.css, cycled by split index
const SEQ_RAMP = [
  "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
  "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
];

/* ---------------------------------------------------------------- helpers */

const $ = (sel) => document.querySelector(sel);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

const isDark = () => window.matchMedia("(prefers-color-scheme: dark)").matches;
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const splitLabel = (split) => split ?? "ad-hoc";
const splitColor = (index) => cssVar(`--cat-${index % CAT_COLOR_COUNT}`);

function rampColor(fraction) {
  const ramp = isDark() ? [...SEQ_RAMP].reverse() : SEQ_RAMP;
  const idx = Math.round(Math.max(0, Math.min(1, fraction)) * (ramp.length - 1));
  return ramp[idx];
}

const pct = (v) =>
  v == null ? "—" : `${(v * 100).toFixed(1).replace(/\.0$/, "")}%`;
/* Expected counts (sums of per-task rates): integral values render as ints. */
const fmtCount = (v) => (Math.abs(v - Math.round(v)) < 1e-9 ? String(Math.round(v)) : v.toFixed(1));
const usd = (v) => (v == null ? "—" : `$${v.toFixed(v >= 10 ? 0 : 2)}`);
const secs = (v) => (v == null ? "—" : v >= 90 ? `${(v / 60).toFixed(1)}m` : `${v.toFixed(0)}s`);
const short = (sha) => (sha ? String(sha).slice(0, 7) : "—");
const genShort = (name) => name.replace(/^generation_/, "g");

function pass1(taskStats) {
  const proportions = taskStats.filter(([, n]) => n > 0).map(([c, n]) => c / n);
  return proportions.length
    ? proportions.reduce((a, b) => a + b, 0) / proportions.length
    : null;
}

function pass1Interval(taskStats) {
  const proportions = taskStats.filter(([, n]) => n > 0).map(([c, n]) => c / n);
  if (proportions.length < 2) return null;
  const mean = proportions.reduce((a, b) => a + b, 0) / proportions.length;
  const variance =
    proportions.reduce((a, p) => a + (p - mean) ** 2, 0) / (proportions.length - 1);
  const half = 1.96 * Math.sqrt(variance / proportions.length);
  return [Math.max(0, mean - half), Math.min(1, mean + half)];
}

/* ------------------------------------------------------------ data shaping */

function splitValues(exp) {
  /* Distinct recorded split values, deterministically ordered: alphabetical, the
     ad-hoc (null) bucket last. No taxonomy is hard-coded — the data decides. */
  const values = new Set();
  for (const gen of exp?.generations || []) for (const round of gen.rounds) values.add(round.split ?? null);
  const named = [...values].filter((v) => v != null).sort();
  return values.has(null) ? [...named, null] : named;
}

function matchesFilters(round) {
  const f = state.filters;
  if (f.split !== "all") {
    if (f.split === "ad-hoc" ? round.split != null : round.split !== f.split) return false;
  }
  if (f.transport !== "all" && round.transport !== f.transport) return false;
  return true;
}

const roundsOf = (gen) => gen.rounds.filter(matchesFilters);

function mergeRounds(rounds) {
  const tasks = {};
  const agg = {
    episodes: 0, graded: 0, infra: 0, abnormal: 0, evidenceIncomplete: 0,
    cost: 0, costCount: 0, messages: 0, kb: 0, duration: 0, simCount: 0,
    shas: new Set(), diagnostic: false, noSentinel: false, elapsed: 0,
  };
  for (const round of rounds) {
    for (const [task, { c, n, trials }] of Object.entries(round.tasks)) {
      const entry = (tasks[task] ||= { c: 0, n: 0, trials: [] });
      entry.c += c;
      entry.n += n;
      // Concatenated, not summed: which individual trials passed is the point (a task at
      // 1/3 is a passing and a failing transcript of the same harness on the same task).
      if (trials) entry.trials.push(...trials);
    }
    agg.episodes += round.episodes;
    agg.graded += round.graded;
    agg.infra += round.infra_errors;
    agg.abnormal += round.abnormal;
    agg.evidenceIncomplete += round.evidence_incomplete;
    agg.elapsed += round.elapsed_seconds || 0;
    if (round.mode && round.mode !== "locked") agg.diagnostic = true;
    if (!round.has_sentinel) agg.noSentinel = true;
    for (const sha of round.shas || []) agg.shas.add(sha);
    for (const sim of round.sims) {
      agg.simCount += 1;
      agg.messages += sim.messages || 0;
      agg.kb += sim.kb_search || 0;
      agg.duration += sim.duration || 0;
      const cost =
        sim.platform_cost != null
          ? sim.platform_cost
          : (sim.agent_cost || 0) + (sim.user_cost || 0) || null;
      if (cost != null) {
        agg.cost += cost;
        agg.costCount += 1;
      }
    }
  }
  const stats = Object.values(tasks).map(({ c, n }) => [c, n]);
  return {
    tasks,
    taskStats: stats,
    pass1: pass1(stats),
    interval: pass1Interval(stats),
    avgCost: agg.costCount ? agg.cost / agg.costCount : null,
    totalCost: agg.costCount ? agg.cost : null,
    avgMessages: agg.simCount ? agg.messages / agg.simCount : null,
    avgKb: agg.simCount ? agg.kb / agg.simCount : null,
    avgDuration: agg.simCount ? agg.duration / agg.simCount : null,
    ...agg,
    shas: [...agg.shas],
  };
}

function splitRounds(gen, split) {
  return roundsOf(gen).filter((r) => (r.split ?? null) === split);
}

/* Statistics count IMPROVEMENT BATCHES only (round.batch, from the runner's own
   split record). Everything else that lands under a generation — calibration
   pilots, mock smokes, single-task probes, concurrency smokes — is a diagnostic:
   still listed in the detail card with its "excluded from metrics" badge, but it
   never reaches a task set, statistic, curve, heatmap or aggregate. Pilots run on
   the locked domain, so a domain/mode test cannot catch them; batch membership is
   the only filter that can. */
const statsRoundsOf = (gen) => roundsOf(gen).filter((r) => r.batch);
const statsSplitRounds = (gen, split) =>
  statsRoundsOf(gen).filter((r) => (r.split ?? null) === split);

/* ---------------------------------------------------------------- badges */

function badge(kind, icon, label) {
  const chip = el("span", `badge badge-${kind}`);
  chip.append(el("span", null, icon), el("span", null, label));
  return chip;
}

function roundBadges(round) {
  const badges = [];
  if (!round.batch) badges.push(badge("warn", "⚠", "not a batch — excluded from metrics"));
  if (!round.has_sentinel) badges.push(badge("critical", "⛔", "interrupted — no completion sentinel"));
  if (round.arm_mismatches > 0) badges.push(badge("critical", "✗", `${round.arm_mismatches} arm sha mismatch`));
  else if (round.arm_dirty) badges.push(badge("warn", "⚠", "dirty arm — lineage soft"));
  if (round.infra_errors > 0) badges.push(badge("serious", "✕", `${round.infra_errors} infra`));
  if (round.abnormal > 0) badges.push(badge("serious", "△", `${round.abnormal} abnormal end`));
  if (round.evidence_incomplete > 0) badges.push(badge("serious", "◐", `${round.evidence_incomplete} evidence incomplete`));
  if (round.incident_count > 0) badges.push(badge("warn", "⚡", `${round.incident_count} incident(s)`));
  if (round.orphaned > 0) badges.push(badge("muted", "≠", `${round.orphaned} orphaned task(s)`));
  if (round.resumed) badges.push(badge("muted", "↻", "resumed"));
  return badges;
}

function gateStrip(gen) {
  /* The generation's gate verdicts (gates/*.json): the story of whether this cycle's
     numbers may be believed, told before the numbers themselves. */
  const wrap = el("div", "chip-strip");
  for (const gate of gen.gates || []) {
    const ok = gate.passed === true;
    const chip = badge(ok ? "good" : "critical", ok ? "✓" : "✗", `${gate.gate || "gate"} ${ok ? "PASS" : "FAIL"}`);
    const lane = (gate.lanes || []).map((l) => `${l.lane} pass¹=${l.pass1}`).join(" vs ");
    chip.title = [gate.generated, lane, gate.note].filter(Boolean).join(" · ");
    wrap.appendChild(chip);
  }
  return wrap;
}

/* ---------------------------------------------------------------- sections */

function renderBanner() {
  const slot = $("#banner-slot");
  slot.replaceChildren();
  const exp = state.current;
  if (!exp) return;
  if (!exp.snapshot) {
    const banner = el("div", "banner");
    banner.append(
      el("span", "b-icon", "⚠"),
      el(
        "span",
        null,
        `No freeze snapshot in ${exp.dirname}: bring-up data under a PROVISIONAL lock — nothing here is a reportable result.`
      )
    );
    slot.appendChild(banner);
  }
}

function latestRound(exp) {
  /* Freeze-chip fallback: prefer the newest batch round; any round only when the
     experiment has no batches at all (bring-up experiments). */
  let anyRound = null;
  for (let g = exp.generations.length - 1; g >= 0; g--) {
    const rounds = exp.generations[g].rounds;
    if (!rounds.length) continue;
    anyRound ||= rounds[rounds.length - 1];
    const batches = rounds.filter((r) => r.batch);
    if (batches.length) return batches[batches.length - 1];
  }
  return anyRound;
}

function renderFreeze() {
  const strip = $("#freeze-strip");
  strip.replaceChildren();
  const exp = state.current;
  if (!exp) return;
  const summary = exp.snapshot?.summary || {};
  const fallback = latestRound(exp) || {};
  const items = [
    ["domain", summary.domain || fallback.domain || "—"],
    ["retrieval", summary.retrieval_config || fallback.retrieval_config || "—"],
    ["agent", summary.agent_model || fallback.agent_llm || "—"],
    ["user sim", summary.user_llm || fallback.user_llm || "—"],
    ["trials × seed", `${summary.num_trials || fallback.num_trials || "?"} × ${summary.seed || fallback.seed || "?"}`],
    ["τ² commit", short(summary.benchmark_commit)],
  ];
  for (const [label, value] of items) {
    const chip = el("span", "chip");
    chip.append(el("span", null, label), el("b", null, String(value)));
    strip.appendChild(chip);
  }
  const status = exp.snapshot
    ? badge("good", "❄", `frozen — snapshot ${exp.snapshot.created || ""}`)
    : badge("warn", "⚠", "PROVISIONAL — no freeze");
  strip.appendChild(status);
}

function renderStats() {
  const row = $("#stat-row");
  row.replaceChildren();
  const exp = state.current;
  if (!exp || !exp.generations.length) return;

  /* Per generation: its improvement-batch rounds, merged. Batches carry per-generation
     split names (batch_01, batch_02, …), so "latest" means the newest generation with a
     batch — never a single split name pinned across the experiment. */
  const perGen = exp.generations.map((g) => mergeRounds(statsRoundsOf(g)));
  const withData = perGen.filter((a) => a.pass1 != null);
  const latest = [...perGen].reverse().find((a) => a.pass1 != null);
  const first = perGen.find((a) => a.pass1 != null);
  const all = mergeRounds(exp.generations.flatMap((g) => statsRoundsOf(g)));

  const hero = el("div", "stat hero");
  hero.append(
    el("div", "s-label", "latest improvement-batch pass¹"),
    el("div", "s-value", pct(latest?.pass1))
  );
  if (latest?.interval) hero.append(el("div", "s-sub", `≈95% CI ${pct(latest.interval[0])}–${pct(latest.interval[1])} · N=${latest.taskStats.length} tasks`));
  row.appendChild(hero);

  const delta = el("div", "stat");
  const diff = latest && first && withData.length > 1 ? latest.pass1 - first.pass1 : null;
  delta.append(el("div", "s-label", "Δ vs first generation"));
  const value = el("div", `s-value ${diff == null || diff === 0 ? "delta-flat" : diff > 0 ? "delta-up" : "delta-down"}`);
  value.textContent = diff == null ? "—" : `${diff > 0 ? "▲" : diff < 0 ? "▼" : "＝"} ${pct(Math.abs(diff))}`;
  delta.appendChild(value);
  row.appendChild(delta);

  const episodes = el("div", "stat");
  episodes.append(
    el("div", "s-label", "batch episodes"),
    el("div", "s-value", String(all.graded)),
    el("div", "s-sub", `${all.episodes} run · ${all.infra} infra excluded · diagnostics not counted`)
  );
  row.appendChild(episodes);

  const cost = el("div", "stat");
  cost.append(
    el("div", "s-label", "batch cost"),
    el("div", "s-value", usd(all.totalCost)),
    el("div", "s-sub", `avg ${usd(all.avgCost)} / episode`)
  );
  row.appendChild(cost);

  const gens = el("div", "stat");
  gens.append(
    el("div", "s-label", "generations"),
    el("div", "s-value", String(exp.generations.length)),
    el("div", "s-sub", "one improvement cycle each")
  );
  row.appendChild(gens);
}

/* -------------------------------------------------------------- the curve */

function curveSeries(exp) {
  /* One series: each generation's improvement-batch rounds, merged. Batch split names
     are per-generation (batch_01, batch_02, …), so a per-split series would fragment
     the curve into single points; the cross-generation identity is "the batch". */
  const gens = exp.generations;
  const line = gens.map((g) => {
    const agg = mergeRounds(statsRoundsOf(g));
    if (agg.pass1 == null) return null;
    return { v: agg.pass1, lo: agg.interval?.[0], hi: agg.interval?.[1] };
  });
  if (!line.some(Boolean)) return [];
  return [{ key: "batches", label: "improvement-batch pass¹", color: splitColor(0), points: line }];
}

function renderLegend(legend, series) {
  legend.replaceChildren();
  if (series.length < 2) return; // one series: the title names it
  for (const s of series) {
    const item = el("span", "lg");
    const key = s.hollow ? el("span", "lg-dot") : el("span", `lg-line${s.dash ? " dashed" : ""}`);
    key.style.borderColor = s.color;
    if (!s.hollow) key.style.borderTopColor = s.color;
    item.append(key, el("span", null, s.label));
    legend.appendChild(item);
  }
}

function renderCurveTable(container, exp) {
  const table = el("table", "data");
  const head = el("tr");
  for (const h of ["generation", "split", "pass¹", "≈95% CI", "tasks", "episodes", "avg cost"])
    head.appendChild(el("th", null, h));
  table.appendChild(head);
  for (const gen of exp.generations) {
    for (const split of splitValues(exp)) {
      const rounds = statsSplitRounds(gen, split);
      if (!rounds.length) continue;
      const agg = mergeRounds(rounds);
      if (agg.pass1 == null) continue;
      const tr = el("tr");
      tr.append(
        el("td", "mono", gen.name),
        el("td", null, splitLabel(split)),
        el("td", null, pct(agg.pass1)),
        el("td", null, agg.interval ? `${pct(agg.interval[0])}–${pct(agg.interval[1])}` : "—"),
        el("td", null, String(agg.taskStats.length)),
        el("td", null, String(agg.graded)),
        el("td", null, usd(agg.avgCost))
      );
      table.appendChild(tr);
    }
  }
  container.replaceChildren(table);
}

function renderRoundBars(container, exp) {
  const list = el("div", "bar-list");
  const color = splitColor(0);
  for (const gen of exp.generations) {
    for (const round of statsRoundsOf(gen)) {
      if (round.pass1 == null) continue;
      const row = el("div", "bar-row");
      const name = el("span", "bar-name", `${genShort(gen.name)}/${round.name}`);
      const track = el("div", "bar-track");
      const fill = el("div", "bar-fill");
      fill.style.width = `${Math.max(1.5, round.pass1 * 100)}%`;
      fill.style.background = color;
      track.appendChild(fill);
      const value = el("span", "bar-val", pct(round.pass1));
      row.append(name, track, value);
      row.addEventListener("pointermove", (evt) =>
        tooltip.show(evt.clientX, evt.clientY, round.path, [
          { color, value: pct(round.pass1), label: `pass¹ over ${round.graded} graded episode(s)` },
        ])
      );
      row.addEventListener("pointerleave", tooltip.hide);
      list.appendChild(row);
    }
  }
  container.replaceChildren(list);
}

function renderCurve() {
  const body = $("#curve-body");
  const note = $("#curve-note");
  const exp = state.current;
  if (!exp || !exp.generations.length) {
    body.replaceChildren(el("div", "empty-note", "No generations found for this experiment."));
    $("#curve-legend").replaceChildren();
    note.textContent = "";
    return;
  }
  if (state.curveAsTable) {
    renderCurveTable(body, exp);
    $("#curve-legend").replaceChildren();
    note.textContent = "Table view — the chart's WCAG-clean twin. Toggle back for the chart.";
    return;
  }
  const series = curveSeries(exp);
  if (!series.length) {
    renderLegend($("#curve-legend"), []);
    renderRoundBars(body, exp);
    note.textContent =
      "No improvement-batch rounds in this experiment — only diagnostics " +
      "(pilots, smokes, probes), which are excluded from all metrics.";
    return;
  }
  renderLegend($("#curve-legend"), series);
  const gens = exp.generations.map((g) => g.name);
  const selected = gens.indexOf(state.selectedGen);
  lineChart(body, {
    xLabels: gens.map(genShort),
    series,
    selected: selected >= 0 ? selected : null,
    onSelect: (i) => selectGeneration(gens[i]),
    yFmt: (v) => `${Math.round(v * 100)}%`,
  });
  note.textContent =
    state.current?.batch_mode === "fixed"
      ? "Improvement batches ONLY — diagnostics excluded from every number. batch_mode " +
        "FIXED: every generation measures the SAME task set, so this is a paired " +
        "saturation curve — can the loop fix what it stares at? Still not the " +
        "progression metric (held-out card). Whiskers are ≈95% intervals over per-task " +
        "pass rates. Click a generation to inspect it."
      : "Improvement batches ONLY — diagnostics (pilots, smokes, probes) are excluded from " +
        "every number here. Batches are disjoint task sets, so this curve is diagnosis " +
        "evidence, never the progression metric — that lives in the held-out card. " +
        "Whiskers are ≈95% intervals over per-task pass rates. Click a generation to inspect it.";
}

/* ------------------------------------------------- held-out progression
   Rendered exclusively from revealed artifacts under results/<experiment>/held_out/
   (the CSVs `make reveal` writes) — never from the vault, and never recomputed here.
   Until the reveal, the card states that the measurement is sealed. */

function heldOutEndpoint(held) {
  const first = held.generations[0];
  const last = held.generations.at(-1);
  const total = first.total;
  const delta = last.passed - first.passed;
  const deltaPp = (100 * delta) / total;
  const sign = (v) => (v >= 0 ? "+" : "");
  const band = held.noise_band_pp;
  const verdict =
    band == null ? "" :
    Math.abs(deltaPp) > band
      ? ` — outside the ±${band} pp noise band`
      : ` — inside the ±${band} pp noise band; directional only`;
  return (
    `Endpoint: ${last.generation} ${fmtCount(last.passed)}/${total} vs ${first.generation} ` +
    `${fmtCount(first.passed)}/${total} → ${sign(delta)}${fmtCount(Math.abs(delta))} task(s) ` +
    `(${sign(deltaPp)}${deltaPp.toFixed(1)} pp)${verdict}`
  );
}

function heldOutProgressionTable(held) {
  const multiTrial = (held.trials || 1) > 1;
  const table = el("table", "data");
  const head = el("tr");
  const headers = multiTrial
    ? ["generation", "solved (expected)", "%", "trials/task", "basis"]
    : ["generation", "solved", "%", "basis"];
  for (const h of headers) head.appendChild(el("th", null, h));
  table.appendChild(head);
  for (const g of held.generations) {
    const tr = el("tr");
    tr.append(
      el("td", "mono", g.generation),
      el("td", null, `${fmtCount(g.passed)}/${g.total}`),
      el("td", null, `${g.percent.toFixed(1)}%`)
    );
    if (multiTrial) tr.append(el("td", null, String(g.trials)));
    tr.append(el("td", null, g.carried ? "carried (identity)" : "measured"));
    table.appendChild(tr);
  }
  return table;
}

function heldOutTransitionsTable(held) {
  const table = el("table", "data");
  const head = el("tr");
  for (const h of ["transition", "gains", "retained", "regressions", "unresolved", "net", "note"])
    head.appendChild(el("th", null, h));
  table.appendChild(head);
  for (const row of held.transitions || []) {
    const tr = el("tr");
    tr.append(
      el("td", "mono", row.transition),
      el("td", null, String(row.gains)),
      el("td", null, String(row.retained)),
      el("td", null, String(row.regressions)),
      el("td", null, String(row.unresolved)),
      el("td", null, `${row.net >= 0 ? "+" : ""}${row.net}`),
      el("td", null, row.identity ? "identity" : "")
    );
    table.appendChild(tr);
  }
  return table;
}

function renderHeldOutMatrix(holder, held) {
  const gens = held.matrix_generations;
  const grid = el("div", "heat-grid");
  grid.style.gridTemplateColumns = `minmax(120px, 220px) repeat(${gens.length}, minmax(24px, 1fr))`;
  grid.appendChild(el("div", "heat-corner"));
  for (const g of gens) grid.appendChild(el("div", "heat-col-label", g));
  for (const row of held.matrix) {
    const label = el("div", "heat-row-label", row.task_id);
    label.title = state.current.task_descriptions?.[row.task_id] || row.task_id;
    grid.appendChild(label);
    row.results.forEach((cellStat, i) => {
      const rate = cellStat.n ? cellStat.c / cellStat.n : 0;
      const single = cellStat.n === 1;
      const cell = el("div", "heat-cell");
      cell.style.background = rampColor(rate);
      const prev = i > 0 ? row.results[i - 1] : null;
      const prevRate = prev ? (prev.n ? prev.c / prev.n : 0) : null;
      const changed = prevRate != null && prevRate !== rate;
      if (changed) cell.appendChild(el("span", "change-dot"));
      if (!single && cellStat.c > 0 && cellStat.c < cellStat.n)
        cell.appendChild(el("span", "unstable-dot"));
      cell.tabIndex = 0;
      const showTip = (evt) => {
        const point = evt.clientX != null ? evt : { clientX: cell.getBoundingClientRect().x, clientY: cell.getBoundingClientRect().y };
        tooltip.show(point.clientX, point.clientY, `${row.task_id} · ${gens[i]}`, [
          {
            color: rampColor(rate),
            value: single
              ? (cellStat.c ? "solved" : "not solved")
              : `${cellStat.c}/${cellStat.n} (${pct(rate)})`,
            label: single ? "single-trial result" : "trials passed",
          },
          ...(changed
            ? [{ value: rate > prevRate ? "rate up" : "rate down", label: "vs previous generation" }]
            : []),
        ]);
      };
      cell.addEventListener("pointermove", showTip);
      cell.addEventListener("focus", showTip);
      cell.addEventListener("pointerleave", tooltip.hide);
      cell.addEventListener("blur", tooltip.hide);
      grid.appendChild(cell);
    });
  }
  holder.appendChild(grid);

  const legend = el("div", "heat-legend");
  const multiTrial = (held.trials || 1) > 1;
  const scale = multiTrial
    ? [[1, "all trials pass"], [0.5, "some trials pass"], [0, "none pass"]]
    : [[1, "solved"], [0, "not solved"]];
  for (const [frac, text] of scale) {
    const item = el("span", "heat-scale");
    const swatch = el("span", "heat-swatch");
    swatch.style.background = rampColor(frac);
    item.append(swatch, el("span", null, text));
    legend.appendChild(item);
  }
  const change = el("span", "heat-scale");
  const dotWrap = el("span", "heat-swatch");
  dotWrap.style.background = rampColor(1);
  dotWrap.style.position = "relative";
  dotWrap.appendChild(el("span", "change-dot"));
  change.append(dotWrap, el("span", null, "· changed vs previous generation"));
  legend.appendChild(change);
  holder.appendChild(legend);
}

/* ------------------------------------------- process signals (progressive disclosure)
   Rendered from the reveal's process_metrics_*.csv — partial credit and behavioral
   signatures under the pass/fail curve. Collapsed by default; the summary teaser
   carries enough deltas that opening it is an informed choice. Descriptive statistics
   only: no noise band exists for these, so chips state direction, never significance,
   and carry no good/bad color — direction is not goodness here. */

const genLabelOf = (dirname) => `H${Number(String(dirname).slice(-3))}`;

function procDeltaChip(first, last, fmt) {
  if (first == null || last == null) return el("span", "proc-chip", "—");
  const delta = last - first;
  const arrow = Math.abs(delta) < 1e-9 ? "≈" : delta > 0 ? "▲" : "▼";
  return el("span", "proc-chip", `${arrow} ${fmt(Math.abs(delta))}`);
}

function procRow(xLabels, spec) {
  const row = el("div", "proc-row");
  row.appendChild(el("span", "proc-label", spec.label));
  const spark = el("span", "proc-spark");
  sparkline(spark, { values: spec.values, color: splitColor(0), domain: spec.domain });
  row.appendChild(spark);
  const measured = spec.values
    .map((v, i) => (v == null ? null : i))
    .filter((i) => i != null);
  const firstIdx = measured[0];
  const lastIdx = measured.at(-1);
  const endpoints =
    firstIdx == null
      ? "—"
      : `${xLabels[firstIdx]} ${spec.fmt(spec.values[firstIdx])} → ` +
        `${xLabels[lastIdx]} ${spec.fmt(spec.values[lastIdx])}`;
  row.appendChild(el("span", "proc-endpoints mono", endpoints));
  row.appendChild(
    procDeltaChip(
      firstIdx == null ? null : spec.values[firstIdx],
      lastIdx == null ? null : spec.values[lastIdx],
      spec.deltaFmt || spec.fmt
    )
  );
  return row;
}

function renderProcessTaskMatrix(holder, held) {
  const gens = held.matrix_generations;
  const byCell = new Map();
  for (const row of held.process.by_task) {
    byCell.set(`${row.task_id}|${genLabelOf(row.generation)}`, row);
  }
  const tasks = [...new Set(held.process.by_task.map((r) => r.task_id))].sort();
  const grid = el("div", "heat-grid");
  grid.style.gridTemplateColumns = `minmax(120px, 220px) repeat(${gens.length}, minmax(24px, 1fr))`;
  grid.appendChild(el("div", "heat-corner"));
  for (const g of gens) grid.appendChild(el("div", "heat-col-label", g));
  for (const task of tasks) {
    const label = el("div", "heat-row-label", task);
    label.title = state.current.task_descriptions?.[task] || task;
    grid.appendChild(label);
    let previousPassed = null;
    for (const g of gens) {
      const cellRow = byCell.get(`${task}|${g}`);
      const cell = el("div", "heat-cell");
      if (!cellRow) {
        cell.classList.add("heat-cell-carried");
        grid.appendChild(cell);
        continue;
      }
      const frac = cellRow.actions_total ? cellRow.actions_matched / cellRow.actions_total : 0;
      cell.style.background = rampColor(frac);
      if (cellRow.passed) cell.appendChild(el("span", "pass-ring"));
      if (previousPassed != null && previousPassed !== cellRow.passed)
        cell.appendChild(el("span", "change-dot"));
      previousPassed = cellRow.passed;
      cell.tabIndex = 0;
      const showTip = (evt) => {
        const point = evt.clientX != null ? evt : { clientX: cell.getBoundingClientRect().x, clientY: cell.getBoundingClientRect().y };
        tooltip.show(point.clientX, point.clientY, `${task} · ${g}`, [
          {
            color: rampColor(frac),
            value: `${cellRow.actions_matched}/${cellRow.actions_total} (${Math.round(100 * frac)}%)`,
            label: "gold actions matched",
          },
          { value: cellRow.passed ? "passed" : "not passed", label: "single-trial result" },
          ...(cellRow.db_match != null
            ? [{ value: cellRow.db_match ? "matched" : "diverged", label: "final DB state" }]
            : []),
        ]);
      };
      cell.addEventListener("pointermove", showTip);
      cell.addEventListener("focus", showTip);
      cell.addEventListener("pointerleave", tooltip.hide);
      cell.addEventListener("blur", tooltip.hide);
      grid.appendChild(cell);
    }
  }
  holder.appendChild(grid);
  const legend = el("div", "heat-legend");
  for (const [frac, text] of [[1, "all gold actions matched"], [0.5, "half"], [0, "none"]]) {
    const item = el("span", "heat-scale");
    const swatch = el("span", "heat-swatch");
    swatch.style.background = rampColor(frac);
    item.append(swatch, el("span", null, text));
    legend.appendChild(item);
  }
  const ring = el("span", "heat-scale");
  const ringWrap = el("span", "heat-swatch");
  ringWrap.style.background = rampColor(0.9);
  ringWrap.style.position = "relative";
  ringWrap.appendChild(el("span", "pass-ring"));
  ring.append(ringWrap, el("span", null, "◦ passed (reward 1.0)"));
  legend.appendChild(ring);
  holder.appendChild(legend);
}

function renderProcessPanel(held) {
  const proc = held.process;
  const gens = held.matrix_generations;
  const byGen = new Map(proc.by_generation.map((r) => [genLabelOf(r.generation), r]));
  const series = (pick) => gens.map((g) => (byGen.has(g) ? pick(byGen.get(g)) : null));
  const pp = (v) => `${v.toFixed(1)} pp`;
  const pctFmt = (v) => `${v.toFixed(1)}%`;
  const intFmt = (v) => `${Math.round(v)}`;

  const actions = series((r) => r.action_match_pct);
  const kb = series((r) => r.kb_search_calls);
  const transfers = series((r) => r.transfers);
  const firstOf = (vals) => vals.find((v) => v != null);
  const lastOf = (vals) => [...vals].reverse().find((v) => v != null);

  const details = el("details", "process-panel");
  const teaser =
    `actions ${firstOf(actions)?.toFixed(0)}→${lastOf(actions)?.toFixed(0)}% · ` +
    `KB searches ${firstOf(kb)}→${lastOf(kb)} · transfers ${firstOf(transfers)}→${lastOf(transfers)}`;
  details.appendChild(
    el("summary", null, `Process signals under the curve — ${teaser}`)
  );

  const dbBasis = proc.by_generation[0]?.db_basis_tasks;
  const groups = [
    {
      caption: "Outcome, decomposed — partial credit beneath pass/fail (scale pinned 0–100%)",
      rows: [
        {
          label: `DB match % (of ${dbBasis} DB-basis)`,
          values: series((r) => (r.db_basis_tasks ? (100 * r.db_matched) / r.db_basis_tasks : null)),
          domain: [0, 100], fmt: pctFmt, deltaFmt: pp,
        },
        { label: "gold actions matched %", values: actions, domain: [0, 100], fmt: pctFmt, deltaFmt: pp },
        { label: "write actions matched %", values: series((r) => r.write_match_pct), domain: [0, 100], fmt: pctFmt, deltaFmt: pp },
        { label: "partial action reward %", values: series((r) => r.partial_action_reward_pct), domain: [0, 100], fmt: pctFmt, deltaFmt: pp },
      ],
    },
    {
      caption: "Behavioral signatures — how the harness worked (zero-based scales)",
      rows: [
        { label: "KB_search calls (total)", values: kb, fmt: intFmt },
        { label: "discoverable-tool ops (total)", values: series((r) => r.discoverable_ops), fmt: intFmt },
        { label: "transfers to human (total)", values: transfers, fmt: intFmt },
        { label: "messages / episode (mean)", values: series((r) => r.messages_mean), fmt: (v) => v.toFixed(1) },
        { label: "cost / episode (mean)", values: series((r) => r.cost_usd_mean), fmt: (v) => `$${v.toFixed(2)}` },
      ],
    },
  ];
  for (const group of groups) {
    const box = el("div", "proc-group");
    box.appendChild(el("div", "proc-caption", group.caption));
    for (const spec of group.rows) {
      if (!spec.domain) {
        const finite = spec.values.filter((v) => v != null);
        spec.domain = [0, Math.max(...finite, 1) * 1.15];
      }
      box.appendChild(procRow(gens, spec));
    }
    details.appendChild(box);
  }

  const taskDetails = el("details", "proc-task-matrix");
  taskDetails.appendChild(el("summary", null, "Per-task gold-action match — the grain under the aggregates"));
  renderProcessTaskMatrix(taskDetails, held);
  details.appendChild(taskDetails);

  const total = held.generations[0]?.total;
  details.appendChild(
    el(
      "p",
      "proc-note",
      `Descriptive statistics over the same single-trial held-out episodes (T=${total}) as the ` +
        "curve above; no noise band is defined for them — read direction, not significance. " +
        "Derived at reveal from graded/updated_results.json into process_metrics_*.csv."
    )
  );
  return details;
}

function renderHeldOut() {
  const body = $("#heldout-body");
  const note = $("#heldout-note");
  const legend = $("#heldout-legend");
  body.replaceChildren();
  legend.replaceChildren();
  note.textContent = "";
  const exp = state.current;
  if (!exp) return;
  const held = exp.held_out;
  if (!held || !held.generations.length) {
    body.appendChild(
      el(
        "div",
        "empty-note",
        "Sealed until `make reveal`. Held-out rounds run on the local lane into the " +
          "out-of-tree vault; this page renders held-out views only from the revealed " +
          "artifacts under results/ (SIA_EVALUATION_PLAN.md D1/D9)."
      )
    );
    return;
  }
  const total = held.generations[0].total;
  const band = held.noise_band_pp != null ? held.noise_band_pp / 100 : null;
  const point = (g) => {
    const v = g.passed / g.total;
    return {
      v,
      lo: band != null ? Math.max(0, v - band) : null,
      hi: band != null ? Math.min(1, v + band) : null,
      hollow: g.carried,
    };
  };
  const multiTrial = (held.trials || 1) > 1;
  const series = [
    {
      key: "held-current",
      label: multiTrial ? "mean pass rate" : "currently solved",
      color: splitColor(0),
      points: held.generations.map(point),
    },
  ];
  if (held.retention?.length) {
    series.push({
      key: "held-ever",
      label: "ever solved",
      color: splitColor(2),
      dash: true,
      points: held.retention.map((row) => ({ v: row.ever / total })),
    });
  }
  renderLegend(legend, series);
  const chart = el("div");
  lineChart(chart, {
    xLabels: held.matrix_generations,
    series,
    yFmt: (v) => `${Math.round(v * 100)}%`,
  });
  body.appendChild(chart);
  body.appendChild(el("p", "heldout-endpoint", heldOutEndpoint(held)));

  const tables = el("div", "heldout-tables");
  tables.appendChild(heldOutProgressionTable(held));
  if (held.transitions?.length) tables.appendChild(heldOutTransitionsTable(held));
  body.appendChild(tables);
  renderHeldOutMatrix(body, held);
  if (held.process) body.appendChild(renderProcessPanel(held));
  if (held.summary) {
    const details = el("details", "raw");
    details.appendChild(el("summary", null, "summary.md — the reveal's own report"));
    details.appendChild(el("pre", null, held.summary));
    body.appendChild(details);
  }
  const trialsText = multiTrial
    ? `${held.trials} trials per task — cells are pass RATES, and the partial dot marks a ` +
      "task that both passes and fails under one harness"
    : "single trial per task";
  note.textContent =
    `Held-out performance on the one frozen set (T=${total}), measured once per ` +
    `generation, ${trialsText}. Whiskers: ±${held.noise_band_pp} pp noise band ` +
    "(one SE of the mean per-task rate at p=0.5) — deltas inside it are noise. Hollow " +
    "markers are identity generations (result carried forward, never re-measured). The " +
    "dashed line is the capability-retention diagnostic (ever solved by any generation " +
    "so far).";
}

function renderEfficiency() {
  const row = $("#spark-row");
  row.replaceChildren();
  const exp = state.current;
  if (!exp || !exp.generations.length) return;
  const perGen = exp.generations.map((g) => mergeRounds(statsRoundsOf(g)));
  const specs = [
    ["avg cost / episode", perGen.map((a) => a.avgCost), usd],
    ["avg messages", perGen.map((a) => a.avgMessages), (v) => (v == null ? "—" : v.toFixed(1))],
    ["avg KB_search calls", perGen.map((a) => a.avgKb), (v) => (v == null ? "—" : v.toFixed(1))],
    ["avg duration", perGen.map((a) => a.avgDuration), secs],
  ];
  const color = splitColor(0);
  for (const [label, values, fmt] of specs) {
    const spark = el("div", "spark");
    const last = [...values].reverse().find((v) => v != null);
    spark.append(el("div", "sp-label", label), el("div", "sp-value", fmt(last)));
    const chart = el("div");
    sparkline(chart, { values, color });
    spark.appendChild(chart);
    row.appendChild(spark);
  }
}

/* ------------------------------------------------------------- generations */

function generationIndex(name) {
  const match = name.match(/(\d+)$/);
  return match ? parseInt(match[1], 10) : null;
}

function recordFor(exp, genName) {
  /* The improvement record whose batch this generation ran: gen_<g>_to_<g+1>.yaml. */
  const index = generationIndex(genName);
  if (index == null) return null;
  return (exp.improvement_records || []).find((r) => r.from_generation === index) || null;
}

function outcomeBadge(record) {
  const outcome = (record?.outcome || "").toLowerCase();
  if (outcome === "accepted") return badge("good", "✓", "accepted");
  if (outcome === "rejected") return badge("critical", "✗", "rejected");
  if (outcome === "identity") return badge("muted", "＝", "identity");
  if (record) return badge("warn", "…", "record in flight");
  return badge("muted", "—", "no record yet");
}

function renderRibbon() {
  const ribbon = $("#generation-ribbon");
  ribbon.replaceChildren();
  const exp = state.current;
  if (!exp) return;
  let previous = null;
  exp.generations.forEach((gen) => {
    const agg = mergeRounds(statsRoundsOf(gen));
    const record = recordFor(exp, gen.name);
    const card = el("div", `gen-card${gen.name === state.selectedGen ? " selected" : ""}`);
    const head = el("div", "g-name");
    head.append(el("span", null, gen.name), outcomeBadge(record));
    card.appendChild(head);
    card.appendChild(el("div", "g-pass", pct(agg.pass1)));
    if (previous != null && agg.pass1 != null) {
      const diff = agg.pass1 - previous;
      const delta = el("div", `g-delta ${diff === 0 ? "delta-flat" : diff > 0 ? "delta-up" : "delta-down"}`);
      delta.textContent = `${diff > 0 ? "▲" : diff < 0 ? "▼" : "＝"} ${pct(Math.abs(diff))} vs prev`;
      card.appendChild(delta);
    }
    const fields = record?.fields || {};
    card.appendChild(
      el("div", "g-mut", fields.hypothesis || fields.proposed_change || "no improvement record yet")
    );
    card.appendChild(
      el(
        "div",
        "g-meta",
        `${agg.graded}/${agg.episodes} ep · ${usd(agg.totalCost)} · ${agg.shas.map(short).join(", ") || "sha —"}`
      )
    );
    card.addEventListener("click", () => selectGeneration(gen.name));
    ribbon.appendChild(card);
    if (agg.pass1 != null) previous = agg.pass1;
  });
}

/* ---------------------------------------------------------------- heatmap */

/* Trial pips: `c/n` plus one mark per trial, in trial order, filled when that trial passed.
   The label flips to a light ink over the dark end of the ramp so the count stays readable
   at every rate. Falls back to the count alone when a round predates per-trial data. */
function trialMarks(cell, frac) {
  const wrap = el("div", "trial-marks");
  if (frac > 0.55) wrap.classList.add("on-dark");
  wrap.appendChild(el("span", "trial-count", `${cell.c}/${cell.n}`));
  const trials = cell.trials || [];
  if (!trials.length) return wrap;
  const pips = el("span", "trial-pips");
  for (const outcome of trials) {
    const pip = el("span", `trial-pip ${outcome.passed ? "passed" : "failed"}`);
    const which = outcome.trial == null ? "?" : outcome.trial + 1;
    pip.title = `trial ${which}: ${outcome.passed ? "passed" : "failed"}`;
    pips.appendChild(pip);
  }
  wrap.appendChild(pips);
  return wrap;
}

/* Names the trials rather than only counting them, so a mixed cell can be opened straight
   to the pair worth reading — the passing and the failing transcript of one harness. */
function trialTooltipRows(cell) {
  const trials = cell.trials || [];
  if (trials.length < 2) return [];
  const label = (o) => (o.trial == null ? "?" : `#${o.trial + 1}`);
  const passed = trials.filter((o) => o.passed).map(label);
  const failed = trials.filter((o) => !o.passed).map(label);
  return [
    { value: passed.length ? passed.join(", ") : "none", label: "passed on trial" },
    { value: failed.length ? failed.join(", ") : "none", label: "failed on trial" },
  ];
}

function heatmapData(exp) {
  const perGen = exp.generations.map((g) => mergeRounds(statsRoundsOf(g)).tasks);
  const tasks = [...new Set(perGen.flatMap((t) => Object.keys(t)))];
  const rows = tasks.map((task) => {
    const cells = perGen.map((t) => t[task] || null);
    const fracs = cells.filter(Boolean).map(({ c, n }) => c / n);
    const trend = fracs.length >= 2 ? fracs[fracs.length - 1] - fracs[0] : 0;
    return { task, cells, trend };
  });
  const sorters = {
    id: (a, b) => a.task.localeCompare(b.task),
    trend: (a, b) => b.trend - a.trend || a.task.localeCompare(b.task),
  };
  rows.sort(sorters[state.heatSort] || sorters.id);
  return rows;
}

function renderHeatmap() {
  const body = $("#heatmap-body");
  const legend = $("#heat-legend");
  body.replaceChildren();
  legend.replaceChildren();
  const exp = state.current;
  if (!exp || !exp.generations.length) return;
  const rows = heatmapData(exp);
  if (!rows.length) {
    body.appendChild(el("div", "empty-note", "No graded tasks under the current filters."));
    return;
  }
  const gens = exp.generations;
  const grid = el("div", "heat-grid");
  grid.style.gridTemplateColumns = `minmax(120px, 220px) repeat(${gens.length}, minmax(24px, 1fr))`;
  grid.appendChild(el("div", "heat-corner"));
  for (const gen of gens) grid.appendChild(el("div", "heat-col-label", genShort(gen.name)));
  for (const row of rows) {
    const label = el("div", "heat-row-label", row.task);
    label.title = state.current.task_descriptions?.[row.task] || row.task;
    grid.appendChild(label);
    row.cells.forEach((cell, gi) => {
      const div = el("div", "heat-cell");
      if (!cell) {
        div.classList.add("empty");
      } else {
        const frac = cell.c / cell.n;
        div.style.background = rampColor(frac);
        // Under num_trials > 1 the colour alone answers "how much", never "which". The cell
        // carries the count and one pip per trial in trial order — filled = passed — so both
        // questions are answered without hovering. Single-trial rounds keep the bare cell.
        if (cell.n > 1) {
          div.classList.add("has-trials");
          div.appendChild(trialMarks(cell, frac));
        } else if (cell.c > 0 && cell.c < cell.n) {
          // Only reachable without per-trial marks; with pips the mixed case is already
          // legible and a centred dot would sit on top of the count.
          div.appendChild(el("span", "unstable-dot"));
        }
        div.tabIndex = 0;
        const showTip = (evt) => {
          const point = evt.clientX != null ? evt : { clientX: div.getBoundingClientRect().x, clientY: div.getBoundingClientRect().y };
          tooltip.show(point.clientX, point.clientY, `${row.task} · ${gens[gi].name}`, [
            { color: rampColor(frac), value: `${cell.c}/${cell.n} (${pct(frac)})`, label: "trials passed" },
            ...trialTooltipRows(cell),
            ...(cell.c > 0 && cell.c < cell.n
              ? [{ value: "unstable", label: "passes and fails under one config" }]
              : []),
          ]);
        };
        div.addEventListener("pointermove", showTip);
        div.addEventListener("focus", showTip);
        div.addEventListener("pointerleave", tooltip.hide);
        div.addEventListener("blur", tooltip.hide);
        div.addEventListener("click", () => selectGeneration(gens[gi].name));
      }
      grid.appendChild(div);
    });
  }
  body.appendChild(grid);

  legend.appendChild(el("span", null, "pass rate"));
  const scale = el("span", "heat-scale");
  for (const frac of [0, 0.25, 0.5, 0.75, 1]) {
    const swatch = el("span", "heat-swatch");
    swatch.style.background = rampColor(frac);
    scale.appendChild(swatch);
    scale.appendChild(el("span", null, `${Math.round(frac * 100)}`));
  }
  legend.appendChild(scale);
  const empty = el("span", "heat-scale");
  const emptySwatch = el("span", "heat-swatch empty");
  empty.append(emptySwatch, el("span", null, "not run"));
  legend.appendChild(empty);
  // With more than one trial per task the cells carry pips, so the legend explains those
  // instead of the centred unstable dot they replace.
  const multiTrial = rows.some((row) => row.cells.some((cell) => cell && cell.n > 1));
  if (multiTrial) {
    const pipLegend = el("span", "heat-scale");
    const sample = el("span", "trial-pips");
    sample.appendChild(el("span", "trial-pip passed"));
    sample.appendChild(el("span", "trial-pip failed"));
    pipLegend.append(
      sample,
      el("span", null, "one pip per trial, in order — filled = passed")
    );
    legend.appendChild(pipLegend);
  } else {
    const unstable = el("span", "heat-scale");
    const dotWrap = el("span", "heat-swatch");
    dotWrap.style.background = rampColor(0.5);
    dotWrap.style.position = "relative";
    dotWrap.appendChild(el("span", "unstable-dot"));
    unstable.append(dotWrap, el("span", null, "· unstable (0 < c < n)"));
    legend.appendChild(unstable);
  }
}

/* ------------------------------------------------------------- detail card */

function copyButton(text) {
  const button = el("button", "copy-btn", "copy");
  button.addEventListener("click", (evt) => {
    evt.stopPropagation();
    navigator.clipboard?.writeText(text);
    button.textContent = "copied";
    setTimeout(() => (button.textContent = "copy"), 1200);
  });
  return button;
}

function renderImprovementRecord(gen) {
  const holder = $("#learning-record");
  const record = recordFor(state.current, gen.name);
  const panel = el("div", "lr-panel");
  panel.appendChild(el("h3", null, "Improvement record — this generation's transition"));
  if (!record) {
    panel.appendChild(
      el(
        "div",
        "lr-empty",
        "No improvement record for this transition yet — one is written per generation " +
          "as it happens (improvement_records/gen_<g>_to_<g+1>.yaml, protocol §24)."
      )
    );
  } else {
    const chips = el("div", "chip-strip");
    chips.appendChild(outcomeBadge(record));
    const fields = record.fields || {};
    for (const key of ["owning_layer", "experiment"]) {
      if (fields[key]) {
        const chip = el("span", "chip");
        chip.append(el("span", null, key.replace("_", " ")), el("b", null, String(fields[key])));
        chips.appendChild(chip);
      }
    }
    panel.appendChild(chips);
    if (fields.hypothesis) panel.appendChild(el("p", "fineprint", `hypothesis: ${fields.hypothesis}`));
    if (fields.proposed_change) panel.appendChild(el("p", "fineprint", `change: ${fields.proposed_change}`));
    const details = el("details");
    details.appendChild(el("summary", null, record.name));
    details.appendChild(el("pre", null, record.raw));
    panel.appendChild(details);
  }
  holder.appendChild(panel);
}

function episodeTable(round) {
  const table = el("table", "data");
  const head = el("tr");
  for (const h of ["task", "trial", "reward", "termination", "flags", "msgs", "KB_search", "cost", "duration", "conversation", ""])
    head.appendChild(el("th", null, h));
  table.appendChild(head);
  for (const sim of round.sims) {
    const tr = el("tr");
    const reward = el("td");
    const chip = el("span", `reward-chip ${sim.success ? "pass" : "fail"}`);
    chip.textContent = sim.success ? "✓ 1.0" : `✗ ${sim.reward ?? "—"}`;
    reward.appendChild(chip);
    const flags = el("td");
    if (sim.arm_sha_ok === false) flags.appendChild(badge("critical", "✗", "arm sha"));
    if (sim.stall_warnings > 0) flags.appendChild(badge("warn", "⏱", `${sim.stall_warnings} stall(s)`));
    if (sim.incident_count > 0) flags.appendChild(badge("warn", "⚡", String(sim.incident_count)));
    const conversation = el("td", "mono");
    if (sim.label) conversation.title = sim.label;
    if (sim.platform_ref) {
      conversation.append(
        el("span", null, `${sim.platform_ref.slice(0, 8)}… `),
        copyButton(sim.platform_ref)
      );
      if (sim.evidence_complete === false) conversation.appendChild(badge("serious", "◐", "incomplete"));
    } else {
      conversation.textContent = "local";
    }
    const open = el("td");
    const button = el("button", "ghost-btn", "transcript");
    button.addEventListener("click", () =>
      openTranscript(round, sim)
    );
    open.appendChild(button);
    tr.append(
      el("td", "mono", sim.task_id),
      el("td", null, String(sim.trial ?? "—")),
      reward,
      el("td", null, sim.termination),
      flags,
      el("td", null, String(sim.messages)),
      el("td", null, String(sim.kb_search)),
      el("td", null, usd(sim.platform_cost != null ? sim.platform_cost : ((sim.agent_cost || 0) + (sim.user_cost || 0)) || null)),
      el("td", null, secs(sim.duration)),
      conversation,
      open
    );
    table.appendChild(tr);
  }
  return table;
}

function renderDetail() {
  const exp = state.current;
  const title = $("#detail-title");
  const body = $("#rounds-body");
  body.replaceChildren();
  if (!exp) return;
  const gen = exp.generations.find((g) => g.name === state.selectedGen) || exp.generations.at(-1);
  if (!gen) {
    title.textContent = "Generation detail";
    $("#learning-record").replaceChildren();
    return;
  }
  title.textContent = `${gen.name} — rounds and episodes`;
  const lrHolder = $("#learning-record");
  lrHolder.replaceChildren();
  if (gen.gates?.length) lrHolder.appendChild(gateStrip(gen));
  renderImprovementRecord(gen);

  /* Batch rounds lead; non-batch diagnostics trail, dimmed and badged — visible for
     inspection (transcripts, seam evidence) but never presented as evaluation data. */
  const rounds = [...roundsOf(gen)].sort((a, b) => (b.batch === true) - (a.batch === true));
  if (!rounds.length) {
    body.appendChild(el("div", "empty-note", "No rounds match the current filters."));
    return;
  }
  const table = el("table", "data");
  const head = el("tr");
  for (const h of ["round", "flags", "transport", "split", "episodes", "pass¹", "avg cost", "wall", "recipe sha"])
    head.appendChild(el("th", null, h));
  table.appendChild(head);
  for (const round of rounds) {
    const tr = el("tr", `round-row${round.batch ? "" : " diagnostic"}`);
    const flags = el("td");
    for (const b of roundBadges(round)) flags.appendChild(b);
    tr.append(
      el("td", "mono", round.name),
      flags,
      el("td", null, round.transport || "—"),
      el("td", null, splitLabel(round.split)),
      el("td", null, `${round.graded}/${round.episodes}`),
      el("td", null, pct(round.pass1)),
      el("td", null, usd(round.avg_cost)),
      el("td", null, secs(round.elapsed_seconds)),
      el("td", "mono", round.shas?.map(short).join(", ") || "—")
    );
    tr.addEventListener("click", () => {
      if (state.openRounds.has(round.path)) state.openRounds.delete(round.path);
      else state.openRounds.add(round.path);
      renderDetail();
    });
    table.appendChild(tr);
    if (state.openRounds.has(round.path)) {
      const holder = el("tr", "episodes-holder");
      const cell = el("td");
      cell.colSpan = 9;
      cell.appendChild(episodeTable(round));
      holder.appendChild(cell);
      table.appendChild(holder);
    }
  }
  body.appendChild(table);
}

/* ------------------------------------------------------------- transcript */

function messageNode(message, index) {
  const role = String(message.role || "unknown").toLowerCase();
  const wrap = el("div", `msg role-${role}`);
  wrap.appendChild(el("div", "m-role", `${index}. ${role}`));
  const bubble = el("div", "m-bubble");
  let content = message.content;
  if (Array.isArray(content)) {
    content = content.map((part) => (typeof part === "string" ? part : part?.text ?? JSON.stringify(part))).join("\n");
  }
  if (role === "tool" || role === "system") {
    const details = el("details");
    details.appendChild(el("summary", null, role === "tool" ? "tool result" : "system prompt"));
    details.appendChild(el("pre", null, String(content ?? "")));
    bubble.appendChild(details);
  } else if (content) {
    bubble.appendChild(document.createTextNode(String(content)));
  }
  for (const call of message.tool_calls || []) {
    const chip = el("span", "toolcall-chip", `⚒ ${call.name || "?"}`);
    bubble.appendChild(chip);
    const args = call.arguments ?? call.args;
    if (args != null) {
      const details = el("details");
      details.appendChild(el("summary", null, "arguments"));
      details.appendChild(
        el("pre", null, typeof args === "string" ? args : JSON.stringify(args, null, 2))
      );
      bubble.appendChild(details);
    }
  }
  wrap.appendChild(bubble);
  return wrap;
}

async function openTranscript(round, sim) {
  const key = sim.sim_id || `${sim.task_id}:${sim.trial}`;
  const response = await fetch(
    `/api/episode?round=${encodeURIComponent(round.path)}&sim=${encodeURIComponent(key)}`
  );
  const episode = await response.json();

  const overlay = el("div", "modal-overlay");
  const modal = el("div", "modal");
  const head = el("div", "modal-head");
  const heading = el("h3", null, `${sim.task_id} · trial ${sim.trial ?? "?"}`);
  const meta = el("div", "modal-meta");
  const chip = el("span", `reward-chip ${sim.success ? "pass" : "fail"}`);
  chip.textContent = sim.success ? "✓ reward 1.0" : `✗ reward ${sim.reward ?? "—"}`;
  meta.append(
    chip,
    badge("muted", "◷", `${secs(sim.duration)} · ${sim.messages} msgs`),
    badge("muted", "◈", sim.termination)
  );
  if (sim.platform_ref) {
    meta.append(el("span", "mono", `${sim.platform_ref.slice(0, 12)}…`), copyButton(sim.platform_ref));
  }
  const close = el("button", "ghost-btn", "close ✕");
  head.append(heading, meta, close);
  const body = el("div", "modal-body");
  if (episode.error) {
    body.appendChild(el("div", "empty-note", `Could not load episode: ${episode.error}`));
  } else {
    if (sim.platform_ref) {
      body.appendChild(
        el("div", "fineprint", `Full platform evidence: introspection conversations get ${sim.platform_ref}`)
      );
    }
    (episode.messages || []).forEach((message, i) => body.appendChild(messageNode(message, i + 1)));
  }
  modal.append(head, body);
  overlay.appendChild(modal);
  const dismiss = () => overlay.remove();
  close.addEventListener("click", dismiss);
  overlay.addEventListener("click", (evt) => {
    if (evt.target === overlay) dismiss();
  });
  document.addEventListener("keydown", function esc(evt) {
    if (evt.key === "Escape") {
      dismiss();
      document.removeEventListener("keydown", esc);
    }
  });
  document.getElementById("modal-root").appendChild(overlay);
}

/* ---------------------------------------------------------------- wiring */

function selectGeneration(name) {
  state.selectedGen = name;
  renderAll();
  $("#detail-card").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderSplitFilter() {
  /* Options come from the loaded experiment's data, never a hard-coded taxonomy. */
  const select = $("#split-filter");
  const values = ["all", ...splitValues(state.current).map(splitLabel)];
  if (!values.includes(state.filters.split)) state.filters.split = "all";
  select.replaceChildren();
  for (const value of values) {
    const option = el("option", null, value);
    option.value = value;
    select.appendChild(option);
  }
  select.value = state.filters.split;
}

function renderAll() {
  renderBanner();
  renderFreeze();
  renderStats();
  renderHeldOut();
  renderCurve();
  renderEfficiency();
  renderRibbon();
  renderHeatmap();
  renderDetail();
}

async function loadExperiment(dirname) {
  const main = $("#main");
  main.style.opacity = "0.55"; // hold the previous render, no skeleton flash
  try {
    const response = await fetch(`/api/experiment?dir=${encodeURIComponent(dirname)}`);
    state.current = await response.json();
    state.selectedGen = state.current.generations?.at(-1)?.name || null;
    state.openRounds = new Set();
    renderSplitFilter();
    renderAll();
  } finally {
    main.style.opacity = "1";
  }
}

async function init() {
  const config = await (await fetch("/api/config")).json();
  $("#config-note").textContent = config.results_root;
  const experiments = await (await fetch("/api/experiments")).json();
  state.experiments = experiments;
  const select = $("#experiment-select");
  select.replaceChildren();
  for (const experiment of experiments) {
    // experiment_<seq>_<name> directories read as "exp_001 · bm25-sonnet46"; legacy
    // pre-sequence directories (experiment_dummy) fall back to their bare id.
    const label = experiment.seq
      ? `exp_${experiment.seq} · ${experiment.name}`
      : experiment.id;
    const option = el("option", null, `${label}${experiment.has_snapshot ? " ❄" : ""}`);
    option.value = experiment.dirname;
    select.appendChild(option);
  }
  if (!experiments.length) {
    $("#main").replaceChildren(
      el(
        "div",
        "empty-note",
        `No experiment_* directories under ${config.results_root}. Point dashboard/config.json ` +
          "at a results tree (results/experiment_<id>/generation_NNN/<round>/) and refresh."
      )
    );
    return;
  }
  const preferred =
    experiments.find((e) => e.has_snapshot)?.dirname || experiments[0].dirname;
  select.value = preferred;
  select.addEventListener("change", () => loadExperiment(select.value));
  $("#split-filter").addEventListener("change", (evt) => {
    state.filters.split = evt.target.value;
    renderAll();
  });
  $("#transport-filter").addEventListener("change", (evt) => {
    state.filters.transport = evt.target.value;
    renderAll();
  });
  $("#heat-sort").addEventListener("change", (evt) => {
    state.heatSort = evt.target.value;
    renderHeatmap();
  });
  $("#curve-table-toggle").addEventListener("click", () => {
    state.curveAsTable = !state.curveAsTable;
    $("#curve-table-toggle").textContent = state.curveAsTable ? "chart" : "table";
    renderCurve();
  });
  $("#refresh").addEventListener("click", () => loadExperiment(select.value));
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renderAll);
  await loadExperiment(preferred);
}

init();
