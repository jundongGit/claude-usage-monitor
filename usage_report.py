#!/usr/bin/env python3
"""
Usage history report for Claude Usage Monitor.

Builds a standalone HTML page from two local sources:

  1. ~/.claude/projects/**/*.jsonl  - every assistant message Claude Code wrote,
     carrying per-message token usage. This is the only source with history, so
     all retrospective numbers come from here.
  2. ~/.claude_usage_history.jsonl  - snapshots of the weekly all-models limit
     written by the menu bar app on each refresh. The API only ever reports the
     *current* utilization, so this file starts empty and fills up over time.

Weeks are the limit's own reset periods (the API resets the weekly quota at a
fixed weekday/hour), not calendar weeks, so a row here matches what the quota
actually counted.
"""

import json
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HISTORY_FILE = Path.home() / ".claude_usage_history.jsonl"
REPORT_FILE = Path.home() / ".claude_usage_report.html"

WEEK = timedelta(days=7)

# Model pricing ($/M tokens) - kept in sync with main.py's _PRICING
_PRICING = {
    "fable": {"input": 10, "output": 50, "cache_read": 0.25, "cache_create": 12.5},
    "opus": {"input": 5, "output": 25, "cache_read": 0.5, "cache_create": 6.25},
    "sonnet": {"input": 2, "output": 10, "cache_read": 0.2, "cache_create": 2.5},
    "haiku": {"input": 1, "output": 5, "cache_read": 0.1, "cache_create": 1.25},
}

# Categorical slots 1-4 of the validated default palette, in fixed order.
# Assigned per model family, never cycled.
_SERIES_COLORS = {
    "opus": "#2a78d6",
    "sonnet": "#eb6834",
    "fable": "#1baf7a",
    "haiku": "#eda100",
    "other": "#4a3aa7",
}


def _family(model):
    lower = (model or "").lower()
    for key in ("fable", "opus", "haiku", "sonnet"):
        if key in lower:
            return key
    return "other"


def _pricing_for(model):
    return _PRICING.get(_family(model), _PRICING["sonnet"])


def _parse_ts(value):
    """Parse a JSONL timestamp into an aware UTC datetime, or None."""
    if not value:
        return None
    try:
        if isinstance(value, (int, float)) or str(value).isdigit():
            return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OSError, OverflowError):
        return None


def read_snapshots():
    """Read the weekly-limit snapshots this app has recorded so far."""
    if not HISTORY_FILE.exists():
        return []
    rows = []
    try:
        with open(HISTORY_FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    rows.sort(key=lambda r: r.get("ts", ""))
    return rows


def resolve_anchor(snapshots):
    """Pick the reset instant that defines where one quota week ends.

    Prefers the newest resets_at the API actually reported; falls back to the
    next Sunday 22:00 local time, which is the observed default.
    """
    for row in reversed(snapshots):
        anchor = _parse_ts(row.get("resets_at"))
        if anchor:
            return anchor, "api"

    now = datetime.now().astimezone()
    # weekday(): Monday=0 .. Sunday=6
    days_ahead = (6 - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(
        hour=22, minute=0, second=0, microsecond=0
    )
    if candidate <= now:
        candidate += WEEK
    return candidate.astimezone(timezone.utc), "assumed"


def period_start(ts, anchor):
    """Start of the quota week containing ts, aligned to anchor."""
    weeks = math.floor((ts - anchor).total_seconds() / WEEK.total_seconds())
    return anchor + WEEK * weeks


def _project_label(cwd, fallback_dir):
    """Short, human-readable project name from the record's cwd."""
    if cwd:
        name = os.path.basename(cwd.rstrip("/"))
        if name:
            return name
    # Directory names are the cwd with separators flattened to "-"
    return (fallback_dir or "unknown").lstrip("-").split("-")[-1] or "unknown"


def scan_usage(anchor):
    """Aggregate every recorded assistant message into (period, day, model, project) buckets."""
    root = Path.home() / ".claude" / "projects"
    if not root.exists():
        return [], None, None

    # message_id -> the record with the largest output_tokens (streaming writes
    # partial usage rows for the same id; only the last one is complete)
    best = {}
    first_ts = None
    last_ts = None

    for proj_dir in root.iterdir():
        if not proj_dir.is_dir():
            continue
        for jsonl_file in proj_dir.glob("*.jsonl"):
            if jsonl_file.name.startswith("agent-"):
                continue
            try:
                with open(jsonl_file, encoding="utf-8") as fh:
                    for line in fh:
                        if '"assistant"' not in line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if obj.get("type") != "assistant":
                            continue

                        message = obj.get("message") or {}
                        usage = message.get("usage") or {}
                        if not usage:
                            continue

                        ts = _parse_ts(obj.get("timestamp"))
                        if not ts:
                            continue

                        model = message.get("model") or "unknown"
                        if model.startswith("<"):
                            model = "unknown"

                        out = usage.get("output_tokens") or 0
                        key = message.get("id") or f"{jsonl_file.name}:{obj.get('uuid')}"
                        if key in best and best[key][0] >= out:
                            continue

                        best[key] = (
                            out,
                            ts,
                            model,
                            _project_label(obj.get("cwd"), proj_dir.name),
                            usage,
                        )
            except (OSError, UnicodeDecodeError):
                continue

    buckets = defaultdict(lambda: {"i": 0, "o": 0, "cr": 0, "cc": 0, "n": 0})
    for _, ts, model, project, usage in best.values():
        if first_ts is None or ts < first_ts:
            first_ts = ts
        if last_ts is None or ts > last_ts:
            last_ts = ts

        local_day = ts.astimezone().strftime("%Y-%m-%d")
        bucket = buckets[(period_start(ts, anchor).isoformat(), local_day, _family(model), project)]
        bucket["i"] += usage.get("input_tokens") or 0
        bucket["o"] += usage.get("output_tokens") or 0
        bucket["cr"] += usage.get("cache_read_input_tokens") or 0
        bucket["cc"] += usage.get("cache_creation_input_tokens") or 0
        bucket["n"] += 1

    records = []
    for (period, day, family, project), b in buckets.items():
        p = _PRICING.get(family, _PRICING["sonnet"])
        cost = (
            b["i"] / 1e6 * p["input"]
            + b["o"] / 1e6 * p["output"]
            + b["cr"] / 1e6 * p["cache_read"]
            + b["cc"] / 1e6 * p["cache_create"]
        )
        records.append(
            {
                "w": period,
                "d": day,
                "m": family,
                "p": project,
                "i": b["i"],
                "o": b["o"],
                "cr": b["cr"],
                "cc": b["cc"],
                "n": b["n"],
                "c": round(cost, 4),
            }
        )

    records.sort(key=lambda r: (r["w"], r["d"]))
    return records, first_ts, last_ts


def build_payload():
    snapshots = read_snapshots()
    anchor, anchor_source = resolve_anchor(snapshots)
    records, first_ts, last_ts = scan_usage(anchor)

    trimmed = [
        {
            "ts": row.get("ts"),
            "w": period_start(_parse_ts(row.get("ts")), anchor).isoformat()
            if _parse_ts(row.get("ts"))
            else None,
            "all": row.get("all_models_pct"),
            "session": row.get("session_pct"),
            "src": row.get("source"),
        }
        for row in snapshots
        if row.get("ts") is not None and row.get("all_models_pct") is not None
    ]

    return {
        "generated": datetime.now().astimezone().isoformat(),
        "anchor": anchor.isoformat(),
        "anchorSource": anchor_source,
        "weekSeconds": int(WEEK.total_seconds()),
        "colors": _SERIES_COLORS,
        "records": records,
        "snapshots": trimmed,
        "firstSeen": first_ts.astimezone().isoformat() if first_ts else None,
        "lastSeen": last_ts.astimezone().isoformat() if last_ts else None,
    }


def generate_report(path=REPORT_FILE):
    """Write the HTML report and return its path."""
    payload = build_payload()
    html = _TEMPLATE.replace("/*__PAYLOAD__*/", json.dumps(payload, ensure_ascii=False))
    path = Path(path)
    path.write_text(html, encoding="utf-8")
    return path


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claude Usage History</title>
<style>
  :root {
    color-scheme: light;
    --surface-0: #f5f5f3;
    --surface-1: #fcfcfb;
    --border: #e2e1dc;
    --border-strong: #d2d1ca;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --text-muted: #83827c;
    --grid: #ebeae5;
    --accent: #2a78d6;
    --seq-100: #cde2fb;
    --seq-250: #86b6ef;
    --seq-400: #3987e5;
    --seq-550: #1c5cab;
    --seq-700: #0d366b;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--surface-0);
    color: var(--text-primary);
    font: 14px/1.55 -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 1120px; margin: 0 auto; padding-block: 32px; padding-left: 20px; padding-right: 20px; }
  header h1 { font-size: 22px; font-weight: 650; margin: 0 0 6px; letter-spacing: -0.01em; }
  header p { margin: 0; color: var(--text-secondary); font-size: 13px; }
  header .note { margin-top: 10px; color: var(--text-muted); font-size: 12.5px; max-width: 74ch; }

  .cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 24px 0; }
  .card {
    background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 10px; padding: 15px 16px;
  }
  .card .label { color: var(--text-secondary); font-size: 12px; display: flex; align-items: center; gap: 6px; }
  .card .value { font-size: 25px; font-weight: 620; margin-top: 7px; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
  .card .sub { color: var(--text-muted); font-size: 12px; margin-top: 3px; font-variant-numeric: tabular-nums; }

  .panel {
    background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 10px; padding: 18px 18px 14px; margin-bottom: 18px;
  }
  .panel-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 4px; }
  .panel h2 { font-size: 14.5px; font-weight: 620; margin: 0; }
  .panel .hint { color: var(--text-muted); font-size: 12px; margin: 2px 0 14px; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
  .two-col .panel { margin-bottom: 18px; }

  .seg { display: inline-flex; border: 1px solid var(--border-strong); border-radius: 7px; overflow: hidden; }
  .seg button {
    appearance: none; border: 0; background: var(--surface-1); color: var(--text-secondary);
    font: inherit; font-size: 12.5px; padding: 5px 12px; cursor: pointer;
  }
  .seg button + button { border-left: 1px solid var(--border-strong); }
  .seg button[aria-pressed="true"] { background: var(--accent); color: #fff; }

  .chart { position: relative; width: 100%; }
  .chart svg { display: block; width: 100%; }
  .empty { color: var(--text-muted); font-size: 13px; padding: 26px 2px 30px; }

  .legend { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 12px; }
  .legend span { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--text-secondary); }
  .legend i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }

  .tbl-scroll { overflow-x: auto; margin-top: 4px; }
  table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
  th, td { text-align: right; padding: 8px 10px; border-bottom: 1px solid var(--grid); white-space: nowrap; font-variant-numeric: tabular-nums; }
  th { color: var(--text-secondary); font-weight: 560; text-align: right; border-bottom: 1px solid var(--border-strong); }
  th:first-child, td:first-child { text-align: left; }
  tbody tr:hover { background: #f7f7f4; }
  td.dim { color: var(--text-muted); }
  .swatch { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 6px; vertical-align: baseline; }

  .tip {
    position: absolute; pointer-events: none; opacity: 0; transform: translate(-50%, -100%);
    background: #ffffff; border: 1px solid var(--border-strong); border-radius: 8px;
    padding: 8px 10px; font-size: 12px; line-height: 1.5; white-space: nowrap;
    box-shadow: 0 6px 20px rgba(0,0,0,.12); transition: opacity .09s ease; z-index: 5;
  }
  .tip b { font-weight: 620; }
  .tip .row { display: flex; align-items: center; gap: 7px; justify-content: space-between; }
  .tip .row i { width: 9px; height: 9px; border-radius: 2px; }
  .tip .row span:last-child { font-variant-numeric: tabular-nums; }

  svg text { font-family: inherit; }
  .ico { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }

  footer { color: var(--text-muted); font-size: 12px; margin-top: 6px; padding-bottom: 10px; }

  @media (max-width: 880px) {
    .cards { grid-template-columns: repeat(2, 1fr); }
    .two-col { grid-template-columns: 1fr; }
  }
  @media (max-width: 520px) {
    .cards { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Claude Usage History</h1>
    <p id="meta"></p>
    <p class="note" id="note"></p>
  </header>

  <section class="cards" id="cards"></section>

  <section class="panel">
    <div class="panel-head">
      <h2>Usage by quota week</h2>
      <div class="seg" id="metricSeg">
        <button data-metric="cost" aria-pressed="true">Cost</button>
        <button data-metric="tokens" aria-pressed="false">Tokens</button>
      </div>
    </div>
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

  <div class="two-col">
    <section class="panel">
      <h2>Cost by model</h2>
      <p class="hint" id="modelHint"></p>
      <div class="chart" id="modelChart"></div>
    </section>
    <section class="panel">
      <h2>Cost by project</h2>
      <p class="hint" id="projectHint"></p>
      <div class="chart" id="projectChart"></div>
    </section>
  </div>

  <section class="panel">
    <h2>Quota week breakdown</h2>
    <p class="hint" id="weekTableHint">Weeks run from one quota reset to the next, so each row matches what the weekly limit counted.</p>
    <div class="tbl-scroll"><table id="weekTable"></table></div>
  </section>

  <section class="panel">
    <h2>Daily breakdown</h2>
    <p class="hint" id="dayHint">Most recent 30 days.</p>
    <div class="tbl-scroll"><table id="dayTable"></table></div>
  </section>

  <footer id="footer"></footer>
</div>

<script>
const DATA = /*__PAYLOAD__*/;

const MODEL_ORDER = ["opus", "sonnet", "fable", "haiku", "other"];
const MODEL_LABEL = { opus: "Opus", sonnet: "Sonnet", fable: "Fable", haiku: "Haiku", other: "Other" };
const C = DATA.colors;
const WEEK_MS = DATA.weekSeconds * 1000;

let metric = "cost";

/* ---------- formatting ---------- */
const fmtTokens = n => n >= 1e9 ? (n / 1e9).toFixed(2) + "B"
  : n >= 1e6 ? (n / 1e6).toFixed(1) + "M"
  : n >= 1e3 ? (n / 1e3).toFixed(1) + "K" : String(n);
const fmtCost = n => n === 0 ? "$0" : n >= 100 ? "$" + n.toFixed(0) : n >= 1 ? "$" + n.toFixed(2) : "$" + n.toFixed(3);
const fmtVal = (n, m) => (m || metric) === "cost" ? fmtCost(n) : fmtTokens(n);
const fmtInt = n => n.toLocaleString("en-US");
const fmtShare = (part, whole) => {
  if (!whole) return "0%";
  const pct = part / whole * 100;
  return pct > 0 && pct < 1 ? "<1%" : pct.toFixed(0) + "%";
};
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const mdy = d => MON[d.getMonth()] + " " + d.getDate();
const weekLabel = t => mdy(new Date(t)) + "–" + mdy(new Date(t + WEEK_MS));
const weekLabelShort = t => mdy(new Date(t));

/* ---------- aggregation ---------- */
const R = DATA.records.map(r => Object.assign({}, r, { wt: new Date(r.w).getTime() }));

const weekTimes = (() => {
  if (!R.length) return [];
  const times = R.map(r => r.wt);
  const first = Math.min(...times), last = Math.max(...times);
  const out = [];
  for (let t = first; t <= last + 1000; t += WEEK_MS) out.push(t);
  return out;
})();

function weekSeries() {
  return weekTimes.map(iso => {
    const rows = R.filter(r => r.wt === iso);
    const byModel = {};
    MODEL_ORDER.forEach(m => { byModel[m] = { cost: 0, tokens: 0 }; });
    let calls = 0, days = new Set();
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
}

const WEEKS = weekSeries();

// Peak recorded utilization per quota week (only weeks this app has observed).
const PEAK_BY_WEEK = {};
DATA.snapshots.forEach(s => {
  if (!s.w) return;
  const t = new Date(s.w).getTime();
  const cur = PEAK_BY_WEEK[t];
  if (!cur || s.all > cur.pct) PEAK_BY_WEEK[t] = { pct: s.all, manual: s.src === "manual" };
});
const hasManualPeak = Object.values(PEAK_BY_WEEK).some(v => v.manual);

// Percentage points per dollar, measured on the weeks that DO have snapshots.
// Used to extrapolate the weeks recorded before the app started tracking.
const PCT_PER_DOLLAR = (() => {
  let pct = 0, cost = 0;
  Object.entries(PEAK_BY_WEEK).forEach(([t, p]) => {
    const wk = WEEKS.find(w => w.iso === Number(t));
    if (wk && wk.cost > 0 && p.pct > 0) { pct += p.pct; cost += wk.cost; }
  });
  return cost > 0 ? pct / cost : null;
})();
const estPct = cost => {
  if (!PCT_PER_DOLLAR || !cost) return null;
  const v = cost * PCT_PER_DOLLAR;
  return v >= 100 ? ">100%" : v < 1 ? "<1%" : "~" + v.toFixed(0) + "%";
};
const CURRENT = WEEKS.length ? WEEKS[WEEKS.length - 1] : null;
const activeModels = MODEL_ORDER.filter(m => WEEKS.some(w => w.byModel[m] && w.byModel[m].tokens > 0));

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
  const width = Math.max(host.clientWidth || 640, 320);
  const svg = el("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img" }, host);
  const tip = document.createElement("div");
  tip.className = "tip";
  host.appendChild(tip);
  return { svg, width, height, tip };
}
function showTip(host, tip, x, y, html) {
  tip.innerHTML = html;
  tip.style.left = Math.min(Math.max(x, 70), host.clientWidth - 70) + "px";
  tip.style.top = (y - 10) + "px";
  tip.style.opacity = 1;
}
const hideTip = tip => { tip.style.opacity = 0; };

function axes(svg, w, h, pad, ticks, fmt) {
  ticks.forEach(t => {
    const y = t.y;
    el("line", { x1: pad.l, y1: y, x2: w - pad.r, y2: y, stroke: "var(--grid)", "stroke-width": 1 }, svg);
    el("text", {
      x: pad.l - 8, y: y + 4, "text-anchor": "end",
      fill: "var(--text-muted)", "font-size": 11,
    }, svg).textContent = fmt(t.v);
  });
}

/* ---------- chart: usage by quota week (stacked columns) ---------- */
function renderWeekChart() {
  const host = document.getElementById("weekChart");
  const hint = document.getElementById("weekHint");
  if (!WEEKS.length) {
    host.innerHTML = '<p class="empty">No local usage records found under ~/.claude/projects.</p>';
    hint.textContent = "";
    return;
  }
  hint.textContent = metric === "cost"
    ? "Estimated spend per quota week, stacked by model. The final bar is the week in progress."
    : "Total tokens per quota week (input, output and cache), stacked by model. The final bar is the week in progress.";

  const H = 300, pad = { t: 18, r: 16, b: 46, l: 58 };
  const { svg, width, tip } = svgRoot(host, H);
  const plotW = width - pad.l - pad.r, plotH = H - pad.t - pad.b;
  const max = Math.max(...WEEKS.map(w => w[metric]), 1) * 1.12;
  const y = v => pad.t + plotH - (v / max) * plotH;

  const step = plotW / WEEKS.length;
  const bw = Math.min(54, step * 0.62);

  const tickCount = 4;
  const ticks = Array.from({ length: tickCount + 1 }, (_, i) => {
    const v = (max / tickCount) * i;
    return { v, y: y(v) };
  });
  axes(svg, width, H, pad, ticks, v => metric === "cost" ? (v >= 1 ? "$" + Math.round(v) : "$" + v.toFixed(2)) : fmtTokens(Math.round(v)));

  WEEKS.forEach((wk, i) => {
    const cx = pad.l + step * i + step / 2;
    let acc = 0;
    const segs = activeModels.map(m => ({ m, v: wk.byModel[m] ? wk.byModel[m][metric] : 0 })).filter(s => s.v > 0);

    segs.forEach((s, si) => {
      const y0 = y(acc), y1 = y(acc + s.v);
      let hgt = Math.max(y0 - y1, 1);
      // 2px surface gap between stacked segments
      if (si > 0) hgt = Math.max(hgt - 2, 1);
      const isTop = si === segs.length - 1;
      el("rect", {
        x: cx - bw / 2, y: y1, width: bw, height: hgt,
        fill: C[s.m] || C.other,
        rx: isTop ? 4 : 0,
      }, svg);
      acc += s.v;
    });

    // direct label on the most recent week only
    if (i === WEEKS.length - 1 && wk[metric] > 0) {
      el("text", {
        x: cx, y: y(wk[metric]) - 8, "text-anchor": "middle",
        fill: "var(--text-primary)", "font-size": 12, "font-weight": 600,
      }, svg).textContent = fmtVal(wk[metric]);
    }

    el("text", {
      x: cx, y: H - pad.b + 18, "text-anchor": "middle",
      fill: "var(--text-secondary)", "font-size": 11,
    }, svg).textContent = weekLabelShort(wk.iso);

    if (i === WEEKS.length - 1) {
      el("text", {
        x: cx, y: H - pad.b + 33, "text-anchor": "middle",
        fill: "var(--text-muted)", "font-size": 10.5,
      }, svg).textContent = "in progress";
    }

    const hit = el("rect", {
      x: pad.l + step * i, y: pad.t, width: step, height: plotH,
      fill: "transparent", style: "cursor:default",
    }, svg);
    hit.addEventListener("mouseenter", () => {
      const rows = activeModels
        .filter(m => wk.byModel[m] && wk.byModel[m][metric] > 0)
        .map(m => `<div class="row"><span><i style="background:${C[m] || C.other}"></i> ${MODEL_LABEL[m]}</span><span>${fmtVal(wk.byModel[m][metric])}</span></div>`)
        .join("");
      showTip(host, tip, cx, y(wk[metric]),
        `<b>${weekLabel(wk.iso)}</b><div class="row"><span>Total</span><span>${fmtVal(wk[metric])}</span></div>${rows}` +
        `<div class="row"><span>Active days</span><span>${wk.days}</span></div>`);
    });
    hit.addEventListener("mouseleave", () => hideTip(tip));
  });

  const legend = document.getElementById("weekLegend");
  legend.innerHTML = activeModels
    .map(m => `<span><i style="background:${C[m] || C.other}"></i>${MODEL_LABEL[m]}</span>`)
    .join("");
}

/* ---------- chart: all-models limit across the week (snapshots) ---------- */
function renderLimitChart() {
  const host = document.getElementById("limitChart");
  const hint = document.getElementById("limitHint");
  const legend = document.getElementById("limitLegend");
  const snaps = DATA.snapshots.filter(s => s.w);

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
  hint.textContent = "Recorded All Models utilization, each line one quota week, plotted against days elapsed in that week.";

  const H = 270, pad = { t: 18, r: 20, b: 42, l: 46 };
  const { svg, width, tip } = svgRoot(host, H);
  const plotW = width - pad.l - pad.r, plotH = H - pad.t - pad.b;
  const maxPct = Math.max(10, ...snaps.map(s => s.all)) * 1.15;
  const x = d => pad.l + (d / 7) * plotW;
  const y = v => pad.t + plotH - (v / maxPct) * plotH;

  const ticks = [0, 0.25, 0.5, 0.75, 1].map(f => ({ v: maxPct * f, y: y(maxPct * f) }));
  axes(svg, width, H, pad, ticks, v => Math.round(v) + "%");

  for (let d = 0; d <= 7; d++) {
    el("text", {
      x: x(d), y: H - pad.b + 18, "text-anchor": "middle",
      fill: "var(--text-secondary)", "font-size": 11,
    }, svg).textContent = d === 0 ? "reset" : "d" + d;
  }

  // Sequential blue ramp: older weeks lighter, current week darkest
  const ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#1c5cab"];
  const shades = isos.map((_, i) => ramp[ramp.length - isos.length + i]);

  isos.forEach((iso, idx) => {
    const start = iso, end = start + WEEK_MS;
    const pts = byWeek[iso]
      .map(s => ({ d: (new Date(s.ts).getTime() - start) / WEEK_MS * 7, v: s.all, ts: s.ts }))
      .filter(p => p.d >= 0 && p.d <= 7)
      .sort((a, b) => a.d - b.d);
    if (!pts.length) return;
    const isLast = idx === isos.length - 1;
    const path = pts.map((p, i) => (i ? "L" : "M") + x(p.d).toFixed(1) + " " + y(p.v).toFixed(1)).join(" ");
    el("path", {
      d: path, fill: "none", stroke: shades[idx],
      "stroke-width": isLast ? 2 : 1.5, "stroke-linejoin": "round", "stroke-linecap": "round",
    }, svg);

    const last = pts[pts.length - 1];
    el("circle", { cx: x(last.d), cy: y(last.v), r: 4, fill: shades[idx], stroke: "var(--surface-1)", "stroke-width": 2 }, svg);
    if (isLast) {
      el("text", {
        x: Math.min(x(last.d) + 9, width - pad.r), y: y(last.v) - 9,
        fill: "var(--text-primary)", "font-size": 12, "font-weight": 600,
        "text-anchor": x(last.d) > width - 80 ? "end" : "start",
      }, svg).textContent = last.v + "%";
    }

    pts.forEach(p => {
      const hit = el("circle", { cx: x(p.d), cy: y(p.v), r: 9, fill: "transparent" }, svg);
      hit.addEventListener("mouseenter", () => showTip(host, tip, x(p.d), y(p.v),
        `<b>${weekLabel(iso)}</b><div class="row"><span>All Models</span><span>${p.v}%</span></div>` +
        `<div class="row"><span>Recorded</span><span>${new Date(p.ts).toLocaleString("en-NZ", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span></div>`));
      hit.addEventListener("mouseleave", () => hideTip(tip));
    });
  });

  legend.innerHTML = isos
    .map((iso, i) => `<span><i style="background:${shades[i]}"></i>${weekLabel(iso)}${i === isos.length - 1 ? " (current)" : ""}</span>`)
    .join("");
}

/* ---------- chart: cost by model (donut) ---------- */
function renderModelChart() {
  const host = document.getElementById("modelChart");
  const hint = document.getElementById("modelHint");
  const totals = activeModels
    .map(m => ({ m, v: R.filter(r => r.m === m).reduce((s, r) => s + r.c, 0) }))
    .filter(d => d.v > 0)
    .sort((a, b) => b.v - a.v);
  const sum = totals.reduce((s, d) => s + d.v, 0);
  if (!sum) { host.innerHTML = '<p class="empty">No data.</p>'; return; }
  hint.textContent = "Share of estimated spend across the whole recorded history.";

  const H = 230;
  const { svg, width, tip } = svgRoot(host, H);
  const cx = 110, cy = H / 2, rO = 82, rI = 52;
  let a0 = -Math.PI / 2;

  totals.forEach(d => {
    const a1 = a0 + (d.v / sum) * Math.PI * 2;
    const gap = 0.012;
    const s = a0 + gap, e = Math.max(a1 - gap, a0 + 0.001);
    const large = e - s > Math.PI ? 1 : 0;
    const p = [
      "M", cx + rO * Math.cos(s), cy + rO * Math.sin(s),
      "A", rO, rO, 0, large, 1, cx + rO * Math.cos(e), cy + rO * Math.sin(e),
      "L", cx + rI * Math.cos(e), cy + rI * Math.sin(e),
      "A", rI, rI, 0, large, 0, cx + rI * Math.cos(s), cy + rI * Math.sin(s), "Z",
    ].join(" ");
    const arc = el("path", { d: p, fill: C[d.m] || C.other }, svg);
    arc.addEventListener("mouseenter", () => showTip(host, tip, cx, cy - rO,
      `<b>${MODEL_LABEL[d.m]}</b><div class="row"><span>Cost</span><span>${fmtCost(d.v)}</span></div>` +
      `<div class="row"><span>Share</span><span>${fmtShare(d.v, sum)}</span></div>`));
    arc.addEventListener("mouseleave", () => hideTip(tip));
    a0 = a1;
  });

  el("text", { x: cx, y: cy - 3, "text-anchor": "middle", fill: "var(--text-primary)", "font-size": 18, "font-weight": 620 }, svg)
    .textContent = fmtCost(sum);
  el("text", { x: cx, y: cy + 15, "text-anchor": "middle", fill: "var(--text-muted)", "font-size": 11 }, svg)
    .textContent = "total";

  // Direct labels to the right - the relief rule for low-contrast slots
  totals.forEach((d, i) => {
    const ty = cy - (totals.length - 1) * 12 + i * 24;
    el("rect", { x: 218, y: ty - 9, width: 10, height: 10, rx: 3, fill: C[d.m] || C.other }, svg);
    el("text", { x: 234, y: ty, fill: "var(--text-secondary)", "font-size": 12.5 }, svg)
      .textContent = MODEL_LABEL[d.m];
    el("text", { x: Math.max(width - 8, 330), y: ty, "text-anchor": "end", fill: "var(--text-primary)", "font-size": 12.5 }, svg)
      .textContent = fmtCost(d.v) + "  ·  " + fmtShare(d.v, sum);
  });
}

/* ---------- chart: cost by project (horizontal bars) ---------- */
function renderProjectChart() {
  const host = document.getElementById("projectChart");
  const hint = document.getElementById("projectHint");
  const map = {};
  R.forEach(r => { map[r.p] = (map[r.p] || 0) + r.c; });
  const rows = Object.entries(map).map(([p, v]) => ({ p, v })).sort((a, b) => b.v - a.v).slice(0, 8);
  if (!rows.length) { host.innerHTML = '<p class="empty">No data.</p>'; return; }
  hint.textContent = "Top 8 working directories by estimated spend, whole recorded history.";

  const rowH = 26, H = rows.length * rowH + 14;
  const { svg, width, tip } = svgRoot(host, H);
  const labelW = Math.min(150, Math.max(96, width * 0.34));
  const max = rows[0].v || 1;
  const barMax = width - labelW - 66;

  rows.forEach((d, i) => {
    const y = i * rowH + 8;
    const w = Math.max((d.v / max) * barMax, 2);
    el("text", { x: 0, y: y + 13, fill: "var(--text-secondary)", "font-size": 12.5 }, svg)
      .textContent = d.p.length > 20 ? d.p.slice(0, 19) + "…" : d.p;
    el("rect", { x: labelW, y: y + 3, width: w, height: 13, rx: 4, fill: "var(--accent)" }, svg);
    el("text", { x: labelW + w + 8, y: y + 13, fill: "var(--text-primary)", "font-size": 12 }, svg)
      .textContent = fmtCost(d.v);

    const hit = el("rect", { x: 0, y, width, height: rowH, fill: "transparent" }, svg);
    hit.addEventListener("mouseenter", () => {
      const tokens = R.filter(r => r.p === d.p).reduce((s, r) => s + r.i + r.o + r.cr + r.cc, 0);
      showTip(host, tip, labelW + w / 2, y, `<b>${d.p}</b><div class="row"><span>Cost</span><span>${fmtCost(d.v)}</span></div><div class="row"><span>Tokens</span><span>${fmtTokens(tokens)}</span></div>`);
    });
    hit.addEventListener("mouseleave", () => hideTip(tip));
  });
}

/* ---------- cards ---------- */
function renderCards() {
  const host = document.getElementById("cards");
  const snaps = DATA.snapshots;
  const latest = snaps.length ? snaps[snaps.length - 1] : null;
  const complete = WEEKS.slice(0, -1);
  const avg = complete.length ? complete.reduce((s, w) => s + w.cost, 0) / complete.length : 0;

  const cards = [
    {
      label: "All Models this week",
      value: latest ? latest.all + "%" : "—",
      sub: latest
        ? "recorded " + new Date(latest.ts).toLocaleString("en-NZ", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
        : "awaiting first snapshot",
    },
    {
      label: "Cost this week",
      value: CURRENT ? fmtCost(CURRENT.cost) : "—",
      sub: CURRENT ? weekLabel(CURRENT.iso) : "",
    },
    {
      label: "Tokens this week",
      value: CURRENT ? fmtTokens(CURRENT.tokens) : "—",
      sub: CURRENT ? fmtInt(CURRENT.calls) + " messages over " + CURRENT.days + " days" : "",
    },
    {
      label: "Average per completed week",
      value: complete.length ? fmtCost(avg) : "—",
      sub: complete.length + " completed weeks recorded",
    },
  ];

  host.innerHTML = cards.map(c =>
    `<div class="card"><div class="label">${c.label}</div><div class="value">${c.value}</div><div class="sub">${c.sub}</div></div>`
  ).join("");
}

/* ---------- tables ---------- */
function renderWeekTable() {
  const t = document.getElementById("weekTable");

  const hint = document.getElementById("weekTableHint");
  if (PCT_PER_DOLLAR) {
    hint.textContent = "Weeks run from one quota reset to the next, so each row matches what the weekly limit counted. "
      + "Peak All Models is only known for weeks the app has recorded. Est. extrapolates the rest from estimated spend at "
      + "the ratio observed in the recorded weeks (currently about " + fmtCost(1 / PCT_PER_DOLLAR) + " per percentage point). "
      + "It assumes the limit tracks per-model pricing and rests on very few observations — read it as an order of magnitude, not a measurement."
      + (hasManualPeak ? " Values marked * were reported manually rather than recorded by the app, and are used for calibration alongside the recorded ones." : "");
  } else {
    hint.textContent = "Weeks run from one quota reset to the next, so each row matches what the weekly limit counted. "
      + "Est. stays empty until the app has recorded at least one week of All Models readings to calibrate against.";
  }

  const head = `<thead><tr><th>Quota week</th><th>Peak All Models</th><th>Est.</th><th>Cost</th><th>Tokens</th>
    <th>Input</th><th>Output</th><th>Cache</th><th>Messages</th><th>Active days</th></tr></thead>`;
  const body = WEEKS.slice().reverse().map(w => {
    const peak = PEAK_BY_WEEK[w.iso];
    const est = peak === undefined ? estPct(w.cost) : null;
    const peakCell = peak === undefined ? "—" : peak.pct + "%" + (peak.manual ? "*" : "");
    return `<tr>
      <td>${weekLabel(w.iso)}${w === CURRENT ? ' <span class="dim">(current)</span>' : ""}</td>
      <td class="${peak === undefined ? "dim" : ""}">${peakCell}</td>
      <td class="dim">${est === null ? "—" : est}</td>
      <td>${fmtCost(w.cost)}</td>
      <td>${fmtTokens(w.tokens)}</td>
      <td class="dim">${fmtTokens(w.input)}</td>
      <td class="dim">${fmtTokens(w.output)}</td>
      <td class="dim">${fmtTokens(w.cache)}</td>
      <td class="dim">${fmtInt(w.calls)}</td>
      <td class="dim">${w.days}</td>
    </tr>`;
  }).join("");
  t.innerHTML = head + "<tbody>" + body + "</tbody>";
}

function renderDayTable() {
  const t = document.getElementById("dayTable");
  const map = {};
  R.forEach(r => {
    const d = (map[r.d] = map[r.d] || { cost: 0, tokens: 0, calls: 0, models: {} });
    d.cost += r.c;
    d.tokens += r.i + r.o + r.cr + r.cc;
    d.calls += r.n;
    d.models[r.m] = (d.models[r.m] || 0) + r.c;
  });
  const days = Object.keys(map).sort().reverse().slice(0, 30);
  const head = `<thead><tr><th>Date</th><th>Cost</th><th>Tokens</th><th>Messages</th><th style="text-align:left">Models</th></tr></thead>`;
  const body = days.map(d => {
    const v = map[d];
    const models = Object.entries(v.models).sort((a, b) => b[1] - a[1])
      .map(([m, c]) => `<span class="swatch" style="background:${C[m] || C.other}"></span>${MODEL_LABEL[m]} ${fmtCost(c)}`)
      .join(" &nbsp; ");
    const dt = new Date(d + "T12:00:00");
    return `<tr><td>${mdy(dt)}, ${dt.getFullYear()}</td><td>${fmtCost(v.cost)}</td><td>${fmtTokens(v.tokens)}</td>
      <td class="dim">${fmtInt(v.calls)}</td><td style="text-align:left" class="dim">${models}</td></tr>`;
  }).join("");
  t.innerHTML = head + "<tbody>" + body + "</tbody>";
}

/* ---------- header & footer ---------- */
function renderMeta() {
  const gen = new Date(DATA.generated);
  document.getElementById("meta").textContent =
    "Generated " + gen.toLocaleString("en-NZ", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) +
    (DATA.firstSeen ? " · local records from " + new Date(DATA.firstSeen).toLocaleDateString("en-NZ", { day: "numeric", month: "short", year: "numeric" }) : "");

  const note = [];
  note.push("Token counts and costs are read from the Claude Code transcripts in ~/.claude/projects and priced from the published per-model rates, so they are an estimate of consumption, not a bill.");
  note.push(DATA.anchorSource === "api"
    ? "Quota weeks are aligned to the reset time reported by the usage API."
    : "Quota weeks are aligned to an assumed Sunday 22:00 reset; the alignment is corrected once the app records a reset time from the API.");
  note.push("The All Models percentage is only available for periods the app has recorded; the API reports the current value only. Earlier weeks carry an extrapolated Est. figure instead, derived from spend — see the note above that table.");
  document.getElementById("note").textContent = note.join(" ");

  document.getElementById("footer").textContent =
    DATA.records.length + " aggregated buckets · " + weekTimes.length + " quota weeks · " + DATA.snapshots.length + " limit snapshots";
}

/* ---------- wire up ---------- */
document.getElementById("metricSeg").addEventListener("click", e => {
  const btn = e.target.closest("button");
  if (!btn) return;
  metric = btn.dataset.metric;
  [...e.currentTarget.querySelectorAll("button")].forEach(b =>
    b.setAttribute("aria-pressed", String(b === btn)));
  renderWeekChart();
});

function renderAll() {
  renderCards();
  renderWeekChart();
  renderLimitChart();
  renderModelChart();
  renderProjectChart();
}

renderMeta();
renderWeekTable();
renderDayTable();
renderAll();

let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(renderAll, 140);
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    print(generate_report())
