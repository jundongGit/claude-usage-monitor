# Claude Usage Monitor

<div align="center">

A sleek macOS status bar app for real-time monitoring of your Claude.ai usage

![Version](https://img.shields.io/badge/version-1.7.1-blue)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

</div>

## ✨ Features

- 🎯 **Real-time Monitoring** - Auto-refresh every 1 minute
- 📊 **Three Metrics** - 5-hour limit, All models, per-model weekly limit (Fable)
- 📈 **Today's Token Usage** - Daily input/output token tracking per model
- 💰 **Cost Estimation** - Real-time cost calculation based on model pricing
- ⏱️ **Countdown Display** - Shows usage and reset countdown in status bar
- 🗓️ **Live usage dashboard** - History by day, hour or quota week, broken down by model and project, served locally and updating while open
- 🚀 **Auto-start** - Optional login item (toggle in menu)
- ⬆️ **In-app updates** - Checks GitHub Releases daily; one click downloads, verifies and installs the new version, then restarts
- 🔔 **Smart Notifications** - Alerts at 90%/95% (15-min dedup)
- 🔒 **Secure** - Cookie stored with 600 permissions
- 🎨 **Visual Indicators** - Color-coded progress (🟢 🟡 🔴)

## 📸 Preview

**Status Bar:** `14% 2h33m`

**Menu:**
```
📊 Claude Usage Monitor v1.7.1
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️  5-Hour: 🟢 14% (Resets in 2hr 33min)
🛠️  All Models: 🟢 4% (Resets Sun 10:00 PM)
🔷 Fable: 🟢 3% (Resets Sun 10:00 PM)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Today: 228.5K tokens
    ⬇️  Input: 532
    ⬆️  Output: 228.0K
💰 Cost: $85.00 (💎 claude-opus-5 $80.95  ✨ claude-fable-5-1 $4.06)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗓️  Usage History
🔄 Refresh
⚙️  Settings
🚀 Auto-start on Login ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Quit
```

## 🚀 Quick Start

### 📥 Download & Install (Recommended)

**No Python installation required!** Download the pre-built app:

1. **Download** [`ClaudeUsageMonitor-1.7.1.dmg`](../../releases/download/v1.7.1/ClaudeUsageMonitor-1.7.1.dmg) (20 MB)
   — or the [`.app.zip`](../../releases/download/v1.7.1/ClaudeUsageMonitor-1.7.1.app.zip)
2. **Open** the DMG and drag `Claude Usage Monitor.app` to `Applications`
3. **Launch** from Applications

The app appears in your menu bar, not in the Dock.

The build is signed with a Developer ID (FREEAI LIMITED) and notarized by Apple, so it opens
with a normal double-click. It is **Apple Silicon only** (arm64); Intel Macs need to run from source.

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

- **📊 Claude Usage Monitor v1.7.1** - Title (non-clickable)
- **⏱️  5-Hour Limit** - Shows 5-hour rolling window usage
- **🛠️  All Models** - Shows 7-day all models usage
- **🔷 <Model>** - Shows the 7-day per-model limit reported by the API (currently Fable); up to three such rows
- **📈 Today** - Today's total token count
- **⬇️ Input / ⬆️ Output** - Input and output token breakdown
- **💰 Cost** - Estimated cost breakdown by model
- **🗓️  Usage History** - Opens the live usage dashboard in the default browser
- **🔄 Refresh** - Manually refresh usage data
- **⚙️  Settings** - Configure via cURL clipboard import
- **🚀 Auto-start on Login** - Toggle auto-start (✓ when enabled)
- **⬇️  Check for Updates…** - Checks for a newer release; reads **⬆️  Update to vX.Y.Z** once one is found
- **❌ Quit** - Exit application

### Usage History dashboard

**🗓️ Usage History** opens a dashboard served from loopback — `http://127.0.0.1:<random port>/?k=<token>`.
The page polls every 15 seconds, so it keeps updating while it stays open.

- **Where the numbers come from**: token counts are read from the Claude Code transcripts in
  `~/.claude/projects` and priced from the published per-model rates, so they are an estimate of
  consumption, not a bill. The All Models percentage comes from the snapshots the app records in
  `~/.claude_usage_history.jsonl`, because the API only ever reports the current value.
- **Range control** (Today / 7 / 30 / 90 days / By week / All time) scopes the tiles, the trend chart, the
  model and project breakdowns and the detail table. **By week** steps through quota weeks with the
  ‹ › arrows. Quota-week panels always show the full history.
- **Access**: the listener is bound to 127.0.0.1, every request must carry the token minted at
  startup, and the Host header must be loopback. The server only reads local files.
- **Offline snapshot**: `python3 usage_report.py` writes a self-contained
  `~/.claude_usage_report.html` with the data inlined — no server, no network. The app falls back to
  it automatically if the server cannot start.

### Updates

The app checks `api.github.com/repos/jundongGit/claude-usage-monitor/releases/latest` about 20 seconds
after launch and then once a day. When a newer version exists, the menu row changes to
**⬆️ Update to vX.Y.Z** and one notification is shown. Choosing it downloads the release's
`.app.zip`, and installs it only if all of these hold:

- the code signature is valid (`codesign --verify --deep --strict`)
- it is signed by the FREEAI Developer ID team (`XF9W8A344D`)
- Gatekeeper accepts it (notarized)
- its bundle id and version match the app and the release tag

The bundle is swapped in place and the app restarts. If any check fails the installed version is left
untouched. When the app's folder is not writable, the update opens the release page instead.

**Publishing a release** (so installed copies pick it up): bump `__version__` in `main.py`, run
`./build.sh` then `./sign_notarize.sh`, and attach `dist/ClaudeUsageMonitor-<version>.app.zip` (and
the `.dmg`) to a GitHub release tagged `v<version>`. The updater needs the `.app.zip` asset.

For testing against a local feed: `defaults write com.freeai.claudeusagemonitor UpdateFeedURL <url>`
(remove with `defaults delete com.freeai.claudeusagemonitor UpdateFeedURL`).

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

## 🔐 What it reads, and what leaves your machine

Worth reading before you install it, and worth passing on if you share it with someone.

### Where the numbers come from

| Figure | Source | Needs a claude.ai session? |
|---|---|---|
| Tokens, cost, messages, per-project and per-model breakdowns, all history | The Claude Code transcripts in `~/.claude/projects` | **No** |
| 5-hour / All Models / per-model limit percentages | The `/api/organizations/.../usage` endpoint on claude.ai | Yes |
| The All Models line chart and per-week peak | Snapshots this app writes to `~/.claude_usage_history.jsonl` as it runs | Yes |

So the dashboard is useful from the first launch with no configuration at all — everything except the
quota percentages is computed locally. Two things to expect in that state: the quota tiles and the
limit chart show their empty state, and **quota weeks are aligned to an assumed Sunday 22:00 reset**
until the API reports your real reset time. Your reset instant is account-specific, so until then the
weekly columns may be split at the wrong boundary. Configuring the session fixes the alignment on the
first refresh.

### What is read out of the transcripts

Only the usage accounting: each assistant message's token counts, its model, its timestamp, and the
working directory (`cwd`) the session ran in, which is what the project breakdown is keyed on. The
message content — your prompts, the model's replies, tool output, file contents — is never extracted,
stored or displayed anywhere; each record is decoded, those few fields are taken, and the rest is
dropped. Directory names do appear in the project chart, so they are as revealing as your folder
names are.

### What leaves the machine

Nothing that this app generates. The dashboard is served from `127.0.0.1` on a random port, every
request must carry a token minted at startup, the Host header must be loopback, and the page fetches
from that server only — no CDN, no web fonts, no analytics. The app makes exactly one kind of network
request of its own: the usage API call to claude.ai, and only when you have configured a session —
plus the daily update check against the GitHub releases API, which sends nothing beyond a plain GET. (It
also opens two URLs in your browser when you click a menu row — the local dashboard, and
claude.ai/settings/usage from the settings help.)

Your session cookie and organisation id live in `~/.claude_usage_config.json` with `600` permissions.

### Costs are an estimate, not a bill

Token counts are real (they come from the transcripts), but the money figure is those counts
multiplied by a **price table hardcoded in `usage_report.py`**. It follows published per-model rates
and is updated by hand, so it drifts when prices change, and a model whose name does not match
`opus` / `sonnet` / `haiku` / `fable` falls back to Sonnet rates. Read it as a measure of consumption
and a way to compare periods and projects — not as what you were charged, and not as a prediction of
what a usage-based plan would bill.

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
  "org_id": "12345678-90ab-cdef-1234-567890abcdef",
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
  "limits": [
    {
      "kind": "session",
      "percent": 12,
      "resets_at": "2026-09-07T02:00:00+00:00",
      "scope": null
    },
    {
      "kind": "weekly_all",
      "percent": 4,
      "resets_at": "2026-09-13T10:00:00+00:00",
      "scope": null
    },
    {
      "kind": "weekly_scoped",
      "percent": 3,
      "resets_at": "2026-09-13T10:00:00+00:00",
      "scope": { "model": { "id": null, "display_name": "Fable" } }
    }
  ]
}
```

**Field Descriptions:**
- `limits[]`: current source of truth. `kind` is `session` (5-hour), `weekly_all`, or `weekly_scoped`; for `weekly_scoped` the model name is at `scope.model.display_name`.
- `utilization` / `percent`: Usage percentage (0-100)
- `resets_at`: Reset time (ISO 8601 format, UTC timezone)
- `five_hour` / `seven_day` / `seven_day_sonnet`: legacy top-level fields, still read as a fallback. `seven_day_sonnet` now returns `null`.

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
