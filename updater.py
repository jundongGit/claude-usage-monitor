"""
In-app updates from GitHub Releases.

The latest release is read from the GitHub API; its ``.app.zip`` asset (signed with
the FREEAI Developer ID and notarized by sign_notarize.sh) is downloaded, verified
and swapped in place of the running bundle, then the app relaunches itself.

A downloaded bundle is installed only if all of these hold, so a tampered or
mislabelled asset can never replace the app:
- it is a valid code signature (``codesign --verify --deep --strict``)
- it is signed by the same team as the running app (``TEAM_ID``)
- Gatekeeper accepts it (``spctl --assess``: notarized Developer ID)
- its bundle id and version match the running app and the release tag
"""

import os
import plistlib
import re
import shutil
import subprocess
import tempfile

import requests

REPO = "jundongGit/claude-usage-monitor"
FEED_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
TEAM_ID = "XF9W8A344D"
BUNDLE_ID = "com.freeai.claudeusagemonitor"
CHECK_INTERVAL = 24 * 3600


class UpdateError(Exception):
    """A failure the user should see as-is."""


def parse_version(text):
    """'v1.7.10' -> (1, 7, 10); None when the tag is not a plain version."""
    m = re.fullmatch(r"v?(\d+(?:\.\d+){0,3})", (text or "").strip())
    return tuple(int(p) for p in m.group(1).split(".")) if m else None


def is_newer(candidate, current):
    a, b = parse_version(candidate), parse_version(current)
    if a is None or b is None:
        return False
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def latest_release(feed_url=FEED_URL):
    """Return {'version', 'zip_url', 'page'} for the newest release, or raise UpdateError."""
    try:
        r = requests.get(feed_url, timeout=10, headers={"Accept": "application/vnd.github+json"})
    except requests.RequestException as e:
        raise UpdateError(f"Unable to reach GitHub: {e}") from e
    if r.status_code != 200:
        raise UpdateError(f"GitHub returned HTTP {r.status_code}")
    data = r.json()
    version = (data.get("tag_name") or "").lstrip("v")
    if parse_version(version) is None:
        raise UpdateError(f"Unrecognised release tag: {data.get('tag_name')!r}")
    zips = [a for a in data.get("assets", []) if a.get("name", "").endswith(".app.zip")]
    if not zips:
        raise UpdateError(f"Release v{version} has no .app.zip asset")
    return {
        "version": version,
        "zip_url": zips[0]["browser_download_url"],
        "page": data.get("html_url") or RELEASES_PAGE,
    }


def running_bundle():
    """Path of the running .app, or None when running from source."""
    try:
        from Foundation import NSBundle
        path = NSBundle.mainBundle().bundlePath()
    except Exception:
        return None
    return path if path and path.endswith(".app") else None


def can_install_in_place(bundle):
    return bool(bundle) and os.access(os.path.dirname(bundle), os.W_OK) and os.access(bundle, os.W_OK)


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def _verify(app, version):
    info = plistlib.load(open(os.path.join(app, "Contents", "Info.plist"), "rb"))
    if info.get("CFBundleIdentifier") != BUNDLE_ID:
        raise UpdateError(f"Unexpected bundle id: {info.get('CFBundleIdentifier')}")
    if info.get("CFBundleShortVersionString") != version:
        raise UpdateError(
            f"Package version {info.get('CFBundleShortVersionString')} does not match release v{version}")

    r = _run(["/usr/bin/codesign", "--verify", "--deep", "--strict", app])
    if r.returncode != 0:
        raise UpdateError("Code signature is invalid: " + (r.stderr.strip() or "codesign failed"))
    r = _run(["/usr/bin/codesign", "-dv", app])
    if f"TeamIdentifier={TEAM_ID}" not in r.stderr:
        raise UpdateError("Package is not signed by the expected developer")
    r = _run(["/usr/sbin/spctl", "--assess", "--type", "execute", app])
    if r.returncode != 0:
        raise UpdateError("Gatekeeper rejected the package: " + (r.stderr.strip() or "spctl failed"))


def download_and_install(release, bundle):
    """Download, verify and swap the bundle at `bundle`. Raises UpdateError.

    Runs off the main thread. The old bundle is kept until the new one is in
    place and restored if the swap fails.
    """
    work = tempfile.mkdtemp(prefix="cum-update-")
    try:
        archive = os.path.join(work, "update.zip")
        try:
            with requests.get(release["zip_url"], stream=True, timeout=30) as r:
                if r.status_code != 200:
                    raise UpdateError(f"Download failed: HTTP {r.status_code}")
                with open(archive, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
        except requests.RequestException as e:
            raise UpdateError(f"Download failed: {e}") from e

        extracted = os.path.join(work, "x")
        r = _run(["/usr/bin/ditto", "-x", "-k", archive, extracted])
        if r.returncode != 0:
            raise UpdateError("Could not unpack the update: " + r.stderr.strip())
        apps = [n for n in os.listdir(extracted) if n.endswith(".app")]
        if len(apps) != 1:
            raise UpdateError("Update archive does not contain exactly one app")
        new_app = os.path.join(extracted, apps[0])
        _verify(new_app, release["version"])

        # Backup beside the bundle: a rename never crosses volumes there
        backup = os.path.join(os.path.dirname(bundle), ".ClaudeUsageMonitor-previous.app")
        shutil.rmtree(backup, ignore_errors=True)
        os.rename(bundle, backup)
        r = _run(["/usr/bin/ditto", new_app, bundle])
        if r.returncode != 0:
            shutil.rmtree(bundle, ignore_errors=True)
            os.rename(backup, bundle)
            raise UpdateError("Could not replace the app: " + r.stderr.strip())
        # The running process keeps its already-loaded files until it exits
        shutil.rmtree(backup, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def relaunch(bundle):
    """Start a detached helper that reopens `bundle` once this process has exited.

    The helper is a child of this app, so macOS attributes the relaunched menu bar
    item to the app itself (launching from a terminal would attribute it to the
    terminal and could hide it).
    """
    script = 'while kill -0 "$1" 2>/dev/null; do sleep 0.2; done; /usr/bin/open "$2"'
    subprocess.Popen(["/bin/sh", "-c", script, "relaunch", str(os.getpid()), bundle],
                     start_new_session=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
