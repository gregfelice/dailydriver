#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# AppImage build script for DailyDriver

set -euo pipefail

DIST_DIR="dist"
mkdir -p "$DIST_DIR"
BUILD_DIR="build-appimage"
APPDIR="DailyDriver.AppDir"

echo "📦 Preparing AppImage build..."

# 1. Download linuxdeploy if missing
if [ ! -f "linuxdeploy-x86_64.AppImage" ]; then
    echo "📥 Downloading linuxdeploy..."
    curl -L -O https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
    chmod +x linuxdeploy-x86_64.AppImage
fi

if [ ! -f "linuxdeploy-plugin-python-x86_64.AppImage" ]; then
    echo "📥 Downloading linuxdeploy-python-plugin..."
    curl -L -O https://github.com/linuxdeploy/linuxdeploy-plugin-python/releases/download/continuous/linuxdeploy-plugin-python-x86_64.AppImage
    chmod +x linuxdeploy-plugin-python-x86_64.AppImage
fi

# 2. Build and Install to AppDir
echo "🔨 Building and installing to AppDir..."
rm -rf "$BUILD_DIR" "$APPDIR"
meson setup "$BUILD_DIR" --prefix=/usr
DESTDIR="$(pwd)/$APPDIR" meson install -C "$BUILD_DIR"

# 3. Use linuxdeploy to package
echo "🚀 Bundling AppImage..."
export ARCH=x86_64
export OUTPUT="DailyDriver-x86_64.AppImage"

./linuxdeploy-x86_64.AppImage 
    --appdir "$APPDIR" 
    --plugin python 
    --output appimage 
    --desktop-file "$APPDIR/usr/share/applications/io.github.gregfelice.DailyDriver.desktop" 
    --icon-file "$APPDIR/usr/share/icons/hicolor/scalable/apps/io.github.gregfelice.DailyDriver.svg"

mv "$OUTPUT" "$DIST_DIR/"
echo "✅ AppImage created: $DIST_DIR/$OUTPUT"
