# SPDX-License-Identifier: GPL-3.0-or-later
"""Desktop-agnostic shortcuts backend abstraction."""

from dailydriver.services.backends.base import ShortcutsBackend
from dailydriver.services.backends.detection import DesktopEnvironment, detect_desktop
from dailydriver.services.backends.factory import get_shortcuts_backend, reset_backend
from dailydriver.services.backends.gnome import GnomeShortcutsBackend
from dailydriver.services.backends.kde import KDEShortcutsBackend

__all__ = [
    "ShortcutsBackend",
    "DesktopEnvironment",
    "detect_desktop",
    "get_shortcuts_backend",
    "reset_backend",
    "GnomeShortcutsBackend",
    "KDEShortcutsBackend",
]
