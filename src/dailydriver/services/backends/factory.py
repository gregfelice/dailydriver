# SPDX-License-Identifier: GPL-3.0-or-later
"""Factory for creating the appropriate shortcuts backend."""

from __future__ import annotations

import logging

from dailydriver.services.backends.base import ShortcutsBackend
from dailydriver.services.backends.detection import DesktopEnvironment, detect_desktop

logger = logging.getLogger(__name__)

_backend_instance: ShortcutsBackend | None = None


def get_shortcuts_backend() -> ShortcutsBackend:
    """Get the shortcuts backend for the current desktop environment.

    Returns a singleton instance of the appropriate backend based on
    the detected desktop environment.

    Returns:
        A ShortcutsBackend implementation for the current desktop.

    Raises:
        RuntimeError: If no backend is available for the current desktop.
    """
    global _backend_instance

    if _backend_instance is not None:
        return _backend_instance

    desktop = detect_desktop()
    logger.info(f"Detected desktop environment: {desktop.name}")

    if desktop == DesktopEnvironment.GNOME:
        from dailydriver.services.backends.gnome import GnomeShortcutsBackend

        _backend_instance = GnomeShortcutsBackend()
    elif desktop == DesktopEnvironment.KDE:
        from dailydriver.services.backends.kde import KDEShortcutsBackend

        _backend_instance = KDEShortcutsBackend()
    else:
        # Default to GNOME for now - many GNOME-based desktops
        # (Budgie, Cinnamon, etc.) use gsettings
        logger.warning(
            f"Unknown desktop environment ({desktop.name}), falling back to GNOME backend"
        )
        from dailydriver.services.backends.gnome import GnomeShortcutsBackend

        _backend_instance = GnomeShortcutsBackend()

    return _backend_instance


def reset_backend() -> None:
    """Reset the backend singleton (useful for testing)."""
    global _backend_instance
    _backend_instance = None
