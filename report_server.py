#!/usr/bin/env python3
"""
Local HTTP server behind the live usage dashboard.

The report used to be a file:// snapshot, which cannot refresh itself: a
file:// page is not allowed to fetch a sibling JSON file, and rewriting the
HTML would throw away scroll position and the selected range. So the page is
served from 127.0.0.1 instead and polls `/api/usage`.

Scope of trust: the listener is bound to the loopback interface, every request
must carry the token minted at startup, and the Host header must be loopback
(cheap defence against DNS rebinding). Nothing is written by the server, and no
request reaches claude.ai - it only reads the local files the menu bar app
already reads.
"""

import hashlib
import hmac
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import usage_report

POLL_SECONDS = 15
_LOOPBACK = ("127.0.0.1", "localhost", "[::1]", "::1")


class _Handler(BaseHTTPRequestHandler):
    server_version = "ClaudeUsage"
    protocol_version = "HTTP/1.1"

    # -- helpers ----------------------------------------------------------
    def _send(self, status, body=b"", content_type="text/plain; charset=utf-8", extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def _authorised(self, query):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        if host and host not in _LOOPBACK:
            return False
        given = (query.get("k") or [""])[0]
        expected = self.server.token
        return hmac.compare_digest(
            hashlib.sha256(given.encode()).digest(),
            hashlib.sha256(expected.encode()).digest(),
        )

    def log_message(self, *args):
        pass  # the menu bar app has no console to log into

    # -- routes -----------------------------------------------------------
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if not self._authorised(query):
            self._send(403, b"Forbidden")
            return

        if parsed.path in ("/", "/index.html"):
            endpoint = "/api/usage?k=" + self.server.token
            html = usage_report.render_page(
                None, live=True, endpoint=endpoint, poll_seconds=POLL_SECONDS
            )
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            return

        if parsed.path == "/api/usage":
            scanner = self.server.scanner
            try:
                payload = scanner.payload(max_age=2.0, live=True, poll_seconds=POLL_SECONDS)
            except Exception as exc:  # a broken scan must not kill the poll loop
                self._send(500, json.dumps({"error": str(exc)}).encode("utf-8"),
                           "application/json; charset=utf-8")
                return
            try:
                seen = int((query.get("v") or ["0"])[0])
            except ValueError:
                seen = 0
            if seen and seen == payload.get("version"):
                self.send_response(304)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return

        self._send(404, b"Not found")


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


_state = {"url": None, "server": None}
_lock = threading.Lock()


def start(port=0, warm=True):
    """Start the dashboard server once and return its URL (token included)."""
    with _lock:
        if _state["url"]:
            return _state["url"]

        scanner = usage_report.Scanner()
        server = _Server(("127.0.0.1", port), _Handler)
        server.token = secrets.token_urlsafe(18)
        server.scanner = scanner

        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.5},
                         daemon=True, name="usage-report-server").start()
        if warm:
            # The first scan reads every transcript; do it off the request path
            # so the page is not staring at a spinner for several seconds.
            threading.Thread(target=scanner.refresh, daemon=True, name="usage-report-warm").start()

        _state["server"] = server
        _state["url"] = "http://127.0.0.1:%d/?k=%s" % (server.server_address[1], server.token)
        return _state["url"]


def stop():
    with _lock:
        if _state["server"]:
            _state["server"].shutdown()
            _state["server"].server_close()
        _state["server"] = None
        _state["url"] = None


def main():
    import webbrowser

    url = start()
    print(url)
    webbrowser.open(url)
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        stop()


if __name__ == "__main__":
    main()
