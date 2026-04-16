#!/usr/bin/env python3
"""
Claude Usage Monitor - macOS Status Bar App
Monitor Claude.ai usage and display in the status bar
"""

__version__ = "1.4.0"
__author__ = "Claude Usage Monitor Contributors"

import rumps
import requests
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os
import sys
import time
import webbrowser
from AppKit import (NSApp, NSAlert, NSAlertFirstButtonReturn, NSFloatingWindowLevel,
                     NSMenu, NSMenuItem, NSPasteboard, NSPasteboardTypeString)


# Model pricing ($/M tokens) — same as cc-statistics
_PRICING = {
    "opus": {"input": 15, "output": 75, "cache_read": 1.5, "cache_create": 18.75},
    "sonnet": {"input": 3, "output": 15, "cache_read": 0.3, "cache_create": 3.75},
    "haiku": {"input": 0.8, "output": 4, "cache_read": 0.08, "cache_create": 1.0},
}


def _match_pricing(model):
    lower = model.lower()
    for key in ("opus", "haiku", "sonnet"):
        if key in lower:
            return _PRICING[key]
    return _PRICING["sonnet"]


def _fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _fmt_cost(n):
    if n >= 100:
        return f"${n:.0f}"
    if n >= 1:
        return f"${n:.2f}"
    return f"${n:.3f}"


def get_today_token_stats():
    """Read ~/.claude/projects/ JSONL files, return today's token usage by model.

    Returns dict: {model_name: {input, output, cache_read, cache_create}}
    """
    claude_projects = Path.home() / ".claude" / "projects"
    if not claude_projects.exists():
        return {}

    today = datetime.now().strftime("%Y-%m-%d")
    model_usage = {}  # model -> {input, output, cache_read, cache_create}
    seen_message_ids = {}  # message_id -> max output_tokens (for dedup)

    for proj_dir in claude_projects.iterdir():
        if not proj_dir.is_dir():
            continue
        for jsonl_file in proj_dir.glob("*.jsonl"):
            if jsonl_file.name.startswith("agent-"):
                continue
            # Skip files not modified today (optimization)
            try:
                mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
                if mtime.strftime("%Y-%m-%d") < today:
                    continue
            except OSError:
                continue

            try:
                with open(jsonl_file, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        if obj.get("type") != "assistant":
                            continue

                        # Check timestamp is today
                        ts = obj.get("timestamp", "")
                        if not ts:
                            continue
                        try:
                            if isinstance(ts, (int, float)) or str(ts).isdigit():
                                dt = datetime.fromtimestamp(int(ts) / 1000)
                            else:
                                dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
                            if dt.strftime("%Y-%m-%d") != today:
                                continue
                        except (ValueError, OSError):
                            continue

                        raw_msg = obj.get("message", {})
                        usage = raw_msg.get("usage", {})
                        if not usage:
                            continue

                        # Streaming dedup: keep the record with max output_tokens per message_id
                        msg_id = raw_msg.get("id", "")
                        out_tokens = usage.get("output_tokens", 0) or 0
                        if msg_id:
                            prev_out = seen_message_ids.get(msg_id, -1)
                            if out_tokens <= prev_out:
                                continue
                            # Remove previous record's contribution
                            if prev_out >= 0:
                                prev_model = seen_message_ids.get(f"{msg_id}_model", "unknown")
                                if prev_model in model_usage:
                                    prev_usage = seen_message_ids.get(f"{msg_id}_usage", {})
                                    mu = model_usage[prev_model]
                                    mu["input"] -= prev_usage.get("input_tokens", 0)
                                    mu["output"] -= prev_usage.get("output_tokens", 0)
                                    mu["cache_read"] -= prev_usage.get("cache_read_input_tokens", 0)
                                    mu["cache_create"] -= prev_usage.get("cache_creation_input_tokens", 0)
                            seen_message_ids[msg_id] = out_tokens
                            seen_message_ids[f"{msg_id}_usage"] = usage
                            seen_message_ids[f"{msg_id}_model"] = raw_msg.get("model", "unknown")

                        model = raw_msg.get("model") or "unknown"
                        if model.startswith("<"):
                            model = "unknown"

                        if model not in model_usage:
                            model_usage[model] = {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0}

                        mu = model_usage[model]
                        mu["input"] += usage.get("input_tokens", 0) or 0
                        mu["output"] += usage.get("output_tokens", 0) or 0
                        mu["cache_read"] += usage.get("cache_read_input_tokens", 0) or 0
                        mu["cache_create"] += usage.get("cache_creation_input_tokens", 0) or 0

            except (OSError, UnicodeDecodeError):
                continue

    return model_usage


class ClaudeUsageApp(rumps.App):
    def __init__(self):
        super(ClaudeUsageApp, self).__init__(
            "Claude",
            icon=None,  # Use text display, no icon needed
            quit_button=None
        )

        # Configuration
        self.config_file = os.path.expanduser("~/.claude_usage_config.json")
        self.plist_path = os.path.expanduser("~/Library/LaunchAgents/com.claude.usage.monitor.plist")

        # Notification deduplication mechanism
        self.last_notification_time = {}

        self.load_config()

        # Mark if this is first run
        self.first_run = not self.cookie and not self.org_id

        # Menu items
        self.menu = [
            rumps.MenuItem(f"📊 Claude Usage Monitor v{__version__}", callback=None),
            rumps.separator,
            rumps.MenuItem("⏱️  5-Hour Limit: Loading...", callback=None),
            rumps.MenuItem("🛠️  All Models: Loading...", callback=None),
            rumps.MenuItem("🔷 Sonnet Limit: Loading...", callback=None),
            rumps.separator,
            rumps.MenuItem("📈 Today: Loading...", callback=None),
            rumps.MenuItem("    ⬇️  Input: ...", callback=None),
            rumps.MenuItem("    ⬆️  Output: ...", callback=None),
            rumps.MenuItem("💰 Cost: Loading...", callback=None),
            rumps.separator,
            rumps.MenuItem("🔄 Refresh", callback=self.refresh_usage),
            rumps.MenuItem("⚙️  Settings", callback=self.set_config),
            rumps.MenuItem("🚀 Auto-start on Login", callback=self.toggle_autostart),
            rumps.separator,
            rumps.MenuItem("❌ Quit", callback=rumps.quit_application)
        ]

        # Update auto-start menu status (must be after menu creation)
        self.update_autostart_menu()

        # First run guide
        if self.first_run:
            self.show_welcome_guide()

        # Fetch data on startup
        self.refresh_usage(None)

        # Add Edit menu so Cmd+V paste works in dialogs (delayed, NSApp not ready in __init__)
        self._edit_menu_timer = rumps.Timer(self._deferred_setup_edit_menu, 1)
        self._edit_menu_timer.start()

        # Set timer to refresh every 1 minute
        self.timer = rumps.Timer(self.refresh_usage, 60)
        self.timer.start()

    def _deferred_setup_edit_menu(self, _):
        """Add standard Edit menu so Cmd+C/V/X/A work in dialogs"""
        self._edit_menu_timer.stop()
        try:
            mainMenu = NSApp.mainMenu()
            if mainMenu is None:
                mainMenu = NSMenu.alloc().init()
                NSApp.setMainMenu_(mainMenu)

            edit_menu = NSMenu.alloc().initWithTitle_("Edit")
            edit_menu.addItemWithTitle_action_keyEquivalent_("Undo", "undo:", "z")
            edit_menu.addItemWithTitle_action_keyEquivalent_("Cut", "cut:", "x")
            edit_menu.addItemWithTitle_action_keyEquivalent_("Copy", "copy:", "c")
            edit_menu.addItemWithTitle_action_keyEquivalent_("Paste", "paste:", "v")
            edit_menu.addItemWithTitle_action_keyEquivalent_("Select All", "selectAll:", "a")

            edit_item = NSMenuItem.alloc().init()
            edit_item.setSubmenu_(edit_menu)
            mainMenu.addItem_(edit_item)
        except Exception as e:
            print(f"Setup edit menu failed: {e}")

    def load_config(self):
        """Load configuration file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.cookie = config.get('cookie', '')
                    self.org_id = config.get('org_id', '')
                    self.account_name = config.get('account_name', '')
            except json.JSONDecodeError as e:
                print(f"Config file corrupted, reset: {e}")
                # Backup corrupted file
                if os.path.exists(self.config_file):
                    backup_file = f"{self.config_file}.backup"
                    try:
                        os.rename(self.config_file, backup_file)
                        print(f"Corrupted config backed up to: {backup_file}")
                    except Exception:
                        pass
                self.cookie = ''
                self.org_id = ''
                self.account_name = ''
            except Exception as e:
                print(f"Error loading config file: {e}")
                self.cookie = ''
                self.org_id = ''
                self.account_name = ''
        else:
            self.cookie = ''
            self.org_id = ''
            self.account_name = ''

    def save_config(self):
        """Save configuration file"""
        config = {
            'cookie': self.cookie,
            'org_id': self.org_id,
            'account_name': self.account_name
        }
        try:
            # Write config file
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

            # Set secure permissions (600 - owner only)
            os.chmod(self.config_file, 0o600)
            print(f"Config saved, permissions set to 600")
        except Exception as e:
            print(f"Error saving config file: {e}")
            rumps.alert("Error", f"Unable to save config: {str(e)}")

    def format_time_remaining(self, reset_time_str):
        """Calculate and format remaining time"""
        if not reset_time_str:
            return "Unused"

        try:
            reset_time = datetime.fromisoformat(reset_time_str.replace('+00:00', '+0000'))
            now = datetime.now(timezone.utc)
            remaining = reset_time - now

            if remaining.total_seconds() < 0:
                return "Expired"

            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)

            if hours > 24:
                days = hours // 24
                hours = hours % 24
                return f"{days}d {hours}hr"
            elif hours > 0:
                return f"{hours}hr {minutes}min"
            else:
                return f"{minutes}min"
        except Exception as e:
            print(f"Time parse error: {e}")
            return "Parse failed"

    def format_time_short(self, reset_time_str):
        """Format short countdown (for status bar)"""
        if not reset_time_str:
            return ""

        try:
            reset_time = datetime.fromisoformat(reset_time_str.replace('+00:00', '+0000'))
            now = datetime.now(timezone.utc)
            remaining = reset_time - now

            if remaining.total_seconds() < 0:
                return "Expired"

            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)

            if hours > 24:
                days = hours // 24
                hours = hours % 24
                return f"{days}d{hours}h"
            elif hours > 0:
                return f"{hours}h{minutes}m"
            else:
                return f"{minutes}m"
        except Exception as e:
            return ""

    def show_welcome_guide(self):
        """Show welcome guide for first run"""
        response = self._top_alert(
            title="Welcome to Claude Usage Monitor",
            message=(
                "Thank you for using Claude Usage Monitor!\n\n"
                "Setup only takes one step:\n"
                "Copy a cURL command from browser DevTools\n"
                "and paste it here. That's it!\n\n"
                "Click \"Configure Now\" to get started."
            ),
            ok="Configure Now",
            cancel="Later"
        )
        if response == 1:
            self._manual_set_config()

    def _top_alert(self, title, message, ok="OK", cancel=None):
        """Show an alert dialog that floats above all windows"""
        NSApp.activateIgnoringOtherApps_(True)
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_(ok)
        if cancel:
            alert.addButtonWithTitle_(cancel)
        alert.window().setLevel_(NSFloatingWindowLevel)
        result = alert.runModal()
        return 1 if result == NSAlertFirstButtonReturn else 0

    def _read_clipboard(self):
        """Read text content from system clipboard"""
        pb = NSPasteboard.generalPasteboard()
        text = pb.stringForType_(NSPasteboardTypeString)
        return str(text) if text else None

    def should_notify(self, notification_key, threshold=900):
        """
        Check if should send notification (prevent duplicates)

        Args:
            notification_key: Unique notification identifier
            threshold: Minimum interval between notifications (seconds), default 15 minutes

        Returns:
            bool: True if should send notification
        """
        now = time.time()
        last_time = self.last_notification_time.get(notification_key, 0)

        if now - last_time > threshold:
            self.last_notification_time[notification_key] = now
            return True
        return False

    def parse_curl_command(self, curl_text):
        """
        Parse cURL command to extract cookie and org_id.
        Supports:
        - Cookie via -H 'Cookie: ...' or -b '...'
        - Org ID from URL /organizations/{uuid}/ or from lastActiveOrg cookie
        Returns: (cookie, org_id) or (None, None) on failure
        """
        curl_text = curl_text.strip()
        if not curl_text:
            return None, None

        # Extract org_id from URL: /organizations/{uuid}/
        org_match = re.search(
            r'/organizations/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
            curl_text
        )
        org_id = org_match.group(1) if org_match else None

        # Extract cookie string from -H 'Cookie: ...' or -b '...'
        # Must match same quote type (cookie values may contain " from JSON)
        cookie_str = None
        for pattern in [
            r"""(?:-H|--header)\s+'Cookie:\s*([^']*)'""",
            r'''(?:-H|--header)\s+"Cookie:\s*([^"]*)"''',
            r"""(?:-b|--cookie)\s+'([^']*)'""",
            r'''(?:-b|--cookie)\s+"([^"]*)"''',
        ]:
            m = re.search(pattern, curl_text, re.DOTALL)
            if m:
                cookie_str = m.group(1).strip()
                break

        cookie = None
        if cookie_str:
            # Verify sessionKey exists in cookie string
            if re.search(r'sessionKey=', cookie_str):
                # Save full cookie string for Cloudflare compatibility
                cookie = cookie_str

            # If org_id not in URL, try lastActiveOrg from cookie
            if not org_id:
                org_cookie_match = re.search(
                    r'lastActiveOrg=([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
                    cookie_str
                )
                if org_cookie_match:
                    org_id = org_cookie_match.group(1)

        return cookie, org_id


    @rumps.clicked("⚙️  Settings")
    def set_config(self, _):
        """Open settings flow"""
        self._manual_set_config()

    def _manual_set_config(self):
        """One-step configuration: copy cURL, then read from clipboard"""
        # Step 1: Open usage page in browser
        choice = self._top_alert(
            title="Configure Claude Usage Monitor",
            message=(
                "Click \"Open Usage Page\" to open the page, then:\n\n"
                "1. Press F12 (or Cmd+Option+I) → Network tab\n"
                "2. Refresh the page\n"
                "3. Find any request (e.g. 'usage')\n"
                "4. Right-click → Copy as cURL\n\n"
                "After copying, come back and click Settings again."
            ),
            ok="Open Usage Page",
            cancel="Read from Clipboard"
        )

        if choice == 1:
            webbrowser.open("https://claude.ai/settings/usage")
            # Show reminder to come back
            self._top_alert(
                "Next Step",
                "After copying the cURL command (Cmd+C),\n"
                "click the button below to configure.",
                ok="Read from Clipboard"
            )

        # Step 2: Read from clipboard
        raw_text = self._read_clipboard()

        if not raw_text:
            self._top_alert("Error", "Clipboard is empty.\nPlease copy the cURL command first.")
            return

        cookie, org_id = self.parse_curl_command(raw_text)

        if not cookie:
            self._top_alert(
                "Parse Failed",
                "Could not find sessionKey in clipboard content.\n\n"
                "Make sure you right-clicked a request on claude.ai\n"
                "and selected \"Copy as cURL\"."
            )
            return

        if not org_id:
            self._top_alert(
                "Parse Failed",
                "Could not find Organization ID.\n\n"
                "Make sure you copied a cURL from claude.ai."
            )
            return

        self.cookie = cookie
        self.org_id = org_id

        # Save and refresh
        self.save_config()
        self.refresh_usage(None)
        rumps.notification(
            title="Configuration Saved",
            subtitle="",
            message="Cookie and Org ID extracted, refreshing..."
        )

    def is_autostart_enabled(self):
        """Check if auto-start is enabled"""
        return os.path.exists(self.plist_path)

    def update_autostart_menu(self):
        """Update auto-start menu item display status"""
        if self.is_autostart_enabled():
            self.menu["🚀 Auto-start on Login"].title = "🚀 Auto-start on Login ✓"
        else:
            self.menu["🚀 Auto-start on Login"].title = "🚀 Auto-start on Login"

    @rumps.clicked("🚀 Auto-start on Login")
    def toggle_autostart(self, _):
        """Toggle auto-start on login"""
        try:
            if self.is_autostart_enabled():
                # Disable auto-start
                os.system(f'launchctl unload "{self.plist_path}" 2>/dev/null')
                os.remove(self.plist_path)
                self.update_autostart_menu()
                rumps.notification(
                    title="Auto-start Disabled",
                    subtitle="",
                    message="Removed from login items"
                )
            else:
                # Enable auto-start
                # Detect if running from .app bundle
                script_path = os.path.abspath(__file__)

                if '.app/Contents/Resources' in script_path:
                    # Running from .app bundle, use 'open' command
                    app_path = script_path.split('.app/Contents')[0] + '.app'
                    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude.usage.monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>{app_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/claude-usage-monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/claude-usage-monitor.log</string>
</dict>
</plist>'''
                else:
                    # Running from Python script, use Python path
                    python_path = sys.executable
                    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude.usage.monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/claude-usage-monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/claude-usage-monitor.log</string>
</dict>
</plist>'''

                # Ensure directory exists
                os.makedirs(os.path.dirname(self.plist_path), exist_ok=True)

                # Write plist file
                with open(self.plist_path, 'w') as f:
                    f.write(plist_content)

                # Load service
                result = os.system(f'launchctl load "{self.plist_path}"')

                if result == 0:
                    self.update_autostart_menu()
                    rumps.notification(
                        title="Auto-start Enabled",
                        subtitle="",
                        message="Will launch automatically on system startup"
                    )
                else:
                    rumps.alert("Error", "Unable to load auto-start service")

        except Exception as e:
            rumps.alert("Error", f"Failed to setup auto-start: {str(e)}")

    def _browser_headers(self):
        """Return browser-like headers to avoid Cloudflare 403"""
        return {
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Ch-Ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Referer': 'https://claude.ai/settings/usage',
        }

    @rumps.clicked("🔄 Refresh")
    def refresh_usage(self, _):
        """Refresh usage data"""
        # Always update token stats (reads local files, no API needed)
        self.update_token_stats()

        if not self.cookie or not self.org_id:
            self.title = "⚠️"
            self.menu["⏱️  5-Hour Limit: Loading..."].title = "⏱️  5-Hour: Not configured"
            self.menu["🛠️  All Models: Loading..."].title = "🛠️  All Models: Not configured"
            self.menu["🔷 Sonnet Limit: Loading..."].title = "🔷 Sonnet only: Not configured"
            return

        try:
            # Call API
            url = f"https://claude.ai/api/organizations/{self.org_id}/usage"
            headers = self._browser_headers()

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.update_ui(data)
            elif response.status_code == 401:
                self.title = "🔒"
                rumps.notification(
                    title="Authentication Failed",
                    subtitle="",
                    message="Cookie expired, please reset"
                )
            else:
                self.title = "❌"
                self.menu["⏱️  5-Hour Limit: Loading..."].title = f"Error: HTTP {response.status_code}"

        except Exception as e:
            self.title = "❌"
            self.menu["⏱️  5-Hour Limit: Loading..."].title = f"Error: {str(e)}"
            print(f"Request failed: {e}")

    def update_token_stats(self):
        """Update today's token usage and cost from local JSONL files"""
        try:
            model_usage = get_today_token_stats()

            if not model_usage:
                self.menu["📈 Today: Loading..."].title = "📈 Today: 0 tokens"
                self.menu["    ⬇️  Input: ..."].title = "    ⬇️  Input: 0"
                self.menu["    ⬆️  Output: ..."].title = "    ⬆️  Output: 0"
                self.menu["💰 Cost: Loading..."].title = "💰 Cost: $0.000"
                return

            # Calculate totals
            total_input = sum(u["input"] for u in model_usage.values())
            total_output = sum(u["output"] for u in model_usage.values())
            total_cache_read = sum(u["cache_read"] for u in model_usage.values())
            total_cache_create = sum(u["cache_create"] for u in model_usage.values())
            total_tokens = total_input + total_output + total_cache_read + total_cache_create

            # Calculate cost per model
            total_cost = 0.0
            cost_parts = []
            for model, usage in sorted(model_usage.items(), key=lambda x: sum(x[1].values()), reverse=True):
                p = _match_pricing(model)
                cost = (
                    usage["input"] / 1e6 * p["input"]
                    + usage["output"] / 1e6 * p["output"]
                    + usage["cache_read"] / 1e6 * p["cache_read"]
                    + usage["cache_create"] / 1e6 * p["cache_create"]
                )
                total_cost += cost
                # Shorten model name
                short_name = model.split("/")[-1] if "/" in model else model
                # Pick emoji for model tier
                if "opus" in model.lower():
                    icon = "💎"
                elif "haiku" in model.lower():
                    icon = "⚡"
                else:
                    icon = "🔷"
                cost_parts.append(f"{icon} {short_name} {_fmt_cost(cost)}")

            # Token breakdown (input + output only, exclude cache)
            display_total = total_input + total_output
            self.menu["📈 Today: Loading..."].title = f"📈 Today: {_fmt_tokens(display_total)} tokens"
            self.menu["    ⬇️  Input: ..."].title = f"    ⬇️  Input: {_fmt_tokens(total_input)}"
            self.menu["    ⬆️  Output: ..."].title = f"    ⬆️  Output: {_fmt_tokens(total_output)}"

            # Cost with model breakdown
            cost_detail = "  ".join(cost_parts[:3])
            self.menu["💰 Cost: Loading..."].title = f"💰 Cost: {_fmt_cost(total_cost)}  ({cost_detail})"

        except Exception as e:
            print(f"Token stats update failed: {e}")
            import traceback
            traceback.print_exc()

    def update_ui(self, data):
        """Update UI display"""
        try:
            print(f"API Response: {json.dumps(data, indent=2, ensure_ascii=False)}")

            # 5-hour limit (current session)
            if 'five_hour' in data and data['five_hour']:
                five_hour = data['five_hour']
                utilization = five_hour.get('utilization', 0)
                reset_time = five_hour.get('resets_at')
                time_remaining = self.format_time_remaining(reset_time)
                time_short = self.format_time_short(reset_time)

                # Status bar shows 5-hour usage and countdown
                self.title = f"{int(utilization)}% {time_short}"

                # Show different colored emoji based on usage
                if utilization >= 90:
                    emoji = "🔴"
                elif utilization >= 70:
                    emoji = "🟡"
                else:
                    emoji = "🟢"

                self.menu["⏱️  5-Hour Limit: Loading..."].title = (
                    f"⏱️  5-Hour: {emoji} {utilization}% (Resets: {time_remaining})"
                )
            else:
                self.menu["⏱️  5-Hour Limit: Loading..."].title = "⏱️  5-Hour: No data"

            # All models (7-day limit)
            if 'seven_day' in data and data['seven_day']:
                seven_day = data['seven_day']
                utilization = seven_day.get('utilization', 0)
                reset_time = seven_day.get('resets_at')
                time_remaining = self.format_time_remaining(reset_time)

                if utilization >= 90:
                    emoji = "🔴"
                elif utilization >= 70:
                    emoji = "🟡"
                else:
                    emoji = "🟢"

                self.menu["🛠️  All Models: Loading..."].title = (
                    f"🛠️  All Models: {emoji} {utilization}% (Resets: {time_remaining})"
                )
            else:
                self.menu["🛠️  All Models: Loading..."].title = "🛠️  All Models: No data"

            # Sonnet limit
            if 'seven_day_sonnet' in data and data['seven_day_sonnet']:
                sonnet = data['seven_day_sonnet']
                utilization = sonnet.get('utilization', 0)
                reset_time = sonnet.get('resets_at')

                if utilization == 0:
                    self.menu["🔷 Sonnet Limit: Loading..."].title = "🔷 Sonnet only: 🟢 0% (Unused)"
                else:
                    time_remaining = self.format_time_remaining(reset_time)
                    if utilization >= 90:
                        emoji = "🔴"
                    elif utilization >= 70:
                        emoji = "🟡"
                    else:
                        emoji = "🟢"
                    self.menu["🔷 Sonnet Limit: Loading..."].title = (
                        f"🔷 Sonnet only: {emoji} {utilization}% (Resets: {time_remaining})"
                    )
            else:
                self.menu["🔷 Sonnet Limit: Loading..."].title = "🔷 Sonnet only: No data"

            # Send notifications (if usage is high and hasn't been notified in 15 minutes)
            if 'five_hour' in data and data['five_hour']:
                utilization = data['five_hour'].get('utilization', 0)

                # Send different level notifications based on thresholds
                if utilization >= 95 and self.should_notify('usage_critical'):
                    rumps.notification(
                        title="⚠️ Claude Usage Critical Warning",
                        subtitle="5-hour limit nearly exhausted",
                        message=f"Current usage: {utilization}%, please reduce usage immediately!"
                    )
                elif utilization >= 90 and self.should_notify('usage_high'):
                    rumps.notification(
                        title="Claude Usage Warning",
                        subtitle="5-hour limit approaching",
                        message=f"Current usage: {utilization}%, please monitor your usage"
                    )

        except Exception as e:
            print(f"UI update failed: {e}")
            import traceback
            traceback.print_exc()
            self.title = "❌"
            self.menu["⏱️  5-Hour Limit: Loading..."].title = f"Parse error: {str(e)}"


if __name__ == "__main__":
    app = ClaudeUsageApp()
    app.run()
