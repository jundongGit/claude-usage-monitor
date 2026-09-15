#!/usr/bin/env python3
"""
Usage history for Claude Usage Monitor.

Builds the dashboard payload from two local sources:

  1. ~/.claude/projects/**/*.jsonl  - every assistant message Claude Code wrote,
     carrying per-message token usage. This is the only source with history, so
     all retrospective numbers come from here.
  2. ~/.claude_usage_history.jsonl  - snapshots of the weekly all-models limit
     written by the menu bar app on each refresh. The API only ever reports the
     *current* utilization, so this file starts empty and fills up over time.

Weeks are the limit's own reset periods (the API resets the weekly quota at a
fixed weekday/hour), not calendar weeks, so a row here matches what the quota
actually counted.

The transcripts are ~2 GB, so a full re-read takes seconds. `Scanner` keeps the
per-file results in memory and re-reads only the bytes appended since the last
pass, which is what makes the live page affordable to poll. `payload()` bumps
`version` only when the numbers actually changed, so the server can answer an
unchanged poll with 304.
"""

import json
import math
import os
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import report_template

HISTORY_FILE = Path.home() / ".claude_usage_history.jsonl"
REPORT_FILE = Path.home() / ".claude_usage_report.html"
PROJECTS_DIR = Path.home() / ".claude" / "projects"

WEEK = timedelta(days=7)
WEEK_SECONDS = int(WEEK.total_seconds())
HOURLY_WINDOW_HOURS = 72

# Model pricing ($/M tokens) - kept in sync with main.py's _PRICING
_PRICING = {
    "fable": {"input": 10, "output": 50, "cache_read": 0.25, "cache_create": 12.5},
    "opus": {"input": 5, "output": 25, "cache_read": 0.5, "cache_create": 6.25},
    "sonnet": {"input": 2, "output": 10, "cache_read": 0.2, "cache_create": 2.5},
    "haiku": {"input": 1, "output": 5, "cache_read": 0.1, "cache_create": 1.25},
}

# Categorical slots 1-4 of the validated default palette, plus slot 7 for the
# catch-all. Assigned per model family, never cycled.
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


def _cost_of(family, i, o, cr, cc):
    p = _PRICING.get(family, _PRICING["sonnet"])
    return (
        i / 1e6 * p["input"]
        + o / 1e6 * p["output"]
        + cr / 1e6 * p["cache_read"]
        + cc / 1e6 * p["cache_create"]
    )


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


def read_snapshots(path=None):
    """Read the weekly-limit snapshots this app has recorded so far."""
    path = Path(path or HISTORY_FILE)
    if not path.exists():
        return []
    rows = []
    try:
        with open(path, encoding="utf-8") as fh:
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


def _period_start_epoch(ts_epoch, anchor_epoch):
    weeks = math.floor((ts_epoch - anchor_epoch) / WEEK_SECONDS)
    return anchor_epoch + WEEK_SECONDS * weeks


def _project_label(cwd, fallback_dir):
    """Short, human-readable project name from the record's cwd."""
    if cwd:
        name = os.path.basename(cwd.rstrip("/"))
        if name:
            return name
    # Directory names are the cwd with separators flattened to "-"
    return (fallback_dir or "unknown").lstrip("-").split("-")[-1] or "unknown"


# The transcripts total ~2 GB, so how the lines are read matters more than how
# they are parsed. Working on bytes and decoding nothing but the fields that are
# kept costs ~3 s and ~250 MB for a cold pass; decoding every line to str first
# costs ~5 s and ~470 MB, because content is largely non-ASCII and widens in
# memory. A regex fast path over the same bytes was tried and is slower still -
# the C json parser beats scanning a 20 KB line several times.


class Scanner:
    """Incremental reader over the Claude Code transcripts.

    State per transcript file: the byte offset already consumed, plus the best
    usage row seen for each message id in it (streaming writes several partial
    rows for one id; only the largest is complete). Re-reading only the appended
    tail keeps a refresh in the low milliseconds once warm.
    """

    # row layout, kept as a tuple to stay small across ~100k messages
    OUT, TS, DAY, HOUR, FAM, PROJ, IN, OUTT, CR, CC = range(10)

    def __init__(self, projects_dir=None, history_file=None):
        self.projects_dir = Path(projects_dir or PROJECTS_DIR)
        self.history_file = Path(history_file or HISTORY_FILE)
        self._files = {}          # path -> {"off": int, "rows": {id: tuple}}
        self._snapshots = []
        self._snap_sig = None
        self._payload = None
        self._version = 0
        self._last_scan = 0.0
        self._lock = threading.RLock()

    # -- public -----------------------------------------------------------
    def payload(self, max_age=1.0, live=False, poll_seconds=15):
        """Current payload, rescanning if the last pass is older than max_age."""
        with self._lock:
            if self._payload is None or (time.monotonic() - self._last_scan) >= max_age:
                self.refresh()
            payload = dict(self._payload)
            payload["live"] = bool(live)
            payload["pollSeconds"] = poll_seconds
            return payload

    def refresh(self):
        """Re-read what changed on disk. Returns True when the payload moved."""
        with self._lock:
            started = time.monotonic()
            changed = self._scan_transcripts()
            changed = self._scan_snapshots() or changed
            self._last_scan = time.monotonic()
            if changed or self._payload is None:
                return self._rebuild(int((time.monotonic() - started) * 1000))
            return False

    @property
    def version(self):
        return self._version

    # -- scanning ---------------------------------------------------------
    def _scan_transcripts(self):
        changed = False
        seen = set()
        if self.projects_dir.exists():
            for proj_dir in self.projects_dir.iterdir():
                if not proj_dir.is_dir():
                    continue
                for jsonl in proj_dir.glob("*.jsonl"):
                    if jsonl.name.startswith("agent-"):
                        continue
                    key = str(jsonl)
                    seen.add(key)
                    try:
                        size = jsonl.stat().st_size
                    except OSError:
                        continue
                    state = self._files.get(key)
                    if state is not None and state["off"] == size:
                        continue
                    if state is None or size < state["off"]:
                        # new file, or rewritten shorter than we had read
                        state = {"off": 0, "rows": {}}
                        self._files[key] = state
                    if self._read_tail(jsonl, proj_dir.name, state):
                        changed = True

        for gone in set(self._files) - seen:
            del self._files[gone]
            changed = True
        return changed

    def _read_tail(self, path, dir_name, state):
        """Consume the appended bytes in blocks; a transcript can be 100+ MB."""
        changed = False
        start = state["off"]
        read = 0
        pending = b""
        try:
            with open(path, "rb") as fh:
                fh.seek(start)
                while True:
                    block = fh.read(1 << 22)  # 4 MiB
                    if not block:
                        break
                    read += len(block)
                    buf = pending + block
                    cut = buf.rfind(b"\n")
                    if cut == -1:
                        pending = buf  # a single line longer than one block
                        continue
                    pending = buf[cut + 1:]
                    lines = buf[:cut + 1].split(b"\n")
                    del buf
                    if self._ingest(lines, path.name, dir_name, state["rows"]):
                        changed = True
        except OSError:
            return changed
        # only whole lines count as consumed, so a half-written tail is re-read
        state["off"] = start + read - len(pending)
        return changed

    def _ingest(self, lines, file_name, dir_name, rows):
        """Fold one block of raw transcript lines into this file's rows."""
        changed = False
        for line in lines:
            if b'"type":"assistant"' not in line:
                continue
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
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

            out = usage.get("output_tokens") or 0
            key = message.get("id") or f"{file_name}:{obj.get('uuid')}"
            prev = rows.get(key)
            if prev is not None and prev[self.OUT] >= out:
                continue

            model = message.get("model") or "unknown"
            if model.startswith("<"):
                model = "unknown"
            local = ts.astimezone()
            # interned: day / family / project repeat across every row in a file
            rows[key] = (
                out,
                ts.timestamp(),
                sys.intern(local.strftime("%Y-%m-%d")),
                int(local.replace(minute=0, second=0, microsecond=0).timestamp() * 1000),
                sys.intern(_family(model)),
                sys.intern(_project_label(obj.get("cwd"), dir_name)),
                usage.get("input_tokens") or 0,
                out,
                usage.get("cache_read_input_tokens") or 0,
                usage.get("cache_creation_input_tokens") or 0,
            )
            changed = True
        return changed

    def _scan_snapshots(self):
        try:
            st = self.history_file.stat()
            sig = (st.st_size, st.st_mtime_ns)
        except OSError:
            sig = None
        if sig == self._snap_sig:
            return False
        self._snap_sig = sig
        self._snapshots = read_snapshots(self.history_file)
        return True

    # -- payload ----------------------------------------------------------
    def _rebuild(self, scan_ms):
        anchor, anchor_source = resolve_anchor(self._snapshots)
        anchor_epoch = anchor.timestamp()

        best = {}
        for state in self._files.values():
            for key, row in state["rows"].items():
                cur = best.get(key)
                if cur is None or row[self.OUT] > cur[self.OUT]:
                    best[key] = row

        buckets = defaultdict(lambda: [0, 0, 0, 0, 0])      # i, o, cr, cc, n
        hourly = defaultdict(lambda: [0, 0, 0, 0, 0])
        periods = {}
        first_ts = last_ts = None
        hourly_cutoff = (time.time() - HOURLY_WINDOW_HOURS * 3600) * 1000

        for row in best.values():
            ts = row[self.TS]
            if first_ts is None or ts < first_ts:
                first_ts = ts
            if last_ts is None or ts > last_ts:
                last_ts = ts

            p_epoch = _period_start_epoch(ts, anchor_epoch)
            if p_epoch not in periods:
                periods[p_epoch] = datetime.fromtimestamp(p_epoch, tz=timezone.utc).isoformat()

            b = buckets[(periods[p_epoch], row[self.DAY], row[self.FAM], row[self.PROJ])]
            b[0] += row[self.IN]
            b[1] += row[self.OUTT]
            b[2] += row[self.CR]
            b[3] += row[self.CC]
            b[4] += 1

            if row[self.HOUR] >= hourly_cutoff:
                h = hourly[(row[self.HOUR], row[self.FAM])]
                h[0] += row[self.IN]
                h[1] += row[self.OUTT]
                h[2] += row[self.CR]
                h[3] += row[self.CC]
                h[4] += 1

        records = [
            {
                "w": period, "d": day, "m": fam, "p": project,
                "i": b[0], "o": b[1], "cr": b[2], "cc": b[3], "n": b[4],
                "c": round(_cost_of(fam, b[0], b[1], b[2], b[3]), 4),
            }
            for (period, day, fam, project), b in buckets.items()
        ]
        records.sort(key=lambda r: (r["w"], r["d"]))

        hourly_rows = [
            {
                "t": hour, "m": fam, "n": h[4],
                "k": h[0] + h[1] + h[2] + h[3],
                "c": round(_cost_of(fam, h[0], h[1], h[2], h[3]), 4),
            }
            for (hour, fam), h in sorted(hourly.items())
        ]

        snapshots = [
            {
                "ts": row.get("ts"),
                "w": datetime.fromtimestamp(
                    _period_start_epoch(_parse_ts(row.get("ts")).timestamp(), anchor_epoch),
                    tz=timezone.utc,
                ).isoformat(),
                "all": row.get("all_models_pct"),
                "session": row.get("session_pct"),
                "src": row.get("source"),
            }
            for row in self._snapshots
            if row.get("all_models_pct") is not None and _parse_ts(row.get("ts"))
        ]

        now = datetime.now(timezone.utc)
        next_reset = anchor
        if next_reset <= now:
            ahead = math.ceil((now - anchor).total_seconds() / WEEK_SECONDS)
            next_reset = anchor + WEEK * max(ahead, 1)

        payload = {
            "version": self._version + 1,
            "generated": datetime.now().astimezone().isoformat(),
            "anchor": anchor.isoformat(),
            "anchorSource": anchor_source,
            "nextReset": next_reset.astimezone().isoformat(),
            "weekSeconds": WEEK_SECONDS,
            "colors": _SERIES_COLORS,
            "records": records,
            "hourly": hourly_rows,
            "snapshots": snapshots,
            "firstSeen": datetime.fromtimestamp(first_ts).astimezone().isoformat() if first_ts else None,
            "lastSeen": datetime.fromtimestamp(last_ts).astimezone().isoformat() if last_ts else None,
            "messages": len(best),
            "scanMs": scan_ms,
        }

        # A rescan that finds only rewritten-but-identical bytes should not
        # invalidate the client's copy, so compare everything but the metadata.
        if self._payload is not None and _same_numbers(self._payload, payload):
            self._payload["nextReset"] = payload["nextReset"]
            return False
        self._version += 1
        self._payload = payload
        return True


def _same_numbers(a, b):
    keys = ("records", "hourly", "snapshots", "anchor", "colors")
    return all(a.get(k) == b.get(k) for k in keys)


_DEFAULT_SCANNER = Scanner()


def build_payload(live=False, poll_seconds=15):
    """One-shot payload for the static report."""
    return _DEFAULT_SCANNER.payload(max_age=0, live=live, poll_seconds=poll_seconds)


def render_page(payload, live=False, endpoint=None, poll_seconds=15):
    """Fill the HTML shell. In live mode the payload is fetched, not inlined."""
    config = {"live": bool(live), "endpoint": endpoint or "", "pollSeconds": poll_seconds}
    return (
        report_template.TEMPLATE
        .replace("/*__PAYLOAD__*/", "null" if live else json.dumps(payload, ensure_ascii=False))
        .replace("/*__CONFIG__*/", json.dumps(config))
    )


def generate_report(path=REPORT_FILE):
    """Write a self-contained snapshot of the report and return its path."""
    html = render_page(build_payload(live=False), live=False)
    path = Path(path)
    path.write_text(html, encoding="utf-8")
    return path


if __name__ == "__main__":
    if "--serve" in sys.argv:
        import report_server

        report_server.main()
    else:
        print(generate_report())
