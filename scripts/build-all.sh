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
    flatpak build-bundle repo "$DIST_DIR/DailyDriver.flatpak" io.github.gregfelice.DailyDriver --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo
    echo "✅ Flatpak bundle created: $DIST_DIR/DailyDriver.flatpak"
else
    echo "⚠️ flatpak-builder not found, skipping Flatpak build."
fi

# 3. Build Snap
if command -v snapcraft >/dev/null; then
    echo "🔨 Building Snap..."
    # Using --destructive-mode to build on host since container networking is restricted
    snapcraft pack --destructive-mode --output "$DIST_DIR/DailyDriver.snap"
    echo "✅ Snap package created: $DIST_DIR/DailyDriver.snap"
else
    echo "⚠️ snapcraft not found, skipping Snap build."
fi

# 4. Build Debian Package (Manual assembly)
if command -v dpkg-deb >/dev/null; then
    echo "🔨 Building Debian package..."
    PKG_ROOT="build-deb-manual"
    rm -rf "$PKG_ROOT"
    mkdir -p "$PKG_ROOT/DEBIAN"
    
    # Ensure we have a build directory
    if [ ! -d "build-appimage" ]; then
        meson setup build-appimage --prefix=/usr
    fi
    DESTDIR="$(pwd)/$PKG_ROOT" meson install -C build-appimage
    
    # Force system python shebang to bypass active venvs
    sed -i '1s|.*|#!/usr/bin/python3|' "$PKG_ROOT/usr/bin/dailydriver"
    
    cat <<EOF > "$PKG_ROOT/DEBIAN/control"
Package: dailydriver
Version: $(grep "version:" meson.build | head -n1 | cut -d"'" -f2)
Architecture: amd64
Maintainer: Greg Felice <greg@gregfelice.com>
Depends: python3-gi, python3-pydantic, python3-tomli-w, gir1.2-gtk-4.0, gir1.2-adw-1, dconf-gsettings-backend
Description: Visual keyboard shortcut configuration for GNOME
 Daily Driver provides a videogame-like options UI for keyboard configuration.
 Easily customize your keyboard shortcuts, create profiles, and configure
 Mac keyboards on Linux.
EOF
    dpkg-deb --build "$PKG_ROOT" "$DIST_DIR/dailydriver_amd64.deb"
    rm -rf "$PKG_ROOT"
    echo "✅ Debian package created: $DIST_DIR/dailydriver_amd64.deb"
fi

# 5. Create Portable ZIP
echo "🔨 Creating Portable ZIP..."
rm -rf "dist/DailyDriver-Portable"
mkdir -p "dist/DailyDriver-Portable"
cp -r DailyDriver.AppDir/usr/* "dist/DailyDriver-Portable/" 2>/dev/null || cp -r build-deb-manual/usr/* "dist/DailyDriver-Portable/" 2>/dev/null || true

cat <<EOF > "dist/DailyDriver-Portable/run.sh"
#!/usr/bin/env bash
HERE="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="\$HERE/lib/python3/dist-packages:\${PYTHONPATH:-}"
export GSETTINGS_SCHEMA_DIR="\$HERE/share/glib-2.0/schemas:\${GSETTINGS_SCHEMA_DIR:-}"
exec "\$HERE/bin/dailydriver" "\$@"
EOF
chmod +x "dist/DailyDriver-Portable/run.sh"
(cd dist && zip -r DailyDriver-Portable.zip DailyDriver-Portable/)

echo "🚀 All builds complete in $DIST_DIR/"
