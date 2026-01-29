# SPDX-License-Identifier: GPL-3.0-or-later
"""Preset selector dialog for choosing keyboard configurations."""

from gi.repository import Adw, GLib, GObject, Gtk

from dailydriver.models import Profile
from dailydriver.services.gsettings_service import GSettingsService
from dailydriver.services.profile_service import ProfileService


class PresetSelector(Adw.Dialog):
    """Dialog for selecting and applying preset profiles."""

    __gtype_name__ = "PresetSelector"

    __gsignals__ = {
        "preset-applied": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str,),  # Preset name
        ),
    }

    def __init__(self) -> None:
        super().__init__()
        self._gsettings_service = GSettingsService()
        self._profile_service = ProfileService(self._gsettings_service)
        self._presets: list[Profile] = []
        self._selected_preset: Profile | None = None

        self.set_title("Choose a Preset")
        self.set_content_width(500)
        self.set_content_height(600)

        self._build_ui()
        self._load_presets()

    def _build_ui(self) -> None:
        """Build the dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_button)

        self._apply_button = Gtk.Button(label="Apply")
        self._apply_button.add_css_class("suggested-action")
        self._apply_button.set_sensitive(False)
        self._apply_button.connect("clicked", self._on_apply)
        header.pack_end(self._apply_button)

        toolbar_view.add_top_bar(header)

        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        toolbar_view.set_content(content)

        # Description
        desc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        desc_box.set_margin_start(24)
        desc_box.set_margin_end(24)
        desc_box.set_margin_top(16)
        desc_box.set_margin_bottom(16)

        desc_label = Gtk.Label(
            label="Choose a preset to configure your keyboard shortcuts.\n"
            "You can customize individual shortcuts afterwards."
        )
        desc_label.set_wrap(True)
        desc_label.add_css_class("dim-label")
        desc_box.append(desc_label)
        content.append(desc_box)

        # Separator
        content.append(Gtk.Separator())

        # Preset list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(500)
        clamp.set_margin_start(12)
        clamp.set_margin_end(12)
        clamp.set_margin_top(12)
        clamp.set_margin_bottom(12)
        scroll.set_child(clamp)

        self._preset_group = Adw.PreferencesGroup()
        self._preset_group.set_title("Available Presets")
        clamp.set_child(self._preset_group)

        content.append(scroll)

        # Changes preview
        self._changes_revealer = Gtk.Revealer()
        self._changes_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)

        changes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        changes_box.set_margin_start(24)
        changes_box.set_margin_end(24)
        changes_box.set_margin_top(16)
        changes_box.set_margin_bottom(16)
        changes_box.add_css_class("card")

        changes_label = Gtk.Label(label="Changes Preview")
        changes_label.add_css_class("heading")
        changes_label.set_xalign(0)
        changes_box.append(changes_label)

        self._changes_list = Gtk.Label()
        self._changes_list.set_xalign(0)
        self._changes_list.set_wrap(True)
        self._changes_list.add_css_class("dim-label")
        self._changes_list.add_css_class("caption")
        changes_box.append(self._changes_list)

        self._changes_revealer.set_child(changes_box)
        content.append(self._changes_revealer)

    def _load_presets(self) -> None:
        """Load available presets."""
        self._presets = []

        # Load from profile service
        for profile in self._profile_service.list_profiles():
            # Only show presets (not user profiles)
            if profile.metadata.get("preset", False):
                self._presets.append(profile)
                self._add_preset_row(profile)

    def _add_preset_row(self, profile: Profile) -> None:
        """Add a row for a preset."""
        row = Adw.ActionRow()
        row.set_title(self._get_display_name(profile.name))
        row.set_subtitle(profile.description)
        row.set_activatable(True)
        row.profile = profile

        # Category badge
        category = profile.metadata.get("category", "standard")
        badge = Gtk.Label(label=category.title())
        badge.add_css_class("profile-indicator")
        row.add_suffix(badge)

        # Selection checkmark (hidden initially)
        check = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        check.set_visible(False)
        check.add_css_class("accent")
        row.add_suffix(check)
        row._check = check

        row.connect("activated", self._on_preset_selected)
        self._preset_group.add(row)

    def _get_display_name(self, name: str) -> str:
        """Convert preset filename to display name."""
        names = {
            "vanilla-gnome": "Vanilla GNOME",
            "gnome-tiling": "GNOME + Tiling",
            "hyprland-style": "Hyprland Style",
            "power-user": "Power User",
            "mac-like": "Mac-like",
        }
        return names.get(name, name.replace("-", " ").title())

    def _on_preset_selected(self, row: Adw.ActionRow) -> None:
        """Handle preset selection."""
        # Deselect all
        child = self._preset_group.get_first_child()
        while child:
            if isinstance(child, Adw.ActionRow) and hasattr(child, "_check"):
                child._check.set_visible(False)
            child = child.get_next_sibling()

        # Select this one
        row._check.set_visible(True)
        self._selected_preset = row.profile
        self._apply_button.set_sensitive(True)

        # Show changes preview
        self._update_changes_preview()

    def _update_changes_preview(self) -> None:
        """Update the changes preview."""
        if not self._selected_preset:
            self._changes_revealer.set_reveal_child(False)
            return

        diff = self._profile_service.get_profile_diff(self._selected_preset)

        if not diff:
            self._changes_list.set_label("No changes needed - already matches this preset.")
        else:
            count = len(diff)
            self._changes_list.set_label(
                f"{count} shortcut{'s' if count != 1 else ''} will be updated."
            )

        self._changes_revealer.set_reveal_child(True)

    def _on_apply(self, button: Gtk.Button) -> None:
        """Apply the selected preset."""
        if not self._selected_preset:
            return

        button.set_sensitive(False)
        button.set_label("Applying...")

        def apply():
            changed = self._profile_service.apply_profile(self._selected_preset)
            GLib.idle_add(self._on_apply_complete, changed)

        GLib.Thread.new("apply-preset", apply)

    def _on_apply_complete(self, changed: dict) -> None:
        """Handle apply completion."""
        self.emit("preset-applied", self._selected_preset.name)
        self.close()
