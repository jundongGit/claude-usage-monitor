# Claude Usage Monitor

<div align="center">

A sleek macOS status bar app for real-time monitoring of your Claude.ai usage

![Version](https://img.shields.io/badge/version-1.4.0-blue)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

</div>

## ✨ Features

- 🎯 **Real-time Monitoring** - Auto-refresh every 1 minute
- 📊 **Three Metrics** - 5-hour limit, All models, Sonnet only limit
- 📈 **Today's Token Usage** - Daily input/output token tracking per model
- 💰 **Cost Estimation** - Real-time cost calculation based on model pricing
- ⏱️ **Countdown Display** - Shows usage and reset countdown in status bar
- 🚀 **Auto-start** - Optional login item (toggle in menu)
- 🔔 **Smart Notifications** - Alerts at 90%/95% (15-min dedup)
- 🔒 **Secure** - Cookie stored with 600 permissions
- 🎨 **Visual Indicators** - Color-coded progress (🟢 🟡 🔴)

## 📸 Preview

**Status Bar:** `12% 4h38m`

**Menu:**
```
📊 Claude Usage Monitor v1.4.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️  5-Hour: 🟢 11% (Resets: 1h11m)
🛠️  All Models: 🟢 43% (Resets: 2d17h)
🔷 Sonnet only: 🟢 3% (Resets: 1d2h)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Today: 354.5K tokens
    ⬇️  Input: 3.3K
    ⬆️  Output: 351.2K
💰 Cost: $234 (💎 claude-opus-4-6 $234  🟢 unknown $0.000)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 Refresh
⚙️  Settings
🚀 Auto-start on Login ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Quit
```

## 🚀 Quick Start

### 📥 Download & Install (Recommended)

**No Python installation required!** Download the pre-built app:

1. **Download** [`ClaudeUsageMonitor-1.4.0.app.zip`](../../releases/download/v1.4.0/ClaudeUsageMonitor-1.4.0.app.zip) (14 MB)
2. **Extract** the ZIP file (double-click)
3. **Drag** `Claude Usage Monitor.app` to `/Applications` folder
4. **Launch** from Applications

The app appears in your menu bar, not in the Dock.

**First-time Setup:**
1. Open [claude.ai/settings/usage](https://claude.ai/settings/usage) in browser
2. Press F12 → Network tab → Refresh page
3. Right-click any request → **Copy as cURL**
4. Click the menu bar icon → **⚙️ Settings** → **Read from Clipboard**

---

### 🛠️ Alternative: Run from Source

**Requirements:**
- macOS 10.14+
- Python 3.8+
- Claude.ai account

#### 1️⃣ Clone Repository

```bash
git clone https://github.com/jundongGit/claude-usage-monitor.git
cd claude-usage-monitor
```

#### 2️⃣ Install Dependencies

```bash
pip3 install -r requirements.txt
```

**Dependencies:**
- `rumps==0.4.0` - macOS status bar app framework
- `requests>=2.31.0` - HTTP library

#### 3️⃣ Launch the App

```bash
python3 main.py
```

#### 4️⃣ First-time Setup

1. Open [claude.ai/settings/usage](https://claude.ai/settings/usage) in browser
2. Press F12 (or Cmd+Option+I) → **Network** tab → Refresh page
3. Right-click any request → **Copy as cURL**
4. Click the ⚠️ icon in the status bar → **⚙️ Settings** → **Read from Clipboard**

Cookie and Organization ID are extracted automatically from the cURL command.

🎉 **Done!** The app will now display your Claude usage

## 🔧 Usage

### Status Bar Display

The status bar shows current usage and reset countdown:
- **12% 4h38m** - 5-hour limit at 12%, resets in 4h 38m
- **⚠️** - Not configured
- **🔒** - Cookie expired, needs reset
- **❌** - Network error or API failure

### Menu Items

- **📊 Claude Usage Monitor v1.4.0** - Title (non-clickable)
- **⏱️  5-Hour Limit** - Shows 5-hour rolling window usage
- **🛠️  All Models** - Shows 7-day all models usage
- **🔷 Sonnet only** - Shows 7-day Sonnet model usage
- **📈 Today** - Today's total token count
- **⬇️ Input / ⬆️ Output** - Input and output token breakdown
- **💰 Cost** - Estimated cost breakdown by model
- **🔄 Refresh** - Manually refresh usage data
- **⚙️  Settings** - Configure via cURL clipboard import
- **🚀 Auto-start on Login** - Toggle auto-start (✓ when enabled)
- **❌ Quit** - Exit application

### Auto-start on Login

Click **🚀 Auto-start on Login** in the menu to toggle:

- **Disabled**: Shows `🚀 Auto-start on Login`
- **Enabled**: Shows `🚀 Auto-start on Login ✓`

Auto-start uses macOS LaunchAgent, config file at:
```
~/Library/LaunchAgents/com.claude.usage.monitor.plist
```

### Smart Notifications

The app sends notifications when usage is high:

- **95%+ usage**: 🔴 Critical warning ("⚠️ Claude Usage Critical Warning")
- **90%+ usage**: 🟡 High usage warning ("Claude Usage Warning")

Smart deduplication: same-level notifications only sent once per 15 minutes.

### Color Indicators

Usage is color-coded in the menu:
- 🟢 **0-69%**: Normal
- 🟡 **70-89%**: High
- 🔴 **90-100%**: Critical

## 🐛 Troubleshooting

### Cookie Expired

If you see 🔒 icon and "Authentication Failed" notification:
1. Open [claude.ai/settings/usage](https://claude.ai/settings/usage) in browser
2. F12 → Network → Refresh → Right-click any request → **Copy as cURL**
3. Click **⚙️ Settings** → **Read from Clipboard**
4. Click **🔄 Refresh** to manually refresh data

### App Not Responding or Crashed

Check the log file for issues:
```bash
tail -f /tmp/claude-usage-monitor.log
```

### Corrupted Config File

The app automatically handles corrupted config files:
- Auto-backup to `~/.claude_usage_config.json.backup`
- Reset to default configuration
- Requires re-setting Cookie

### Network Errors

- Check network connection
- Confirm access to https://claude.ai
- Check log file for detailed error info
- Try clicking **🔄 Refresh** to manually retry

### Auto-start Not Working

If the app doesn't auto-start after reboot:

1. Check if plist file exists:
```bash
ls -la ~/Library/LaunchAgents/com.claude.usage.monitor.plist
```

2. Manually load service:
```bash
launchctl load ~/Library/LaunchAgents/com.claude.usage.monitor.plist
```

3. Check service status:
```bash
launchctl list | grep claude
```

## 🔐 Security

This app prioritizes your privacy and security:

- ✅ **Local Storage**: Cookie stored locally only, never uploaded
- ✅ **Permission Protection**: Config file set to `600` (owner read/write only)
- ✅ **HTTPS Encryption**: All API requests use HTTPS
- ✅ **Error Handling**: Complete error handling and data validation
- ✅ **Auto Backup**: Config file auto-backed up when corrupted

⚠️ **Security Note**: Cookie contains your login credentials. Never share or upload to public locations.

## 📂 Files

### Configuration File

Location: `~/.claude_usage_config.json`

```json
{
  "cookie": "sessionKey=sk-ant-sid02-...; lastActiveOrg=...; cf_clearance=...",
  "org_id": "314822f8-5b98-410e-a092-1ef999fe98a8",
  "account_name": ""
}
```

Permissions: `-rw------- (600)` - Owner read/write only

### Auto-start Configuration

Location: `~/Library/LaunchAgents/com.claude.usage.monitor.plist`

Auto-created and managed via **🚀 Auto-start on Login** menu item.

### Log File

Location: `/tmp/claude-usage-monitor.log`

Contains app logs and error info for debugging.

## 🛠️ Uninstall

### 1. Stop the App

Click **❌ Quit** in the menu, or use command:

```bash
# Find process
ps aux | grep "python.*main.py" | grep -v grep

# Kill process
kill <PID>
```

### 2. Disable Auto-start

Click **🚀 Auto-start on Login** in menu to uncheck, or manually:

```bash
launchctl unload ~/Library/LaunchAgents/com.claude.usage.monitor.plist
rm ~/Library/LaunchAgents/com.claude.usage.monitor.plist
```

### 3. Remove Config and Logs

```bash
# Remove config file
rm ~/.claude_usage_config.json
rm ~/.claude_usage_config.json.backup  # if exists

# Remove log file
rm /tmp/claude-usage-monitor.log

# Remove app directory (optional)
rm -rf "/path/to/claude-usage-monitor"
```

## 📝 API Documentation

The app uses Claude.ai's official API to fetch usage data:

**Endpoint:**
```
GET https://claude.ai/api/organizations/{org_id}/usage
```

**Response Example:**
```json
{
  "five_hour": {
    "utilization": 12,
    "resets_at": "2025-10-28T00:59:59.601930+00:00"
  },
  "seven_day": {
    "utilization": 51,
    "resets_at": "2025-10-29T21:59:59.601949+00:00"
  },
  "seven_day_sonnet": {
    "utilization": 3,
    "resets_at": "2026-04-17T10:00:00+00:00"
  }
}
```

**Field Descriptions:**
- `utilization`: Usage percentage (0-100)
- `resets_at`: Reset time (ISO 8601 format, UTC timezone)

## 🤝 Contributing

Issues and Pull Requests are welcome!

### Development

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Roadmap

- [ ] Multi-account support
- [ ] Usage trend charts
- [ ] Custom notification thresholds
- [ ] Export usage data
- [ ] Dark mode theme

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## ⭐ Acknowledgments

- [rumps](https://github.com/jaredks/rumps) - macOS status bar app framework
- [requests](https://requests.readthedocs.io/) - HTTP library
- Claude.ai - Powerful AI service

---

<div align="center">

Made with ❤️ for Claude users

If this project helps you, please give it a ⭐️

</div>
