#!/bin/bash
# Sign the py2app bundle with Developer ID, notarize it with Apple and staple the ticket,
# so the app opens on any Mac with a plain double-click (no Gatekeeper warning).
# Run after build.sh. Rebuilds the ZIP and DMG from the signed app.

set -euo pipefail

VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' main.py)
APP="dist/Claude Usage Monitor.app"
ZIP="dist/ClaudeUsageMonitor-${VERSION}.app.zip"
DMG="dist/ClaudeUsageMonitor-${VERSION}.dmg"
IDENTITY="Developer ID Application: FREEAI LIMITED (XF9W8A344D)"
ENTITLEMENTS="entitlements.plist"

KEY_ID="${NOTARY_KEY_ID:-U674AAAC7Z}"
ISSUER="${NOTARY_ISSUER:-61f8dc50-f079-422a-aa53-f1530aaa41d0}"
KEY_PATH="$HOME/.appstoreconnect/private_keys/AuthKey_${KEY_ID}.p8"

sign() { codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" --sign "$IDENTITY" "$@"; }

# py2app leaves lib/pythonX.Y/site.pyo -> ../../site.pyo, but only site.pyc exists;
# a dangling symlink fails strict verification and notarization
find "$APP" -type l ! -exec test -e {} \; -print -delete

echo "Signing nested binaries..."
# Inside-out: every Mach-O except the main executable, then the bundle itself
while IFS= read -r -d '' f; do
    if file -b "$f" | grep -q "Mach-O"; then
        sign "$f"
    fi
done < <(find "$APP/Contents" -type f ! -path "$APP/Contents/MacOS/Claude Usage Monitor" -print0)
sign "$APP"
codesign --verify --deep --strict "$APP"

echo "Notarizing app..."
rm -f "$ZIP"
ditto -c -k --keepParent "$APP" "$ZIP"
xcrun notarytool submit "$ZIP" --key "$KEY_PATH" --key-id "$KEY_ID" --issuer "$ISSUER" --wait
xcrun stapler staple "$APP"
# Re-zip so the archive carries the stapled ticket (offline first launch)
rm -f "$ZIP"
ditto -c -k --keepParent "$APP" "$ZIP"

echo "Building and notarizing DMG..."
rm -f "$DMG"
create-dmg \
    --volname "Claude Usage Monitor" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "Claude Usage Monitor.app" 175 190 \
    --hide-extension "Claude Usage Monitor.app" \
    --app-drop-link 425 190 \
    "$DMG" "$APP"
codesign --force --timestamp --sign "$IDENTITY" "$DMG"
xcrun notarytool submit "$DMG" --key "$KEY_PATH" --key-id "$KEY_ID" --issuer "$ISSUER" --wait
xcrun stapler staple "$DMG"

echo "Gatekeeper assessment:"
spctl -a -vvv -t exec "$APP"
spctl -a -vvv -t open --context context:primary-signature "$DMG"
