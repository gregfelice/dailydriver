# SPDX-License-Identifier: GPL-3.0-or-later
"""Keyboard layout and hardware models."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class KeyboardType(Enum):
    """Type of keyboard layout."""

    ANSI_104 = "ansi-104"  # Full-size with numpad
    ANSI_87 = "ansi-87"  # TKL (tenkeyless)
    ANSI_60 = "ansi-60"  # 60% compact
    ISO_105 = "iso-105"
    MAC_ANSI = "mac-ansi"
    MAC_ISO = "mac-iso"

    @property
    def display_name(self) -> str:
        """Human-readable name."""
        names = {
            KeyboardType.ANSI_104: "Full-size (104-key)",
            KeyboardType.ANSI_87: "TKL (87-key)",
            KeyboardType.ANSI_60: "60% Compact",
            KeyboardType.ISO_105: "ISO 105-key",
            KeyboardType.MAC_ANSI: "Apple Magic Keyboard",
            KeyboardType.MAC_ISO: "Apple (ISO)",
        }
        return names.get(self, self.value)

    @property
    def is_apple(self) -> bool:
        """Check if this is an Apple keyboard type."""
        return self in (KeyboardType.MAC_ANSI, KeyboardType.MAC_ISO)

    @property
    def is_iso(self) -> bool:
        """Check if this is an ISO keyboard type."""
        return self in (KeyboardType.ISO_105, KeyboardType.MAC_ISO)


@dataclass
class Key:
    """A single key on the keyboard."""

    # Position and size (in key units, typically 1u = 19.05mm)
    x: float
    y: float
    width: float = 1.0
    height: float = 1.0

    # Key identity
    keycode: int = 0  # Linux keycode
    keyval: int = 0  # GDK keyval for default binding
    label: str = ""  # Display label
    secondary_label: str = ""  # Shift label
    is_modifier: bool = False
    is_special: bool = False

    # Visual properties
    row: int = 0  # Row number for styling

    @property
    def center_x(self) -> float:
        """Get center X position."""
        return self.x + (self.width / 2.0)

    @property
    def center_y(self) -> float:
        """Get center Y position."""
        return self.y + (self.height / 2.0)


@dataclass
class KeyboardLayout:
    """A keyboard layout definition."""

    id: str
    name: str
    type: KeyboardType
    keys: list[Key] = field(default_factory=list)

    # Layout dimensions in key units
    width: float = 0.0
    height: float = 0.0

    @classmethod
    def from_json(cls, path: str | Path) -> "KeyboardLayout":
        """Load keyboard layout from JSON file."""
        import json

        with open(path) as f:
            data = json.load(f)

        keys = []
        for k in data.get("keys", []):
            keys.append(
                Key(
                    x=k.get("x", 0.0),
                    y=k.get("y", 0.0),
                    width=k.get("width", 1.0),
                    height=k.get("height", 1.0),
                    keycode=k.get("keycode", 0),
                    keyval=k.get("keyval", 0),
                    label=k.get("label", ""),
                    secondary_label=k.get("secondary_label", ""),
                    is_modifier=k.get("is_modifier", False),
                    is_special=k.get("is_special", False),
                    row=k.get("row", 0),
                )
            )

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=KeyboardType(data.get("type", "ansi-104")),
            keys=keys,
            width=data.get("width", 0.0),
            height=data.get("height", 0.0),
        )

    def get_key_at(self, x: float, y: float) -> Key | None:
        """Find key at given position (in key units)."""
        for key in self.keys:
            if key.x <= x < key.x + key.width and key.y <= y < key.y + key.height:
                return key
        return None

    def get_key_by_keycode(self, keycode: int) -> Key | None:
        """Find key by Linux keycode."""
        for key in self.keys:
            if key.keycode == keycode:
                return key
        return None


@dataclass
class DetectedKeyboard:
    """A detected physical keyboard."""

    name: str
    path: str  # /dev/input/event* path
    vendor_id: int
    product_id: int

    # Identification
    is_mac: bool = False
    is_bluetooth: bool = False
    is_internal: bool = False  # Laptop built-in keyboard

    # Brand info (populated by HardwareService)
    brand_name: str = ""
    brand_id: str = ""  # For asset lookup: "apple", "logitech", etc.
    model_name: str = ""

    # Capabilities (from evdev)
    has_numpad: bool = False
    has_media_keys: bool = False
    has_fn_key: bool = False

    @property
    def display_name(self) -> str:
        """Get display name for the keyboard."""
        if self.model_name:
            return self.model_name
        name = self.name
        if self.brand_name and self.brand_name.lower() not in name.lower():
            name = f"{self.brand_name} {name}"
        if self.is_bluetooth:
            name += " (Bluetooth)"
        return name

    @property
    def usb_id(self) -> str:
        """Get USB vendor:product ID string."""
        return f"{self.vendor_id:04x}:{self.product_id:04x}"

    @property
    def form_factor(self) -> str:
        """Get keyboard form factor description."""
        if self.has_numpad:
            return "Full-size (100%)"
        elif self.is_internal:
            return "Laptop"
        else:
            return "Tenkeyless (TKL)"

    def suggested_layout(self) -> KeyboardType:
        """Suggest a keyboard layout based on detection."""
        if self.is_mac:
            return KeyboardType.MAC_ANSI
        if self.has_numpad:
            return KeyboardType.ANSI_104
        return KeyboardType.ANSI_87
