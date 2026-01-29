# SPDX-License-Identifier: GPL-3.0-or-later
"""Shortcut and key binding models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Flag, auto
from typing import TYPE_CHECKING, Self

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

if TYPE_CHECKING:
    from gi.repository import Gdk


class Modifier(Flag):
    """Keyboard modifiers for shortcuts."""

    NONE = 0
    SHIFT = auto()
    CTRL = auto()
    ALT = auto()
    SUPER = auto()
    HYPER = auto()
    META = auto()

    @classmethod
    def from_gtk(cls, state: int) -> Self:
        """Convert GTK modifier state to Modifier flags."""
        from gi.repository import Gdk

        result = cls.NONE
        if state & Gdk.ModifierType.SHIFT_MASK:
            result |= cls.SHIFT
        if state & Gdk.ModifierType.CONTROL_MASK:
            result |= cls.CTRL
        if state & Gdk.ModifierType.ALT_MASK:
            result |= cls.ALT
        if state & Gdk.ModifierType.SUPER_MASK:
            result |= cls.SUPER
        if state & Gdk.ModifierType.HYPER_MASK:
            result |= cls.HYPER
        if state & Gdk.ModifierType.META_MASK:
            result |= cls.META
        return result

    def to_gtk(self) -> Gdk.ModifierType:
        """Convert to GTK modifier state."""
        from gi.repository import Gdk

        result = Gdk.ModifierType(0)
        if self & Modifier.SHIFT:
            result |= Gdk.ModifierType.SHIFT_MASK
        if self & Modifier.CTRL:
            result |= Gdk.ModifierType.CONTROL_MASK
        if self & Modifier.ALT:
            result |= Gdk.ModifierType.ALT_MASK
        if self & Modifier.SUPER:
            result |= Gdk.ModifierType.SUPER_MASK
        if self & Modifier.HYPER:
            result |= Gdk.ModifierType.HYPER_MASK
        if self & Modifier.META:
            result |= Gdk.ModifierType.META_MASK
        return result


@dataclass(frozen=True)
class KeyBinding:
    """A single key binding (modifier + key combination)."""

    keyval: int  # GDK keyval
    modifiers: Modifier = Modifier.NONE

    @classmethod
    def from_accelerator(cls, accelerator: str) -> Self | None:
        """Parse a GTK accelerator string like '<Super>a' or '<Control><Shift>c'."""
        if not accelerator:
            return None

        from gi.repository import Gtk

        ok, keyval, mods = Gtk.accelerator_parse(accelerator)
        if not ok or keyval == 0:
            return None

        return cls(keyval=keyval, modifiers=Modifier.from_gtk(mods))

    def to_accelerator(self) -> str:
        """Convert to GTK accelerator string."""
        from gi.repository import Gtk

        return Gtk.accelerator_name(self.keyval, self.modifiers.to_gtk())

    def to_label(self) -> str:
        """Convert to human-readable label."""
        from gi.repository import Gtk

        return Gtk.accelerator_get_label(self.keyval, self.modifiers.to_gtk())

    @property
    def key_name(self) -> str:
        """Get the key name without modifiers."""
        from gi.repository import Gdk

        return Gdk.keyval_name(self.keyval) or ""


@dataclass
class ShortcutCategory:
    """Category of shortcuts (e.g., 'Window Management', 'Navigation')."""

    id: str
    name: str
    icon: str = "preferences-system-symbolic"
    description: str = ""


@dataclass
class Shortcut:
    """A configurable keyboard shortcut."""

    id: str
    name: str
    description: str
    category: str  # Category ID
    schema: str  # GSettings schema
    key: str  # GSettings key

    # Subcategory for grouping within a category (e.g., "Move to Workspace")
    group: str = "Other"

    # Current binding(s) - some shortcuts support multiple bindings
    bindings: list[KeyBinding] = field(default_factory=list)

    # Default binding(s) for reset functionality
    default_bindings: list[KeyBinding] = field(default_factory=list)

    # Whether this shortcut can have multiple bindings
    allow_multiple: bool = False

    # Whether this is a system shortcut (read-only)
    system: bool = False

    @property
    def accelerator(self) -> str:
        """Get the primary accelerator string."""
        if not self.bindings:
            return ""
        return self.bindings[0].to_accelerator()

    @property
    def accelerators(self) -> list[str]:
        """Get all accelerator strings."""
        return [b.to_accelerator() for b in self.bindings]

    @property
    def label(self) -> str:
        """Get human-readable label for primary binding."""
        if not self.bindings:
            return "Disabled"
        return self.bindings[0].to_label()

    @property
    def is_modified(self) -> bool:
        """Check if shortcut differs from default."""
        return set(self.bindings) != set(self.default_bindings)

    def set_binding(self, binding: KeyBinding | None) -> None:
        """Set a single binding, replacing existing."""
        self.bindings = [binding] if binding else []

    def add_binding(self, binding: KeyBinding) -> None:
        """Add an additional binding (if multiple allowed)."""
        if self.allow_multiple:
            if binding not in self.bindings:
                self.bindings.append(binding)
        else:
            self.bindings = [binding]

    def remove_binding(self, binding: KeyBinding) -> None:
        """Remove a specific binding."""
        if binding in self.bindings:
            self.bindings.remove(binding)

    def reset(self) -> None:
        """Reset to default bindings."""
        self.bindings = list(self.default_bindings)

    def conflicts_with(self, other: Shortcut) -> bool:
        """Check if this shortcut conflicts with another."""
        if self.id == other.id:
            return False
        my_bindings = set(self.bindings)
        other_bindings = set(other.bindings)
        return bool(my_bindings & other_bindings)
