"""
Cloud mirror of the usage dashboard, for reading it away from the Mac.

The menu bar app pushes the same payload the local dashboard renders
(`POST /api/upload`, bearer token) and, while nothing changed, a heartbeat
(`POST /api/ping`) so the page can tell "no new usage" from "the Mac is off".
Viewers sign in with a username and password and get the unchanged dashboard
template, polling `/api/usage` on this server instead of the loopback one.

Only the latest payload is kept; it is the full history already, aggregated.
"""

import calendar
import gzip
import hashlib
import hmac
import io
import json
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from html import escape
from pathlib import Path

import bcrypt
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

import report_template

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
PAYLOAD_FILE = DATA_DIR / "payload.json"
SYNC_FILE = DATA_DIR / "sync.json"

ADMIN_USERNAME = os.environ["ADMIN_USERNAME"]
ADMIN_PASSWORD_HASH = os.environ["ADMIN_PASSWORD_HASH"].encode()
UPLOAD_TOKEN = os.environ["UPLOAD_TOKEN"]
SESSION_SECRET = os.environ["SESSION_SECRET"].encode()
COOKIE_NAME = "cu_session"
SESSION_DAYS = 30
POLL_SECONDS = 30
MAX_UPLOAD_BYTES = 8 * 1024 * 1024      # compressed
MAX_PAYLOAD_BYTES = 64 * 1024 * 1024    # decompressed
REQUIRED_KEYS = ("records", "hourly", "snapshots", "colors", "generated")

LOGIN_WINDOW = 15 * 60
LOGIN_ATTEMPTS = 5

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
_lock = threading.Lock()
_failures = defaultdict(deque)


# -- storage ----------------------------------------------------------------
def _write_atomic(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def _load_sync():
    try:
        return json.loads(SYNC_FILE.read_text())
    except (OSError, ValueError):
        return {"version": 0, "digest": None, "uploadedAt": None, "seenAt": None, "client": None}


def _save_sync(sync):
    _write_atomic(SYNC_FILE, json.dumps(sync).encode())


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# -- auth -------------------------------------------------------------------
def _digest_equal(a, b):
    return hmac.compare_digest(hashlib.sha256(a.encode()).digest(), hashlib.sha256(b.encode()).digest())


def _upload_authorised(request):
    header = request.headers.get("authorization", "")
    return header.startswith("Bearer ") and _digest_equal(header[7:], UPLOAD_TOKEN)


def _sign(value):
    return hmac.new(SESSION_SECRET, value.encode(), hashlib.sha256).hexdigest()


def _make_session():
    value = "%s|%d|%s" % (ADMIN_USERNAME, int(time.time()) + SESSION_DAYS * 86400, secrets.token_hex(8))
    return value + "|" + _sign(value)


def _session_valid(request):
    raw = request.cookies.get(COOKIE_NAME, "")
    value, _, sig = raw.rpartition("|")
    if not value or not hmac.compare_digest(_sign(value), sig):
        return False
    user, expires, _nonce = (value.split("|") + ["", "", ""])[:3]
    return user == ADMIN_USERNAME and expires.isdigit() and int(expires) > time.time()


def _client_ip(request):
    # behind Cloudflare -> NPM, the peer and X-Real-IP are proxies, not the viewer
    return (request.headers.get("cf-connecting-ip") or request.headers.get("x-real-ip")
            or (request.client.host if request.client else "?"))


def _rate_limited(ip):
    attempts = _failures[ip]
    while attempts and attempts[0] < time.time() - LOGIN_WINDOW:
        attempts.popleft()
    return len(attempts) >= LOGIN_ATTEMPTS


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


# -- upload (menu bar app) --------------------------------------------------
@app.post("/api/upload")
async def upload(request: Request):
    if not _upload_authorised(request):
        return JSONResponse({"error": "Invalid upload token"}, status_code=401)
    body = await request.body()
    if len(body) > MAX_UPLOAD_BYTES:
        return JSONResponse({"error": "Payload too large"}, status_code=413)
    try:
        if request.headers.get("content-encoding") == "gzip":
            with gzip.GzipFile(fileobj=io.BytesIO(body)) as gz:
                body = gz.read(MAX_PAYLOAD_BYTES + 1)
        if len(body) > MAX_PAYLOAD_BYTES:
            return JSONResponse({"error": "Payload too large"}, status_code=413)
        payload = json.loads(body)
    except (OSError, ValueError):
        return JSONResponse({"error": "Body is not valid JSON"}, status_code=400)
    if not isinstance(payload, dict) or any(k not in payload for k in REQUIRED_KEYS):
        return JSONResponse({"error": "Payload is missing required fields"}, status_code=400)

    numbers = {k: payload.get(k) for k in ("records", "hourly", "snapshots", "anchor", "colors")}
    digest = hashlib.sha256(json.dumps(numbers, sort_keys=True).encode()).hexdigest()
    with _lock:
        sync = _load_sync()
        now = _now_iso()
        if digest != sync.get("digest") or not PAYLOAD_FILE.exists():
            sync["version"] = int(sync.get("version") or 0) + 1
            sync["digest"] = digest
            sync["uploadedAt"] = now
        for k in ("live", "pollSeconds", "version"):
            payload.pop(k, None)
        _write_atomic(PAYLOAD_FILE, json.dumps(payload, ensure_ascii=False).encode())
        sync["seenAt"] = now
        sync["client"] = (request.headers.get("user-agent") or "")[:80]
        _save_sync(sync)
    return {"version": sync["version"], "digest": digest, "seenAt": now}


@app.post("/api/ping")
async def ping(request: Request):
    """Heartbeat while the numbers are unchanged; 409 asks for a full upload."""
    if not _upload_authorised(request):
        return JSONResponse({"error": "Invalid upload token"}, status_code=401)
    with _lock:
        sync = _load_sync()
        if not PAYLOAD_FILE.exists() or request.headers.get("x-payload-digest") != sync.get("digest"):
            return JSONResponse({"error": "Upload required"}, status_code=409)
        sync["seenAt"] = _now_iso()
        _save_sync(sync)
    return {"version": sync["version"], "seenAt": sync["seenAt"]}


# -- viewer -----------------------------------------------------------------
@app.get("/api/usage")
def usage(request: Request, v: int = 0):
    if not _session_valid(request):
        return _no_store(JSONResponse({"error": "Not signed in"}, status_code=401))
    with _lock:
        sync = _load_sync()
        if not PAYLOAD_FILE.exists():
            return _no_store(JSONResponse({"error": "No data uploaded yet"}, status_code=404))
        # seenAt moves on every heartbeat, so it is part of what the page must refresh
        stamp = int(sync["version"]) * 10**10 + calendar.timegm(time.strptime(sync["seenAt"], "%Y-%m-%dT%H:%M:%SZ"))
        if v and v == stamp:
            return _no_store(Response(status_code=304))
        payload = json.loads(PAYLOAD_FILE.read_text())
    payload.update(version=stamp, live=True, pollSeconds=POLL_SECONDS,
                   syncedAt=sync["seenAt"], uploadedAt=sync["uploadedAt"])
    return _no_store(JSONResponse(payload))


@app.get("/")
def dashboard(request: Request):
    if not _session_valid(request):
        return RedirectResponse("/login", status_code=303)
    config = {"live": True, "cloud": True, "endpoint": "/api/usage", "pollSeconds": POLL_SECONDS}
    html = (report_template.TEMPLATE
            .replace("/*__PAYLOAD__*/", "null")
            .replace("/*__CONFIG__*/", json.dumps(config)))
    return _no_store(HTMLResponse(html))


@app.get("/healthz")
def healthz():
    return {"ok": True}


# -- login ------------------------------------------------------------------
LOGIN_PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Claude Usage · 登录</title>
<style>
:root{--bg:#f5f6f8;--card:#fff;--text:#1f2329;--muted:#6b7280;--border:#d9dce1;--accent:#1677ff;--danger:#d93026}
@media (prefers-color-scheme:dark){:root{--bg:#141517;--card:#1e1f22;--text:#e8e9eb;--muted:#9aa0a6;--border:#3a3c40;--danger:#ff6b5e}}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px;
  background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Segoe UI",sans-serif}
form{width:100%;max-width:360px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:28px 24px}
.brand{display:flex;align-items:center;gap:10px;margin-bottom:22px}
.brand svg{width:26px;height:26px;fill:none;stroke:var(--accent);stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
h1{font-size:18px;margin:0}
label{display:block;font-size:13px;color:var(--muted);margin:14px 0 6px}
input{width:100%;font-size:16px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:transparent;color:var(--text)}
input:focus{outline:none;border-color:var(--accent)}
button{width:100%;margin-top:22px;padding:11px;border:0;border-radius:8px;background:var(--accent);color:#fff;font-size:16px;cursor:pointer}
.err{color:var(--danger);font-size:13px;margin-top:14px;min-height:1em}
</style></head><body>
<form method="post" action="/login">
  <div class="brand"><svg viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/></svg><h1>Claude Usage</h1></div>
  <label for="u">用户名</label>
  <input id="u" name="username" value="__USER__" autocomplete="username" autocapitalize="off" autocorrect="off" spellcheck="false" required __FOCUS_U__>
  <label for="p">密码</label>
  <input id="p" name="password" type="password" autocomplete="current-password" required __FOCUS_P__>
  <button type="submit">登录</button>
  <div class="err">__ERROR__</div>
</form></body></html>"""


def _login_page(username="", error="", status=200):
    html = (LOGIN_PAGE.replace("__USER__", escape(username))
            .replace("__ERROR__", escape(error))
            .replace("__FOCUS_U__", "" if username else "autofocus")
            .replace("__FOCUS_P__", "autofocus" if username else ""))
    return _no_store(HTMLResponse(html, status_code=status))


@app.get("/login")
def login_form(request: Request):
    if _session_valid(request):
        return RedirectResponse("/", status_code=303)
    return _login_page()


@app.post("/login")
def login(request: Request, username: str = Form(""), password: str = Form("")):
    ip = _client_ip(request)
    if _rate_limited(ip):
        return _login_page(username, "尝试次数过多，请 15 分钟后再试", 429)
    ok_user = _digest_equal(username, ADMIN_USERNAME)
    ok_pass = bcrypt.checkpw(password.encode()[:72], ADMIN_PASSWORD_HASH)
    if not (ok_user and ok_pass):
        _failures[ip].append(time.time())
        return _login_page(username, "用户名或密码不正确", 401)
    _failures.pop(ip, None)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(COOKIE_NAME, _make_session(), max_age=SESSION_DAYS * 86400,
                        httponly=True, secure=True, samesite="lax")
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response
