# SPDX-License-Identifier: GPL-3.0-or-later
"""Entry point for running dailydriver as a module or script."""

import os
import sys

# Configure dconf/GIO for Flatpak BEFORE any gi imports
# This must be set before any GSettings/dconf access
if "FLATPAK_ID" in os.environ:
    home = os.environ.get("HOME", os.path.expanduser("~"))
    # Override XDG_CONFIG_HOME to read host's dconf database
    # This is needed because dconf looks for its database at $XDG_CONFIG_HOME/dconf/user
    os.environ["XDG_CONFIG_HOME"] = f"{home}/.config"
    # Tell GIO to load dconf module from /app
    os.environ.setdefault("GIO_EXTRA_MODULES", "/app/lib/gio/modules")

# Import cairo before gi to register the foreign struct converter
import cairo  # noqa: F401
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from dailydriver.application import main

if __name__ == "__main__":
    sys.exit(main())
