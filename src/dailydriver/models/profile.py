# SPDX-License-Identifier: GPL-3.0-or-later
"""Profile and configuration models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Self

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

import tomli_w


class FnMode(Enum):
    """Function key mode for hid-apple."""

    DISABLED = 0  # Fn key disabled
    FKEYS = 1  # F1-F12 by default, media with Fn
    MEDIA = 2  # Media keys by default, F1-F12 with Fn


@dataclass
class MacKeyboardConfig:
    """Configuration for Mac keyboards via hid-apple kernel module."""

    fn_mode: FnMode = FnMode.MEDIA
    swap_opt_cmd: bool = False  # Swap Option and Command keys
    swap_fn_leftctrl: bool = False  # Swap Fn and Left Ctrl
    iso_layout: bool = False  # ISO keyboard layout

    def to_modprobe_options(self) -> dict[str, int]:
        """Convert to kernel module parameter values."""
        return {
            "fnmode": self.fn_mode.value,
            "swap_opt_cmd": 1 if self.swap_opt_cmd else 0,
            "swap_fn_leftctrl": 1 if self.swap_fn_leftctrl else 0,
            "iso_layout": 1 if self.iso_layout else 0,
        }


@dataclass
class XKBOptions:
    """XKB keyboard options."""

    # Common options
    caps_lock_behavior: str = ""  # e.g., "caps:escape", "caps:ctrl_modifier"
    alt_win_behavior: str = ""  # e.g., "altwin:swap_alt_win"
    compose_key: str = ""  # e.g., "compose:ralt"
    numpad_behavior: str = ""  # e.g., "numpad:mac"

    def to_xkb_options(self) -> list[str]:
        """Convert to XKB options list."""
        options = []
        if self.caps_lock_behavior:
            options.append(self.caps_lock_behavior)
        if self.alt_win_behavior:
            options.append(self.alt_win_behavior)
        if self.compose_key:
            options.append(self.compose_key)
        if self.numpad_behavior:
            options.append(self.numpad_behavior)
        return options


@dataclass
class Profile:
    """A saved keyboard configuration profile."""

    name: str
    description: str = ""
    author: str = ""
    version: str = "1.0"
    created: datetime = field(default_factory=datetime.now)
    modified: datetime = field(default_factory=datetime.now)

    # Shortcut bindings: schema.key -> list of accelerators
    shortcuts: dict[str, list[str]] = field(default_factory=dict)

    # XKB options
    xkb_options: XKBOptions = field(default_factory=XKBOptions)

    # Mac keyboard config (optional)
    mac_keyboard: MacKeyboardConfig | None = None

    # Custom metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_toml(cls, path: Path) -> Self:
        """Load profile from TOML file."""
        with open(path, "rb") as f:
            data = tomllib.load(f)

        # Parse profile metadata
        profile_data = data.get("profile", {})
        shortcuts = data.get("shortcuts", {})

        # Parse XKB options
        xkb_data = data.get("xkb", {})
        xkb_options = XKBOptions(
            caps_lock_behavior=xkb_data.get("caps_lock", ""),
            alt_win_behavior=xkb_data.get("alt_win", ""),
            compose_key=xkb_data.get("compose", ""),
            numpad_behavior=xkb_data.get("numpad", ""),
        )

        # Parse Mac keyboard config
        mac_data = data.get("mac_keyboard")
        mac_keyboard = None
        if mac_data:
            fn_mode_str = mac_data.get("fn_mode", "media")
            fn_mode = {
                "disabled": FnMode.DISABLED,
                "fkeys": FnMode.FKEYS,
                "media": FnMode.MEDIA,
            }.get(fn_mode_str, FnMode.MEDIA)

            mac_keyboard = MacKeyboardConfig(
                fn_mode=fn_mode,
                swap_opt_cmd=mac_data.get("swap_opt_cmd", False),
                swap_fn_leftctrl=mac_data.get("swap_fn_leftctrl", False),
                iso_layout=mac_data.get("iso_layout", False),
            )

        # Parse timestamps
        created = datetime.fromisoformat(profile_data.get("created", datetime.now().isoformat()))
        modified = datetime.fromisoformat(profile_data.get("modified", datetime.now().isoformat()))

        return cls(
            name=profile_data.get("name", path.stem),
            description=profile_data.get("description", ""),
            author=profile_data.get("author", ""),
            version=profile_data.get("version", "1.0"),
            created=created,
            modified=modified,
            shortcuts=shortcuts,
            xkb_options=xkb_options,
            mac_keyboard=mac_keyboard,
            metadata=data.get("metadata", {}),
        )

    def to_toml(self, path: Path) -> None:
        """Save profile to TOML file."""
        self.modified = datetime.now()

        data: dict[str, Any] = {
            "profile": {
                "name": self.name,
                "description": self.description,
                "author": self.author,
                "version": self.version,
                "created": self.created.isoformat(),
                "modified": self.modified.isoformat(),
            },
            "shortcuts": self.shortcuts,
        }

        # Add XKB options if any are set
        xkb_data = {}
        if self.xkb_options.caps_lock_behavior:
            xkb_data["caps_lock"] = self.xkb_options.caps_lock_behavior
        if self.xkb_options.alt_win_behavior:
            xkb_data["alt_win"] = self.xkb_options.alt_win_behavior
        if self.xkb_options.compose_key:
            xkb_data["compose"] = self.xkb_options.compose_key
        if self.xkb_options.numpad_behavior:
            xkb_data["numpad"] = self.xkb_options.numpad_behavior
        if xkb_data:
            data["xkb"] = xkb_data

        # Add Mac keyboard config if present
        if self.mac_keyboard:
            fn_mode_str = {
                FnMode.DISABLED: "disabled",
                FnMode.FKEYS: "fkeys",
                FnMode.MEDIA: "media",
            }[self.mac_keyboard.fn_mode]

            data["mac_keyboard"] = {
                "fn_mode": fn_mode_str,
                "swap_opt_cmd": self.mac_keyboard.swap_opt_cmd,
                "swap_fn_leftctrl": self.mac_keyboard.swap_fn_leftctrl,
                "iso_layout": self.mac_keyboard.iso_layout,
            }

        # Add metadata if present
        if self.metadata:
            data["metadata"] = self.metadata

        with open(path, "wb") as f:
            tomli_w.dump(data, f)

    def get_shortcut_key(self, schema: str, key: str) -> str:
        """Get the storage key for a shortcut."""
        return f"{schema}.{key}"

    def set_shortcut(self, schema: str, key: str, accelerators: list[str]) -> None:
        """Set shortcut binding(s)."""
        storage_key = self.get_shortcut_key(schema, key)
        self.shortcuts[storage_key] = accelerators

    def get_shortcut(self, schema: str, key: str) -> list[str] | None:
        """Get shortcut binding(s), or None if not in profile."""
        storage_key = self.get_shortcut_key(schema, key)
        return self.shortcuts.get(storage_key)
