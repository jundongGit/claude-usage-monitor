#!/bin/bash
# Post-build script to copy required dynamic libraries
# Run this after py2app build to fix library dependencies

APP_PATH="dist/Claude Usage Monitor.app"
FRAMEWORKS_DIR="${APP_PATH}/Contents/Frameworks"

echo "📦 Post-build: Copying required libraries..."

# Create Frameworks directory if it doesn't exist
mkdir -p "${FRAMEWORKS_DIR}"

# Copy libffi (required for ctypes)
if [ -f "/opt/miniconda3/lib/libffi.8.dylib" ]; then
    cp /opt/miniconda3/lib/libffi.8.dylib "${FRAMEWORKS_DIR}/"
    echo "✓ Copied libffi.8.dylib"
else
    echo "⚠️  libffi.8.dylib not found in /opt/miniconda3/lib"
fi

# Copy OpenSSL libraries (required for HTTPS)
if [ -f "/opt/miniconda3/lib/libssl.3.dylib" ]; then
    cp /opt/miniconda3/lib/libssl.3.dylib "${FRAMEWORKS_DIR}/"
    echo "✓ Copied libssl.3.dylib"
else
    echo "⚠️  libssl.3.dylib not found"
fi

if [ -f "/opt/miniconda3/lib/libcrypto.3.dylib" ]; then
    cp /opt/miniconda3/lib/libcrypto.3.dylib "${FRAMEWORKS_DIR}/"
    echo "✓ Copied libcrypto.3.dylib"
else
    echo "⚠️  libcrypto.3.dylib not found"
fi

echo ""
echo "✅ Post-build complete!"
echo "Libraries in Frameworks:"
ls -lh "${FRAMEWORKS_DIR}/" | tail -n +2 | awk '{print "   " $9 " (" $5 ")"}'
