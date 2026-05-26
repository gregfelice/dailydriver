# SPDX-License-Identifier: GPL-3.0-or-later
"""Profiles panel — manage, import, export, and switch keyboard profiles."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from gi.repository import Adw, Gio, GLib, Gtk


class ProfilesView(Gtk.Box):
    """Panel for listing, applying, importing, and exporting profiles."""

    __gtype_name__ = "ProfilesView"

    def __init__(
        self,
        gsettings_service,
        profile_service,
        app_settings,
        on_toast: Callable[[str, str | None, Callable | None], None],
        on_shortcuts_reload: Callable[[], None],
        window,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._gs = gsettings_service
        self._ps = profile_service
        self._settings = app_settings
        self._on_toast = on_toast
        self._on_reload = on_shortcuts_reload
        self._window = window

        self._build_ui()
        GLib.idle_add(self._populate)

    # ------------------------------------------------------------------ build

    def _build_ui(self) -> None:
        # Scrollable content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(760)
        clamp.set_margin_start(12)
        clamp.set_margin_end(12)
        clamp.set_margin_top(12)
        clamp.set_margin_bottom(12)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(content)
        scroll.set_child(clamp)
        self.append(scroll)

        # ── User profiles group ────────────────────────────────────────────
        self._user_group = Adw.PreferencesGroup()
        self._user_group.set_title("my profiles")
        self._user_group.set_description(
            "snapshots of your configuration. export as a shell script to drop into dotfiles."
        )

        save_btn = Gtk.Button(label="save current state…")
        save_btn.add_css_class("flat")
        save_btn.set_icon_name("document-save-symbolic")
        save_btn.connect("clicked", self._on_save_current)
        self._user_group.set_header_suffix(save_btn)

        content.append(self._user_group)

        # Placeholder shown when user has no profiles
        self._user_placeholder = Adw.ActionRow()
        self._user_placeholder.set_title("no saved profiles yet")
        self._user_placeholder.set_subtitle('click "save current state" to snapshot your setup')
        self._user_placeholder.set_sensitive(False)
        self._user_group.add(self._user_placeholder)

        # ── Presets group ──────────────────────────────────────────────────
        self._preset_group = Adw.PreferencesGroup()
        self._preset_group.set_title("built-in presets")
        self._preset_group.set_description("read-only. export to customise.")

        import_btn = Gtk.Button(label="import…")
        import_btn.add_css_class("flat")
        import_btn.set_icon_name("document-open-symbolic")
        import_btn.connect("clicked", self._on_import)
        self._preset_group.set_header_suffix(import_btn)

        content.append(self._preset_group)

    # ---------------------------------------------------------------- populate

    def _populate(self) -> bool:
        self._clear_group(self._user_group, keep_placeholder=True)
        self._clear_group(self._preset_group, keep_placeholder=False)

        active_name = self._settings.get_string("current-preset") if self._settings else ""
        has_user = False

        for profile in self._ps.list_profiles():
            is_preset = profile.metadata.get("preset", False)
            is_active = profile.name == active_name
            row = self._make_profile_row(profile, is_preset=is_preset, is_active=is_active)
            if is_preset:
                self._preset_group.add(row)
            else:
                has_user = True
                self._user_group.add(row)

        self._user_placeholder.set_visible(not has_user)
        return False

    def _clear_group(self, group: Adw.PreferencesGroup, keep_placeholder: bool) -> None:
        child = group.get_first_child()
        rows_to_remove = []
        while child:
            # PreferencesGroup wraps rows in a ListBox; walk its children
            if isinstance(child, Gtk.ListBox):
                row = child.get_first_child()
                while row:
                    widget = row.get_child() if hasattr(row, "get_child") else row
                    if isinstance(widget, Adw.ActionRow):
                        if not keep_placeholder or widget is not self._user_placeholder:
                            rows_to_remove.append((group, widget))
                    row = row.get_next_sibling()
            child = child.get_next_sibling()
        for grp, row in rows_to_remove:
            try:
                grp.remove(row)
            except Exception:
                pass

    def _make_profile_row(self, profile, *, is_preset: bool, is_active: bool) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(self._display_name(profile.name))
        shortcut_count = len(profile.shortcuts)
        row.set_subtitle(
            profile.description or f"{shortcut_count} shortcut{'s' if shortcut_count != 1 else ''}"
        )

        # Active badge
        if is_active:
            active_badge = Gtk.Label(label="active")
            active_badge.add_css_class("success")
            active_badge.add_css_class("caption")
            active_badge.set_valign(Gtk.Align.CENTER)
            row.add_prefix(active_badge)

        # Apply button
        apply_btn = Gtk.Button()
        apply_btn.set_icon_name("media-playback-start-symbolic")
        apply_btn.set_tooltip_text("apply this profile")
        apply_btn.add_css_class("flat")
        apply_btn.set_valign(Gtk.Align.CENTER)
        apply_btn.connect("clicked", self._on_apply_profile, profile)
        row.add_suffix(apply_btn)

        # Export menu button
        export_menu = Gio.Menu()
        export_menu.append("export as toml…", f"profiles.export-toml::{profile.name}")
        export_menu.append("export as shell script…", f"profiles.export-sh::{profile.name}")

        export_btn = Gtk.MenuButton()
        export_btn.set_icon_name("document-send-symbolic")
        export_btn.set_tooltip_text("export profile")
        export_btn.add_css_class("flat")
        export_btn.set_valign(Gtk.Align.CENTER)
        export_btn.set_menu_model(export_menu)
        row.add_suffix(export_btn)

        # Wire export actions onto the row (so menu targets work)
        ag = Gio.SimpleActionGroup()

        export_toml_action = Gio.SimpleAction.new_stateful(
            "export-toml", GLib.VariantType.new("s"), GLib.Variant("s", "")
        )
        export_toml_action.connect("activate", self._on_export_toml_action)
        ag.add_action(export_toml_action)

        export_sh_action = Gio.SimpleAction.new_stateful(
            "export-sh", GLib.VariantType.new("s"), GLib.Variant("s", "")
        )
        export_sh_action.connect("activate", self._on_export_sh_action)
        ag.add_action(export_sh_action)

        row.insert_action_group("profiles", ag)

        # Delete button — user profiles only
        if not is_preset:
            delete_btn = Gtk.Button()
            delete_btn.set_icon_name("user-trash-symbolic")
            delete_btn.set_tooltip_text("delete profile")
            delete_btn.add_css_class("flat")
            delete_btn.add_css_class("error")
            delete_btn.set_valign(Gtk.Align.CENTER)
            delete_btn.connect("clicked", self._on_delete_profile, profile.name)
            row.add_suffix(delete_btn)

        return row

    # ---------------------------------------------------------------- actions

    def _on_apply_profile(self, _btn, profile) -> None:
        old_name = self._settings.get_string("current-preset") if self._settings else ""

        def apply():
            if old_name and old_name != profile.name:
                old = self._ps.get_profile(old_name)
                if old:
                    self._ps.reset_orphaned_shortcuts(old, profile)
            self._ps.apply_profile(profile)
            if profile.name in ("hyprland-style",):
                self._gs.setup_workspaces_for_hyprland()
            if self._settings:
                self._settings.set_string("current-preset", profile.name)
                self._settings.set_boolean("tiling-enabled", profile.name != "vanilla-gnome")
            GLib.idle_add(self._after_apply, profile.name, old_name)

        GLib.Thread.new("profiles-apply", apply)

    def _after_apply(self, name: str, old_name: str) -> bool:
        self._on_reload()
        self._populate()
        self._on_toast(f"applied: {self._display_name(name)}", None, None)
        return False

    def _on_save_current(self, _btn) -> None:
        dialog = Adw.AlertDialog()
        dialog.set_heading("save current state")
        dialog.set_body("name this snapshot of your current shortcuts.")
        dialog.add_response("cancel", "cancel")
        dialog.add_response("save", "save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(8)

        name_entry = Gtk.Entry()
        name_entry.set_placeholder_text("e.g. work-laptop, home-desktop")
        name_entry.set_activates_default(True)
        box.append(name_entry)

        desc_entry = Gtk.Entry()
        desc_entry.set_placeholder_text("description (optional)")
        box.append(desc_entry)

        dialog.set_extra_child(box)
        dialog.connect("response", self._on_save_dialog_response, name_entry, desc_entry)
        dialog.present(self._window)

    def _on_save_dialog_response(
        self, dialog, response, name_entry: Gtk.Entry, desc_entry: Gtk.Entry
    ) -> None:
        if response != "save":
            return
        name = name_entry.get_text().strip()
        if not name:
            return
        desc = desc_entry.get_text().strip()
        # Sanitise name for filename
        safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-")
        if not safe_name:
            safe_name = "my-profile"

        def save():
            self._ps.capture_current_state(safe_name, desc)
            GLib.idle_add(self._after_save, name)

        GLib.Thread.new("profiles-save", save)

    def _after_save(self, display_name: str) -> bool:
        self._populate()
        self._on_toast(f"saved: {display_name}", None, None)
        return False

    def _on_delete_profile(self, _btn, name: str) -> None:
        dialog = Adw.AlertDialog()
        dialog.set_heading("delete profile?")
        dialog.set_body(f'"{self._display_name(name)}" will be permanently removed.')
        dialog.add_response("cancel", "cancel")
        dialog.add_response("delete", "delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda d, r: self._do_delete(name) if r == "delete" else None)
        dialog.present(self._window)

    def _do_delete(self, name: str) -> None:
        self._ps.delete_profile(name)
        self._populate()
        self._on_toast(f"deleted: {self._display_name(name)}", None, None)

    def _on_import(self, _btn) -> None:
        fd = Gtk.FileDialog()
        fd.set_title("import profile")
        fd.set_modal(True)

        toml_filter = Gtk.FileFilter()
        toml_filter.set_name("toml profiles (*.toml)")
        toml_filter.add_pattern("*.toml")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(toml_filter)
        fd.set_filters(filters)

        fd.open(self._window, None, self._on_import_file_chosen)

    def _on_import_file_chosen(self, fd: Gtk.FileDialog, result) -> None:
        try:
            gfile = fd.open_finish(result)
        except Exception:
            return
        path = Path(gfile.get_path())
        try:
            profile = self._ps.import_profile(path)
            self._populate()
            self._on_toast(f"imported: {self._display_name(profile.name)}", None, None)
        except Exception as e:
            self._on_toast(f"import failed: {e}", None, None)

    def _on_export_toml_action(self, action, param) -> None:
        name = param.get_string()
        profile = self._ps.get_profile(name)
        if not profile:
            return
        self._show_export_dialog(
            profile,
            title="export as toml",
            default_name=f"{profile.name}.toml",
            suffix=".toml",
            filter_name="toml profiles (*.toml)",
            is_script=False,
        )

    def _on_export_sh_action(self, action, param) -> None:
        name = param.get_string()
        profile = self._ps.get_profile(name)
        if not profile:
            return
        self._show_export_dialog(
            profile,
            title="export as shell script",
            default_name=f"{profile.name}-keymaps.sh",
            suffix=".sh",
            filter_name="shell scripts (*.sh)",
            is_script=True,
        )

    def _show_export_dialog(
        self,
        profile,
        *,
        title: str,
        default_name: str,
        suffix: str,
        filter_name: str,
        is_script: bool,
    ) -> None:
        fd = Gtk.FileDialog()
        fd.set_title(title)
        fd.set_modal(True)
        fd.set_initial_name(default_name)

        f = Gtk.FileFilter()
        f.set_name(filter_name)
        f.add_pattern(f"*{suffix}")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        fd.set_filters(filters)

        fd.save(
            self._window,
            None,
            lambda d, r: self._on_export_file_chosen(d, r, profile, is_script),
        )

    def _on_export_file_chosen(self, fd, result, profile, is_script: bool) -> None:
        try:
            gfile = fd.save_finish(result)
        except Exception:
            return
        path = Path(gfile.get_path())
        try:
            if is_script:
                self._ps.export_as_shell_script(profile, path)
                self._on_toast(f"exported shell script: {path.name}", None, None)
            else:
                self._ps.export_profile(profile, path)
                self._on_toast(f"exported: {path.name}", None, None)
        except Exception as e:
            self._on_toast(f"export failed: {e}", None, None)

    # ----------------------------------------------------------------- helpers

    def _display_name(self, name: str) -> str:
        names = {
            "vanilla-gnome": "vanilla gnome",
            "gnome-tiling": "gnome + tiling",
            "hyprland-style": "hyprland style",
        }
        return names.get(name, name.replace("-", " "))
