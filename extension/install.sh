#!/bin/bash
# Install DailyDriver Cheat Sheet extension

set -e

EXTENSION_UUID="dailydriver-cheatsheet@gregfelice.github.io"
EXTENSION_DIR="$HOME/.local/share/gnome-shell/extensions/$EXTENSION_UUID"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing DailyDriver Cheat Sheet extension..."

# Create extension directory
mkdir -p "$EXTENSION_DIR"

# Copy files
cp "$SCRIPT_DIR/metadata.json" "$EXTENSION_DIR/"
cp "$SCRIPT_DIR/extension.js" "$EXTENSION_DIR/"
cp "$SCRIPT_DIR/stylesheet.css" "$EXTENSION_DIR/"
mkdir -p "$EXTENSION_DIR/schemas"
cp "$SCRIPT_DIR/schemas/"*.xml "$EXTENSION_DIR/schemas/"

# Compile schemas
glib-compile-schemas "$EXTENSION_DIR/schemas/"

echo "Extension installed to: $EXTENSION_DIR"
echo ""
echo "To enable:"
echo "  1. Log out and log back in (Wayland) or press Alt+F2 and type 'r' (X11)"
echo "  2. Run: gnome-extensions enable $EXTENSION_UUID"
echo ""
echo "Or use GNOME Extensions app to enable it."
echo ""
echo "Shortcut: Alt+Super+/ to toggle cheat sheet"
