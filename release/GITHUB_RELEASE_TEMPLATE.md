# GitHub Release Template

Use this template when creating the GitHub release.

---

## Tag Version

```
v1.0.0
```

## Release Title

```
Claude Usage Monitor v1.0.0 - Initial Release
```

## Release Description

Copy the content below into the release description:

---

# 🎉 Claude Usage Monitor v1.0.0 - Initial Release

A free, open-source macOS status bar app for real-time monitoring of your Claude.ai usage.

## 📥 Download

**Pre-built App** (Recommended - No Python required):
- Download: `ClaudeUsageMonitor-1.0.0.app.zip` (19 MB)
- SHA256: `237ef1d987cf88805f2ea54ccc172e0f0a861325fa7bcf5da1ce6c1f8a9a2232`
- Requirements: macOS 10.14 or later

## 🚀 Quick Install

1. Download `ClaudeUsageMonitor-1.0.0.app.zip`
2. Extract and drag to `/Applications`
3. Launch and configure with your Claude Cookie
4. Enjoy real-time usage monitoring!

📖 See [INSTALL.md](INSTALL.md) for detailed installation instructions.

## ✨ Features

### Core Functionality
- ⏱️ **5-hour rolling window** - Monitor short-term usage limit
- 🛠️ **7-day all models** - Track weekly usage across all models
- 💎 **7-day Opus** - Premium model usage monitoring
- 🔄 **Auto-refresh** - Updates every 1 minute automatically

### User Experience
- 📊 **Status bar display** - Shows usage % and reset countdown (e.g., `65% 3hr 24min`)
- 🎨 **Color-coded indicators** - 🟢 Green (safe), 🟡 Yellow (caution), 🔴 Red (critical)
- 🔔 **Smart notifications** - Alerts at 90% and 95% with 15-min deduplication
- 🚀 **Auto-start on login** - Optional, one-click toggle

### Security & Privacy
- 🔒 **Secure local storage** - Cookie stored with 600 permissions
- 🔐 **No data collection** - Everything stays on your Mac
- 🌐 **HTTPS only** - Encrypted communication with Claude API

## 📸 Screenshot

**Menu Interface:**
```
📊 Claude Usage Monitor v1.0.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️  5-Hour Limit: 🟢 12% (Resets: 4hr 38min)
🛠️  All Models: 🟢 51% (Resets: 1d 22hr)
💎 Opus Limit: 🟢 0% (Unused)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 Refresh
⚙️  Set Cookie
🚀 Auto-start on Login ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Quit
```

## 🛠️ Built With

- [rumps](https://github.com/jaredks/rumps) - macOS status bar framework
- [requests](https://requests.readthedocs.io/) - HTTP library
- [py2app](https://py2app.readthedocs.io/) - macOS app packaging

## 📝 Documentation

- [INSTALL.md](INSTALL.md) - Installation guide
- [README.md](README.md) - Full documentation
- [CHANGELOG.md](CHANGELOG.md) - Version history

## 🐛 Known Limitations

- Single account support (one Claude.ai account at a time)
- macOS only (Windows/Linux not supported)
- Manual Cookie entry required (no OAuth yet)

## 🔮 Planned Features

- 📊 Usage trend charts
- 👥 Multi-account support
- 🎨 Dark mode theme
- 🔔 Custom notification thresholds
- 📤 Export usage data (CSV/JSON)

## 🤝 Contributing

Contributions welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation

## 📄 License

MIT License - Free to use, modify, and distribute.

---

**Enjoy monitoring your Claude usage!** 🎉

If you encounter any issues, please check the [documentation](README.md) or [open an issue](../../issues).

---

## Checksums

**ClaudeUsageMonitor-1.0.0.app.zip**
```
SHA256: 237ef1d987cf88805f2ea54ccc172e0f0a861325fa7bcf5da1ce6c1f8a9a2232
```

Verify:
```bash
shasum -a 256 -c ClaudeUsageMonitor-1.0.0.app.zip.sha256
```

---

## Assets

Upload these files when creating the release:
- [ ] ClaudeUsageMonitor-1.0.0.app.zip
- [ ] ClaudeUsageMonitor-1.0.0.app.zip.sha256

---

**Release Date**: October 29, 2025
**Build**: Production-ready
**Status**: Stable
