"""
Push the usage dashboard payload to a cloud mirror (see cloud/server.py), so
the history can be read from a phone while the Mac is elsewhere.

Off unless both a server URL and an upload token are configured. What is sent
is exactly the dashboard payload: aggregated token counts, estimated costs,
quota readings and project names (the working directory's folder name). No
transcript text, cookie or org id leaves the machine.

Each pass rescans the transcripts incrementally (cheap once warm), uploads the
gzipped payload when the numbers moved, and otherwise sends a heartbeat so the
page can show that the Mac is still online.
"""

import gzip
import json
import threading

import requests

import usage_report

INTERVAL = 5 * 60
TIMEOUT = 30


class CloudSync:
    def __init__(self, user_agent, on_result):
        self._user_agent = user_agent
        self._on_result = on_result   # called from the worker thread: (ok: bool, message: str)
        self._url = ""
        self._token = ""
        self._digest = None           # server's digest of what it holds, from the last upload
        self._sent_version = None
        self._busy = threading.Lock()

    def configure(self, url, token):
        url = (url or "").strip().rstrip("/")
        if url != self._url or token != self._token:
            self._digest = None
            self._sent_version = None
        self._url, self._token = url, (token or "").strip()

    @property
    def enabled(self):
        return bool(self._url and self._token)

    def sync_async(self):
        if self.enabled:
            threading.Thread(target=self.sync, daemon=True, name="cloud-sync").start()

    def sync(self):
        """One pass. Returns (ok, message); also reported through on_result."""
        if not self.enabled or not self._busy.acquire(blocking=False):
            return None
        try:
            result = self._sync()
        except requests.RequestException as e:
            result = (False, "Cannot reach server: %s" % type(e).__name__)
        except Exception as e:  # a failed pass must not take the app down
            result = (False, str(e))
        finally:
            self._busy.release()
        self._on_result(*result)
        return result

    def _post(self, path, data=None, headers=None):
        h = {"Authorization": "Bearer " + self._token, "User-Agent": self._user_agent}
        h.update(headers or {})
        return requests.post(self._url + path, data=data, headers=h, timeout=TIMEOUT)

    def _sync(self):
        scanner = usage_report.shared_scanner()
        payload = scanner.payload(max_age=0)
        version = scanner.version

        if self._digest and version == self._sent_version:
            r = self._post("/api/ping", headers={"X-Payload-Digest": self._digest})
            if r.status_code == 200:
                return True, "Synced"
            if r.status_code != 409:
                return False, _error(r)
            # the server lost or replaced its copy - fall through to a full upload

        body = gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        r = self._post("/api/upload", data=body,
                       headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})
        if r.status_code != 200:
            return False, _error(r)
        self._digest = r.json().get("digest")
        self._sent_version = version
        return True, "Synced"


def _error(response):
    try:
        message = response.json().get("error")
    except ValueError:
        message = None
    return "HTTP %d%s" % (response.status_code, (" · " + message) if message else "")
