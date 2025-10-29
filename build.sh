#!/bin/bash
# Build script for Claude Usage Monitor
# Creates macOS .app bundle and DMG installer

set -e  # Exit on error

echo "🚀 Claude Usage Monitor - Build Script"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Version from main.py
VERSION="1.0.0"
APP_NAME="Claude Usage Monitor"
DMG_NAME="ClaudeUsageMonitor-${VERSION}"

# Step 1: Check dependencies
echo "${YELLOW}📋 Checking dependencies...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "${RED}❌ Python 3 not found${NC}"
    exit 1
fi

if ! python3 -c "import py2app" 2>/dev/null; then
    echo "${YELLOW}⚙️  Installing py2app...${NC}"
    pip3 install py2app
fi

if ! command -v create-dmg &> /dev/null; then
    echo "${YELLOW}⚙️  Installing create-dmg...${NC}"
    brew install create-dmg || echo "${YELLOW}⚠️  create-dmg not installed, will skip DMG creation${NC}"
fi

echo "${GREEN}✓${NC} Dependencies OK"
echo ""

# Step 2: Clean previous builds
echo "${YELLOW}🧹 Cleaning previous builds...${NC}"
rm -rf build dist
echo "${GREEN}✓${NC} Clean complete"
echo ""

# Step 3: Build .app bundle
echo "${YELLOW}📦 Building .app bundle...${NC}"
python3 setup.py py2app

if [ -d "dist/${APP_NAME}.app" ]; then
    echo "${GREEN}✓${NC} .app bundle created successfully"
    echo "   Location: dist/${APP_NAME}.app"

    # Run post-build script to copy required libraries
    echo ""
    echo "${YELLOW}📦 Running post-build script...${NC}"
    if [ -f "post_build.sh" ]; then
        ./post_build.sh
    else
        echo "${YELLOW}⚠️  post_build.sh not found, skipping library copy${NC}"
    fi

    # Get app size
    APP_SIZE=$(du -sh "dist/${APP_NAME}.app" | cut -f1)
    echo "   Final Size: ${APP_SIZE}"
else
    echo "${RED}❌ Failed to create .app bundle${NC}"
    exit 1
fi
echo ""

# Step 4: Create ZIP archive
echo "${YELLOW}📦 Creating ZIP archive...${NC}"
cd dist
zip -r -q "${DMG_NAME}.app.zip" "${APP_NAME}.app"
cd ..

if [ -f "dist/${DMG_NAME}.app.zip" ]; then
    ZIP_SIZE=$(du -sh "dist/${DMG_NAME}.app.zip" | cut -f1)
    echo "${GREEN}✓${NC} ZIP archive created"
    echo "   Location: dist/${DMG_NAME}.app.zip"
    echo "   Size: ${ZIP_SIZE}"
else
    echo "${RED}❌ Failed to create ZIP archive${NC}"
fi
echo ""

# Step 5: Create DMG (optional)
if command -v create-dmg &> /dev/null; then
    echo "${YELLOW}📦 Creating DMG installer...${NC}"
    
    create-dmg \
        --volname "${APP_NAME}" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "${APP_NAME}.app" 175 190 \
        --hide-extension "${APP_NAME}.app" \
        --app-drop-link 425 190 \
        "dist/${DMG_NAME}.dmg" \
        "dist/${APP_NAME}.app" \
        2>/dev/null || true
    
    if [ -f "dist/${DMG_NAME}.dmg" ]; then
        DMG_SIZE=$(du -sh "dist/${DMG_NAME}.dmg" | cut -f1)
        echo "${GREEN}✓${NC} DMG installer created"
        echo "   Location: dist/${DMG_NAME}.dmg"
        echo "   Size: ${DMG_SIZE}"
    else
        echo "${YELLOW}⚠️  DMG creation failed or skipped${NC}"
    fi
else
    echo "${YELLOW}⚠️  create-dmg not installed, skipping DMG creation${NC}"
    echo "   Install with: brew install create-dmg"
fi
echo ""

# Step 6: Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "${GREEN}✅ Build Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Build artifacts:"
ls -lh dist/ | grep -E '\.(app|zip|dmg)' | awk '{print "   " $9 " (" $5 ")"}'
echo ""
echo "🧪 Test the app:"
echo "   open \"dist/${APP_NAME}.app\""
echo ""
echo "📤 Ready to distribute:"
if [ -f "dist/${DMG_NAME}.dmg" ]; then
    echo "   ${GREEN}dist/${DMG_NAME}.dmg${NC} (recommended for users)"
fi
echo "   ${GREEN}dist/${DMG_NAME}.app.zip${NC} (alternative)"
echo ""
