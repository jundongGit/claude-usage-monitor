# Changelog

All notable changes to Claude Usage Monitor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
