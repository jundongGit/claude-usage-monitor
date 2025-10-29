#!/usr/bin/env python3
"""
Claude Usage Monitor - macOS Status Bar App
Monitor Claude.ai usage and display in the status bar
"""

__version__ = "1.0.0"
__author__ = "Claude Usage Monitor Contributors"

import rumps
import requests
import json
from datetime import datetime, timezone
import os
import sys
import time


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
            rumps.MenuItem("💎 Opus Limit: Loading...", callback=None),
            rumps.separator,
            rumps.MenuItem("🔄 Refresh", callback=self.refresh_usage),
            rumps.MenuItem("⚙️  Set Cookie", callback=self.set_cookie),
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

        # Set timer to refresh every 1 minute
        self.timer = rumps.Timer(self.refresh_usage, 60)
        self.timer.start()

    def load_config(self):
        """Load configuration file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.cookie = config.get('cookie', '')
                    self.org_id = config.get('org_id', '')
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
            except Exception as e:
                print(f"Error loading config file: {e}")
                self.cookie = ''
                self.org_id = ''
        else:
            self.cookie = ''
            self.org_id = ''

    def save_config(self):
        """Save configuration file"""
        config = {
            'cookie': self.cookie,
            'org_id': self.org_id
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
                return f"{days}d {hours}hr"
            elif hours > 0:
                return f"{hours}hr {minutes}min"
            else:
                return f"{minutes}min"
        except Exception as e:
            return ""

    def show_welcome_guide(self):
        """Show welcome guide for first run"""
        response = rumps.alert(
            title="Welcome to Claude Usage Monitor 👋",
            message=(
                "Thank you for using Claude Usage Monitor!\n\n"
                "First-time setup requires your Claude Cookie and Organization ID.\n\n"
                "📌 How to get configuration:\n"
                "1. Visit claude.ai and login\n"
                "2. Open browser DevTools (F12)\n"
                "3. Go to Network tab\n"
                "4. Visit claude.ai/settings/usage\n"
                "5. Find 'usage' request, get Cookie & org_id\n\n"
                "See README.md for detailed steps.\n\n"
                "Configure now?"
            ),
            ok="Configure Now",
            cancel="Later"
        )

        if response == 1:  # Clicked "Configure Now"
            self.set_cookie(None)

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

    @rumps.clicked("⚙️  Set Cookie")
    def set_cookie(self, _):
        """Set Cookie and Organization ID"""
        window = rumps.Window(
            message="Enter Cookie from browser (full Cookie string)",
            title="Set Cookie",
            default_text=self.cookie,
            dimensions=(400, 100)
        )
        response = window.run()

        if response.clicked:
            self.cookie = response.text

            # Ask for Organization ID
            window2 = rumps.Window(
                message="Enter Organization ID (from API request)",
                title="Set Organization ID",
                default_text=self.org_id,
                dimensions=(400, 24)
            )
            response2 = window2.run()

            if response2.clicked:
                self.org_id = response2.text
                self.save_config()
                self.refresh_usage(None)
                rumps.notification(
                    title="Configuration Saved",
                    subtitle="",
                    message="Cookie saved, refreshing data..."
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

    @rumps.clicked("🔄 Refresh")
    def refresh_usage(self, _):
        """Refresh usage data"""
        if not self.cookie or not self.org_id:
            self.title = "⚠️"
            self.menu["⏱️  5-Hour Limit: Loading..."].title = "⏱️  5-Hour: Not configured"
            self.menu["🛠️  All Models: Loading..."].title = "🛠️  All Models: Not configured"
            self.menu["💎 Opus Limit: Loading..."].title = "💎 Opus: Not configured"
            return

        try:
            # Call API
            url = f"https://claude.ai/api/organizations/{self.org_id}/usage"
            headers = {
                'Cookie': self.cookie,
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

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
                self.title = f"{utilization}% {time_short}"

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

            # Opus limit
            if 'seven_day_opus' in data and data['seven_day_opus']:
                opus = data['seven_day_opus']
                utilization = opus.get('utilization', 0)
                reset_time = opus.get('resets_at')

                if utilization == 0:
                    self.menu["💎 Opus Limit: Loading..."].title = "💎 Opus: 🟢 0% (Unused)"
                else:
                    time_remaining = self.format_time_remaining(reset_time)
                    if utilization >= 90:
                        emoji = "🔴"
                    elif utilization >= 70:
                        emoji = "🟡"
                    else:
                        emoji = "🟢"
                    self.menu["💎 Opus Limit: Loading..."].title = (
                        f"💎 Opus: {emoji} {utilization}% (Resets: {time_remaining})"
                    )
            else:
                self.menu["💎 Opus Limit: Loading..."].title = "💎 Opus: No data"

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
