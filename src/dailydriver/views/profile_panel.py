# SPDX-License-Identifier: GPL-3.0-or-later
"""Profile management panel."""

from gi.repository import Adw, GLib, GObject, Gtk

from dailydriver.models import Profile
from dailydriver.services.profile_service import ProfileService


class ProfilePanel(Adw.NavigationPage):
    """Panel for managing keyboard configuration profiles."""

    __gtype_name__ = "ProfilePanel"

    __gsignals__ = {
        "profile-selected": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),  # Profile
        ),
        "profile-applied": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),  # Profile
        ),
    }

    def __init__(self, profile_service: ProfileService) -> None:
        super().__init__(title="Profiles", tag="profiles")
        self._service = profile_service
        self._profiles: dict[str, Profile] = {}

        # Build UI
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        # Header
        header = Adw.HeaderBar()
        header.set_show_back_button(True)

        new_button = Gtk.Button.new_from_icon_name("list-add-symbolic")
        new_button.set_tooltip_text("Create new profile")
        new_button.connect("clicked", self._on_new_profile)
        header.pack_end(new_button)

        toolbar_view.add_top_bar(header)

        # Content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar_view.set_content(scroll)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(600)
        clamp.set_margin_start(12)
        clamp.set_margin_end(12)
        clamp.set_margin_top(12)
        clamp.set_margin_bottom(12)
        scroll.set_child(clamp)

        self._content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(self._content_box)

        # Presets section
        presets_group = Adw.PreferencesGroup()
        presets_group.set_title("Built-in Presets")
        presets_group.set_description("Pre-configured keyboard setups")
        self._presets_list = Gtk.ListBox()
        self._presets_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._presets_list.add_css_class("boxed-list")
        presets_group.add(self._presets_list)
        self._content_box.append(presets_group)

        # User profiles section
        user_group = Adw.PreferencesGroup()
        user_group.set_title("Your Profiles")
        user_group.set_description("Custom configurations you've saved")
        self._user_list = Gtk.ListBox()
        self._user_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._user_list.add_css_class("boxed-list")
        user_group.add(self._user_list)
        self._content_box.append(user_group)

        # Load profiles
        GLib.idle_add(self._load_profiles)

    def _load_profiles(self) -> bool:
        """Load and display all profiles."""
        for profile in self._service.list_profiles():
            self._profiles[profile.name] = profile
            row = self._create_profile_row(profile)

            # Determine if preset or user profile
            if profile.author == "Daily Driver":
                self._presets_list.append(row)
            else:
                self._user_list.append(row)

        return False

    def _create_profile_row(self, profile: Profile) -> Adw.ActionRow:
        """Create a row for a profile."""
        row = Adw.ActionRow()
        row.set_title(profile.name)
        row.set_subtitle(profile.description)
        row.set_activatable(True)
        row.profile_name = profile.name

        # Apply button
        apply_button = Gtk.Button(label="Apply")
        apply_button.set_valign(Gtk.Align.CENTER)
        apply_button.add_css_class("suggested-action")
        apply_button.connect("clicked", lambda _: self._on_apply_profile(profile))
        row.add_suffix(apply_button)

        row.connect("activated", lambda _: self.emit("profile-selected", profile))

        return row

    def _on_new_profile(self, button: Gtk.Button) -> None:
        """Handle new profile button click."""
        # TODO: Show new profile dialog
        pass

    def _on_apply_profile(self, profile: Profile) -> None:
        """Apply a profile."""
        self._service.apply_profile(profile)
        self.emit("profile-applied", profile)
