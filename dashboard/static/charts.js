/* Hand-rolled SVG chart primitives. No dependencies; text via textContent only. */

const SVG_NS = "http://www.w3.org/2000/svg";

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}

/* ---------------------------------------------------------------- tooltip */

const tipRoot = () => document.getElementById("tooltip");

export const tooltip = {
  show(clientX, clientY, title, rows) {
    const tip = tipRoot();
    tip.replaceChildren();
    if (title) {
      const t = document.createElement("div");
      t.className = "tt-title";
      t.textContent = title;
      tip.appendChild(t);
    }
    for (const row of rows || []) {
      const line = document.createElement("div");
      line.className = "tt-row";
      if (row.color) {
        const key = document.createElement("span");
        key.className = "tt-key";
        key.style.borderTopColor = row.color;
        line.appendChild(key);
      }
      const value = document.createElement("span");
      value.className = "tt-val";
      value.textContent = row.value;
      line.appendChild(value);
      if (row.label) {
        const label = document.createElement("span");
        label.className = "tt-label";
        label.textContent = row.label;
        line.appendChild(label);
      }
      tip.appendChild(line);
    }
    tip.hidden = false;
    const pad = 14;
    const rect = tip.getBoundingClientRect();
    let x = clientX + pad;
    let y = clientY + pad;
    if (x + rect.width > window.innerWidth - 8) x = clientX - rect.width - pad;
    if (y + rect.height > window.innerHeight - 8) y = clientY - rect.height - pad;
    tip.style.left = `${Math.max(4, x)}px`;
    tip.style.top = `${Math.max(4, y)}px`;
  },
  hide() {
    tipRoot().hidden = true;
  },
};

/* ---------------------------------------------------------------- line chart */

const W = 900;
const H = 300;
const PAD = { l: 42, r: 118, t: 14, b: 32 };

export function lineChart(container, opts) {
  const { xLabels, series, selected, onSelect, yFmt } = opts;
  const n = xLabels.length;
  const innerW = W - PAD.l - PAD.r;
  const innerH = H - PAD.t - PAD.b;
  const step = n > 1 ? innerW / (n - 1) : 0;
  const x = (i) => PAD.l + (n > 1 ? i * step : innerW / 2);
  const y = (v) => PAD.t + (1 - Math.max(0, Math.min(1, v))) * innerH;

  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img" });

  if (selected != null && selected >= 0 && selected < n) {
    const bandW = Math.min(Math.max(step * 0.6, 26), 60);
    svg.appendChild(
      svgEl("rect", {
        class: "x-select-band",
        x: x(selected) - bandW / 2,
        y: PAD.t,
        width: bandW,
        height: innerH,
        rx: 5,
      })
    );
  }

  for (const tick of [0, 0.25, 0.5, 0.75, 1]) {
    const cls = tick === 0 ? "baseline-rule" : "gridline";
    svg.appendChild(
      svgEl("line", { class: cls, x1: PAD.l, x2: W - PAD.r, y1: y(tick), y2: y(tick) })
    );
    const label = svgEl("text", {
      class: "axis-text",
      x: PAD.l - 8,
      y: y(tick) + 3.5,
      "text-anchor": "end",
    });
    label.textContent = yFmt(tick);
    svg.appendChild(label);
  }
  xLabels.forEach((name, i) => {
    const label = svgEl("text", {
      class: "axis-text",
      x: x(i),
      y: H - 10,
      "text-anchor": "middle",
    });
    label.textContent = name;
    svg.appendChild(label);
  });

  const surface = getComputedStyle(document.documentElement).getPropertyValue("--surface-1").trim();

  for (const s of series) {
    for (let i = 0; i < n; i++) {
      const p = s.points[i];
      if (!p || p.lo == null || p.hi == null) continue;
      const whisker = svgEl("g", { opacity: "0.5" });
      whisker.appendChild(
        svgEl("line", { x1: x(i), x2: x(i), y1: y(p.lo), y2: y(p.hi), stroke: s.color, "stroke-width": 1.5 })
      );
      for (const bound of [p.lo, p.hi]) {
        whisker.appendChild(
          svgEl("line", { x1: x(i) - 3.5, x2: x(i) + 3.5, y1: y(bound), y2: y(bound), stroke: s.color, "stroke-width": 1.5 })
        );
      }
      svg.appendChild(whisker);
    }
  }

  for (const s of series) {
    if (s.noLine) continue;
    let d = "";
    s.points.forEach((p, i) => {
      if (!p || p.v == null) return;
      d += (d ? " L " : "M ") + `${x(i)} ${y(p.v)}`;
    });
    if (!d) continue;
    const path = svgEl("path", {
      d,
      fill: "none",
      stroke: s.color,
      "stroke-width": 2,
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    });
    if (s.dash) path.setAttribute("stroke-dasharray", "5 4");
    svg.appendChild(path);
  }

  for (const s of series) {
    s.points.forEach((p, i) => {
      if (!p || p.v == null) return;
      const marker = s.hollow || p.hollow
        ? svgEl("circle", { cx: x(i), cy: y(p.v), r: 4.5, fill: surface, stroke: s.color, "stroke-width": 2.5 })
        : svgEl("circle", { cx: x(i), cy: y(p.v), r: 5, fill: s.color, stroke: surface, "stroke-width": 2 });
      svg.appendChild(marker);
    });
  }

  // Selective direct labels: the endpoint of each line series (relief for sub-contrast hues).
  const ends = [];
  for (const s of series) {
    if (s.noLine) continue;
    for (let i = n - 1; i >= 0; i--) {
      const p = s.points[i];
      if (p && p.v != null) {
        ends.push({ s, i, v: p.v, y: y(p.v) });
        break;
      }
    }
  }
  ends.sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) {
    if (ends[i].y - ends[i - 1].y < 14) ends[i].y = ends[i - 1].y + 14;
  }
  for (const end of ends) {
    const group = svgEl("g");
    group.appendChild(
      svgEl("circle", { cx: x(end.i) + 12, cy: end.y - 3.5, r: 3.5, fill: end.s.color })
    );
    const text = svgEl("text", { class: "end-label", x: x(end.i) + 20, y: end.y });
    text.textContent = `${yFmt(end.v)} ${end.s.label}`;
    group.appendChild(text);
    svg.appendChild(group);
  }

  // Crosshair + one tooltip listing every series at the snapped X.
  const crosshair = svgEl("line", {
    class: "crosshair",
    x1: 0, x2: 0, y1: PAD.t, y2: PAD.t + innerH, visibility: "hidden",
  });
  svg.appendChild(crosshair);
  const overlay = svgEl("rect", {
    x: PAD.l - 10, y: PAD.t, width: innerW + 20, height: innerH, fill: "transparent",
  });
  overlay.style.cursor = onSelect ? "pointer" : "default";
  const indexAt = (evt) => {
    const rect = svg.getBoundingClientRect();
    const mx = ((evt.clientX - rect.left) / rect.width) * W;
    if (n <= 1) return 0;
    return Math.max(0, Math.min(n - 1, Math.round((mx - PAD.l) / step)));
  };
  overlay.addEventListener("pointermove", (evt) => {
    const i = indexAt(evt);
    crosshair.setAttribute("x1", x(i));
    crosshair.setAttribute("x2", x(i));
    crosshair.setAttribute("visibility", "visible");
    const rows = [];
    for (const s of series) {
      const p = s.points[i];
      if (!p || p.v == null) continue;
      let value = yFmt(p.v);
      if (p.lo != null && p.hi != null) value += ` [${yFmt(p.lo)}–${yFmt(p.hi)}]`;
      rows.push({ color: s.color, value, label: s.label });
    }
    if (rows.length) tooltip.show(evt.clientX, evt.clientY, xLabels[i], rows);
    else tooltip.hide();
  });
  overlay.addEventListener("pointerleave", () => {
    crosshair.setAttribute("visibility", "hidden");
    tooltip.hide();
  });
  if (onSelect) overlay.addEventListener("click", (evt) => onSelect(indexAt(evt)));
  svg.appendChild(overlay);

  container.replaceChildren(svg);
}

/* ---------------------------------------------------------------- sparkline */

export function sparkline(container, { values, color }) {
  const w = 200;
  const h = 46;
  const pad = 6;
  const svg = svgEl("svg", { viewBox: `0 0 ${w} ${h}` });
  const finite = values.filter((v) => v != null);
  if (!finite.length) {
    container.replaceChildren(svg);
    return;
  }
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  const span = max - min || 1;
  const n = values.length;
  const x = (i) => pad + (n > 1 ? (i * (w - 2 * pad)) / (n - 1) : (w - 2 * pad) / 2);
  const y = (v) => h - pad - ((v - min) / span) * (h - 2 * pad);

  let d = "";
  let area = "";
  values.forEach((v, i) => {
    if (v == null) return;
    d += (d ? " L " : "M ") + `${x(i)} ${y(v)}`;
    area += (area ? " L " : "M ") + `${x(i)} ${y(v)}`;
  });
  if (area) {
    const firstIdx = values.findIndex((v) => v != null);
    let lastIdx = -1;
    values.forEach((v, i) => { if (v != null) lastIdx = i; });
    area += ` L ${x(lastIdx)} ${h - pad} L ${x(firstIdx)} ${h - pad} Z`;
    svg.appendChild(svgEl("path", { d: area, fill: color, opacity: "0.1" }));
  }
  svg.appendChild(
    svgEl("path", { d, fill: "none", stroke: color, "stroke-width": 2, "stroke-linecap": "round" })
  );
  let lastIdx = -1;
  values.forEach((v, i) => { if (v != null) lastIdx = i; });
  const surface = getComputedStyle(document.documentElement).getPropertyValue("--surface-1").trim();
  svg.appendChild(
    svgEl("circle", { cx: x(lastIdx), cy: y(values[lastIdx]), r: 4, fill: color, stroke: surface, "stroke-width": 2 })
  );
  container.replaceChildren(svg);
}
