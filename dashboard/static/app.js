/* Results dashboard application. Read-only over /api/*; all dynamic text via textContent. */

import { lineChart, sparkline, tooltip } from "./charts.js";

const state = {
  experiments: [],
  current: null,
  filters: { split: "all", arm: "all", transport: "all" },
  selectedGen: null,
  heatSort: "id",
  curveAsTable: false,
  openRounds: new Set(),
};

const SPLIT_ORDER = ["discovery", "validation", "checkpoint"];
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
const seriesColor = (split) => cssVar(`--s-${split}`) || cssVar("--s-other");

function rampColor(fraction) {
  const ramp = isDark() ? [...SEQ_RAMP].reverse() : SEQ_RAMP;
  const idx = Math.round(Math.max(0, Math.min(1, fraction)) * (ramp.length - 1));
  return ramp[idx];
}

const pct = (v) =>
  v == null ? "—" : `${(v * 100).toFixed(1).replace(/\.0$/, "")}%`;
const usd = (v) => (v == null ? "—" : `$${v.toFixed(v >= 10 ? 0 : 2)}`);
const secs = (v) => (v == null ? "—" : v >= 90 ? `${(v / 60).toFixed(1)}m` : `${v.toFixed(0)}s`);
const short = (sha) => (sha ? String(sha).slice(0, 7) : "—");
const genShort = (name) => name.replace(/^generation_/, "g");

function comb(n, k) {
  if (k < 0 || k > n) return 0;
  k = Math.min(k, n - k);
  let result = 1;
  for (let i = 1; i <= k; i++) result = (result * (n - k + i)) / i;
  return result;
}

function passHatK(taskStats, k) {
  const values = taskStats.filter(([, n]) => n >= k).map(([c, n]) => comb(c, k) / comb(n, k));
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
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

function matchesFilters(round) {
  const f = state.filters;
  if (f.split !== "all") {
    if (f.split === "other" ? round.split != null : round.split !== f.split) return false;
  }
  if (f.arm !== "all" && round.arm !== f.arm) return false;
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
    for (const [task, { c, n }] of Object.entries(round.tasks)) {
      const entry = (tasks[task] ||= { c: 0, n: 0 });
      entry.c += c;
      entry.n += n;
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
  const minTrials = stats.length ? Math.min(...stats.map(([, n]) => n)) : 0;
  return {
    tasks,
    taskStats: stats,
    pass1: passHatK(stats, 1),
    interval: pass1Interval(stats),
    kMax: minTrials,
    passK: minTrials >= 2 ? passHatK(stats, minTrials) : null,
    avgCost: agg.costCount ? agg.cost / agg.costCount : null,
    totalCost: agg.costCount ? agg.cost : null,
    avgMessages: agg.simCount ? agg.messages / agg.simCount : null,
    avgKb: agg.simCount ? agg.kb / agg.simCount : null,
    avgDuration: agg.simCount ? agg.duration / agg.simCount : null,
    ...agg,
    shas: [...agg.shas],
  };
}

function splitSeriesRounds(gen, split, arms) {
  return roundsOf(gen).filter((r) => r.split === split && arms.includes(r.arm));
}

/* ---------------------------------------------------------------- badges */

function badge(kind, icon, label) {
  const chip = el("span", `badge badge-${kind}`);
  chip.append(el("span", null, icon), el("span", null, label));
  return chip;
}

function roundBadges(round) {
  const badges = [];
  if (round.mode && round.mode !== "locked") badges.push(badge("warn", "⚠", "diagnostic — not reportable"));
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
  for (let g = exp.generations.length - 1; g >= 0; g--) {
    const rounds = exp.generations[g].rounds;
    if (rounds.length) return rounds[rounds.length - 1];
  }
  return null;
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

function primarySplit(exp) {
  for (const split of SPLIT_ORDER) {
    if (exp.generations.some((g) => roundsOf(g).some((r) => r.split === split))) return split;
  }
  return null;
}

function renderStats() {
  const row = $("#stat-row");
  row.replaceChildren();
  const exp = state.current;
  if (!exp || !exp.generations.length) return;

  const split = primarySplit(exp);
  const perGen = exp.generations.map((g) =>
    mergeRounds(split ? splitSeriesRounds(g, split, ["baseline", null]) : roundsOf(g))
  );
  const withData = perGen.filter((a) => a.pass1 != null);
  const latest = [...perGen].reverse().find((a) => a.pass1 != null);
  const first = perGen.find((a) => a.pass1 != null);
  const all = mergeRounds(exp.generations.flatMap((g) => roundsOf(g)));

  const hero = el("div", "stat hero");
  hero.append(
    el("div", "s-label", split ? `latest ${split} pass¹` : "latest pass¹ (all rounds)"),
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

  const passK = el("div", "stat");
  passK.append(
    el("div", "s-label", latest?.kMax >= 2 ? `pass^${latest.kMax} (latest)` : "pass^k"),
    el("div", "s-value", latest?.kMax >= 2 ? pct(latest.passK) : "n/a"),
    el("div", "s-sub", latest?.kMax >= 2 ? "reliability, not luck" : "needs num_trials ≥ 2")
  );
  row.appendChild(passK);

  const episodes = el("div", "stat");
  episodes.append(
    el("div", "s-label", "episodes (filtered)"),
    el("div", "s-value", String(all.graded)),
    el("div", "s-sub", `${all.episodes} run · ${all.infra} infra excluded`)
  );
  row.appendChild(episodes);

  const cost = el("div", "stat");
  cost.append(
    el("div", "s-label", "total cost"),
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
  const gens = exp.generations;
  const series = [];
  for (const split of SPLIT_ORDER) {
    if (state.filters.split !== "all") {
      if (state.filters.split === "other" || state.filters.split !== split) continue;
    }
    const color = seriesColor(split);
    const line = gens.map((g) => {
      const agg = mergeRounds(splitSeriesRounds(g, split, ["baseline", null]));
      if (agg.pass1 == null) return null;
      return { v: agg.pass1, lo: agg.interval?.[0], hi: agg.interval?.[1] };
    });
    if (line.some(Boolean)) {
      series.push({ key: split, label: `${split} pass¹`, color, points: line });
      const kMax = Math.max(
        ...gens.map((g) => mergeRounds(splitSeriesRounds(g, split, ["baseline", null])).kMax || 0)
      );
      if (kMax >= 2) {
        const kLine = gens.map((g) => {
          const agg = mergeRounds(splitSeriesRounds(g, split, ["baseline", null]));
          return agg.passK == null ? null : { v: agg.passK };
        });
        series.push({ key: `${split}-k`, label: `${split} pass^k`, color, dash: true, points: kLine });
      }
    }
    const candidate = gens.map((g) => {
      const agg = mergeRounds(splitSeriesRounds(g, split, ["candidate"]));
      return agg.pass1 == null ? null : { v: agg.pass1, lo: agg.interval?.[0], hi: agg.interval?.[1] };
    });
    if (candidate.some(Boolean)) {
      series.push({ key: `${split}-cand`, label: `${split} candidate`, color, hollow: true, noLine: true, points: candidate });
    }
  }
  return series;
}

function renderLegend(series) {
  const legend = $("#curve-legend");
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
  for (const h of ["generation", "split", "arm", "pass¹", "≈95% CI", "pass^k", "k", "tasks", "episodes", "avg cost"])
    head.appendChild(el("th", null, h));
  table.appendChild(head);
  for (const gen of exp.generations) {
    for (const split of [...SPLIT_ORDER, null]) {
      for (const arms of [["baseline", null], ["candidate"]]) {
        const rounds = split === null
          ? roundsOf(gen).filter((r) => r.split == null && arms.includes(r.arm))
          : splitSeriesRounds(gen, split, arms);
        if (!rounds.length) continue;
        const agg = mergeRounds(rounds);
        if (agg.pass1 == null) continue;
        const tr = el("tr");
        tr.append(
          el("td", "mono", gen.name),
          el("td", null, split ?? "other"),
          el("td", null, arms.includes("candidate") ? "candidate" : "baseline"),
          el("td", null, pct(agg.pass1)),
          el("td", null, agg.interval ? `${pct(agg.interval[0])}–${pct(agg.interval[1])}` : "—"),
          el("td", null, agg.kMax >= 2 ? pct(agg.passK) : "—"),
          el("td", null, agg.kMax >= 2 ? String(agg.kMax) : "—"),
          el("td", null, String(agg.taskStats.length)),
          el("td", null, String(agg.graded)),
          el("td", null, usd(agg.avgCost))
        );
        table.appendChild(tr);
      }
    }
  }
  container.replaceChildren(table);
}

function renderRoundBars(container, exp) {
  const list = el("div", "bar-list");
  const color = seriesColor("discovery");
  for (const gen of exp.generations) {
    for (const round of roundsOf(gen)) {
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
    renderLegend([]);
    renderRoundBars(body, exp);
    note.textContent =
      "No split-convention rounds (discovery/validation) yet — showing per-round pass¹ instead. " +
      "The generation curve appears once rounds follow <split>_<arm> naming.";
    return;
  }
  renderLegend(series);
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
    "Whiskers are ≈95% intervals over per-task pass rates. Hollow markers are candidate arms. " +
    "Click a generation to inspect it.";
}

function renderEfficiency() {
  const row = $("#spark-row");
  row.replaceChildren();
  const exp = state.current;
  if (!exp || !exp.generations.length) return;
  const perGen = exp.generations.map((g) => mergeRounds(roundsOf(g)));
  const specs = [
    ["avg cost / episode", perGen.map((a) => a.avgCost), usd],
    ["avg messages", perGen.map((a) => a.avgMessages), (v) => (v == null ? "—" : v.toFixed(1))],
    ["avg KB_search calls", perGen.map((a) => a.avgKb), (v) => (v == null ? "—" : v.toFixed(1))],
    ["avg duration", perGen.map((a) => a.avgDuration), secs],
  ];
  const color = seriesColor("discovery");
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

function decisionBadge(fields) {
  const decision = (fields?.decision || "").toLowerCase();
  if (decision.startsWith("accept")) return badge("good", "✓", "accepted");
  if (decision.startsWith("reject")) return badge("critical", "✗", "rejected");
  if (decision.startsWith("direction")) return badge("warn", "→", "directional");
  return badge("muted", "—", "no decision yet");
}

function renderRibbon() {
  const ribbon = $("#generation-ribbon");
  ribbon.replaceChildren();
  const exp = state.current;
  if (!exp) return;
  let previous = null;
  exp.generations.forEach((gen) => {
    const agg = mergeRounds(roundsOf(gen));
    const card = el("div", `gen-card${gen.name === state.selectedGen ? " selected" : ""}`);
    const head = el("div", "g-name");
    head.append(el("span", null, gen.name), decisionBadge(gen.learning_record?.fields));
    card.appendChild(head);
    card.appendChild(el("div", "g-pass", pct(agg.pass1)));
    if (previous != null && agg.pass1 != null) {
      const diff = agg.pass1 - previous;
      const delta = el("div", `g-delta ${diff === 0 ? "delta-flat" : diff > 0 ? "delta-up" : "delta-down"}`);
      delta.textContent = `${diff > 0 ? "▲" : diff < 0 ? "▼" : "＝"} ${pct(Math.abs(diff))} vs prev`;
      card.appendChild(delta);
    }
    const fields = gen.learning_record?.fields || {};
    card.appendChild(
      el("div", "g-mut", fields.candidate || fields.hypothesis || "no learning record yet")
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

function heatmapData(exp) {
  const perGen = exp.generations.map((g) => mergeRounds(roundsOf(g)).tasks);
  const tasks = [...new Set(perGen.flatMap((t) => Object.keys(t)))];
  const rows = tasks.map((task) => {
    const cells = perGen.map((t) => t[task] || null);
    const fracs = cells.filter(Boolean).map(({ c, n }) => c / n);
    const volatility = fracs.reduce((a, p) => a + p * (1 - p), 0);
    const trend = fracs.length >= 2 ? fracs[fracs.length - 1] - fracs[0] : 0;
    return { task, cells, volatility, trend };
  });
  const sorters = {
    id: (a, b) => a.task.localeCompare(b.task),
    volatility: (a, b) => b.volatility - a.volatility || a.task.localeCompare(b.task),
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
        if (cell.c > 0 && cell.c < cell.n) div.appendChild(el("span", "unstable-dot"));
        div.tabIndex = 0;
        const showTip = (evt) => {
          const point = evt.clientX != null ? evt : { clientX: div.getBoundingClientRect().x, clientY: div.getBoundingClientRect().y };
          tooltip.show(point.clientX, point.clientY, `${row.task} · ${gens[gi].name}`, [
            { color: rampColor(frac), value: `${cell.c}/${cell.n} (${pct(frac)})`, label: "trials passed" },
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
  const unstable = el("span", "heat-scale");
  const dotWrap = el("span", "heat-swatch");
  dotWrap.style.background = rampColor(0.5);
  dotWrap.style.position = "relative";
  dotWrap.appendChild(el("span", "unstable-dot"));
  unstable.append(dotWrap, el("span", null, "· unstable (0 < c < n)"));
  legend.appendChild(unstable);
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

function renderLearningRecord(gen) {
  const holder = $("#learning-record");
  const panel = el("div", "lr-panel");
  panel.appendChild(el("h3", null, "Learning record"));
  if (!gen.learning_record && !gen.decision) {
    panel.appendChild(
      el(
        "div",
        "lr-empty",
        "No learning record for this generation yet — it arrives with the first improvement cycle (v2 §5.6)."
      )
    );
  } else {
    if (gen.learning_record) {
      const chips = el("div", "chip-strip");
      const fields = gen.learning_record.fields || {};
      for (const key of ["candidate", "decision", "experiment"]) {
        if (fields[key]) {
          const chip = el("span", "chip");
          chip.append(el("span", null, key), el("b", null, String(fields[key])));
          chips.appendChild(chip);
        }
      }
      panel.appendChild(chips);
      const details = el("details");
      details.appendChild(el("summary", null, "learning_record.yaml"));
      const pre = el("pre", null, gen.learning_record.raw);
      details.appendChild(pre);
      panel.appendChild(details);
    }
    if (gen.decision) {
      const details = el("details");
      details.appendChild(el("summary", null, "decision.md"));
      details.appendChild(el("pre", null, gen.decision));
      panel.appendChild(details);
    }
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
  renderLearningRecord(gen);

  const rounds = roundsOf(gen);
  if (!rounds.length) {
    body.appendChild(el("div", "empty-note", "No rounds match the current filters."));
    return;
  }
  const table = el("table", "data");
  const head = el("tr");
  for (const h of ["round", "flags", "transport", "arm", "episodes", "pass¹", "pass^k", "avg cost", "wall", "recipe sha"])
    head.appendChild(el("th", null, h));
  table.appendChild(head);
  for (const round of rounds) {
    const tr = el("tr", `round-row${round.mode !== "locked" ? " diagnostic" : ""}`);
    const flags = el("td");
    for (const b of roundBadges(round)) flags.appendChild(b);
    const kEntries = Object.entries(round.pass_curve || {}).filter(([k]) => Number(k) >= 2);
    tr.append(
      el("td", "mono", round.name),
      flags,
      el("td", null, round.transport || "—"),
      el("td", null, round.arm || "—"),
      el("td", null, `${round.graded}/${round.episodes}`),
      el("td", null, pct(round.pass1)),
      el("td", null, kEntries.length ? `${pct(kEntries.at(-1)[1])} (k=${kEntries.at(-1)[0]})` : "—"),
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
      cell.colSpan = 11;
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

function renderAll() {
  renderBanner();
  renderFreeze();
  renderStats();
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
  $("#arm-filter").addEventListener("change", (evt) => {
    state.filters.arm = evt.target.value;
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
