#!/usr/bin/env bash
# Development runner for Daily Driver
# Runs the app without installation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
VENV_DIR="$SCRIPT_DIR/.venv-dev"

# Create venv with system site packages (for GTK bindings) if needed
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating development venv with system site packages..."
    /usr/bin/python3 -m venv --system-site-packages "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet tomli_w pydantic
fi

PYTHON="$VENV_DIR/bin/python"

# Check dependencies
$PYTHON -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1')" 2>/dev/null || {
    echo "Error: Missing GTK4 or libadwaita Python bindings"
    echo "Install: sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1"
    exit 1
}

# Compile GSettings schema for development
SCHEMA_DIR="$SCRIPT_DIR/data"
if command -v glib-compile-schemas &> /dev/null; then
    echo "Compiling GSettings schemas..."
    glib-compile-schemas "$SCHEMA_DIR" 2>/dev/null || true
fi

# Set up environment
export PYTHONPATH="$SRC_DIR:${PYTHONPATH:-}"
export GSETTINGS_SCHEMA_DIR="$SCHEMA_DIR:${GSETTINGS_SCHEMA_DIR:-}"

# Run the application directly (no gresource needed for dev)
echo "Starting Daily Driver..."
exec $PYTHON "$SRC_DIR/dailydriver/__main__.py" "$@"
