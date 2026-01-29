# SPDX-License-Identifier: GPL-3.0-or-later
"""Keyboard shortcut cheat sheet - clean read-only reference."""

import re

from gi.repository import Adw, Gio, Gtk, Pango

from dailydriver.models import Shortcut, ShortcutCategory
from dailydriver.services.gsettings_service import GSettingsService


def _natural_sort_key(text: str) -> list:
    """Sort key for natural ordering (Workspace 2 before Workspace 10)."""
    parts = re.split(r"(\d+)", text)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _humanize_binding(binding) -> str:
    """Convert binding to human-readable label, with better XF86 key names."""
    label = binding.to_label()
    key_name = binding.key_name

    # Map XF86 keys to friendly names (these are physical keys on Mac keyboards)
    xf86_names = {
        "XF86AudioLowerVolume": "Vol−",
        "XF86AudioRaiseVolume": "Vol+",
        "XF86AudioMute": "Mute",
        "XF86AudioPlay": "Play",
        "XF86AudioPause": "Pause",
        "XF86AudioStop": "Stop",
        "XF86AudioNext": "Next",
        "XF86AudioPrev": "Prev",
        "XF86AudioMedia": "Media",
        "XF86MonBrightnessUp": "Bright+",
        "XF86MonBrightnessDown": "Bright−",
        "XF86KbdBrightnessUp": "KbdLight+",
        "XF86KbdBrightnessDown": "KbdLight−",
        "XF86Display": "Display",
        "XF86LaunchA": "F3",
        "XF86LaunchB": "F4",
        "XF86Eject": "Eject",
    }

    if key_name in xf86_names:
        # Replace the key portion with friendly name
        friendly = xf86_names[key_name]
        # If there are modifiers, they're already in the label
        if "+" in label:
            # Get modifier part and replace key
            parts = label.rsplit("+", 1)
            return f"{parts[0]}+{friendly}"
        return friendly

    return label


class ShortcutChip(Gtk.Box):
    """A single shortcut displayed as a chip with key combo."""

    def __init__(self, shortcut: Shortcut) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.set_margin_top(3)
        self.set_margin_bottom(3)

        # Key binding display (prominent, monospace)
        if shortcut.bindings:
            binding = shortcut.bindings[0]
            key_label = Gtk.Label(label=_humanize_binding(binding))
            key_label.add_css_class("monospace")
            key_label.set_xalign(1)
            key_label.set_width_chars(18)
            self.append(key_label)

        # Action name (dimmed)
        name_label = Gtk.Label(label=shortcut.name)
        name_label.add_css_class("dim-label")
        name_label.set_xalign(0)
        name_label.set_hexpand(True)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.append(name_label)


class CategorySection(Gtk.Frame):
    """A section showing shortcuts for one category, organized by groups."""

    # Define group ordering for consistent display
    GROUP_ORDER = [
        # Window management
        "Window State",
        "Window Actions",
        # Tiling
        "Tile Halves",
        "Tile Quarters",
        "Tile Actions",
        "Layouts",
        # Navigation
        "Switch Windows",
        "Switch Workspace",
        "Move to Workspace",
        "Move to Monitor",
        # Media
        "Volume",
        "Playback",
        # Shell
        "Shell Actions",
        "Screenshots",
        # System
        "System",
        "Accessibility",
        # Custom
        "Launchers",
    ]

    def __init__(self, category: ShortcutCategory, shortcuts: list[Shortcut]) -> None:
        super().__init__()
        self.set_valign(Gtk.Align.START)  # Align to top, don't stretch
        self.add_css_class("card")

        # Inner box with padding
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        inner.set_margin_start(20)
        inner.set_margin_end(20)
        inner.set_margin_top(14)
        inner.set_margin_bottom(14)
        self.set_child(inner)

        # Category header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_bottom(8)

        icon = Gtk.Image.new_from_icon_name(category.icon)
        icon.add_css_class("dim-label")
        header.append(icon)

        title = Gtk.Label(label=category.name)
        title.add_css_class("heading")
        title.set_xalign(0)
        header.append(title)

        inner.append(header)

        # Group shortcuts by their group field
        groups: dict[str, list[Shortcut]] = {}
        for shortcut in shortcuts:
            if shortcut.bindings:
                group = shortcut.group or "Other"
                if group not in groups:
                    groups[group] = []
                groups[group].append(shortcut)

        # Sort groups by defined order, unknowns at end
        def group_sort_key(group_name: str) -> int:
            try:
                return self.GROUP_ORDER.index(group_name)
            except ValueError:
                return len(self.GROUP_ORDER)

        sorted_groups = sorted(groups.keys(), key=group_sort_key)

        # Display groups with sub-headers if multiple groups
        show_group_headers = len(sorted_groups) > 1

        for i, group_name in enumerate(sorted_groups):
            group_shortcuts = groups[group_name]
            group_shortcuts.sort(key=lambda s: _natural_sort_key(s.name))

            # Add separator between groups (not before first)
            if show_group_headers and i > 0:
                sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                sep.set_margin_top(6)
                sep.set_margin_bottom(4)
                inner.append(sep)

            # Group sub-header (smaller, dimmed, aligned with action names)
            if show_group_headers:
                group_label = Gtk.Label(label=group_name)
                group_label.add_css_class("caption")
                group_label.add_css_class("dim-label")
                group_label.set_xalign(0)
                group_label.set_margin_start(4)  # Align with shortcut chips
                group_label.set_margin_top(6)
                group_label.set_margin_bottom(2)
                inner.append(group_label)

            # Shortcuts in this group
            for shortcut in group_shortcuts:
                chip = ShortcutChip(shortcut)
                inner.append(chip)


class CheatSheetView(Gtk.Box):
    """Clean read-only cheat sheet of all keyboard shortcuts."""

    __gtype_name__ = "CheatSheetView"

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._gsettings = GSettingsService()
        self._app_settings = Gio.Settings.new("io.github.gregfelice.DailyDriver")

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the cheat sheet UI."""
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header_box.set_halign(Gtk.Align.CENTER)
        header_box.set_margin_start(24)
        header_box.set_margin_end(24)
        header_box.set_margin_top(24)
        header_box.set_margin_bottom(16)

        title = Gtk.Label(label="Keyboard Shortcuts")
        title.add_css_class("title-1")
        header_box.append(title)

        subtitle = Gtk.Label(label="Quick reference for all configured shortcuts")
        subtitle.add_css_class("dim-label")
        header_box.append(subtitle)

        self.append(header_box)

        # Scrolled content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        self.append(scroll)

        # Clamp for max width
        clamp = Adw.Clamp()
        clamp.set_maximum_size(1400)
        clamp.set_tightening_threshold(1000)
        scroll.set_child(clamp)

        # Manual column layout for masonry effect
        self._columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=32)
        self._columns_box.set_halign(Gtk.Align.CENTER)
        self._columns_box.set_homogeneous(True)
        self._columns_box.set_margin_start(32)
        self._columns_box.set_margin_end(32)
        self._columns_box.set_margin_top(16)
        self._columns_box.set_margin_bottom(32)
        clamp.set_child(self._columns_box)

        # Create columns
        self._num_columns = 3
        self._columns: list[Gtk.Box] = []
        for _ in range(self._num_columns):
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            col.set_valign(Gtk.Align.START)
            self._columns.append(col)
            self._columns_box.append(col)

        # Load shortcuts
        self._load_shortcuts()

    def _load_shortcuts(self) -> None:
        """Load and display all shortcuts."""
        shortcuts = self._gsettings.load_all_shortcuts()
        all_categories = self._gsettings.get_categories()

        # Filter categories based on tiling setting
        tiling_enabled = self._app_settings.get_boolean("tiling-enabled")
        tiling_groups = {"Tile Halves", "Tile Quarters", "Tile Actions", "Layouts"}

        categories = [c for c in all_categories if tiling_enabled or c.id != "tiling"]

        # Collect sections with their estimated heights
        sections: list[tuple[CategorySection, int]] = []
        for category in categories:
            category_shortcuts = [
                s
                for s in shortcuts.values()
                if s.category == category.id
                and s.bindings
                and (tiling_enabled or s.group not in tiling_groups)
            ]

            if category_shortcuts:
                category_shortcuts.sort(key=lambda s: _natural_sort_key(s.name))
                section = CategorySection(category, category_shortcuts)
                # Estimate height: header + shortcuts
                est_height = 1 + len(category_shortcuts)
                sections.append((section, est_height))

        # Distribute to columns (shortest column first)
        column_heights = [0] * self._num_columns
        for section, height in sections:
            # Find shortest column
            min_col = column_heights.index(min(column_heights))
            # Apply larger left margin for center and right columns
            if min_col > 0:
                section.get_child().set_margin_start(25)
            self._columns[min_col].append(section)
            column_heights[min_col] += height

    def refresh(self) -> None:
        """Refresh the cheat sheet with current shortcuts."""
        # Clear existing
        for col in self._columns:
            while child := col.get_first_child():
                col.remove(child)

        # Reload
        self._load_shortcuts()
