# Build Guide for Claude Usage Monitor

This guide explains how to build macOS .app bundle and DMG installer for distribution.

## Prerequisites

### Required
- macOS 10.14+
- Python 3.8+
- pip3

### Install Build Tools

```bash
# Install py2app (Python to macOS app packager)
pip3 install py2app

# Install create-dmg (for DMG creation, optional)
brew install create-dmg
```

## Quick Build

### One-command Build (Recommended)

```bash
./build.sh
```

This will:
1. ✅ Check dependencies
2. ✅ Clean previous builds
3. ✅ Build .app bundle
4. ✅ Create ZIP archive
5. ✅ Create DMG installer (if create-dmg installed)

**Output:**
```
dist/
├── Claude Usage Monitor.app            # macOS application
├── ClaudeUsageMonitor-1.0.0.app.zip   # ZIP archive for distribution
└── ClaudeUsageMonitor-1.0.0.dmg       # DMG installer for distribution
```

## Manual Build Steps

### Step 1: Clean Previous Builds

```bash
rm -rf build dist
```

### Step 2: Build .app Bundle

```bash
python3 setup.py py2app
```

**What happens:**
- Collects all Python dependencies
- Bundles Python runtime
- Creates standalone .app
- Output: `dist/Claude Usage Monitor.app`

**Options:**
```bash
# Development mode (faster, uses symlinks)
python3 setup.py py2app -A

# Release mode (slower, fully standalone)
python3 setup.py py2app
```

### Step 3: Test the App

```bash
# Open the built app
open "dist/Claude Usage Monitor.app"

# Check if it runs correctly
# Should appear in menu bar, not in Dock
```

### Step 4: Create ZIP Archive

```bash
cd dist
zip -r ClaudeUsageMonitor-1.0.0.app.zip "Claude Usage Monitor.app"
cd ..
```

### Step 5: Create DMG (Optional)

```bash
create-dmg \
  --volname "Claude Usage Monitor" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "Claude Usage Monitor.app" 175 190 \
  --hide-extension "Claude Usage Monitor.app" \
  --app-drop-link 425 190 \
  "dist/ClaudeUsageMonitor-1.0.0.dmg" \
  "dist/Claude Usage Monitor.app"
```

## Troubleshooting

### Build Fails: "No module named 'rumps'"

**Solution:** Install dependencies first
```bash
pip3 install -r requirements.txt
```

### App Fails: "Library not loaded: libffi.8.dylib"

**Issue:** py2app doesn't automatically bundle all dynamic libraries

**Solution:** Run the post-build script (automatically called by build.sh)
```bash
./post_build.sh
```

This copies required libraries to the app bundle:
- `libffi.8.dylib` (for ctypes support)
- `libssl.3.dylib` (for HTTPS support)
- `libcrypto.3.dylib` (for SSL/TLS support)

### App Crashes on Launch

**Solution:** Check the log
```bash
# View system logs
log show --predicate 'process == "Claude Usage Monitor"' --last 1m

# Or check Console.app
# Filter: process:Claude Usage Monitor
```

### "App is damaged" Error

**Solution:** Remove quarantine attribute
```bash
xattr -cr "dist/Claude Usage Monitor.app"
```

### Large App Size

**Solution:** The app includes Python runtime and dependencies, typical size 40-60MB.

To reduce size:
- Exclude unnecessary packages in `setup.py`
- Use `strip` option (already enabled)
- Use `optimize` option (already enabled)

### App Not Hiding from Dock

**Solution:** Check `LSUIElement` in setup.py
```python
'LSUIElement': True,  # Must be True for menu bar only apps
```

## File Structure

### setup.py Configuration

```python
OPTIONS = {
    'LSUIElement': True,        # Hide from Dock
    'packages': ['rumps', ...], # Include packages
    'excludes': ['tkinter'],    # Exclude unused packages
    'strip': True,              # Strip debug symbols
    'optimize': 2,              # Optimize bytecode
}
```

### Build Output

```
build/                              # Temporary build files
└── bdist.macosx-10.14-x86_64/
    └── python3.x-standalone/

dist/
└── Claude Usage Monitor.app/      # Standalone application
    └── Contents/
        ├── MacOS/
        │   └── Claude Usage Monitor  # Executable
        ├── Resources/
        │   ├── lib/                  # Python libraries
        │   └── site.pyc              # Python site packages
        ├── Frameworks/               # Python framework (if needed)
        └── Info.plist                # App metadata
```

## Code Signing (Optional)

For distribution outside friends & family, consider code signing:

### Prerequisites
- Apple Developer Account ($99/year)
- Developer ID certificate

### Sign the App

```bash
# Sign
codesign --deep --force --sign "Developer ID Application: Your Name" \
  "dist/Claude Usage Monitor.app"

# Verify
codesign --verify --deep --strict "dist/Claude Usage Monitor.app"
spctl -a -vv "dist/Claude Usage Monitor.app"
```

### Notarize (macOS 10.14+)

```bash
# Create DMG first
# Upload for notarization
xcrun altool --notarize-app \
  --primary-bundle-id "com.claude.usage.monitor" \
  --username "your@apple.id" \
  --password "@keychain:AC_PASSWORD" \
  --file "dist/ClaudeUsageMonitor-1.0.0.dmg"

# Check status
xcrun altool --notarization-info <RequestUUID> \
  --username "your@apple.id" \
  --password "@keychain:AC_PASSWORD"

# Staple the ticket
xcrun stapler staple "dist/ClaudeUsageMonitor-1.0.0.dmg"
```

## Distribution Checklist

Before releasing:

- [ ] Test .app on different macOS versions
- [ ] Test on clean macOS (no Python installed)
- [ ] Verify menu bar icon appears
- [ ] Verify Dock icon hidden
- [ ] Test auto-start functionality
- [ ] Test Cookie configuration
- [ ] Test notifications
- [ ] Check app size (should be < 100MB)
- [ ] Create release notes
- [ ] Update version in main.py and setup.py
- [ ] Tag git release

## Release Workflow

```bash
# 1. Update version
# Edit main.py: __version__ = "1.0.1"
# Edit setup.py: 'CFBundleVersion': '1.0.1'

# 2. Build
./build.sh

# 3. Test
open "dist/Claude Usage Monitor.app"

# 4. Create GitHub Release
gh release create v1.0.1 \
  --title "v1.0.1 - Bug Fixes" \
  --notes-file CHANGELOG.md \
  dist/ClaudeUsageMonitor-1.0.1.dmg \
  dist/ClaudeUsageMonitor-1.0.1.app.zip

# 5. Update Homebrew Cask (if published)
# Edit homebrew-cask formula with new version and SHA256
```

## Advanced: Custom Icon

### Create .icns Icon

```bash
# 1. Prepare PNG files (multiple sizes)
# icon_16x16.png
# icon_32x32.png
# icon_128x128.png
# icon_256x256.png
# icon_512x512.png

# 2. Create iconset
mkdir Claude.iconset
cp icon_16x16.png Claude.iconset/icon_16x16.png
cp icon_32x32.png Claude.iconset/icon_32x32.png
# ... (copy all sizes)

# 3. Convert to .icns
iconutil -c icns Claude.iconset -o icon.icns

# 4. Update setup.py
OPTIONS = {
    'iconfile': 'icon.icns',
    ...
}
```

## Support

If you encounter issues:
1. Check this guide
2. Check py2app documentation: https://py2app.readthedocs.io/
3. Open GitHub issue with build logs

---

Last updated: 2025-10-28
