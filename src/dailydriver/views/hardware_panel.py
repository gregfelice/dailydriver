# SPDX-License-Identifier: GPL-3.0-or-later
"""Hardware configuration panel for Mac keyboards."""

from gi.repository import Adw, GLib, GObject, Gtk

from dailydriver.models import DetectedKeyboard, FnMode, MacKeyboardConfig
from dailydriver.services.hardware_service import HardwareService
from dailydriver.services.hid_apple_service import HidAppleService


class HardwarePanel(Adw.NavigationPage):
    """Panel for configuring keyboard hardware settings."""

    __gtype_name__ = "HardwarePanel"

    __gsignals__ = {
        "config-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),  # MacKeyboardConfig
        ),
    }

    def __init__(self) -> None:
        super().__init__(title="Hardware", tag="hardware")
        self._hardware_service = HardwareService()
        self._hid_apple_service = HidAppleService()
        self._keyboards: list[DetectedKeyboard] = []

        # Build UI
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        # Header
        header = Adw.HeaderBar()
        header.set_show_back_button(True)

        refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_button.set_tooltip_text("Refresh keyboard list")
        refresh_button.connect("clicked", self._on_refresh)
        header.pack_end(refresh_button)

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

        # Detected keyboards section
        keyboards_group = Adw.PreferencesGroup()
        keyboards_group.set_title("Detected Keyboards")
        self._keyboards_list = Gtk.ListBox()
        self._keyboards_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._keyboards_list.add_css_class("boxed-list")
        keyboards_group.add(self._keyboards_list)
        self._content_box.append(keyboards_group)

        # Mac keyboard settings section (only shown if Mac keyboard detected)
        self._mac_group = Adw.PreferencesGroup()
        self._mac_group.set_title("Apple Keyboard Settings")
        self._mac_group.set_description("Configure hid-apple kernel module")
        self._mac_group.set_visible(False)
        self._content_box.append(self._mac_group)

        self._build_mac_settings()

        # Load keyboards
        GLib.idle_add(self._load_keyboards)

    def _build_mac_settings(self) -> None:
        """Build Mac keyboard settings UI."""
        # Fn mode selector
        fn_row = Adw.ComboRow()
        fn_row.set_title("Function Keys Mode")
        fn_row.set_subtitle("Choose default behavior for F1-F12")

        fn_model = Gtk.StringList.new(["Media keys (default)", "Function keys", "Disabled"])
        fn_row.set_model(fn_model)
        fn_row.set_selected(0)
        fn_row.connect("notify::selected", self._on_fn_mode_changed)
        self._fn_row = fn_row
        self._mac_group.add(fn_row)

        # Swap Option/Command
        swap_row = Adw.SwitchRow()
        swap_row.set_title("Swap Option and Command")
        swap_row.set_subtitle("Match standard PC Alt/Super layout")
        swap_row.connect("notify::active", self._on_swap_opt_cmd_changed)
        self._swap_row = swap_row
        self._mac_group.add(swap_row)

        # Swap Fn/Ctrl
        fn_ctrl_row = Adw.SwitchRow()
        fn_ctrl_row.set_title("Swap Fn and Left Control")
        fn_ctrl_row.set_subtitle("Put Fn where Ctrl usually is")
        fn_ctrl_row.connect("notify::active", self._on_swap_fn_ctrl_changed)
        self._fn_ctrl_row = fn_ctrl_row
        self._mac_group.add(fn_ctrl_row)

        # Apply button
        apply_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        apply_box.set_halign(Gtk.Align.END)
        apply_box.set_margin_top(12)

        self._apply_button = Gtk.Button(label="Apply Changes")
        self._apply_button.add_css_class("suggested-action")
        self._apply_button.connect("clicked", self._on_apply_mac_settings)
        apply_box.append(self._apply_button)

        self._mac_group.add(apply_box)

    def _load_keyboards(self) -> bool:
        """Load and display detected keyboards."""
        # Clear existing
        while child := self._keyboards_list.get_first_child():
            self._keyboards_list.remove(child)

        self._keyboards = list(self._hardware_service.list_keyboards())
        has_mac = False

        for kb in self._keyboards:
            row = Adw.ActionRow()
            row.set_title(kb.display_name)
            row.set_subtitle(f"USB ID: {kb.usb_id}")

            # Add type badges
            if kb.is_mac:
                badge = Gtk.Label(label="Apple")
                badge.add_css_class("profile-indicator")
                row.add_suffix(badge)
                has_mac = True

            if kb.is_bluetooth:
                bt_icon = Gtk.Image.new_from_icon_name("bluetooth-symbolic")
                row.add_suffix(bt_icon)

            self._keyboards_list.append(row)

        # Show/hide Mac settings
        self._mac_group.set_visible(has_mac and self._hid_apple_service.is_module_loaded())

        # Load current Mac settings if available
        if has_mac:
            self._load_mac_settings()

        if not self._keyboards:
            # Show empty state
            row = Adw.ActionRow()
            row.set_title("No keyboards detected")
            row.set_subtitle("Connect a keyboard and click refresh")
            self._keyboards_list.append(row)

        return False

    def _load_mac_settings(self) -> None:
        """Load current hid-apple settings."""
        config = self._hid_apple_service.get_current_config()
        if not config:
            return

        # Update UI
        fn_index = {FnMode.MEDIA: 0, FnMode.FKEYS: 1, FnMode.DISABLED: 2}.get(config.fn_mode, 0)
        self._fn_row.set_selected(fn_index)
        self._swap_row.set_active(config.swap_opt_cmd)
        self._fn_ctrl_row.set_active(config.swap_fn_leftctrl)

    def _on_refresh(self, button: Gtk.Button) -> None:
        """Refresh keyboard list."""
        self._load_keyboards()

    def _on_fn_mode_changed(self, row: Adw.ComboRow, pspec) -> None:
        """Handle Fn mode change."""
        pass  # Will apply on button click

    def _on_swap_opt_cmd_changed(self, row: Adw.SwitchRow, pspec) -> None:
        """Handle swap option/command change."""
        pass  # Will apply on button click

    def _on_swap_fn_ctrl_changed(self, row: Adw.SwitchRow, pspec) -> None:
        """Handle swap Fn/Ctrl change."""
        pass  # Will apply on button click

    def _on_apply_mac_settings(self, button: Gtk.Button) -> None:
        """Apply Mac keyboard settings."""
        fn_modes = [FnMode.MEDIA, FnMode.FKEYS, FnMode.DISABLED]
        config = MacKeyboardConfig(
            fn_mode=fn_modes[self._fn_row.get_selected()],
            swap_opt_cmd=self._swap_row.get_active(),
            swap_fn_leftctrl=self._fn_ctrl_row.get_active(),
        )

        if self._hid_apple_service.apply_config(config):
            self.emit("config-changed", config)
