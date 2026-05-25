# SPDX-License-Identifier: GPL-3.0-or-later
"""Desktop environment detection utilities."""

from __future__ import annotations

import os
from enum import Enum, auto


class DesktopEnvironment(Enum):
    """Supported desktop environments."""

    GNOME = auto()
    KDE = auto()
    UNKNOWN = auto()


def detect_desktop() -> DesktopEnvironment:
    """Detect the current desktop environment.

    Uses XDG_CURRENT_DESKTOP and other environment signals to determine
    which desktop environment is running.

    Returns:
        The detected DesktopEnvironment.
    """
    # XDG_CURRENT_DESKTOP can contain multiple values separated by colons
    # e.g., "ubuntu:GNOME" or "KDE"
    xdg_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    desktop_parts = xdg_desktop.split(":")

    # Check for GNOME (including Ubuntu's variant)
    if any(part in ("GNOME", "UNITY", "UBUNTU") for part in desktop_parts):
        return DesktopEnvironment.GNOME

    # Check for KDE Plasma
    if any(part in ("KDE", "PLASMA") for part in desktop_parts):
        return DesktopEnvironment.KDE

    # Fallback: check XDG_SESSION_DESKTOP
    session_desktop = os.environ.get("XDG_SESSION_DESKTOP", "").upper()
    if session_desktop in ("GNOME", "GNOME-XORG", "GNOME-WAYLAND", "UBUNTU"):
        return DesktopEnvironment.GNOME
    if session_desktop in ("KDE", "PLASMA", "PLASMAWAYLAND"):
        return DesktopEnvironment.KDE

    # Fallback: check for running processes/services
    # This is a last resort and may not be reliable
    if _is_gnome_running():
        return DesktopEnvironment.GNOME
    if _is_kde_running():
        return DesktopEnvironment.KDE

    return DesktopEnvironment.UNKNOWN


def _is_gnome_running() -> bool:
    """Check if GNOME Shell is running via D-Bus."""
    try:
        from gi.repository import Gio

        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        result = connection.call_sync(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "NameHasOwner",
            Gio.Variant("(s)", ("org.gnome.Shell",)),
            Gio.VariantType("(b)"),
            Gio.DBusCallFlags.NONE,
            1000,
            None,
        )
        return result.unpack()[0]
    except Exception:
        return False


def _is_kde_running() -> bool:
    """Check if KDE Plasma is running via D-Bus."""
    try:
        from gi.repository import Gio

        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        result = connection.call_sync(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "NameHasOwner",
            Gio.Variant("(s)", ("org.kde.plasmashell",)),
            Gio.VariantType("(b)"),
            Gio.DBusCallFlags.NONE,
            1000,
            None,
        )
        return result.unpack()[0]
    except Exception:
        return False
