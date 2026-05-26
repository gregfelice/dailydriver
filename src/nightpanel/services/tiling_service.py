# SPDX-License-Identifier: GPL-3.0-or-later
"""Service for managing tiling window manager extensions and settings."""

from __future__ import annotations

import glob
import os
import subprocess
from dataclasses import dataclass
from enum import Enum

from gi.repository import Gio


class TilingStatus(Enum):
    """Tiling status for the current desktop."""

    NONE = "none"
    NATIVE_BASIC = "native-basic"
    NATIVE_EXTENDED = "native-extended"
    TILING_ASSISTANT = "tiling-assistant"


@dataclass
class TilingInfo:
    """Information about current tiling status."""

    status: TilingStatus
    extension_id: str | None = None
    extension_enabled: bool = False
    extension_installed: str | None = None
    native_keys_bound: bool = False


NATIVE_TILING_DEFAULTS = {
    "org.gnome.mutter": {
        "edge-tiling": True,
    },
    "org.gnome.mutter.keybindings": {
        "toggle-tiled-left": ["<Super>Left"],
        "toggle-tiled-right": ["<Super>Right"],
    },
    "org.gnome.desktop.wm.keybindings": {
        "maximize": ["<Super>Up"],
        "unmaximize": ["<Super>Down"],
        "move-to-corner-nw": ["<Super>KP_7"],
        "move-to-corner-ne": ["<Super>KP_9"],
        "move-to-corner-sw": ["<Super>KP_1"],
        "move-to-corner-se": ["<Super>KP_3"],
    },
}

TA_SCHEMA = "org.gnome.shell.extensions.tiling-assistant"


class TilingService:
    """Service for managing tiling window management extensions."""

    TILING_ASSISTANT_ID = "tiling-assistant@leleat"
    SHELL_EXTENSIONS_SCHEMA = "org.gnome.shell"

    def __init__(self) -> None:
        self._schema_source = self._build_schema_source()

    @staticmethod
    def _build_schema_source() -> Gio.SettingsSchemaSource:
        """Build a schema source that includes GNOME extension schemas."""
        source = Gio.SettingsSchemaSource.get_default()
        ext_base = os.path.expanduser("~/.local/share/gnome-shell/extensions")
        for schema_dir in sorted(glob.glob(f"{ext_base}/*/schemas")):
            if os.path.isdir(schema_dir):
                try:
                    source = Gio.SettingsSchemaSource.new_from_directory(schema_dir, source, False)
                except Exception:
                    pass
        return source

    def _get_ta_settings(self) -> Gio.Settings | None:
        """Get Tiling Assistant GSettings using the composite schema source."""
        if not self._schema_source:
            return None
        schema = self._schema_source.lookup(TA_SCHEMA, True)
        if not schema:
            return None
        try:
            return Gio.Settings.new_full(schema, None, None)
        except Exception:
            return None

    def detect_status(self) -> TilingInfo:
        """Detect current tiling status."""
        try:
            result = subprocess.run(
                ["gnome-extensions", "list", "--enabled"],
                capture_output=True,
                text=True,
            )
            if "tiling-assistant" in result.stdout:
                return TilingInfo(
                    status=TilingStatus.TILING_ASSISTANT,
                    extension_id=self.TILING_ASSISTANT_ID,
                    extension_enabled=True,
                    extension_installed="Tiling Assistant",
                )
        except Exception:
            pass

        try:
            mutter_settings = Gio.Settings.new("org.gnome.mutter")
            if mutter_settings.get_boolean("edge-tiling"):
                wm_settings = Gio.Settings.new("org.gnome.desktop.wm.keybindings")
                bound_keys = wm_settings.get_strv("maximize")
                if bound_keys:
                    return TilingInfo(status=TilingStatus.NATIVE_BASIC, native_keys_bound=True)
        except Exception:
            pass

        return TilingInfo(status=TilingStatus.NONE)

    def get_ta_settings(self) -> dict | None:
        """Return current Tiling Assistant behavior settings as a plain dict."""
        s = self._get_ta_settings()
        if not s:
            return None
        return {
            "tile_groups_enabled": not s.get_boolean("disable-tile-groups"),
            "raise_group": s.get_boolean("enable-raise-tile-group"),
        }

    def set_tile_groups(self, enabled: bool) -> bool:
        """Enable or disable tile groups (auto-resize adjacent windows)."""
        s = self._get_ta_settings()
        if not s:
            return False
        try:
            s.set_boolean("disable-tile-groups", not enabled)
            return True
        except Exception:
            return False

    def set_raise_group(self, enabled: bool) -> bool:
        """Enable or disable raising the whole tile group on focus."""
        s = self._get_ta_settings()
        if not s:
            return False
        try:
            s.set_boolean("enable-raise-tile-group", enabled)
            return True
        except Exception:
            return False

    def apply_hyprland_tiling_settings(self) -> bool:
        """Apply TA settings for the best Hyprland-like tiling experience."""
        s = self._get_ta_settings()
        if not s:
            return False
        try:
            s.set_boolean("disable-tile-groups", False)  # tile groups ON
            s.set_boolean("enable-raise-tile-group", True)  # raise group together
            return True
        except Exception:
            return False

    def enable_extension(self, extension_id: str) -> bool:
        """Enable a GNOME Shell extension."""
        try:
            result = subprocess.run(
                ["gnome-extensions", "enable", extension_id],
                capture_output=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def enable_native_tiling(self) -> bool:
        """Enable native GNOME edge tiling."""
        try:
            mutter_settings = Gio.Settings.new("org.gnome.mutter")
            mutter_settings.set_boolean("edge-tiling", True)
            wm_settings = Gio.Settings.new("org.gnome.desktop.wm.keybindings")
            wm_settings.set_strv("maximize", ["<Super>Up"])
            return True
        except Exception:
            return False

    def get_tiling_assistant_id(self) -> str | None:
        """Get the ID of the Tiling Assistant extension if installed."""
        try:
            result = subprocess.run(
                ["gnome-extensions", "list"],
                capture_output=True,
                text=True,
            )
            if self.TILING_ASSISTANT_ID in result.stdout:
                return self.TILING_ASSISTANT_ID
            if "tiling-assistant@ubuntu.com" in result.stdout:
                return "tiling-assistant@ubuntu.com"
        except Exception:
            pass
        return None

    def apply_tiling_assistant_defaults(self) -> bool:
        """Apply recommended defaults for Tiling Assistant."""
        s = self._get_ta_settings()
        if not s:
            return False
        try:
            s.set_strv("search-popup-layout", ["<Super>s"])
            return True
        except Exception:
            return False
