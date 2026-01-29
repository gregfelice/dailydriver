# SPDX-License-Identifier: GPL-3.0-or-later
"""Service for detecting and configuring tiling window management."""

import subprocess
from dataclasses import dataclass
from enum import Enum, auto

from gi.repository import Gio


class TilingStatus(Enum):
    """Current tiling configuration status."""

    NONE = auto()  # No tiling configured
    NATIVE_BASIC = auto()  # Native GNOME tiling enabled
    TILING_ASSISTANT = auto()  # Recommended extension


@dataclass
class TilingInfo:
    """Information about tiling configuration."""

    status: TilingStatus
    extension_installed: str | None = None  # Name of installed but disabled extension
    native_keys_bound: bool = False


# Default keybindings for native GNOME tiling
NATIVE_TILING_DEFAULTS = {
    "org.gnome.mutter.keybindings": {
        "toggle-tiled-left": ["<Super>Left"],
        "toggle-tiled-right": ["<Super>Right"],
    },
    "org.gnome.desktop.wm.keybindings": {
        "move-to-corner-nw": ["<Super><Shift>KP_7"],
        "move-to-corner-ne": ["<Super><Shift>KP_9"],
        "move-to-corner-sw": ["<Super><Shift>KP_1"],
        "move-to-corner-se": ["<Super><Shift>KP_3"],
        "move-to-side-n": ["<Super><Shift>KP_8"],
        "move-to-side-s": ["<Super><Shift>KP_2"],
        "move-to-side-e": ["<Super><Shift>KP_6"],
        "move-to-side-w": ["<Super><Shift>KP_4"],
    },
}


class TilingService:
    """Service for managing tiling configuration."""

    def __init__(self) -> None:
        self._schema_source = Gio.SettingsSchemaSource.get_default()

    def _schema_exists(self, schema_id: str) -> bool:
        """Check if a GSettings schema exists."""
        return self._schema_source.lookup(schema_id, True) is not None

    def _get_enabled_extensions(self) -> list[str]:
        """Get list of enabled GNOME Shell extensions."""
        try:
            result = subprocess.run(
                ["gnome-extensions", "list", "--enabled"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return [e.strip() for e in result.stdout.strip().split("\n") if e.strip()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return []

    def _get_installed_extensions(self) -> list[str]:
        """Get list of installed GNOME Shell extensions."""
        try:
            result = subprocess.run(
                ["gnome-extensions", "list"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return [e.strip() for e in result.stdout.strip().split("\n") if e.strip()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return []

    def _check_native_tiling_bound(self) -> bool:
        """Check if native GNOME tiling keys are bound."""
        schema = self._schema_source.lookup("org.gnome.mutter.keybindings", True)
        if not schema:
            return False

        settings = Gio.Settings.new("org.gnome.mutter.keybindings")

        # Check if either left or right tiling is bound
        for key in ["toggle-tiled-left", "toggle-tiled-right"]:
            value = settings.get_strv(key)
            if value and value != [""] and value != []:
                return True

        return False

    def detect_status(self) -> TilingInfo:
        """Detect current tiling configuration status."""
        enabled = self._get_enabled_extensions()
        installed = self._get_installed_extensions()

        # Check if Tiling Assistant is enabled
        for ext in enabled:
            if "tiling-assistant" in ext.lower():
                return TilingInfo(status=TilingStatus.TILING_ASSISTANT)

        # Check if Tiling Assistant is installed but not enabled
        extension_installed = None
        for ext in installed:
            if "tiling-assistant" in ext.lower():
                extension_installed = "Tiling Assistant"
                break

        # Check native tiling
        native_bound = self._check_native_tiling_bound()
        if native_bound:
            return TilingInfo(
                status=TilingStatus.NATIVE_BASIC,
                extension_installed=extension_installed,
                native_keys_bound=True,
            )

        return TilingInfo(
            status=TilingStatus.NONE,
            extension_installed=extension_installed,
            native_keys_bound=False,
        )

    def enable_native_tiling(self) -> bool:
        """Enable basic native GNOME tiling by binding default keys."""
        try:
            for schema_id, keys in NATIVE_TILING_DEFAULTS.items():
                if not self._schema_exists(schema_id):
                    continue

                settings = Gio.Settings.new(schema_id)
                for key, value in keys.items():
                    settings.set_strv(key, value)

            return True
        except Exception:
            return False

    def enable_extension(self, extension_id: str) -> bool:
        """Enable a GNOME Shell extension."""
        try:
            result = subprocess.run(
                ["gnome-extensions", "enable", extension_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_tiling_assistant_id(self) -> str | None:
        """Get the full extension ID for Tiling Assistant if installed."""
        installed = self._get_installed_extensions()
        for ext in installed:
            if "tiling-assistant" in ext.lower():
                return ext
        return None

    def apply_tiling_assistant_defaults(self) -> bool:
        """Apply good default keybindings for Tiling Assistant."""
        schema_id = "org.gnome.shell.extensions.tiling-assistant"
        if not self._schema_exists(schema_id):
            return False

        try:
            settings = Gio.Settings.new(schema_id)

            # Good defaults for tiling
            defaults = {
                "tile-left-half": ["<Super>Left", "<Super>KP_4"],
                "tile-right-half": ["<Super>Right", "<Super>KP_6"],
                "tile-top-half": ["<Super>KP_8"],
                "tile-bottom-half": ["<Super>KP_2"],
                "tile-topleft-quarter": ["<Super>KP_7"],
                "tile-topright-quarter": ["<Super>KP_9"],
                "tile-bottomleft-quarter": ["<Super>KP_1"],
                "tile-bottomright-quarter": ["<Super>KP_3"],
                "tile-maximize": ["<Super>Up", "<Super>KP_5"],
                "center-window": ["<Super>KP_0"],
                "restore-window": ["<Super>Down"],
            }

            for key, value in defaults.items():
                try:
                    settings.set_strv(key, value)
                except Exception:
                    pass  # Key might not exist in all versions

            return True
        except Exception:
            return False
