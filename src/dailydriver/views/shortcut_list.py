# SPDX-License-Identifier: GPL-3.0-or-later
"""Shortcut list view using Adwaita widgets."""

import re
from collections import defaultdict
from pathlib import Path

from gi.repository import Adw, GObject, Gtk

from dailydriver.models import Shortcut, ShortcutCategory

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


# Load preset data for modification comparison
def _normalize_accelerator(accel: str) -> str:
    """Normalize accelerator string through GTK parsing."""
    from dailydriver.models import KeyBinding

    binding = KeyBinding.from_accelerator(accel)
    return binding.to_accelerator() if binding else accel


def _load_preset_shortcuts(preset_name: str) -> dict[str, set[str]]:
    """Load shortcuts from a preset file, normalized for comparison."""
    preset_path = Path(__file__).parent.parent / "resources" / "presets" / f"{preset_name}.toml"
    if not preset_path.exists():
        return {}
    try:
        with open(preset_path, "rb") as f:
            data = tomllib.load(f)
        shortcuts = data.get("shortcuts", {})
        # Normalize accelerators for consistent comparison
        return {
            key: set(_normalize_accelerator(a) for a in accels) for key, accels in shortcuts.items()
        }
    except Exception:
        return {}


# Cache preset data
_VANILLA_GNOME_SHORTCUTS = _load_preset_shortcuts("vanilla-gnome")
_GNOME_TILING_SHORTCUTS = _load_preset_shortcuts("gnome-tiling")
_HYPRLAND_SHORTCUTS = _load_preset_shortcuts("hyprland-style")


def natural_sort_key(s: str) -> list:
    """Sort strings with embedded numbers naturally.

    "Layout 2" comes before "Layout 10", not after.
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


class ShortcutRow(Adw.ActionRow):
    """A row displaying a single shortcut."""

    __gtype_name__ = "ShortcutRow"

    def __init__(self, shortcut: Shortcut) -> None:
        super().__init__()
        self.shortcut = shortcut

        self.set_title(shortcut.name)
        if shortcut.description:
            self.set_subtitle(shortcut.description)

        self.set_activatable(True)

        # Add reset button (hidden by default) - before shortcut label
        self._reset_button = Gtk.Button.new_from_icon_name("edit-undo-symbolic")
        self._reset_button.set_valign(Gtk.Align.CENTER)
        self._reset_button.set_tooltip_text("Reset to default")
        self._reset_button.add_css_class("flat")
        self._reset_button.set_visible(False)
        self.add_suffix(self._reset_button)

        # Add modified indicator - before shortcut label
        self._modified_icon = Gtk.Image.new_from_icon_name("emblem-important-symbolic")
        self._modified_icon.set_visible(False)
        self.add_suffix(self._modified_icon)

        # Create shortcut label widget
        self._shortcut_label = Gtk.ShortcutLabel()
        self._shortcut_label.set_valign(Gtk.Align.CENTER)
        self.add_suffix(self._shortcut_label)

        # Add edit button (rightmost)
        self._edit_button = Gtk.Button.new_from_icon_name("document-edit-symbolic")
        self._edit_button.set_valign(Gtk.Align.CENTER)
        self._edit_button.set_tooltip_text("Edit shortcut")
        self._edit_button.add_css_class("flat")
        self.add_suffix(self._edit_button)

        self.update_display()

    def update_display(self) -> None:
        """Update the display based on current shortcut state."""
        accel = self.shortcut.accelerator
        self._shortcut_label.set_accelerator(accel if accel else "")

        # Check modification status against presets, not just GNOME defaults
        mod_type = self._get_modification_type()
        is_user_modification = mod_type == "user"

        self._modified_icon.set_visible(is_user_modification)
        self._reset_button.set_visible(is_user_modification)

        if is_user_modification:
            self._update_modification_style()

    def _get_modification_type(self) -> str:
        """
        Determine what type of modification this shortcut represents.

        Returns:
            "vanilla-gnome" - matches vanilla GNOME preset
            "gnome-tiling" - matches GNOME Tiling preset
            "hyprland-style" - matches Hyprland Style preset
            "default" - matches GNOME default (not modified)
            "user" - user modification (doesn't match any preset)
        """
        current_accels = set(self.shortcut.accelerators)
        shortcut_key = f"{self.shortcut.schema}.{self.shortcut.key}"

        # Check if matches GNOME default (not modified at all)
        if not self.shortcut.is_modified:
            return "default"

        # Check if matches Vanilla GNOME preset (already normalized sets)
        if shortcut_key in _VANILLA_GNOME_SHORTCUTS:
            if current_accels == _VANILLA_GNOME_SHORTCUTS[shortcut_key]:
                return "vanilla-gnome"

        # Check if matches GNOME Tiling preset
        if shortcut_key in _GNOME_TILING_SHORTCUTS:
            if current_accels == _GNOME_TILING_SHORTCUTS[shortcut_key]:
                return "gnome-tiling"

        # Check if matches Hyprland preset
        if shortcut_key in _HYPRLAND_SHORTCUTS:
            if current_accels == _HYPRLAND_SHORTCUTS[shortcut_key]:
                return "hyprland-style"

        # User modification (doesn't match any preset)
        return "user"

    def _update_modification_style(self) -> None:
        """Update the modified icon color and tooltip based on modification type."""
        # Remove existing style classes
        for cls in ["accent", "warning", "error", "success"]:
            self._modified_icon.remove_css_class(cls)

        # User modification - show warning style
        self._modified_icon.add_css_class("warning")  # Orange
        self._modified_icon.set_tooltip_text("User modification (differs from preset)")

    def connect_reset(self, callback: callable) -> None:
        """Connect reset button click handler."""
        self._reset_button.connect("clicked", lambda _: callback(self.shortcut))

    def connect_edit(self, callback: callable) -> None:
        """Connect edit button click handler."""
        self._edit_button.connect("clicked", lambda _: callback(self.shortcut))


# Define group ordering for consistent display
GROUP_ORDER = [
    # Tiling
    "Tile Halves",
    "Tile Quarters",
    "Tile Actions",
    "Layouts",
    # Window Management
    "Window State",
    "Window Actions",
    # Navigation
    "Switch Windows",
    "Switch Workspace",
    "Move to Workspace",
    "Move to Monitor",
    # Shell
    "Shell Actions",
    "Screenshots",
    "Input",
    # Media
    "Volume",
    "Playback",
    # System
    "System",
    "Accessibility",
    # Catchall
    "Other",
]

# Concise descriptions for each group
GROUP_DESCRIPTIONS = {
    # Tiling
    "Tile Halves": "Snap window to half of screen",
    "Tile Quarters": "Snap window to corner of screen",
    "Tile Actions": "Maximize, center, or restore tiled windows",
    "Layouts": "Apply predefined window arrangements",
    # Window Management
    "Window State": "Minimize, maximize, or fullscreen windows",
    "Window Actions": "Close, move, or resize windows",
    # Navigation
    "Switch Windows": "Cycle between open windows",
    "Switch Workspace": "Move to another workspace",
    "Move to Workspace": "Send window to another workspace",
    "Move to Monitor": "Send window to another display",
    # Shell
    "Shell Actions": "Activities, app grid, and notifications",
    "Screenshots": "Capture screen, window, or selection",
    "Input": "Switch keyboard layout or input method",
    # Media
    "Volume": "Adjust speaker and microphone levels",
    "Playback": "Play, pause, and skip media",
    # System
    "System": "Lock, logout, and power controls",
    "Accessibility": "Screen reader, magnifier, and contrast",
    # Catchall
    "Other": "Miscellaneous shortcuts",
}


class ShortcutListView(Gtk.Box):
    """View displaying shortcuts for a category, grouped by subcategory."""

    __gtype_name__ = "ShortcutListView"

    __gsignals__ = {
        "shortcut-edit-requested": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),  # Shortcut
        ),
        "shortcut-reset-requested": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),  # Shortcut
        ),
    }

    def __init__(self, category: ShortcutCategory, shortcuts: list[Shortcut]) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.category = category
        self._shortcuts = {s.id: s for s in shortcuts}
        self._rows: dict[str, ShortcutRow] = {}
        self._list_boxes: dict[str, Gtk.ListBox] = {}

        # Category header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_margin_bottom(6)

        icon = Gtk.Image.new_from_icon_name(category.icon)
        icon.set_icon_size(Gtk.IconSize.LARGE)
        header_box.append(icon)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        title_label = Gtk.Label(label=category.name)
        title_label.add_css_class("title-2")
        title_label.set_xalign(0)
        title_box.append(title_label)

        if category.description:
            desc_label = Gtk.Label(label=category.description)
            desc_label.add_css_class("dim-label")
            desc_label.set_xalign(0)
            title_box.append(desc_label)

        header_box.append(title_box)
        self.append(header_box)

        # Group shortcuts by their group field
        groups: dict[str, list[Shortcut]] = defaultdict(list)
        for shortcut in shortcuts:
            groups[shortcut.group].append(shortcut)

        # Sort groups by predefined order
        def group_sort_key(group_name: str) -> int:
            try:
                return GROUP_ORDER.index(group_name)
            except ValueError:
                return len(GROUP_ORDER)  # Unknown groups go last

        sorted_groups = sorted(groups.keys(), key=group_sort_key)

        # Create a PreferencesGroup for each group
        for group_name in sorted_groups:
            group_shortcuts = groups[group_name]
            if not group_shortcuts:
                continue

            # Create preferences group with title and description
            prefs_group = Adw.PreferencesGroup()
            prefs_group.set_title(group_name)
            if group_name in GROUP_DESCRIPTIONS:
                prefs_group.set_description(GROUP_DESCRIPTIONS[group_name])

            # Create list box for this group
            list_box = Gtk.ListBox()
            list_box.set_selection_mode(Gtk.SelectionMode.NONE)
            list_box.add_css_class("boxed-list")
            list_box.connect("row-activated", self._on_row_activated)
            self._list_boxes[group_name] = list_box

            # Sort shortcuts naturally within group (1, 2, 10 not 1, 10, 2)
            sorted_shortcuts = sorted(group_shortcuts, key=lambda s: natural_sort_key(s.name))

            for shortcut in sorted_shortcuts:
                row = ShortcutRow(shortcut)
                row.connect_reset(self._on_reset_clicked)
                row.connect_edit(self._on_edit_clicked)
                self._rows[shortcut.id] = row
                list_box.append(row)

            prefs_group.add(list_box)
            self.append(prefs_group)

    def _on_row_activated(self, list_box: Gtk.ListBox, row: ShortcutRow) -> None:
        """Handle row activation (edit request)."""
        self.emit("shortcut-edit-requested", row.shortcut)

    def _on_edit_clicked(self, shortcut: Shortcut) -> None:
        """Handle edit button click."""
        self.emit("shortcut-edit-requested", shortcut)

    def _on_reset_clicked(self, shortcut: Shortcut) -> None:
        """Handle reset button click."""
        self.emit("shortcut-reset-requested", shortcut)

    def update_shortcut(self, shortcut: Shortcut) -> None:
        """Update display for a shortcut."""
        self._shortcuts[shortcut.id] = shortcut
        if shortcut.id in self._rows:
            self._rows[shortcut.id].shortcut = shortcut
            self._rows[shortcut.id].update_display()

    def get_shortcut(self, shortcut_id: str) -> Shortcut | None:
        """Get a shortcut by ID."""
        return self._shortcuts.get(shortcut_id)
