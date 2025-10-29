# Installation Guide - Claude Usage Monitor v1.0.0

## 📥 Quick Install (5 minutes)

### Step 1: Download

Download the latest release:
- **File**: [`ClaudeUsageMonitor-1.0.0.app.zip`](ClaudeUsageMonitor-1.0.0.app.zip) (19 MB)
- **SHA256**: `237ef1d987cf88805f2ea54ccc172e0f0a861325fa7bcf5da1ce6c1f8a9a2232`

### Step 2: Install

1. **Extract** the ZIP file (double-click)
2. You'll see `Claude Usage Monitor.app`
3. **Drag** it to your `/Applications` folder
4. **Done!**

### Step 3: Launch

1. Open `Claude Usage Monitor.app` from Applications
2. The app will appear in your **menu bar** (top right, near the clock)
3. It will NOT appear in the Dock

### Step 4: Configure (First-time only)

1. Click the menu bar icon (shows ⚠️ initially)
2. Click **"⚙️ Set Cookie"**
3. Follow the welcome guide to get your:
   - Cookie from claude.ai
   - Organization ID

## 🔧 Getting Cookie & Org ID

### Method: Browser DevTools

1. Visit [claude.ai](https://claude.ai) and login
2. Press **F12** (or Cmd+Option+I on Mac) to open DevTools
3. Go to **Network** tab
4. Visit [claude.ai/settings/usage](https://claude.ai/settings/usage)
5. In Network tab, find the `usage` request
6. Click it to view details:

**Cookie:**
- In **Request Headers** section
- Find the `Cookie:` line
- Copy the entire Cookie value (starts with `sessionKey=...`)

**Organization ID:**
- In the request **URL**: `https://api.claude.ai/api/organizations/{ORG_ID}/usage`
- Copy the `{ORG_ID}` part (UUID format like `314822f8-...`)

### Example

```
Cookie: sessionKey=sk-ant-sid01-ABC123...; intercom-id-ixnq...
Org ID: 314822f8-5b98-410e-a092-1ef999fe98a8
```

## ✅ Verification

After configuration:
- Menu bar should show usage (e.g., `65% 3hr 24min`)
- Click icon to see detailed menu with three metrics
- Data refreshes automatically every 1 minute

## 🐛 Troubleshooting

### "App is damaged" Error

This happens due to macOS Gatekeeper. Fix:

```bash
xattr -cr "/Applications/Claude Usage Monitor.app"
```

Then try launching again.

### App Doesn't Show in Menu Bar

1. Check if app is running: Open **Activity Monitor**, search "Claude Usage"
2. If running but no icon: Try restarting the app
3. Check **System Preferences** → **Users & Groups** → **Login Items**

### No Data / Shows "Not configured"

1. Verify Cookie is correct (copy the entire Cookie header)
2. Verify Org ID is correct (UUID format)
3. Cookie may expire - get a fresh one from claude.ai
4. Check internet connection

### Cookie Expired

If you see 🔒 icon:
1. Click icon → **"⚙️ Set Cookie"**
2. Get a fresh Cookie from claude.ai
3. Re-enter Cookie and Org ID

## 🚀 Optional: Auto-start

To launch automatically on login:
1. Click menu bar icon
2. Click **"🚀 Auto-start on Login"**
3. Check mark (✓) appears when enabled

## 📚 More Help

- See [README.md](README.md) for full documentation
- See [CHANGELOG.md](CHANGELOG.md) for version history
- Check [RELEASE_NOTES.md](RELEASE_NOTES.md) for latest updates

## 🔒 Security & Privacy

- All data stored **locally** on your Mac
- Config file: `~/.claude_usage_config.json` (600 permissions)
- Cookie **never uploaded** to any server
- Only communicates with official Claude API

---

**Version**: 1.0.0
**Requirements**: macOS 10.14 or later
**No Python installation required**
