#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Local packaging script for DailyDriver

set -euo pipefail

# 1. Setup output directory
DIST_DIR="dist"
mkdir -p "$DIST_DIR"
echo "📦 Packaging DailyDriver to $DIST_DIR/..."

# 2. Build Flatpak
if command -v flatpak-builder >/dev/null; then
    echo "🔨 Building Flatpak..."
    # Install dependencies if needed
    flatpak --user install -y flathub org.gnome.Sdk//47 org.gnome.Platform//47 || true
    
    # Build
    flatpak-builder --force-clean --user --repo=repo --bundle-sources build-dir io.github.gregfelice.DailyDriver.yml
    
    # Create Bundle
    flatpak-builder --force-clean --bundle build-dir io.github.gregfelice.DailyDriver.yml "$DIST_DIR/DailyDriver.flatpak"
    echo "✅ Flatpak bundle created: $DIST_DIR/DailyDriver.flatpak"
else
    echo "⚠️ flatpak-builder not found, skipping Flatpak build."
fi

# 3. Build Snap
if command -v snapcraft >/dev/null; then
    echo "🔨 Building Snap..."
    # Snapcraft usually requires Multipass or LXD. 
    # Use --destructive-mode if you are already inside a dedicated build container.
    snapcraft --output "$DIST_DIR/DailyDriver.snap"
    echo "✅ Snap package created: $DIST_DIR/DailyDriver.snap"
else
    echo "⚠️ snapcraft not found, skipping Snap build."
fi

echo "🚀 All builds complete in $DIST_DIR/"
