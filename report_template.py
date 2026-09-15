"""HTML shell for the usage report.

Kept in its own module so py2app picks it up as ordinary Python and the report
code stays readable. Two placeholders are substituted before the page is sent:

  /*__PAYLOAD__*/  the usage payload, or ``null`` in live mode (the page then
                   fetches it, so the first paint is not blocked by a scan)
  /*__CONFIG__*/   {live, endpoint, pollSeconds}

The page is deliberately light-only: it is read on a desktop next to the menu
bar app, and the palette below is the validated light-surface instance.
"""

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claude Usage</title>
<style>
  :root {
    color-scheme: light;
    --surface-0: #f9f9f7;
    --surface-1: #fcfcfb;
    --surface-2: #f3f2ee;
    --border: #e1e0d9;
    --border-strong: #c3c2b7;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --text-muted: #898781;
    --grid: #e1e0d9;
    --accent: #2a78d6;
    --seq-100: #cde2fb;
    --seq-250: #86b6ef;
    --seq-400: #3987e5;
    --seq-550: #1c5cab;
    --good: #0ca30c;
    --warning: #fab219;
    --critical: #d03b3b;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--surface-0);
    color: var(--text-primary);
    font: 14px/1.55 system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 1180px; margin: 0 auto; padding-block: 28px 40px; padding-left: 20px; padding-right: 20px; }

  header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  header h1 { font-size: 22px; font-weight: 650; margin: 0 0 5px; letter-spacing: -0.01em; }
  header p { margin: 0; color: var(--text-secondary); font-size: 13px; }

  .status {
    display: inline-flex; align-items: center; gap: 8px; flex-shrink: 0;
    background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 999px; padding: 6px 13px 6px 11px; font-size: 12.5px; color: var(--text-secondary);
    font-variant-numeric: tabular-nums;
  }
  .status i { width: 8px; height: 8px; border-radius: 50%; background: var(--good); flex-shrink: 0; }
  .status[data-state="stale"] i { background: var(--warning); }
  .status[data-state="offline"] i { background: var(--critical); }
  .status[data-state="static"] i { background: var(--border-strong); }

  .toolbar {
    position: sticky; top: 0; z-index: 8;
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    margin: 20px 0 18px; padding: 10px 0;
    background: var(--surface-0);
    border-bottom: 1px solid var(--border);
  }
  .toolbar .scope { color: var(--text-muted); font-size: 12.5px; margin-left: auto; font-variant-numeric: tabular-nums; }
  .toolbar .lbl { color: var(--text-muted); font-size: 12px; }

  .seg { display: inline-flex; border: 1px solid var(--border-strong); border-radius: 7px; overflow: hidden; background: var(--surface-1); }
  .seg button {
    appearance: none; border: 0; background: transparent; color: var(--text-secondary);
    font: inherit; font-size: 12.5px; padding: 5px 12px; cursor: pointer; white-space: nowrap;
  }
  .seg button + button { border-left: 1px solid var(--border-strong); }
  .seg button:hover { background: var(--surface-2); }
  .seg button[aria-pressed="true"] { background: var(--accent); color: #fff; }
  .seg button[aria-pressed="true"]:hover { background: var(--seq-550); }

  .cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 18px; }
  .card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 15px 16px; }
  .card .label { color: var(--text-secondary); font-size: 12px; }
  .card .value { font-size: 26px; font-weight: 620; margin-top: 6px; letter-spacing: -0.02em; }
  .card .sub { color: var(--text-muted); font-size: 12px; margin-top: 4px; font-variant-numeric: tabular-nums; }
  .card .delta { display: inline-flex; align-items: center; gap: 4px; color: var(--text-secondary); }
  .card .delta svg { width: 11px; height: 11px; fill: none; stroke: currentColor; stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; }
  .meter { height: 5px; border-radius: 3px; background: var(--seq-100); margin-top: 11px; overflow: hidden; }
  .meter i { display: block; height: 100%; background: var(--accent); border-radius: 3px; }
  .meter[data-level="warning"] i { background: var(--warning); }
  .meter[data-level="critical"] i { background: var(--critical); }

  .panel { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 18px 18px 14px; margin-bottom: 18px; }
  .panel-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .panel h2 { font-size: 14.5px; font-weight: 620; margin: 0; }
  .panel .hint { color: var(--text-muted); font-size: 12px; margin: 3px 0 14px; max-width: 78ch; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; align-items: start; }
  .two-col .panel { margin-bottom: 18px; }
  .section-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin: 26px 0 10px; }

  .chart { position: relative; width: 100%; }
  .chart svg { display: block; width: 100%; }
  .empty { color: var(--text-muted); font-size: 13px; padding: 26px 2px 30px; }

  .legend { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 12px; }
  .legend span { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--text-secondary); }
  .legend i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; flex-shrink: 0; }
  .legend i.line { width: 14px; height: 2px; border-radius: 2px; }

  .tbl-scroll { overflow-x: auto; margin-top: 4px; }
  table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
  th, td { text-align: right; padding: 8px 10px; border-bottom: 1px solid var(--grid); white-space: nowrap; font-variant-numeric: tabular-nums; }
  th { color: var(--text-secondary); font-weight: 560; border-bottom: 1px solid var(--border-strong); }
  th:first-child, td:first-child { text-align: left; }
  tbody tr:hover { background: var(--surface-2); }
  td.dim { color: var(--text-muted); }
  .swatch { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 6px; }
  .bar-cell { display: block; height: 5px; border-radius: 3px; background: var(--accent); }

  .tip {
    position: absolute; pointer-events: none; opacity: 0; transform: translate(-50%, -100%);
    background: #ffffff; border: 1px solid var(--border-strong); border-radius: 8px;
    padding: 8px 10px; font-size: 12px; line-height: 1.5; white-space: nowrap;
    box-shadow: 0 6px 20px rgba(11,11,11,.12); z-index: 5;
  }
  .tip b { font-weight: 620; display: block; margin-bottom: 4px; color: var(--text-secondary); font-size: 11.5px; }
  .tip .row { display: flex; align-items: center; gap: 14px; justify-content: space-between; }
  .tip .row i { width: 12px; height: 2px; border-radius: 2px; flex-shrink: 0; }
  .tip .row .k { display: inline-flex; align-items: center; gap: 7px; color: var(--text-secondary); }
  .tip .row .v { font-weight: 620; font-variant-numeric: tabular-nums; }
  .tip .sep { height: 1px; background: var(--grid); margin: 5px 0; }

  svg text { font-family: inherit; }
  /* labels that can land on a mark keep a surface-coloured halo so they stay legible */
  svg text.halo { paint-order: stroke; stroke: var(--surface-1); stroke-width: 3px; stroke-linejoin: round; }
  footer { color: var(--text-muted); font-size: 12px; margin-top: 8px; }
  .note { color: var(--text-muted); font-size: 12.5px; margin: 6px 0 0; max-width: 88ch; }
  .loading { opacity: .45; }

  @media (max-width: 960px) {
    .cards { grid-template-columns: repeat(2, 1fr); }
    .two-col { grid-template-columns: 1fr; }
    .toolbar .scope { margin-left: 0; width: 100%; }
  }
  @media (max-width: 540px) {
    .cards { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="wrap" id="root">
  <header>
    <div>
      <h1>Claude Usage</h1>
      <p id="meta">Loading usage data…</p>
    </div>
    <div class="status" id="status" data-state="static"><i></i><span id="statusText">Starting…</span></div>
  </header>

  <div class="toolbar">
    <span class="lbl">Range</span>
    <div class="seg" id="rangeSeg"></div>
    <span class="lbl">Metric</span>
    <div class="seg" id="metricSeg">
      <button data-metric="cost" aria-pressed="true">Cost</button>
      <button data-metric="tokens" aria-pressed="false">Tokens</button>
    </div>
    <span class="scope" id="scope"></span>
  </div>

  <section class="cards" id="cards"></section>

  <section class="panel">
    <div class="panel-head"><h2 id="trendTitle">Usage over time</h2></div>
    <p class="hint" id="trendHint"></p>
    <div class="chart" id="trendChart"></div>
    <div class="legend" id="trendLegend"></div>
  </section>

  <div class="two-col">
    <section class="panel">
      <h2>By model</h2>
      <p class="hint" id="modelHint"></p>
      <div class="chart" id="modelChart"></div>
    </section>
    <section class="panel">
      <h2>By project</h2>
      <p class="hint" id="projectHint"></p>
      <div class="chart" id="projectChart"></div>
    </section>
  </div>

  <p class="section-label">Quota weeks · always the full recorded history</p>

  <div class="two-col">
    <section class="panel">
      <h2>Usage by quota week</h2>
      <p class="hint" id="weekHint"></p>
      <div class="chart" id="weekChart"></div>
      <div class="legend" id="weekLegend"></div>
    </section>
    <section class="panel">
      <h2>All-models limit across the quota week</h2>
      <p class="hint" id="limitHint"></p>
      <div class="chart" id="limitChart"></div>
      <div class="legend" id="limitLegend"></div>
    </section>
  </div>

  <section class="panel">
    <div class="panel-head">
      <h2>Detail</h2>
      <div class="seg" id="tableSeg">
        <button data-table="day" aria-pressed="true">Daily</button>
        <button data-table="week" aria-pressed="false">Quota weeks</button>
        <button data-table="project" aria-pressed="false">Projects</button>
      </div>
    </div>
    <p class="hint" id="tableHint"></p>
    <div class="tbl-scroll"><table id="detailTable"></table></div>
  </section>

  <footer id="footer"></footer>
  <p class="note" id="note"></p>
</div>

<script>
let DATA = /*__PAYLOAD__*/;
const CFG = /*__CONFIG__*/;

const MODEL_ORDER = ["opus", "sonnet", "fable", "haiku", "other"];
const MODEL_LABEL = { opus: "Opus", sonnet: "Sonnet", fable: "Fable", haiku: "Haiku", other: "Other" };
const FALLBACK_COLORS = { opus: "#2a78d6", sonnet: "#eb6834", fable: "#1baf7a", haiku: "#eda100", other: "#4a3aa7" };
const DAY_MS = 86400000;

const RANGES = [
  { id: "today", label: "Today" },
  { id: "7d", label: "7 days", days: 7 },
  { id: "30d", label: "30 days", days: 30 },
  { id: "90d", label: "90 days", days: 90 },
  { id: "all", label: "All time" },
];

const STATE = { range: "7d", metric: "cost", table: "day" };
try {
  const saved = JSON.parse(localStorage.getItem("claudeUsageView") || "{}");
  if (RANGES.some(r => r.id === saved.range)) STATE.range = saved.range;
  if (saved.metric === "cost" || saved.metric === "tokens") STATE.metric = saved.metric;
  if (["day", "week", "project"].includes(saved.table)) STATE.table = saved.table;
} catch (e) { /* private mode or blocked storage - defaults are fine */ }
const persist = () => {
  try { localStorage.setItem("claudeUsageView", JSON.stringify(STATE)); } catch (e) { /* ignore */ }
};

let C = FALLBACK_COLORS;
let WEEK_MS = 7 * DAY_MS;

/* ---------- formatting ---------- */
const fmtTokens = n => n >= 1e9 ? (n / 1e9).toFixed(2) + "B"
  : n >= 1e6 ? (n / 1e6).toFixed(1) + "M"
  : n >= 1e3 ? (n / 1e3).toFixed(1) + "K" : String(Math.round(n));
const fmtCost = n => !n ? "$0" : n >= 100 ? "$" + n.toFixed(0) : n >= 1 ? "$" + n.toFixed(2) : "$" + n.toFixed(3);
const fmtVal = (n, m) => (m || STATE.metric) === "cost" ? fmtCost(n) : fmtTokens(n);
const fmtInt = n => Math.round(n).toLocaleString("en-US");
const fmtShare = (part, whole) => {
  if (!whole) return "0%";
  const pct = part / whole * 100;
  return pct > 0 && pct < 1 ? "<1%" : pct.toFixed(0) + "%";
};
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const mdy = d => MON[d.getMonth()] + " " + d.getDate();
const hm = d => String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
const weekLabel = t => mdy(new Date(t)) + "–" + mdy(new Date(t + WEEK_MS));
const clock = d => d.toLocaleTimeString("en-NZ", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
const esc = s => String(s).replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
const startOfDay = d => new Date(d.getFullYear(), d.getMonth(), d.getDate());
const dayKey = d => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
const parseDay = s => new Date(s + "T00:00:00");
const durationText = ms => {
  if (ms <= 0) return "now";
  const h = Math.floor(ms / 3600000), d = Math.floor(h / 24);
  if (d >= 1) return d + "d " + (h - d * 24) + "h";
  const m = Math.floor(ms / 60000);
  return h >= 1 ? h + "h " + (m - h * 60) + "m" : m + "m";
};

/* ---------- index (rebuilt whenever new data lands) ---------- */
let IDX = null;

function buildIndex() {
  C = (DATA && DATA.colors) || FALLBACK_COLORS;
  WEEK_MS = (DATA && DATA.weekSeconds ? DATA.weekSeconds : 604800) * 1000;

  const R = (DATA.records || []).map(r => Object.assign({}, r, { wt: new Date(r.w).getTime() }));
  const weekTimes = [];
  if (R.length) {
    const times = R.map(r => r.wt);
    for (let t = Math.min(...times); t <= Math.max(...times) + 1000; t += WEEK_MS) weekTimes.push(t);
  }

  const weeks = weekTimes.map(iso => {
    const rows = R.filter(r => r.wt === iso);
    const byModel = {};
    MODEL_ORDER.forEach(m => { byModel[m] = { cost: 0, tokens: 0 }; });
    const days = new Set();
    let calls = 0;
    rows.forEach(r => {
      const b = byModel[r.m] || byModel.other;
      b.cost += r.c;
      b.tokens += r.i + r.o + r.cr + r.cc;
      calls += r.n;
      days.add(r.d);
    });
    return {
      iso, byModel, calls, days: days.size,
      cost: rows.reduce((s, r) => s + r.c, 0),
      tokens: rows.reduce((s, r) => s + r.i + r.o + r.cr + r.cc, 0),
      input: rows.reduce((s, r) => s + r.i, 0),
      output: rows.reduce((s, r) => s + r.o, 0),
      cache: rows.reduce((s, r) => s + r.cr + r.cc, 0),
    };
  });

  const peakByWeek = {};
  (DATA.snapshots || []).forEach(s => {
    if (!s.w) return;
    const t = new Date(s.w).getTime();
    const cur = peakByWeek[t];
    if (!cur || s.all > cur.pct) peakByWeek[t] = { pct: s.all, manual: s.src === "manual" };
  });

  let pctSum = 0, costSum = 0;
  Object.entries(peakByWeek).forEach(([t, p]) => {
    const wk = weeks.find(w => w.iso === Number(t));
    if (wk && wk.cost > 0 && p.pct > 0) { pctSum += p.pct; costSum += wk.cost; }
  });

  const days = R.map(r => r.d).sort();
  IDX = {
    R, weeks, weekTimes, peakByWeek,
    hasManualPeak: Object.values(peakByWeek).some(v => v.manual),
    pctPerDollar: costSum > 0 ? pctSum / costSum : null,
    current: weeks.length ? weeks[weeks.length - 1] : null,
    activeModels: MODEL_ORDER.filter(m => weeks.some(w => w.byModel[m] && w.byModel[m].tokens > 0)),
    firstDay: days.length ? days[0] : null,
    lastDay: days.length ? days[days.length - 1] : null,
    latestSnap: (DATA.snapshots || []).length ? DATA.snapshots[DATA.snapshots.length - 1] : null,
  };
}

const estPct = cost => {
  if (!IDX.pctPerDollar || !cost) return null;
  const v = cost * IDX.pctPerDollar;
  return v >= 100 ? ">100%" : v < 1 ? "<1%" : "~" + v.toFixed(0) + "%";
};

/* ---------- the selected window ---------- */
function currentWindow() {
  const now = new Date();
  const def = RANGES.find(r => r.id === STATE.range) || RANGES[1];
  if (def.id === "today") {
    return { start: startOfDay(now), end: now, gran: "hour", label: "Today", days: 1,
             compare: "vs the same hours yesterday" };
  }
  if (def.id === "all") {
    const first = IDX.firstDay ? parseDay(IDX.firstDay) : startOfDay(now);
    const span = Math.round((startOfDay(now) - first) / DAY_MS) + 1;
    return { start: first, end: now, gran: span > 140 ? "week" : "day", label: "All time", days: span,
             compare: "" };
  }
  return {
    start: startOfDay(new Date(now.getTime() - (def.days - 1) * DAY_MS)),
    end: now, gran: "day", label: def.label, days: def.days,
    compare: "vs the previous " + def.days + " days",
  };
}

const inWindow = (r, win) => r.d >= dayKey(win.start) && r.d <= dayKey(win.end);

function recordsIn(win) { return IDX.R.filter(r => inWindow(r, win)); }

function emptyBucket(t, label) {
  const byModel = {};
  MODEL_ORDER.forEach(m => { byModel[m] = { cost: 0, tokens: 0 }; });
  return { t, label, byModel, cost: 0, tokens: 0, calls: 0 };
}

function addRow(b, m, cost, tokens, calls) {
  const slot = b.byModel[m] || b.byModel.other;
  slot.cost += cost;
  slot.tokens += tokens;
  b.cost += cost;
  b.tokens += tokens;
  b.calls += calls;
}

/** Continuous buckets across the window - gaps stay visible as empty slots. */
function seriesFor(win) {
  if (win.gran === "hour") {
    const out = [];
    const first = win.start.getTime();
    const last = new Date(win.end.getFullYear(), win.end.getMonth(), win.end.getDate(), win.end.getHours()).getTime();
    for (let t = first; t <= last; t += 3600000) out.push(emptyBucket(t, hm(new Date(t))));
    const byT = {};
    out.forEach(b => { byT[b.t] = b; });
    (DATA.hourly || []).forEach(h => {
      const b = byT[h.t];
      if (b) addRow(b, h.m, h.c, h.k, h.n);
    });
    return out;
  }
  if (win.gran === "week") {
    const out = IDX.weeks.map(w => emptyBucket(w.iso, mdy(new Date(w.iso))));
    const byT = {};
    out.forEach(b => { byT[b.t] = b; });
    recordsIn(win).forEach(r => {
      const b = byT[r.wt];
      if (b) addRow(b, r.m, r.c, r.i + r.o + r.cr + r.cc, r.n);
    });
    return out;
  }
  const out = [];
  for (let t = win.start.getTime(); t <= win.end.getTime(); t += DAY_MS) {
    const d = new Date(t);
    out.push(emptyBucket(startOfDay(d).getTime(), mdy(d)));
  }
  const byKey = {};
  out.forEach(b => { byKey[dayKey(new Date(b.t))] = b; });
  recordsIn(win).forEach(r => {
    const b = byKey[r.d];
    if (b) addRow(b, r.m, r.c, r.i + r.o + r.cr + r.cc, r.n);
  });
  return out;
}

/* ---------- svg helpers ---------- */
const NS = "http://www.w3.org/2000/svg";
function el(name, attrs, parent) {
  const node = document.createElementNS(NS, name);
  for (const k in attrs) node.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(node);
  return node;
}
function svgRoot(host, height) {
  host.innerHTML = "";
  const width = Math.max(host.clientWidth || 640, 300);
  const svg = el("svg", { width, height, viewBox: "0 0 " + width + " " + height, role: "img" }, host);
  const tip = document.createElement("div");
  tip.className = "tip";
  host.appendChild(tip);
  return { svg, width, height, tip };
}
function showTip(host, tip, x, y, html) {
  tip.innerHTML = html;
  tip.style.opacity = 1;
  const half = tip.offsetWidth / 2;
  tip.style.left = Math.min(Math.max(x, half + 4), host.clientWidth - half - 4) + "px";
  tip.style.top = Math.max(y - 10, tip.offsetHeight + 6) + "px";
}
const hideTip = tip => { tip.style.opacity = 0; };

/** Ticks from 0 to a round value at or above `max` - the top tick sets the
 *  scale, so it must cover the data or the tallest bars draw off the top. */
function niceTicks(max, count) {
  const raw = (max || 1) / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw) || mag * 10;
  const top = Math.ceil(max / step) * step;
  const out = [];
  for (let v = 0; v <= top + step * 0.001; v += step) out.push(v);
  return out;
}

function gridlines(svg, w, pad, ticks, y, fmt) {
  ticks.forEach(v => {
    el("line", { x1: pad.l, y1: y(v), x2: w - pad.r, y2: y(v), stroke: "var(--grid)", "stroke-width": 1 }, svg);
    el("text", { x: pad.l - 8, y: y(v) + 4, "text-anchor": "end", fill: "var(--text-muted)", "font-size": 11 }, svg)
      .textContent = fmt(v);
  });
}

const tipRow = (color, label, value) =>
  '<div class="row"><span class="k">' + (color ? '<i style="background:' + color + '"></i>' : "") +
  esc(label) + '</span><span class="v">' + esc(value) + "</span></div>";

/* ---------- chart: usage over time (stacked columns) ---------- */
function renderTrend() {
  const host = document.getElementById("trendChart");
  const legend = document.getElementById("trendLegend");
  const win = currentWindow();
  const buckets = seriesFor(win);
  const models = MODEL_ORDER.filter(m => buckets.some(b => b.byModel[m][STATE.metric] > 0));

  document.getElementById("trendTitle").textContent =
    win.gran === "hour" ? "Usage by hour" : win.gran === "week" ? "Usage by quota week" : "Usage by day";
  document.getElementById("trendHint").textContent =
    (STATE.metric === "cost" ? "Estimated spend" : "Tokens read and written") +
    " per " + (win.gran === "hour" ? "hour" : win.gran === "week" ? "quota week" : "day") +
    ", stacked by model. " + (win.gran === "hour"
      ? "Hourly detail covers the last 72 hours."
      : "Empty slots are days with no recorded activity.");

  if (!buckets.length || !models.length) {
    host.innerHTML = '<p class="empty">No usage recorded in this range.</p>';
    legend.innerHTML = "";
    return;
  }

  const H = 330, pad = { t: 24, r: 20, b: 46, l: 64 };
  const { svg, width, tip } = svgRoot(host, H);
  const plotW = width - pad.l - pad.r, plotH = H - pad.t - pad.b;
  const peak = Math.max(...buckets.map(b => b[STATE.metric]), 0);
  const ticks = niceTicks(peak * 1.1 || 1, 4);
  const max = ticks[ticks.length - 1] || 1;
  const y = v => pad.t + plotH - (v / max) * plotH;
  gridlines(svg, width, pad, ticks, y,
    v => STATE.metric === "cost" ? (v >= 1 ? "$" + fmtInt(v) : "$" + v.toFixed(2)) : fmtTokens(v));

  const step = plotW / buckets.length;
  const bw = Math.min(24, Math.max(step * 0.62, 2));
  const gap = bw > 6 ? 2 : 0;

  // one label roughly every 74px, always including the most recent slot
  const every = Math.max(1, Math.ceil(buckets.length / Math.max(1, Math.floor(plotW / 74))));
  const active = buckets.filter(b => b[STATE.metric] > 0);
  const avg = active.length ? active.reduce((s, b) => s + b[STATE.metric], 0) / active.length : 0;
  const peakIdx = buckets.reduce((bi, b, i) => b[STATE.metric] > buckets[bi][STATE.metric] ? i : bi, 0);

  buckets.forEach((b, i) => {
    const cx = pad.l + step * i + step / 2;
    let acc = 0;
    const segs = models.map(m => ({ m, v: b.byModel[m][STATE.metric] })).filter(s => s.v > 0);
    segs.forEach((s, si) => {
      const y0 = y(acc), y1 = y(acc + s.v);
      let h = Math.max(y0 - y1, 1);
      if (si > 0) h = Math.max(h - gap, 1);
      el("rect", {
        x: cx - bw / 2, y: y1, width: bw, height: h,
        fill: C[s.m] || C.other, rx: si === segs.length - 1 ? Math.min(4, bw / 2) : 0,
      }, svg);
      acc += s.v;
    });

    if ((i - (buckets.length - 1)) % every === 0 || i === buckets.length - 1) {
      el("text", { x: cx, y: H - pad.b + 18, "text-anchor": "middle", fill: "var(--text-secondary)", "font-size": 11 }, svg)
        .textContent = b.label;
    }
    if ((i === buckets.length - 1 || i === peakIdx) && b[STATE.metric] > 0 &&
        (i === buckets.length - 1 || Math.abs(i - (buckets.length - 1)) > 1)) {
      el("text", {
        x: cx, y: Math.max(y(b[STATE.metric]) - 10, 12), "text-anchor": "middle",
        fill: "var(--text-primary)", "font-size": 11.5, "font-weight": 620, class: "halo",
      }, svg).textContent = fmtVal(b[STATE.metric]);
    }

    const hit = el("rect", { x: pad.l + step * i, y: pad.t, width: step, height: plotH, fill: "transparent" }, svg);
    let wash = null;
    hit.addEventListener("mouseenter", () => {
      wash = el("rect", { x: pad.l + step * i, y: pad.t, width: step, height: plotH, fill: "rgba(11,11,11,0.035)" }, svg);
      svg.insertBefore(wash, svg.firstChild);
      const rows = models.filter(m => b.byModel[m][STATE.metric] > 0)
        .map(m => tipRow(C[m] || C.other, MODEL_LABEL[m], fmtVal(b.byModel[m][STATE.metric]))).join("");
      const when = win.gran === "hour"
        ? mdy(new Date(b.t)) + " " + hm(new Date(b.t)) + "–" + hm(new Date(b.t + 3600000))
        : win.gran === "week" ? weekLabel(b.t) : mdy(new Date(b.t));
      showTip(host, tip, cx, y(b[STATE.metric]),
        "<b>" + esc(when) + "</b>" + tipRow(null, "Total", fmtVal(b[STATE.metric])) +
        (rows ? '<div class="sep"></div>' + rows : "") +
        '<div class="sep"></div>' + tipRow(null, "Messages", fmtInt(b.calls)));
    });
    hit.addEventListener("mouseleave", () => {
      hideTip(tip);
      if (wash && wash.parentNode) wash.parentNode.removeChild(wash);
      wash = null;
    });
  });

  if (avg > 0 && buckets.length > 2) {
    el("line", {
      x1: pad.l, y1: y(avg), x2: width - pad.r, y2: y(avg),
      stroke: "var(--border-strong)", "stroke-width": 1,
    }, svg);
    el("text", {
      x: width - pad.r, y: Math.max(y(avg) - 6, 10), "text-anchor": "end",
      fill: "var(--text-muted)", "font-size": 10.5, class: "halo",
    }, svg).textContent = "avg " + fmtVal(avg) + " per active " +
      (win.gran === "hour" ? "hour" : win.gran === "week" ? "week" : "day");
  }

  legend.innerHTML = models.map(m =>
    '<span><i style="background:' + (C[m] || C.other) + '"></i>' + MODEL_LABEL[m] + "</span>").join("");
}

/* ---------- chart: by model (donut) ---------- */
function renderModelChart() {
  const host = document.getElementById("modelChart");
  const win = currentWindow();
  const rows = recordsIn(win);
  const metric = STATE.metric;
  const valueOf = r => metric === "cost" ? r.c : r.i + r.o + r.cr + r.cc;
  const totals = MODEL_ORDER
    .map(m => ({ m, v: rows.filter(r => r.m === m).reduce((s, r) => s + valueOf(r), 0) }))
    .filter(d => d.v > 0).sort((a, b) => b.v - a.v);
  const sum = totals.reduce((s, d) => s + d.v, 0);

  document.getElementById("modelHint").textContent =
    "Share of " + (metric === "cost" ? "estimated spend" : "tokens") + " in the selected range.";
  if (!sum) { host.innerHTML = '<p class="empty">No usage recorded in this range.</p>'; return; }

  const H = 236;
  const { svg, width, tip } = svgRoot(host, H);
  const cx = 104, cy = H / 2, rO = 78, rI = 50;
  let a0 = -Math.PI / 2;

  totals.forEach(d => {
    const a1 = a0 + (d.v / sum) * Math.PI * 2;
    const g = totals.length > 1 ? 0.014 : 0;
    const s = a0 + g, e = Math.max(a1 - g, a0 + 0.001);
    const large = e - s > Math.PI ? 1 : 0;
    const path = [
      "M", cx + rO * Math.cos(s), cy + rO * Math.sin(s),
      "A", rO, rO, 0, large, 1, cx + rO * Math.cos(e), cy + rO * Math.sin(e),
      "L", cx + rI * Math.cos(e), cy + rI * Math.sin(e),
      "A", rI, rI, 0, large, 0, cx + rI * Math.cos(s), cy + rI * Math.sin(s), "Z",
    ].join(" ");
    const arc = el("path", { d: path, fill: C[d.m] || C.other }, svg);
    arc.addEventListener("mouseenter", () => showTip(host, tip, cx, cy - rO,
      "<b>" + MODEL_LABEL[d.m] + "</b>" + tipRow(C[d.m] || C.other, metric === "cost" ? "Cost" : "Tokens", fmtVal(d.v)) +
      tipRow(null, "Share", fmtShare(d.v, sum))));
    arc.addEventListener("mouseleave", () => hideTip(tip));
    a0 = a1;
  });

  el("text", { x: cx, y: cy - 2, "text-anchor": "middle", fill: "var(--text-primary)", "font-size": 18, "font-weight": 620 }, svg)
    .textContent = fmtVal(sum);
  el("text", { x: cx, y: cy + 16, "text-anchor": "middle", fill: "var(--text-muted)", "font-size": 11 }, svg)
    .textContent = "total";

  // direct labels carry identity where the light hues fall under 3:1 on the surface
  const labelX = Math.min(212, width - 150);
  totals.forEach((d, i) => {
    const ty = cy - (totals.length - 1) * 12 + i * 24;
    el("rect", { x: labelX, y: ty - 9, width: 10, height: 10, rx: 3, fill: C[d.m] || C.other }, svg);
    el("text", { x: labelX + 16, y: ty, fill: "var(--text-secondary)", "font-size": 12.5 }, svg)
      .textContent = MODEL_LABEL[d.m];
    el("text", { x: width - 4, y: ty, "text-anchor": "end", fill: "var(--text-primary)", "font-size": 12.5 }, svg)
      .textContent = fmtVal(d.v) + "  ·  " + fmtShare(d.v, sum);
  });
}

/* ---------- chart: by project (horizontal bars) ---------- */
function renderProjectChart() {
  const host = document.getElementById("projectChart");
  const win = currentWindow();
  const metric = STATE.metric;
  const valueOf = r => metric === "cost" ? r.c : r.i + r.o + r.cr + r.cc;
  const map = {};
  recordsIn(win).forEach(r => { map[r.p] = (map[r.p] || 0) + valueOf(r); });
  let rows = Object.entries(map).map(([p, v]) => ({ p, v })).filter(d => d.v > 0).sort((a, b) => b.v - a.v);
  const total = rows.reduce((s, d) => s + d.v, 0);
  const hidden = rows.slice(8);
  rows = rows.slice(0, 8);
  if (hidden.length) rows.push({ p: "Other (" + hidden.length + ")", v: hidden.reduce((s, d) => s + d.v, 0), fold: true });

  document.getElementById("projectHint").textContent = rows.length
    ? "Working directories by " + (metric === "cost" ? "estimated spend" : "tokens") + " in the selected range."
    : "";
  if (!rows.length) { host.innerHTML = '<p class="empty">No usage recorded in this range.</p>'; return; }

  const rowH = 28, H = rows.length * rowH + 10;
  const { svg, width, tip } = svgRoot(host, H);
  const labelW = Math.min(158, Math.max(92, width * 0.32));
  const max = Math.max(...rows.map(d => d.v)) || 1;
  const barMax = Math.max(width - labelW - 76, 30);

  rows.forEach((d, i) => {
    const top = i * rowH + 6;
    const w = Math.max((d.v / max) * barMax, 2);
    el("text", { x: 0, y: top + 13, fill: "var(--text-secondary)", "font-size": 12.5 }, svg)
      .textContent = d.p.length > 22 ? d.p.slice(0, 21) + "…" : d.p;
    el("rect", {
      x: labelW, y: top + 4, width: w, height: 12, rx: 4,
      fill: d.fold ? "var(--seq-250)" : "var(--accent)",
    }, svg);
    el("text", { x: labelW + w + 8, y: top + 14, fill: "var(--text-primary)", "font-size": 12 }, svg)
      .textContent = fmtVal(d.v);

    const hit = el("rect", { x: 0, y: top - 3, width, height: rowH, fill: "transparent" }, svg);
    hit.addEventListener("mouseenter", () => showTip(host, tip, labelW + w / 2, top,
      "<b>" + esc(d.p) + "</b>" + tipRow("var(--accent)", metric === "cost" ? "Cost" : "Tokens", fmtVal(d.v)) +
      tipRow(null, "Share", fmtShare(d.v, total))));
    hit.addEventListener("mouseleave", () => hideTip(tip));
  });
}

/* ---------- chart: usage by quota week ---------- */
function renderWeekChart() {
  const host = document.getElementById("weekChart");
  const legend = document.getElementById("weekLegend");
  const hint = document.getElementById("weekHint");
  const weeks = IDX.weeks;
  if (!weeks.length) {
    host.innerHTML = '<p class="empty">No local usage records found under ~/.claude/projects.</p>';
    hint.textContent = "";
    legend.innerHTML = "";
    return;
  }
  hint.textContent = (STATE.metric === "cost" ? "Estimated spend" : "Tokens")
    + " per quota week, stacked by model. The final bar is the week in progress.";

  const H = 280, pad = { t: 22, r: 14, b: 46, l: 58 };
  const { svg, width, tip } = svgRoot(host, H);
  const plotW = width - pad.l - pad.r, plotH = H - pad.t - pad.b;
  const ticks = niceTicks(Math.max(...weeks.map(w => w[STATE.metric]), 1) * 1.12, 4);
  const max = ticks[ticks.length - 1] || 1;
  const y = v => pad.t + plotH - (v / max) * plotH;
  gridlines(svg, width, pad, ticks, y,
    v => STATE.metric === "cost" ? (v >= 1 ? "$" + fmtInt(v) : "$" + v.toFixed(2)) : fmtTokens(v));

  const step = plotW / weeks.length;
  const bw = Math.min(24, step * 0.6);
  const models = IDX.activeModels;
  const every = Math.max(1, Math.ceil(weeks.length / Math.max(1, Math.floor(plotW / 62))));

  weeks.forEach((wk, i) => {
    const cx = pad.l + step * i + step / 2;
    let acc = 0;
    const segs = models.map(m => ({ m, v: wk.byModel[m] ? wk.byModel[m][STATE.metric] : 0 })).filter(s => s.v > 0);
    segs.forEach((s, si) => {
      const y0 = y(acc), y1 = y(acc + s.v);
      let h = Math.max(y0 - y1, 1);
      if (si > 0) h = Math.max(h - 2, 1);
      el("rect", {
        x: cx - bw / 2, y: y1, width: bw, height: h,
        fill: C[s.m] || C.other, rx: si === segs.length - 1 ? Math.min(4, bw / 2) : 0,
      }, svg);
      acc += s.v;
    });
    if (i === weeks.length - 1 && wk[STATE.metric] > 0) {
      el("text", {
        x: cx, y: Math.max(y(wk[STATE.metric]) - 10, 12), "text-anchor": "middle",
        fill: "var(--text-primary)", "font-size": 11.5, "font-weight": 620, class: "halo",
      }, svg).textContent = fmtVal(wk[STATE.metric]);
    }
    if ((i - (weeks.length - 1)) % every === 0 || i === weeks.length - 1) {
      el("text", { x: cx, y: H - pad.b + 18, "text-anchor": "middle", fill: "var(--text-secondary)", "font-size": 11 }, svg)
        .textContent = mdy(new Date(wk.iso));
    }
    if (i === weeks.length - 1) {
      el("text", { x: cx, y: H - pad.b + 33, "text-anchor": "middle", fill: "var(--text-muted)", "font-size": 10.5 }, svg)
        .textContent = "in progress";
    }

    const hit = el("rect", { x: pad.l + step * i, y: pad.t, width: step, height: plotH, fill: "transparent" }, svg);
    hit.addEventListener("mouseenter", () => {
      const rows = models.filter(m => wk.byModel[m] && wk.byModel[m][STATE.metric] > 0)
        .map(m => tipRow(C[m] || C.other, MODEL_LABEL[m], fmtVal(wk.byModel[m][STATE.metric]))).join("");
      showTip(host, tip, cx, y(wk[STATE.metric]),
        "<b>" + esc(weekLabel(wk.iso)) + "</b>" + tipRow(null, "Total", fmtVal(wk[STATE.metric])) +
        (rows ? '<div class="sep"></div>' + rows : "") +
        '<div class="sep"></div>' + tipRow(null, "Active days", String(wk.days)));
    });
    hit.addEventListener("mouseleave", () => hideTip(tip));
  });

  legend.innerHTML = models.map(m =>
    '<span><i style="background:' + (C[m] || C.other) + '"></i>' + MODEL_LABEL[m] + "</span>").join("");
}

/* ---------- chart: all-models limit across the week ---------- */
function renderLimitChart() {
  const host = document.getElementById("limitChart");
  const hint = document.getElementById("limitHint");
  const legend = document.getElementById("limitLegend");
  const snaps = (DATA.snapshots || []).filter(s => s.w);

  if (snaps.length < 2) {
    host.innerHTML = '<p class="empty">No limit history yet. The app records the All Models percentage on every refresh; this chart fills in from the next refresh onward.</p>';
    hint.textContent = "";
    legend.innerHTML = "";
    return;
  }

  const byWeek = {};
  snaps.forEach(s => {
    const t = new Date(s.w).getTime();
    (byWeek[t] = byWeek[t] || []).push(s);
  });
  const isos = Object.keys(byWeek).map(Number).sort((a, b) => a - b).slice(-5);
  hint.textContent = "Recorded All Models utilization, one line per quota week, plotted against days elapsed since that week's reset.";

  const H = 280, pad = { t: 20, r: 22, b: 44, l: 48 };
  const { svg, width, tip } = svgRoot(host, H);
  const plotW = width - pad.l - pad.r, plotH = H - pad.t - pad.b;
  const maxPct = Math.max(10, ...snaps.map(s => s.all)) * 1.15;
  const x = d => pad.l + (d / 7) * plotW;
  const y = v => pad.t + plotH - (v / maxPct) * plotH;
  gridlines(svg, width, pad, niceTicks(maxPct, 4), y, v => Math.round(v) + "%");

  for (let d = 0; d <= 7; d++) {
    el("text", { x: x(d), y: H - pad.b + 18, "text-anchor": "middle", fill: "var(--text-secondary)", "font-size": 11 }, svg)
      .textContent = d === 0 ? "reset" : "d" + d;
  }

  const ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#1c5cab"];
  const shades = isos.map((_, i) => ramp[ramp.length - isos.length + i]);

  isos.forEach((iso, idx) => {
    const pts = byWeek[iso]
      .map(s => ({ d: (new Date(s.ts).getTime() - iso) / WEEK_MS * 7, v: s.all, ts: s.ts }))
      .filter(p => p.d >= 0 && p.d <= 7).sort((a, b) => a.d - b.d);
    if (!pts.length) return;
    const isLast = idx === isos.length - 1;
    el("path", {
      d: pts.map((p, i) => (i ? "L" : "M") + x(p.d).toFixed(1) + " " + y(p.v).toFixed(1)).join(" "),
      fill: "none", stroke: shades[idx], "stroke-width": isLast ? 2 : 1.5,
      "stroke-linejoin": "round", "stroke-linecap": "round",
    }, svg);

    const last = pts[pts.length - 1];
    el("circle", { cx: x(last.d), cy: y(last.v), r: 4, fill: shades[idx], stroke: "var(--surface-1)", "stroke-width": 2 }, svg);
    if (isLast) {
      el("text", {
        x: Math.min(x(last.d) + 9, width - pad.r), y: Math.max(y(last.v) - 9, 12),
        fill: "var(--text-primary)", "font-size": 12, "font-weight": 620, class: "halo",
        "text-anchor": x(last.d) > width - 80 ? "end" : "start",
      }, svg).textContent = last.v + "%";
    }

    pts.forEach(p => {
      const hit = el("circle", { cx: x(p.d), cy: y(p.v), r: 12, fill: "transparent" }, svg);
      hit.addEventListener("mouseenter", () => showTip(host, tip, x(p.d), y(p.v),
        "<b>" + esc(weekLabel(iso)) + "</b>" + tipRow(shades[idx], "All Models", p.v + "%") +
        tipRow(null, "Recorded", new Date(p.ts).toLocaleString("en-NZ", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }))));
      hit.addEventListener("mouseleave", () => hideTip(tip));
    });
  });

  legend.innerHTML = isos.map((iso, i) =>
    '<span><i class="line" style="background:' + shades[i] + '"></i>' + esc(weekLabel(iso)) +
    (i === isos.length - 1 ? " (current)" : "") + "</span>").join("");
}

/* ---------- stat tiles ---------- */
const ARROW_UP = '<svg viewBox="0 0 24 24"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
const ARROW_DOWN = '<svg viewBox="0 0 24 24"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>';

function renderCards() {
  const host = document.getElementById("cards");
  const win = currentWindow();
  const metric = STATE.metric;
  const valueOf = r => metric === "cost" ? r.c : r.i + r.o + r.cr + r.cc;

  const cur = recordsIn(win);
  const curVal = cur.reduce((s, r) => s + valueOf(r), 0);
  const curCalls = cur.reduce((s, r) => s + r.n, 0);

  const spanMs = win.end - win.start;
  const prevWin = { start: new Date(win.start.getTime() - spanMs), end: new Date(win.start.getTime() - 1) };
  const prevVal = IDX.R.filter(r => inWindow(r, prevWin)).reduce((s, r) => s + valueOf(r), 0);
  const delta = prevVal > 0 ? (curVal - prevVal) / prevVal * 100 : null;

  const buckets = seriesFor(win).filter(b => b[metric] > 0);
  const avg = buckets.length ? buckets.reduce((s, b) => s + b[metric], 0) / buckets.length : 0;
  const top = buckets.slice().sort((a, b) => b[metric] - a[metric])[0];
  const unit = win.gran === "hour" ? "hour" : win.gran === "week" ? "week" : "day";

  const snap = IDX.latestSnap;
  const pct = snap ? snap.all : null;
  const level = pct === null ? "" : pct >= 95 ? "critical" : pct >= 80 ? "warning" : "";
  const reset = DATA.nextReset ? new Date(DATA.nextReset) : null;

  const tiles = [];
  tiles.push(
    '<div class="card"><div class="label">All Models this quota week</div>' +
    '<div class="value">' + (pct === null ? "—" : pct + "%") + "</div>" +
    '<div class="meter"' + (level ? ' data-level="' + level + '"' : "") + '><i style="width:' +
      Math.max(0, Math.min(100, pct || 0)) + '%"></i></div>' +
    '<div class="sub">' + (reset ? "resets in " + durationText(reset - new Date()) : "awaiting first snapshot") +
    (snap ? " · read " + esc(clock(new Date(snap.ts))) : "") + "</div></div>"
  );
  tiles.push(
    '<div class="card"><div class="label">' + (metric === "cost" ? "Cost" : "Tokens") + " · " + esc(win.label) + "</div>" +
    '<div class="value">' + fmtVal(curVal) + "</div>" +
    '<div class="sub">' + (delta === null || !win.compare
      ? "no earlier period to compare"
      : '<span class="delta">' + (delta >= 0 ? ARROW_UP : ARROW_DOWN) + Math.abs(delta).toFixed(0) +
        "% " + esc(win.compare) + "</span>") + "</div></div>"
  );
  tiles.push(
    '<div class="card"><div class="label">Messages · ' + esc(win.label) + "</div>" +
    '<div class="value">' + fmtInt(curCalls) + "</div>" +
    '<div class="sub">' + (curCalls ? fmtVal(curVal / curCalls) + " per message" : "no assistant messages") + "</div></div>"
  );
  tiles.push(
    '<div class="card"><div class="label">Average per active ' + unit + "</div>" +
    '<div class="value">' + (buckets.length ? fmtVal(avg) : "—") + "</div>" +
    '<div class="sub">' + (top ? "peak " + esc(top.label) + " · " + fmtVal(top[metric]) : "no activity") + "</div></div>"
  );

  host.innerHTML = tiles.join("");
}

/* ---------- detail tables ---------- */
function renderTable() {
  const t = document.getElementById("detailTable");
  const hint = document.getElementById("tableHint");
  const win = currentWindow();

  if (STATE.table === "week") {
    hint.textContent = "Quota weeks run from one reset to the next, so each row matches what the weekly limit counted. "
      + (IDX.pctPerDollar
        ? "Peak All Models is known only for weeks the app has recorded; Est. extrapolates the rest from spend at the observed ratio (about "
          + fmtCost(1 / IDX.pctPerDollar) + " per percentage point) and should be read as an order of magnitude."
          + (IDX.hasManualPeak ? " Values marked * were reported manually rather than recorded by the app." : "")
        : "Est. stays empty until the app has recorded at least one week of All Models readings to calibrate against.");
    const head = "<thead><tr><th>Quota week</th><th>Peak All Models</th><th>Est.</th><th>Cost</th><th>Tokens</th>"
      + "<th>Input</th><th>Output</th><th>Cache</th><th>Messages</th><th>Active days</th></tr></thead>";
    const body = IDX.weeks.slice().reverse().map(w => {
      const peak = IDX.peakByWeek[w.iso];
      const est = peak === undefined ? estPct(w.cost) : null;
      return "<tr><td>" + esc(weekLabel(w.iso)) + (w === IDX.current ? ' <span class="dim">(current)</span>' : "") + "</td>"
        + '<td class="' + (peak === undefined ? "dim" : "") + '">' + (peak === undefined ? "—" : peak.pct + "%" + (peak.manual ? "*" : "")) + "</td>"
        + '<td class="dim">' + (est === null ? "—" : est) + "</td>"
        + "<td>" + fmtCost(w.cost) + "</td><td>" + fmtTokens(w.tokens) + "</td>"
        + '<td class="dim">' + fmtTokens(w.input) + '</td><td class="dim">' + fmtTokens(w.output) + "</td>"
        + '<td class="dim">' + fmtTokens(w.cache) + '</td><td class="dim">' + fmtInt(w.calls) + "</td>"
        + '<td class="dim">' + w.days + "</td></tr>";
    }).join("");
    t.innerHTML = head + "<tbody>" + body + "</tbody>";
    return;
  }

  if (STATE.table === "project") {
    hint.textContent = "Working directories in the selected range, by estimated spend.";
    const map = {};
    recordsIn(win).forEach(r => {
      const d = (map[r.p] = map[r.p] || { cost: 0, tokens: 0, calls: 0, days: new Set() });
      d.cost += r.c;
      d.tokens += r.i + r.o + r.cr + r.cc;
      d.calls += r.n;
      d.days.add(r.d);
    });
    const rows = Object.entries(map).sort((a, b) => b[1].cost - a[1].cost);
    const total = rows.reduce((s, [, v]) => s + v.cost, 0);
    const max = rows.length ? rows[0][1].cost : 1;
    const head = "<thead><tr><th>Project</th><th>Cost</th><th>Share</th><th style=\"width:26%\"></th>"
      + "<th>Tokens</th><th>Messages</th><th>Active days</th></tr></thead>";
    const body = rows.map(([p, v]) =>
      "<tr><td>" + esc(p) + "</td><td>" + fmtCost(v.cost) + "</td>"
      + '<td class="dim">' + fmtShare(v.cost, total) + "</td>"
      + '<td><span class="bar-cell" style="width:' + Math.max(2, v.cost / max * 100) + '%"></span></td>'
      + '<td class="dim">' + fmtTokens(v.tokens) + '</td><td class="dim">' + fmtInt(v.calls) + "</td>"
      + '<td class="dim">' + v.days.size + "</td></tr>").join("");
    t.innerHTML = head + "<tbody>" + (body || '<tr><td colspan="7" class="dim">No usage recorded in this range.</td></tr>') + "</tbody>";
    return;
  }

  hint.textContent = "Every day in the selected range, newest first.";
  const map = {};
  recordsIn(win).forEach(r => {
    const d = (map[r.d] = map[r.d] || { cost: 0, tokens: 0, calls: 0, models: {}, projects: new Set() });
    d.cost += r.c;
    d.tokens += r.i + r.o + r.cr + r.cc;
    d.calls += r.n;
    d.models[r.m] = (d.models[r.m] || 0) + r.c;
    d.projects.add(r.p);
  });
  const days = Object.keys(map).sort().reverse();
  const head = "<thead><tr><th>Date</th><th>Cost</th><th>Tokens</th><th>Messages</th><th>Projects</th>"
    + '<th style="text-align:left">Models</th></tr></thead>';
  const body = days.map(d => {
    const v = map[d];
    const models = Object.entries(v.models).sort((a, b) => b[1] - a[1])
      .map(([m, c]) => '<span class="swatch" style="background:' + (C[m] || C.other) + '"></span>' + MODEL_LABEL[m] + " " + fmtCost(c))
      .join(" &nbsp; ");
    const dt = parseDay(d);
    return "<tr><td>" + mdy(dt) + ", " + dt.getFullYear() + "</td><td>" + fmtCost(v.cost) + "</td>"
      + "<td>" + fmtTokens(v.tokens) + '</td><td class="dim">' + fmtInt(v.calls) + "</td>"
      + '<td class="dim">' + v.projects.size + "</td>"
      + '<td style="text-align:left" class="dim">' + models + "</td></tr>";
  }).join("");
  t.innerHTML = head + "<tbody>" + (body || '<tr><td colspan="6" class="dim">No usage recorded in this range.</td></tr>') + "</tbody>";
}

/* ---------- header, scope, footer ---------- */
function renderMeta() {
  const win = currentWindow();
  document.getElementById("scope").textContent = win.gran === "hour"
    ? mdy(win.start) + " · " + hm(win.start) + "–" + hm(win.end) + " · hourly"
    : mdy(win.start) + " – " + mdy(win.end) + " · " + win.days + " days · " + (win.gran === "week" ? "by quota week" : "daily");

  document.getElementById("meta").textContent =
    (DATA.firstSeen ? "Local records from " + new Date(DATA.firstSeen).toLocaleDateString("en-NZ", { day: "numeric", month: "short", year: "numeric" }) : "")
    + (IDX.latestSnap ? " · quota readings from the menu bar app" : "");

  document.getElementById("footer").textContent =
    (DATA.records || []).length + " aggregated buckets · " + IDX.weekTimes.length + " quota weeks · "
    + (DATA.snapshots || []).length + " limit snapshots"
    + (DATA.scanMs ? " · scanned in " + DATA.scanMs + " ms" : "");

  document.getElementById("note").textContent =
    "Token counts and costs are read from the Claude Code transcripts in ~/.claude/projects and priced from the published per-model rates, "
    + "so they are an estimate of consumption, not a bill. "
    + (DATA.anchorSource === "api"
      ? "Quota weeks are aligned to the reset time reported by the usage API. "
      : "Quota weeks are aligned to an assumed Sunday 22:00 reset; the alignment is corrected once the app records a reset time from the API. ")
    + "The All Models percentage is available only for periods the app has recorded, because the API reports the current value only.";
}

/* ---------- live status ---------- */
let lastOk = null;
let failures = 0;

function renderStatus() {
  const pill = document.getElementById("status");
  const text = document.getElementById("statusText");
  if (!CFG.live) {
    pill.dataset.state = "static";
    text.textContent = "Snapshot · " + (DATA ? new Date(DATA.generated).toLocaleString("en-NZ", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");
    return;
  }
  if (!lastOk) {
    pill.dataset.state = failures ? "offline" : "stale";
    text.textContent = failures ? "Cannot reach the app" : "Connecting…";
    return;
  }
  if (document.hidden) {
    // polling is paused in a background tab - say so rather than claim a retry
    pill.dataset.state = "static";
    text.textContent = "Paused · data from " + clock(new Date(lastOk));
    return;
  }
  const age = Date.now() - lastOk;
  const stale = age > CFG.pollSeconds * 3000;
  pill.dataset.state = failures >= 3 ? "offline" : stale ? "stale" : "live";
  text.textContent = failures >= 3
    ? "Disconnected · data from " + clock(new Date(lastOk))
    : stale ? "Retrying · data from " + clock(new Date(lastOk))
    : "Live · updated " + clock(new Date(lastOk));
}

/* ---------- render ---------- */
function renderAll() {
  if (!DATA) return;
  if (!IDX) buildIndex();
  renderMeta();
  renderCards();
  renderTrend();
  renderModelChart();
  renderProjectChart();
  renderWeekChart();
  renderLimitChart();
  renderTable();
  renderStatus();
}

function setData(next) {
  DATA = next;
  buildIndex();
  document.getElementById("root").classList.remove("loading");
  renderAll();
}

/* ---------- controls ---------- */
const rangeSeg = document.getElementById("rangeSeg");
rangeSeg.innerHTML = RANGES.map(r =>
  '<button data-range="' + r.id + '" aria-pressed="' + (r.id === STATE.range) + '">' + r.label + "</button>").join("");

function wireSeg(id, key, after) {
  document.getElementById(id).addEventListener("click", e => {
    const btn = e.target.closest("button");
    if (!btn) return;
    STATE[key] = btn.dataset[key];
    [...e.currentTarget.querySelectorAll("button")].forEach(b => b.setAttribute("aria-pressed", String(b === btn)));
    persist();
    if (DATA) after();
  });
}
wireSeg("rangeSeg", "range", renderAll);
wireSeg("metricSeg", "metric", renderAll);
wireSeg("tableSeg", "table", renderTable);

[...document.querySelectorAll("#metricSeg button")].forEach(b =>
  b.setAttribute("aria-pressed", String(b.dataset.metric === STATE.metric)));
[...document.querySelectorAll("#tableSeg button")].forEach(b =>
  b.setAttribute("aria-pressed", String(b.dataset.table === STATE.table)));

let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { if (DATA) renderAll(); }, 140);
});

/* ---------- live polling ---------- */
async function poll(force) {
  if (!CFG.live) return;
  if (document.hidden && !force) return;
  try {
    const url = CFG.endpoint + (CFG.endpoint.includes("?") ? "&" : "?") + "v=" + (DATA ? DATA.version : 0);
    const res = await fetch(url, { cache: "no-store" });
    if (res.status === 304) {
      lastOk = Date.now();
      failures = 0;
      renderStatus();
      return;
    }
    if (!res.ok) throw new Error("HTTP " + res.status);
    setData(await res.json());
    lastOk = Date.now();
    failures = 0;
    renderStatus();
  } catch (e) {
    failures += 1;
    renderStatus();
  }
}

if (CFG.live) {
  document.getElementById("root").classList.add("loading");
  poll(true);
  setInterval(poll, CFG.pollSeconds * 1000);
  setInterval(renderStatus, 5000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(true); });
  window.addEventListener("focus", () => poll(true));
} else if (DATA) {
  setData(DATA);
}
</script>
</body>
</html>
"""
