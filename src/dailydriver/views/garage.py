# SPDX-License-Identifier: GPL-3.0-or-later
"""Garage view - racing game style component configurator."""

from gi.repository import Adw, GLib, GObject, Gtk

from dailydriver.models import DetectedKeyboard
from dailydriver.services.gsettings_service import GSettingsService
from dailydriver.services.hardware_service import HardwareService
from dailydriver.services.keyboard_config_service import CapsLockBehavior, KeyboardConfigService
from dailydriver.views.keyboard_view import KeyboardView


class ComponentCard(Gtk.Frame):
    """A component selection card in the garage."""

    __gtype_name__ = "ComponentCard"

    __gsignals__ = {
        "selection-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str,),  # Selected option ID
        ),
    }

    def __init__(
        self,
        title: str,
        icon: str,
        options: list[tuple[str, str, str]],  # (id, name, subtitle)
        multi_select: bool = False,
    ) -> None:
        super().__init__()
        self._options = options
        self._multi_select = multi_select
        self._checks: dict[str, Gtk.CheckButton] = {}

        self.add_css_class("card")
        self.set_margin_start(6)
        self.set_margin_end(6)
        self.set_margin_top(6)
        self.set_margin_bottom(6)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        self.set_child(content)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon_widget = Gtk.Image.new_from_icon_name(icon)
        icon_widget.add_css_class("dim-label")
        header.append(icon_widget)

        title_label = Gtk.Label(label=title)
        title_label.add_css_class("heading")
        title_label.set_xalign(0)
        header.append(title_label)
        content.append(header)

        # Options
        first_check = None
        for opt_id, opt_name, opt_subtitle in options:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

            check = Gtk.CheckButton()
            if not multi_select:
                if first_check is None:
                    first_check = check
                else:
                    check.set_group(first_check)
            check.connect("toggled", self._on_toggled, opt_id)
            row.append(check)
            self._checks[opt_id] = check

            label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            name_label = Gtk.Label(label=opt_name)
            name_label.set_xalign(0)
            label_box.append(name_label)

            if opt_subtitle:
                sub_label = Gtk.Label(label=opt_subtitle)
                sub_label.set_xalign(0)
                sub_label.add_css_class("dim-label")
                sub_label.add_css_class("caption")
                label_box.append(sub_label)

            row.append(label_box)
            content.append(row)

    def _on_toggled(self, check: Gtk.CheckButton, opt_id: str) -> None:
        if check.get_active():
            self.emit("selection-changed", opt_id)

    def set_active(self, opt_id: str) -> None:
        """Set the active option."""
        if opt_id in self._checks:
            self._checks[opt_id].set_active(True)

    def get_active(self) -> str | None:
        """Get the active option ID."""
        for opt_id, check in self._checks.items():
            if check.get_active():
                return opt_id
        return None


class ToggleCard(Gtk.Frame):
    """A simple on/off toggle card."""

    __gtype_name__ = "ToggleCard"

    __gsignals__ = {
        "toggled": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (bool,),
        ),
    }

    def __init__(self, title: str, icon: str, subtitle: str = "") -> None:
        super().__init__()

        self.add_css_class("card")
        self.set_margin_start(6)
        self.set_margin_end(6)
        self.set_margin_top(6)
        self.set_margin_bottom(6)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        self.set_child(content)

        # Header with icon and title
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon_widget = Gtk.Image.new_from_icon_name(icon)
        icon_widget.add_css_class("dim-label")
        header.append(icon_widget)

        title_label = Gtk.Label(label=title)
        title_label.add_css_class("heading")
        title_label.set_xalign(0)
        title_label.set_hexpand(True)
        header.append(title_label)

        self._switch = Gtk.Switch()
        self._switch.set_valign(Gtk.Align.CENTER)
        self._switch.connect("state-set", self._on_state_set)
        header.append(self._switch)

        content.append(header)

        if subtitle:
            sub = Gtk.Label(label=subtitle)
            sub.set_xalign(0)
            sub.add_css_class("dim-label")
            sub.add_css_class("caption")
            sub.set_wrap(True)
            content.append(sub)

    def _on_state_set(self, switch: Gtk.Switch, state: bool) -> bool:
        self.emit("toggled", state)
        return False

    def set_active(self, active: bool) -> None:
        self._switch.set_active(active)

    def get_active(self) -> bool:
        return self._switch.get_active()


class GarageView(Gtk.Box):
    """Main garage view with keyboard and component cards."""

    __gtype_name__ = "GarageView"

    __gsignals__ = {
        "config-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (),
        ),
    }

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._kbd_config = KeyboardConfigService()
        self._gsettings = GSettingsService()
        self._hardware = HardwareService()
        self._detected_keyboard: DetectedKeyboard | None = None
        self._loading = True

        # Detect keyboard first
        self._detect_keyboard()

        self._build_ui()
        GLib.idle_add(self._load_current_state)

    def _detect_keyboard(self) -> None:
        """Detect connected keyboards."""
        keyboards = list(self._hardware.list_keyboards())

        # Prefer Mac keyboards, then external keyboards, then internal
        mac_kbs = [kb for kb in keyboards if kb.is_mac]
        external_kbs = [kb for kb in keyboards if not kb.is_internal]
        internal_kbs = [kb for kb in keyboards if kb.is_internal]

        if mac_kbs:
            self._detected_keyboard = mac_kbs[0]
        elif external_kbs:
            self._detected_keyboard = external_kbs[0]
        elif internal_kbs:
            self._detected_keyboard = internal_kbs[0]
        else:
            self._detected_keyboard = None

    def _build_ui(self) -> None:
        """Build the garage UI."""
        # Scrolled container
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        self.append(scroll)

        # Main content with clamp
        clamp = Adw.Clamp()
        clamp.set_maximum_size(1000)
        clamp.set_margin_start(12)
        clamp.set_margin_end(12)
        clamp.set_margin_top(12)
        clamp.set_margin_bottom(12)
        scroll.set_child(clamp)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(main_box)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header.set_halign(Gtk.Align.CENTER)

        title = Gtk.Label(label="🏎️ The Garage")
        title.add_css_class("title-1")
        header.append(title)

        subtitle = Gtk.Label(label="Tune your daily driver")
        subtitle.add_css_class("dim-label")
        header.append(subtitle)

        main_box.append(header)

        # Center section: keyboard with flanking components
        center_section = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        center_section.set_halign(Gtk.Align.CENTER)
        center_section.set_valign(Gtk.Align.CENTER)
        center_section.set_hexpand(True)
        main_box.append(center_section)

        # Left components
        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left_col.set_valign(Gtk.Align.CENTER)
        center_section.append(left_col)

        # Tiling
        self._tiling_card = ComponentCard(
            "Tiling",
            "view-grid-symbolic",
            [
                ("none", "None", "Stock GNOME"),
                ("tiling-assistant", "Tiling Assistant", "Smart window tiling"),
            ],
        )
        self._tiling_card.connect("selection-changed", self._on_tiling_changed)
        left_col.append(self._tiling_card)

        # Terminal
        self._terminal_card = ComponentCard(
            "Terminal",
            "utilities-terminal-symbolic",
            [
                ("gnome-terminal", "GNOME Terminal", "Stock experience"),
                ("alacritty", "Alacritty", "GPU-accelerated"),
                ("kitty", "Kitty", "Feature-rich"),
            ],
        )
        self._terminal_card.connect("selection-changed", self._on_terminal_changed)
        left_col.append(self._terminal_card)

        # Center: Keyboard with detected hardware info (borderless, centered)
        kbd_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        kbd_container.set_halign(Gtk.Align.CENTER)
        kbd_container.set_valign(Gtk.Align.CENTER)
        kbd_container.set_margin_start(24)
        kbd_container.set_margin_end(24)
        kbd_container.set_margin_top(16)
        kbd_container.set_margin_bottom(16)

        kbd_box = kbd_container  # Alias for compatibility with the rest of the code

        # "Your Setup" badge with detected keyboard
        setup_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        setup_header.set_halign(Gtk.Align.CENTER)

        if self._detected_keyboard:
            # Brand icon based on detection
            brand_icons = {
                "apple": "input-keyboard-symbolic",  # TODO: custom Apple icon
                "logitech": "input-keyboard-symbolic",
                "razer": "input-keyboard-symbolic",
                "corsair": "input-keyboard-symbolic",
                "generic": "input-keyboard-symbolic",
            }
            brand_icon = brand_icons.get(
                self._detected_keyboard.brand_id, "input-keyboard-symbolic"
            )

            icon = Gtk.Image.new_from_icon_name(brand_icon)
            if self._detected_keyboard.is_mac:
                icon.add_css_class("accent")  # Highlight Apple keyboards
            setup_header.append(icon)

            # Keyboard name and form factor
            kbd_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

            kbd_name = Gtk.Label(label=self._detected_keyboard.display_name)
            kbd_name.add_css_class("heading")
            kbd_name.set_xalign(0)
            kbd_info.append(kbd_name)

            # Details: form factor, connection type
            details_parts = [self._detected_keyboard.form_factor]
            if self._detected_keyboard.is_bluetooth:
                details_parts.append("Bluetooth")
            if self._detected_keyboard.is_mac:
                details_parts.append("Apple")
            details_text = " · ".join(details_parts)

            kbd_details = Gtk.Label(label=details_text)
            kbd_details.add_css_class("dim-label")
            kbd_details.add_css_class("caption")
            kbd_details.set_xalign(0)
            kbd_info.append(kbd_details)

            setup_header.append(kbd_info)

            # USB ID badge
            usb_badge = Gtk.Label(label=self._detected_keyboard.usb_id)
            usb_badge.add_css_class("dim-label")
            usb_badge.add_css_class("caption")
            usb_badge.add_css_class("monospace")
            setup_header.append(usb_badge)
        else:
            # No keyboard detected
            icon = Gtk.Image.new_from_icon_name("input-keyboard-symbolic")
            icon.add_css_class("dim-label")
            setup_header.append(icon)

            no_kbd = Gtk.Label(label="No keyboard detected")
            no_kbd.add_css_class("dim-label")
            setup_header.append(no_kbd)

        kbd_box.append(setup_header)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        kbd_box.append(sep)

        # Create keyboard view with appropriate layout for detected keyboard
        kbd_layout_type = None
        if self._detected_keyboard:
            kbd_layout_type = self._detected_keyboard.suggested_layout()

        self._keyboard_view = KeyboardView(keyboard_type=kbd_layout_type)
        self._keyboard_view.set_size_request(500, 180)
        self._keyboard_view.set_halign(Gtk.Align.CENTER)
        kbd_box.append(self._keyboard_view)

        # Mouse/trackpad below keyboard
        pointer_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pointer_row.set_halign(Gtk.Align.CENTER)
        pointer_icon = Gtk.Image.new_from_icon_name("input-mouse-symbolic")
        pointer_icon.set_opacity(0.5)
        pointer_row.append(pointer_icon)
        pointer_label = Gtk.Label(label="Mouse / Trackpad")
        pointer_label.set_opacity(0.5)
        pointer_label.add_css_class("caption")
        pointer_row.append(pointer_label)
        kbd_box.append(pointer_row)

        center_section.append(kbd_container)

        # Right components
        right_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right_col.set_valign(Gtk.Align.CENTER)
        center_section.append(right_col)

        # Layout
        self._layout_card = ComponentCard(
            "Layout",
            "input-keyboard-symbolic",
            [
                ("pc", "PC Standard", "Ctrl-Alt-Super"),
                ("mac", "Mac Style", "Cmd↔Option swap"),
            ],
        )
        self._layout_card.connect("selection-changed", self._on_layout_changed)
        right_col.append(self._layout_card)

        # Pointer
        self._pointer_card = ComponentCard(
            "Pointer",
            "input-mouse-symbolic",
            [
                ("comfort", "Comfort", "Slow & precise"),
                ("standard", "Standard", "Balanced"),
                ("sport", "Sport", "Fast & responsive"),
            ],
        )
        self._pointer_card.connect("selection-changed", self._on_pointer_changed)
        right_col.append(self._pointer_card)

        # Bottom row: more components
        bottom_section = Gtk.FlowBox()
        bottom_section.set_selection_mode(Gtk.SelectionMode.NONE)
        bottom_section.set_max_children_per_line(4)
        bottom_section.set_min_children_per_line(2)
        bottom_section.set_homogeneous(True)
        bottom_section.set_column_spacing(0)
        bottom_section.set_row_spacing(0)
        main_box.append(bottom_section)

        # Caps Lock
        self._caps_card = ComponentCard(
            "Caps Lock",
            "preferences-desktop-keyboard-symbolic",
            [
                ("stock", "Caps Lock", "Default behavior"),
                ("escape", "Escape", "Vim power move"),
                ("ctrl", "Control", "Ergonomic ctrl"),
            ],
        )
        self._caps_card.connect("selection-changed", self._on_caps_changed)
        bottom_section.append(self._caps_card)

        # File Manager
        self._files_card = ComponentCard(
            "File Manager",
            "system-file-manager-symbolic",
            [
                ("nautilus", "Files", "GNOME default"),
                ("nemo", "Nemo", "More features"),
                ("thunar", "Thunar", "Lightweight"),
            ],
        )
        self._files_card.connect("selection-changed", self._on_files_changed)
        bottom_section.append(self._files_card)

        # Workspaces
        self._workspace_card = ComponentCard(
            "Workspaces",
            "view-paged-symbolic",
            [
                ("arrows", "Arrow Keys", "Dynamic workspaces"),
                ("numbers", "Super+1-0", "10 fixed workspaces"),
            ],
        )
        self._workspace_card.connect("selection-changed", self._on_workspace_changed)
        bottom_section.append(self._workspace_card)

        # Tmux
        self._tmux_card = ToggleCard(
            "tmux Support",
            "utilities-terminal-symbolic",
            "Terminal multiplexer keybindings",
        )
        self._tmux_card.connect("toggled", self._on_tmux_toggled)
        bottom_section.append(self._tmux_card)

    def _load_current_state(self) -> bool:
        """Load current configuration state."""
        self._loading = True

        # Detect tiling
        # TODO: Check if Tiling Assistant is enabled
        self._tiling_card.set_active("none")

        # Detect layout (Mac swap) - auto-detect from keyboard or current setting
        if self._kbd_config.get_apple_swap_cmd_opt():
            self._layout_card.set_active("mac")
        elif self._detected_keyboard and self._detected_keyboard.is_mac:
            # Mac keyboard detected but swap not enabled yet - suggest Mac layout
            self._layout_card.set_active("mac")
        else:
            self._layout_card.set_active("pc")

        # Detect caps lock
        caps = self._kbd_config.get_caps_lock_behavior()
        caps_map = {
            CapsLockBehavior.CAPS_LOCK: "stock",
            CapsLockBehavior.ESCAPE: "escape",
            CapsLockBehavior.CTRL: "ctrl",
        }
        self._caps_card.set_active(caps_map.get(caps, "stock"))

        # Default selections for others
        self._terminal_card.set_active("gnome-terminal")
        self._pointer_card.set_active("standard")
        self._files_card.set_active("nautilus")
        self._workspace_card.set_active("arrows")

        self._loading = False
        return False

    def _on_tiling_changed(self, card: ComponentCard, opt_id: str) -> None:
        if self._loading:
            return
        # TODO: Enable/disable Tiling Assistant extension
        self.emit("config-changed")

    def _on_terminal_changed(self, card: ComponentCard, opt_id: str) -> None:
        if self._loading:
            return
        # TODO: Set preferred terminal
        self.emit("config-changed")

    def _on_layout_changed(self, card: ComponentCard, opt_id: str) -> None:
        if self._loading:
            return

        from dailydriver.models import FnMode, MacKeyboardConfig
        from dailydriver.services.hid_apple_service import HidAppleService

        hid = HidAppleService()
        if hid.is_module_loaded():
            config = MacKeyboardConfig(
                fn_mode=FnMode.MEDIA,
                swap_opt_cmd=(opt_id == "mac"),
            )
            hid.apply_config(config)

        self.emit("config-changed")

    def _on_pointer_changed(self, card: ComponentCard, opt_id: str) -> None:
        if self._loading:
            return

        # Set mouse/touchpad acceleration profile and speed
        try:
            from gi.repository import Gio

            touchpad = Gio.Settings.new("org.gnome.desktop.peripherals.touchpad")
            mouse = Gio.Settings.new("org.gnome.desktop.peripherals.mouse")

            speeds = {"comfort": -0.5, "standard": 0.0, "sport": 0.5}
            speed = speeds.get(opt_id, 0.0)

            touchpad.set_double("speed", speed)
            mouse.set_double("speed", speed)
        except Exception:
            pass

        self.emit("config-changed")

    def _on_caps_changed(self, card: ComponentCard, opt_id: str) -> None:
        if self._loading:
            return

        behavior_map = {
            "stock": CapsLockBehavior.CAPS_LOCK,
            "escape": CapsLockBehavior.ESCAPE,
            "ctrl": CapsLockBehavior.CTRL,
        }
        behavior = behavior_map.get(opt_id, CapsLockBehavior.CAPS_LOCK)
        self._kbd_config.set_caps_lock_behavior(behavior)
        self.emit("config-changed")

    def _on_files_changed(self, card: ComponentCard, opt_id: str) -> None:
        if self._loading:
            return
        # TODO: Set preferred file manager
        self.emit("config-changed")

    def _on_workspace_changed(self, card: ComponentCard, opt_id: str) -> None:
        if self._loading:
            return

        try:
            from gi.repository import Gio

            wm = Gio.Settings.new("org.gnome.desktop.wm.keybindings")
            mutter = Gio.Settings.new("org.gnome.mutter")
            wm_prefs = Gio.Settings.new("org.gnome.desktop.wm.preferences")

            if opt_id == "numbers":
                # Enable 10 fixed workspaces (Hyprland-style)
                mutter.set_boolean("dynamic-workspaces", False)
                wm_prefs.set_int("num-workspaces", 10)

                # Set workspace switching shortcuts (Super+1-9, Super+0 = 10)
                wm.set_strv("switch-to-workspace-1", ["<Super>1"])
                wm.set_strv("switch-to-workspace-2", ["<Super>2"])
                wm.set_strv("switch-to-workspace-3", ["<Super>3"])
                wm.set_strv("switch-to-workspace-4", ["<Super>4"])
                wm.set_strv("switch-to-workspace-5", ["<Super>5"])
                wm.set_strv("switch-to-workspace-6", ["<Super>6"])
                wm.set_strv("switch-to-workspace-7", ["<Super>7"])
                wm.set_strv("switch-to-workspace-8", ["<Super>8"])
                wm.set_strv("switch-to-workspace-9", ["<Super>9"])
                wm.set_strv("switch-to-workspace-10", ["<Super>0"])

                # Set move-to-workspace shortcuts (Super+Shift+1-9, Super+Shift+0 = 10)
                wm.set_strv("move-to-workspace-1", ["<Super><Shift>1"])
                wm.set_strv("move-to-workspace-2", ["<Super><Shift>2"])
                wm.set_strv("move-to-workspace-3", ["<Super><Shift>3"])
                wm.set_strv("move-to-workspace-4", ["<Super><Shift>4"])
                wm.set_strv("move-to-workspace-5", ["<Super><Shift>5"])
                wm.set_strv("move-to-workspace-6", ["<Super><Shift>6"])
                wm.set_strv("move-to-workspace-7", ["<Super><Shift>7"])
                wm.set_strv("move-to-workspace-8", ["<Super><Shift>8"])
                wm.set_strv("move-to-workspace-9", ["<Super><Shift>9"])
                wm.set_strv("move-to-workspace-10", ["<Super><Shift>0"])
            else:  # arrows - use dynamic workspaces
                mutter.set_boolean("dynamic-workspaces", True)

                wm.set_strv("switch-to-workspace-1", ["<Super>Home"])
                wm.set_strv("switch-to-workspace-2", [])
                wm.set_strv("switch-to-workspace-3", [])
                wm.set_strv("switch-to-workspace-4", [])
                wm.set_strv("switch-to-workspace-5", [])
                wm.set_strv("switch-to-workspace-6", [])
                wm.set_strv("switch-to-workspace-7", [])
                wm.set_strv("switch-to-workspace-8", [])
                wm.set_strv("switch-to-workspace-9", [])
                wm.set_strv("switch-to-workspace-10", [])
                wm.set_strv("move-to-workspace-1", ["<Super><Shift>Home"])
                wm.set_strv("move-to-workspace-2", [])
                wm.set_strv("move-to-workspace-3", [])
                wm.set_strv("move-to-workspace-4", [])
                wm.set_strv("move-to-workspace-5", [])
                wm.set_strv("move-to-workspace-6", [])
                wm.set_strv("move-to-workspace-7", [])
                wm.set_strv("move-to-workspace-8", [])
                wm.set_strv("move-to-workspace-9", [])
                wm.set_strv("move-to-workspace-10", [])
        except Exception:
            pass

        self.emit("config-changed")

    def _on_tmux_toggled(self, card: ToggleCard, active: bool) -> None:
        if self._loading:
            return
        # TODO: Configure tmux-friendly keybindings
        self.emit("config-changed")
