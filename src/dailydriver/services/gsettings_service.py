# SPDX-License-Identifier: GPL-3.0-or-later
"""Backwards-compatible alias for GnomeShortcutsBackend.

This module is deprecated. Use dailydriver.services.backends instead:

    from dailydriver.services.backends import get_shortcuts_backend
    backend = get_shortcuts_backend()

Or for GNOME-specific code:

    from dailydriver.services.backends import GnomeShortcutsBackend
    backend = GnomeShortcutsBackend()
"""

# Re-export everything from gnome backend for backwards compatibility
from gi.repository import Gio, GLib  # noqa: F401

from dailydriver.services.backends.gnome import (
    CATEGORIES,
    KEY_CATEGORIES,
    SHORTCUT_SCHEMAS,
    GnomeShortcutsBackend,
    _get_key_category,
    _get_shortcut_group,
    _humanize_key_name,
)

# Backwards-compatible alias
GSettingsService = GnomeShortcutsBackend

__all__ = [
    "GSettingsService",
    "GnomeShortcutsBackend",
    "CATEGORIES",
    "SHORTCUT_SCHEMAS",
    "KEY_CATEGORIES",
    "_humanize_key_name",
    "_get_shortcut_group",
    "_get_key_category",
    "Gio",
    "GLib",
]
