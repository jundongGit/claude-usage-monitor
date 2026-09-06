# Changelog

All notable changes to Claude Usage Monitor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2026-09-07

### ✨ Added
- **Per-model weekly limits driven by the API**: the third row now reads the `limits` array returned by `/usage` and renders every `kind: "weekly_scoped"` entry with the model name supplied by the API (currently **Fable**, matching claude.ai/settings/usage). Up to three such rows are supported; unused rows stay hidden.
- **Fable pricing** in the cost estimate — `claude-fable-5-1` was previously falling back to Sonnet rates, understating its cost roughly 3x. Now $10 / $50 per million input / output tokens, $0.25 cache read.

### 🔧 Changed
- Limit parsing was rewritten around `_normalize_limits()`, which prefers the `limits` array and falls back to the legacy `five_hour` / `seven_day` / `seven_day_opus` / `seven_day_sonnet` fields.
- Percentages render without a trailing `.0` (`12%`, not `12.0%`) now that the API reports integers.
- Fable rows in the cost breakdown use the ✨ icon.
- **Model pricing refreshed to current rates** ($ per million input / output tokens) — the table still held previous-generation numbers, overstating every estimate:

  | Model | Was | Now |
  |---|---|---|
  | Opus 5 | 15 / 75 | 5 / 25 |
  | Sonnet 5 | 3 / 15 | 2 / 10 |
  | Haiku 4.5 | 0.8 / 4 | 1 / 5 |
  | Fable 5.1 | (fell back to Sonnet) | 10 / 50 |

### 🐛 Fixed
- **Weekly rows showed a multi-day countdown** (`Resets: 6d 10hr`) instead of the weekday claude.ai displays. They now read `Resets Sun 10:00 PM` in local time, rounded to the minute — `resets_at` is computed relative to the request, so it jitters across the minute boundary. The 5-hour row keeps its countdown (`Resets in 2hr 33min`), matching claude.ai.
- **Read-only menu rows were barely legible.** Rows created with `callback=None` are disabled, and macOS draws disabled items in a washed-out gray. They now carry an attributed title with an explicit `labelColor`, so they stay unclickable but render at full contrast in light and dark mode.
- The third row showed "Sonnet only: No data" on every account: Claude.ai now returns `seven_day_sonnet: null` and moved the per-model quota into the `limits` array.

## [1.4.0] - 2026-04-16

### 🔧 Changed

#### Adapt to Claude.ai Usage API Change
- **Third limit row**: Replaced "💎 Opus Limit" with "🔷 Sonnet only" — Claude.ai removed the dedicated `seven_day_opus` quota and added `seven_day_sonnet` (matches the new Usage page on claude.ai/settings/usage)
- Without this update the third row always showed "No data"

### 🛠️ Technical Details
- API field rename: `seven_day_opus` → `seven_day_sonnet`
- Menu item key renamed from `💎 Opus Limit` to `🔷 Sonnet Limit`
- Dropped `install_requires` from `setup.py` — newer setuptools rejects it during py2app builds; dependencies are pinned via `requirements.txt` instead

---

## [1.3.0] - 2026-04-12

### ✨ New Features

#### Today's Token Usage & Cost Tracking
- **📈 Daily Token Stats**: Real-time tracking of today's input/output tokens by model
- **💰 Cost Estimation**: Automatic cost calculation based on official model pricing (Opus/Sonnet/Haiku)
- **Per-model Breakdown**: See token usage and cost for each model separately
- **Smart Deduplication**: Handles streaming records correctly, avoiding double-counting
- **Local Data**: Reads from `~/.claude/projects/` JSONL files — no additional API calls needed

#### Display Improvements
- **Compact Time Format**: Shortened reset time display (e.g., `1h11m` instead of `1hr 11min`, `2d17h` instead of `2d 17hr`)
- **Cleaner Status Bar**: Removed decimal points from percentage display

### 🛠️ Technical Details
- Added model pricing constants matching cc-statistics
- Token formatting helpers for K/M display
- Cost formatting with smart precision ($0.001 / $1.23 / $234)

---

## [1.2.0] - 2025-10-29

### ✨ New Features

#### One-step cURL Clipboard Config
- **⚙️ Settings Revamp**: Replaced manual Cookie/Org ID input with one-click cURL clipboard import
- **Auto-extraction**: Automatically extracts Cookie and Organization ID from copied cURL command
- **Edit Menu Support**: Added standard Edit menu (Cmd+C/V/X/A) for dialog input fields

#### Other Improvements
- Added account name support in configuration
- Improved first-run welcome guide

---

## [1.0.0] - 2025-10-28

### 🎉 Initial Release

The first public release of Claude Usage Monitor - a sleek macOS status bar app for real-time monitoring of your Claude.ai usage.

### ✨ Features

#### Core Functionality
- **Real-time Monitoring**: Auto-refresh usage data every 1 minute
- **Three Usage Metrics**: 
  - 5-hour rolling window limit
  - 7-day all models limit
  - 7-day Opus model limit
- **Status Bar Display**: Shows current usage percentage and reset countdown (e.g., "12% 4hr 38min")
- **Color-coded Indicators**: Visual progress with 🟢 (0-69%), 🟡 (70-89%), 🔴 (90-100%)

#### User Experience
- **Smart Notifications**:
  - Critical warning at 95%+ usage
  - High usage warning at 90%+
  - 15-minute deduplication to avoid notification spam
- **First-run Welcome Guide**: Step-by-step setup instructions
- **Auto-start on Login**: Optional login item with one-click toggle
- **Menu-based Configuration**: Easy Cookie and Organization ID setup

#### Security & Reliability
- **Secure Storage**: Config file with 600 permissions (owner read/write only)
- **HTTPS Encryption**: All API requests encrypted
- **Error Handling**: 
  - Automatic config backup on corruption
  - Graceful recovery from errors
  - Detailed error logging
- **Data Privacy**: All data stored locally, never uploaded

### 🛠️ Technical Details

#### Architecture
- **Language**: Python 3.8+
- **Framework**: rumps (macOS status bar app)
- **HTTP Client**: requests library
- **API**: Claude.ai official usage API

#### Files & Locations
- **Config**: ~/.claude_usage_config.json (600 permissions)
- **Auto-start**: ~/Library/LaunchAgents/com.claude.usage.monitor.plist
- **Logs**: /tmp/claude-usage-monitor.log

### 📦 Installation

#### Prerequisites
- macOS 10.14 or later
- Python 3.8 or later
- Claude.ai account

#### Quick Install
```bash
pip3 install -r requirements.txt
python3 main.py
```

See [README.md](README.md) for detailed installation and setup instructions.

### 🌍 Internationalization
- **Interface Language**: English
- **Time Format**: 12-hour format with hr/min units
- **Date Format**: ISO 8601 (UTC timezone)

### 📝 Known Limitations

- **Single Account**: Currently supports one Claude.ai account at a time
- **macOS Only**: Not compatible with Windows or Linux
- **Cookie-based Auth**: Requires manual Cookie extraction from browser

### 🔮 Future Enhancements

Planned features for upcoming releases:
- Multi-account support
- Usage trend charts and analytics
- Customizable notification thresholds
- Export usage data (CSV/JSON)
- Dark mode theme support
- Localization (multiple languages)

### 🙏 Acknowledgments

Special thanks to:
- [rumps](https://github.com/jaredks/rumps) - Excellent macOS status bar framework
- [requests](https://requests.readthedocs.io/) - Reliable HTTP library
- Claude.ai - Amazing AI platform

### 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Full Changelog**: https://github.com/yourusername/claude-usage-monitor/commits/v1.0.0
