# SPDX-License-Identifier: GPL-3.0-or-later
"""Keyboard setup banner for hardware detection and configuration."""

from gi.repository import GLib, GObject, Gtk

from dailydriver.models import KeyboardType
from dailydriver.services.hardware_service import HardwareService
from dailydriver.services.hid_apple_service import HidAppleService
from dailydriver.services.keyboard_config_service import (
    KeyboardConfigService,
)


class KeyboardSetupBanner(Gtk.Box):
    """Banner for keyboard hardware setup when Mac keyboard detected."""

    __gtype_name__ = "KeyboardSetupBanner"

    __gsignals__ = {
        "keyboard-configured": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str,),  # Configuration type applied
        ),
    }

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._config_service = KeyboardConfigService()
        self._hardware_service = HardwareService()
        self._hid_apple_service = HidAppleService()
        self._detected_mac = False

        self.add_css_class("card")
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the banner UI."""
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        self.append(content)

        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        header_box.set_halign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name("input-keyboard-symbolic")
        icon.set_icon_size(Gtk.IconSize.LARGE)
        icon.add_css_class("dim-label")
        header_box.append(icon)

        self._title = Gtk.Label(label="Apple Keyboard Detected")
        self._title.add_css_class("title-2")
        header_box.append(self._title)

        content.append(header_box)

        # Description
        self._description = Gtk.Label(
            label="Configure your Mac keyboard for Linux.\n"
            "Choose how Command and Option keys should behave."
        )
        self._description.set_wrap(True)
        self._description.set_justify(Gtk.Justification.CENTER)
        self._description.add_css_class("dim-label")
        content.append(self._description)

        # Options
        options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        options_box.set_halign(Gtk.Align.CENTER)
        content.append(options_box)

        # Option 1: Mac-like (keep Cmd = Super)
        self._mac_like_button = Gtk.Button()
        mac_like_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        mac_like_box.set_margin_start(12)
        mac_like_box.set_margin_end(12)
        mac_like_box.set_margin_top(8)
        mac_like_box.set_margin_bottom(8)
        mac_like_label = Gtk.Label(label="Mac-like")
        mac_like_label.add_css_class("heading")
        mac_like_box.append(mac_like_label)
        mac_like_desc = Gtk.Label(label="⌘ Cmd = Super (launcher)  |  ⌥ Opt = Alt")
        mac_like_desc.add_css_class("dim-label")
        mac_like_desc.add_css_class("caption")
        mac_like_box.append(mac_like_desc)
        self._mac_like_button.set_child(mac_like_box)
        self._mac_like_button.connect("clicked", self._on_mac_like)
        options_box.append(self._mac_like_button)

        # Option 2: PC-like (swap Cmd/Opt)
        self._pc_like_button = Gtk.Button()
        self._pc_like_button.add_css_class("suggested-action")
        pc_like_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        pc_like_box.set_margin_start(12)
        pc_like_box.set_margin_end(12)
        pc_like_box.set_margin_top(8)
        pc_like_box.set_margin_bottom(8)
        pc_like_label = Gtk.Label(label="PC-like (Recommended)")
        pc_like_label.add_css_class("heading")
        pc_like_box.append(pc_like_label)
        pc_like_desc = Gtk.Label(label="⌘ Cmd = Alt  |  ⌥ Opt = Super (like PC keyboard)")
        pc_like_desc.add_css_class("dim-label")
        pc_like_desc.add_css_class("caption")
        pc_like_box.append(pc_like_desc)
        self._pc_like_button.set_child(pc_like_box)
        self._pc_like_button.connect("clicked", self._on_pc_like)
        options_box.append(self._pc_like_button)

        # Dismiss
        dismiss_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        dismiss_box.set_halign(Gtk.Align.CENTER)
        dismiss_box.set_margin_top(8)
        dismiss_button = Gtk.Button(label="Configure Later")
        dismiss_button.add_css_class("flat")
        dismiss_button.connect("clicked", self._on_dismiss)
        dismiss_box.append(dismiss_button)
        content.append(dismiss_box)

    def check_and_update(self) -> bool:
        """Check for Mac keyboard and update visibility.

        Returns True if banner should be shown.
        """
        # Check if we have a Mac keyboard
        keyboards = list(self._hardware_service.list_keyboards())
        mac_keyboards = [kb for kb in keyboards if kb.is_mac]

        if not mac_keyboards:
            self.set_visible(False)
            return False

        self._detected_mac = True

        # Check if already configured (hid_apple module loaded with non-default settings)
        if self._hid_apple_service.is_module_loaded():
            config = self._hid_apple_service.get_current_config()
            if config and config.swap_opt_cmd:
                # Already configured with swap
                self.set_visible(False)
                return False

        # Check current keyboard type setting
        current_type = self._config_service.get_keyboard_type()
        if current_type.is_apple:
            # Already set as Apple keyboard, don't prompt again
            self.set_visible(False)
            return False

        # Show the banner
        kb_name = mac_keyboards[0].display_name
        self._title.set_label("Apple Keyboard Detected")
        self._description.set_label(
            f"Found: {kb_name}\nConfigure how Command and Option keys should behave."
        )

        self.set_visible(True)
        return True

    def _on_mac_like(self, button: Gtk.Button) -> None:
        """Keep Mac-like layout (Cmd = Super)."""
        self._apply_config(swap_cmd_opt=False)

    def _on_pc_like(self, button: Gtk.Button) -> None:
        """Apply PC-like layout (swap Cmd/Opt)."""
        self._apply_config(swap_cmd_opt=True)

    def _apply_config(self, swap_cmd_opt: bool) -> None:
        """Apply the keyboard configuration."""
        self._mac_like_button.set_sensitive(False)
        self._pc_like_button.set_sensitive(False)

        def apply():
            success = True

            # Set global keyboard type to Apple
            self._config_service.set_keyboard_type(KeyboardType.MAC_ANSI)

            # Apply hid_apple settings
            from dailydriver.models import FnMode, MacKeyboardConfig

            config = MacKeyboardConfig(
                fn_mode=FnMode.MEDIA,
                swap_opt_cmd=swap_cmd_opt,
                swap_fn_leftctrl=False,
            )

            if self._hid_apple_service.is_module_loaded():
                success = self._hid_apple_service.apply_config(config)

            GLib.idle_add(self._on_apply_complete, success, swap_cmd_opt)

        GLib.Thread.new("apply-keyboard-config", apply)

    def _on_apply_complete(self, success: bool, swap_cmd_opt: bool) -> None:
        """Handle configuration completion."""
        if success:
            self.set_visible(False)
            config_type = "pc-like" if swap_cmd_opt else "mac-like"
            self.emit("keyboard-configured", config_type)
        else:
            self._mac_like_button.set_sensitive(True)
            self._pc_like_button.set_sensitive(True)

    def _on_dismiss(self, button: Gtk.Button) -> None:
        """Dismiss the banner."""
        self.set_visible(False)
