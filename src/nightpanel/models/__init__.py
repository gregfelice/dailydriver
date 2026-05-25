# SPDX-License-Identifier: GPL-3.0-or-later
"""Data models for Daily Driver."""

from nightpanel.models.keyboard import (
    DetectedKeyboard,
    Key,
    KeyboardLayout,
    KeyboardType,
)
from nightpanel.models.profile import (
    FnMode,
    MacKeyboardConfig,
    Profile,
    XKBOptions,
)
from nightpanel.models.shortcut import (
    KeyBinding,
    Modifier,
    Shortcut,
    ShortcutCategory,
)

__all__ = [
    "DetectedKeyboard",
    "FnMode",
    "Key",
    "KeyBinding",
    "KeyboardLayout",
    "KeyboardType",
    "MacKeyboardConfig",
    "Modifier",
    "Profile",
    "Shortcut",
    "ShortcutCategory",
    "XKBOptions",
]
