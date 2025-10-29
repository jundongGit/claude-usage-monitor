# Release Notes - Claude Usage Monitor v1.0.0

**Release Date**: October 28, 2025

## 🎉 Initial Public Release

Claude Usage Monitor is a free, open-source macOS status bar app for real-time monitoring of your Claude.ai usage.

## 📥 Download

**Pre-built App** (Recommended):
- **File**: `ClaudeUsageMonitor-1.0.0.app.zip`
- **Size**: 19 MB
- **SHA256**: `237ef1d987cf88805f2ea54ccc172e0f0a861325fa7bcf5da1ce6c1f8a9a2232`
- **Requirements**: macOS 10.14 or later
- **No Python installation required!**

**Installation**: See [INSTALL.md](INSTALL.md) for step-by-step instructions.

## ✨ Key Features

### 📊 Real-time Monitoring
- Auto-refresh every 1 minute
- Three usage metrics displayed:
  - ⏱️ **5-hour rolling window** - Short-term usage limit
  - 🛠️ **7-day all models** - Weekly usage across all models
  - 💎 **7-day Opus** - Premium model usage tracking

### 🎨 User Interface
- **Status bar display**: Shows current usage % and reset countdown (e.g., `65% 3hr 24min`)
- **Color-coded indicators**:
  - 🟢 Green (0-69%) - Safe zone
  - 🟡 Yellow (70-89%) - Caution
  - 🔴 Red (90-100%) - Critical
- **Clean menu interface** with all details

### 🔔 Smart Notifications
- Alert at **90%** usage (high warning)
- Alert at **95%** usage (critical warning)
- 15-minute deduplication to prevent spam
- macOS native notifications

### 🚀 Convenience Features
- **Auto-start on login** (optional, one-click toggle)
- **Secure local storage** (Cookie with 600 file permissions)
- **Menu-based configuration** (no command line needed)
- **First-run welcome guide** with setup instructions

### 🔒 Security & Privacy
- All data stored **locally** on your Mac
- Cookie stored in `~/.claude_usage_config.json` (encrypted file permissions)
- **No data collection** - App never uploads your data anywhere
- Only communicates with official Claude.ai API via HTTPS

## 🆕 What's New in v1.0.0

### Core Features
- ✅ Real-time Claude.ai usage monitoring
- ✅ Three independent usage metrics
- ✅ Status bar integration (menu bar only, hidden from Dock)
- ✅ Automatic refresh every 60 seconds
- ✅ Color-coded usage indicators

### User Experience
- ✅ First-run welcome wizard
- ✅ Menu-based Cookie configuration
- ✅ Smart notification system with deduplication
- ✅ Auto-start on login option
- ✅ Countdown timer showing time until reset

### Technical
- ✅ Standalone macOS .app bundle (no Python needed)
- ✅ Custom app icon
- ✅ Graceful error handling
- ✅ HTTPS encrypted API requests
- ✅ Secure credential storage

### Interface
- ✅ Clean English interface
- ✅ Professional menu design with emojis
- ✅ Visual progress indicators
- ✅ Informative error messages

## 🛠️ Built With

- **[rumps](https://github.com/jaredks/rumps)** - macOS status bar app framework
- **[requests](https://requests.readthedocs.io/)** - HTTP library for Python
- **[py2app](https://py2app.readthedocs.io/)** - macOS app packaging tool

## 📝 Known Limitations

- **Single account**: Currently supports one Claude.ai account at a time
- **macOS only**: Not available for Windows or Linux
- **Manual Cookie entry**: Requires extracting Cookie from browser (no OAuth yet)

## 🔮 Roadmap

Planned for future releases:
- 📊 Usage trend charts and analytics
- 👥 Multi-account support
- 🎨 Dark mode theme
- 🔔 Customizable notification thresholds
- 📤 Export usage data (CSV/JSON)
- 🌍 Localization (multiple languages)
- 🔄 Auto-update checker

## 📚 Documentation

- **[INSTALL.md](INSTALL.md)** - Installation instructions
- **[README.md](README.md)** - Full documentation and usage guide
- **[CHANGELOG.md](CHANGELOG.md)** - Complete version history

## 🐛 Reporting Issues

Found a bug or have a feature request?
- Open an issue on GitHub
- Include your macOS version and app version
- Describe steps to reproduce

## 🤝 Contributing

This is an open-source project! Contributions welcome:
- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation

## 📄 License

MIT License - Free to use, modify, and distribute.

See [LICENSE](../LICENSE) for details.

## 🙏 Acknowledgments

Special thanks to:
- Anthropic for the amazing Claude AI
- The rumps project for the excellent macOS framework
- The open-source community

---

**Enjoy monitoring your Claude usage!** 🎉

For questions and support, please refer to the documentation or open a GitHub issue.
