# SPDX-License-Identifier: GPL-3.0-or-later
"""Zero-friction setup view — tiling, keymap, and keyboard in one screen."""

from __future__ import annotations

from collections.abc import Callable

from gi.repository import Adw, GLib, Gtk

PRESET_META = {
    "vanilla-gnome": {
        "label": "Vanilla GNOME",
        "subtitle": "Default GNOME shortcuts, no tiling keys",
        "tiling": False,
        "hyprland_bundle": False,
    },
    "gnome-tiling": {
        "label": "GNOME + Tiling",
        "subtitle": "Adds tiling extension keymaps to GNOME defaults",
        "tiling": True,
        "hyprland_bundle": False,
    },
    "hyprland-style": {
        "label": "Hyprland Style",
        "subtitle": "Keyboard-centric, vim-nav, workspace numbers, tiling",
        "tiling": True,
        "hyprland_bundle": True,
    },
}


class SetupView(Adw.PreferencesPage):
    """Single-screen setup: tiling manager, keymap, and keyboard config."""

    __gtype_name__ = "SetupView"

    def __init__(
        self,
        gsettings_service,
        profile_service,
        kbd_config,
        tiling_service,
        app_settings,
        on_toast: Callable[[str, str | None, Callable | None], None],
        on_shortcuts_reload: Callable[[], None],
    ) -> None:
        super().__init__()
        self._gs = gsettings_service
        self._profiles = profile_service
        self._kbd = kbd_config
        self._tiling = tiling_service
        self._settings = app_settings
        self._on_toast = on_toast
        self._on_reload = on_shortcuts_reload
        self._loading = True
        self._preset_radios: dict[str, Gtk.CheckButton] = {}

        self._build_ui()
        GLib.idle_add(self._load_state)

    # ------------------------------------------------------------------ build

    def _build_ui(self) -> None:
        self.set_title("Setup")

        # ── Tiling Manager ────────────────────────────────────────────────
        tiling_group = Adw.PreferencesGroup()
        tiling_group.set_title("Tiling Manager")
        tiling_group.set_description("Snap and auto-resize windows side-by-side")
        self.add(tiling_group)

        # Status row (read-only)
        self._tiling_status_row = Adw.ActionRow()
        self._tiling_status_row.set_title("Tiling Assistant")
        self._tiling_status_row.set_subtitle("Checking…")
        self._tiling_status_icon = Gtk.Image()
        self._tiling_status_row.add_suffix(self._tiling_status_icon)
        tiling_group.add(self._tiling_status_row)

        # Tile groups (auto-resize adjacent windows)
        self._tile_groups_row = Adw.SwitchRow()
        self._tile_groups_row.set_title("Tile Groups")
        self._tile_groups_row.set_subtitle("Resize adjacent tiled windows together")
        self._tile_groups_row.connect("notify::active", self._on_tile_groups_toggled)
        tiling_group.add(self._tile_groups_row)

        # Raise group together
        self._raise_group_row = Adw.SwitchRow()
        self._raise_group_row.set_title("Raise Group Together")
        self._raise_group_row.set_subtitle("Focusing one tiled window raises its group")
        self._raise_group_row.connect("notify::active", self._on_raise_group_toggled)
        tiling_group.add(self._raise_group_row)

        # ── Keymap Style ──────────────────────────────────────────────────
        keymap_group = Adw.PreferencesGroup()
        keymap_group.set_title("Keymap Style")
        keymap_group.set_description("Choose once — applied immediately")
        self.add(keymap_group)

        first_radio: Gtk.CheckButton | None = None
        for key, meta in PRESET_META.items():
            row = Adw.ActionRow()
            row.set_title(meta["label"])
            row.set_subtitle(meta["subtitle"])
            row.set_activatable(True)

            radio = Gtk.CheckButton()
            radio.set_valign(Gtk.Align.CENTER)
            if first_radio:
                radio.set_group(first_radio)
            else:
                first_radio = radio
            row.add_suffix(radio)
            row.set_activatable_widget(radio)
            radio.connect("notify::active", self._on_preset_radio_toggled, key)
            self._preset_radios[key] = radio

            if meta["hyprland_bundle"]:
                badge = Gtk.Label(label="Recommended")
                badge.add_css_class("accent")
                badge.add_css_class("caption")
                badge.set_valign(Gtk.Align.CENTER)
                row.add_prefix(badge)

            keymap_group.add(row)

        # ── Keyboard Hardware ─────────────────────────────────────────────
        kbd_group = Adw.PreferencesGroup()
        kbd_group.set_title("Keyboard")
        self.add(kbd_group)

        self._caps_row = Adw.ComboRow()
        self._caps_row.set_title("Caps Lock key")
        caps_model = Gtk.StringList()
        for label in ("Caps Lock", "Escape", "Control"):
            caps_model.append(label)
        self._caps_row.set_model(caps_model)
        self._caps_row.connect("notify::selected", self._on_caps_selected)
        kbd_group.add(self._caps_row)

    # ------------------------------------------------------------------ state

    def _load_state(self) -> bool:
        self._loading = True

        # Tiling status
        try:
            tiling_info = self._tiling.detect_status()
            from dailydriver.services.tiling_service import TilingStatus

            if tiling_info.status == TilingStatus.TILING_ASSISTANT:
                self._tiling_status_row.set_subtitle("Active")
                self._tiling_status_icon.set_from_icon_name("emblem-ok-symbolic")
                self._tiling_status_icon.add_css_class("success")
            else:
                self._tiling_status_row.set_subtitle("Not installed — install from GNOME Extensions")
                self._tiling_status_icon.set_from_icon_name("dialog-warning-symbolic")
                self._tiling_status_icon.add_css_class("warning")
                self._tile_groups_row.set_sensitive(False)
                self._raise_group_row.set_sensitive(False)
        except Exception:
            pass

        # TA settings
        try:
            ta = self._tiling.get_ta_settings()
            if ta:
                self._tile_groups_row.set_active(ta.get("tile_groups_enabled", True))
                self._raise_group_row.set_active(ta.get("raise_group", True))
        except Exception:
            pass

        # Current preset
        if self._settings:
            current = self._settings.get_string("current-preset")
            if current in self._preset_radios:
                self._preset_radios[current].set_active(True)

        # Caps Lock
        try:
            from dailydriver.services.keyboard_config_service import CapsLockBehavior

            caps = self._kbd.get_caps_lock_behavior()
            idx = {
                CapsLockBehavior.CAPS_LOCK: 0,
                CapsLockBehavior.ESCAPE: 1,
                CapsLockBehavior.CTRL: 2,
            }.get(caps, 0)
            self._caps_row.set_selected(idx)
        except Exception:
            pass

        self._loading = False
        return False

    # ---------------------------------------------------------------- handlers

    def _on_tile_groups_toggled(self, row: Adw.SwitchRow, _param) -> None:
        if self._loading:
            return
        enabled = row.get_active()
        try:
            self._tiling.set_tile_groups(enabled)
        except Exception:
            pass

    def _on_raise_group_toggled(self, row: Adw.SwitchRow, _param) -> None:
        if self._loading:
            return
        enabled = row.get_active()
        try:
            self._tiling.set_raise_group(enabled)
        except Exception:
            pass

    def _on_preset_radio_toggled(self, radio: Gtk.CheckButton, _param, key: str) -> None:
        if self._loading or not radio.get_active():
            return
        self._apply_preset(key)

    def _apply_preset(self, key: str) -> None:
        meta = PRESET_META.get(key, {})
        label = meta.get("label", key)
        is_hyprland = meta.get("hyprland_bundle", False)

        # Remember previous state for undo
        old_key = self._settings.get_string("current-preset") if self._settings else ""
        old_tiling = self._settings.get_boolean("tiling-enabled") if self._settings else True

        def do_apply():
            profile = self._profiles.get_profile(key)
            if not profile:
                return

            # Reset orphaned shortcuts from previous preset
            if old_key and old_key != key:
                old_profile = self._profiles.get_profile(old_key)
                if old_profile:
                    self._profiles.reset_orphaned_shortcuts(old_profile, profile)

            # Apply keymap preset
            self._profiles.apply_profile(profile)

            if is_hyprland:
                # Full Hyprland bundle: 10 workspaces + TA defaults
                self._gs.setup_workspaces_for_hyprland()
                self._tiling.apply_hyprland_tiling_settings()

            # Persist app setting
            if self._settings:
                self._settings.set_string("current-preset", key)
                self._settings.set_boolean("tiling-enabled", meta.get("tiling", False))

            GLib.idle_add(self._after_apply, label, old_key, old_tiling, is_hyprland)

        GLib.Thread.new("setup-apply-preset", do_apply)

    def _after_apply(
        self, label: str, old_key: str, old_tiling: bool, was_hyprland: bool
    ) -> bool:
        self._on_reload()

        def undo():
            if old_key:
                self._loading = True
                if old_key in self._preset_radios:
                    self._preset_radios[old_key].set_active(True)
                self._loading = False
                self._apply_preset(old_key)
                if was_hyprland and old_key != "hyprland-style":
                    self._gs.restore_default_workspaces()

        self._on_toast(f"Applied: {label}", "Undo", undo)
        return False

    def _on_caps_selected(self, row: Adw.ComboRow, _param) -> None:
        if self._loading:
            return
        from dailydriver.services.keyboard_config_service import CapsLockBehavior

        behaviors = [CapsLockBehavior.CAPS_LOCK, CapsLockBehavior.ESCAPE, CapsLockBehavior.CTRL]
        idx = row.get_selected()
        if 0 <= idx < len(behaviors):
            try:
                self._kbd.set_caps_lock_behavior(behaviors[idx])
            except Exception:
                pass
