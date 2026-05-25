# SPDX-License-Identifier: GPL-3.0-or-later
"""Desktop-agnostic shortcuts backend abstraction."""

from nightpanel.services.backends.base import ShortcutsBackend
from nightpanel.services.backends.detection import DesktopEnvironment, detect_desktop
from nightpanel.services.backends.factory import get_shortcuts_backend, reset_backend
from nightpanel.services.backends.gnome import GnomeShortcutsBackend
from nightpanel.services.backends.kde import KDEShortcutsBackend

__all__ = [
    "ShortcutsBackend",
    "DesktopEnvironment",
    "detect_desktop",
    "get_shortcuts_backend",
    "reset_backend",
    "GnomeShortcutsBackend",
    "KDEShortcutsBackend",
]
