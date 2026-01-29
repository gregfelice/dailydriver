# SPDX-License-Identifier: GPL-3.0-or-later
"""Trim packages panel - composable keyboard configuration packages."""

from gi.repository import Adw, GObject, Gtk

from dailydriver.services.gsettings_service import GSettingsService
from dailydriver.services.keyboard_config_service import CapsLockBehavior, KeyboardConfigService


class TrimPackagesPanel(Gtk.Box):
    """Panel for selecting composable keyboard trim packages."""

    __gtype_name__ = "TrimPackagesPanel"

    __gsignals__ = {
        "config-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (),
        ),
    }

    # Trim package definitions
    PACKAGES = {
        # Base packages (mutually exclusive)
        "touring": {
            "name": "Touring",
            "subtitle": "Stock GNOME • smooth & familiar",
            "icon": "driving-symbolic",
            "group": "base",
            "shortcuts": {
                "org.gnome.desktop.wm.keybindings.switch-to-workspace-1": ["<Super>Home"],
                "org.gnome.desktop.wm.keybindings.switch-to-workspace-2": [],
                "org.gnome.desktop.wm.keybindings.switch-to-workspace-3": [],
                "org.gnome.desktop.wm.keybindings.switch-to-workspace-4": [],
            },
        },
        "gt": {
            "name": "GT",
            "subtitle": "Grand Tiling • window management power",
            "icon": "view-grid-symbolic",
            "group": "base",
            "shortcuts": {
                # Tiling shortcuts enabled
                "org.gnome.shell.extensions.tiling-assistant.tile-left-half": ["<Super>Left"],
                "org.gnome.shell.extensions.tiling-assistant.tile-right-half": ["<Super>Right"],
                "org.gnome.shell.extensions.tiling-assistant.tile-topleft-quarter": [
                    "<Super><Control>Left"
                ],
                "org.gnome.shell.extensions.tiling-assistant.tile-topright-quarter": [
                    "<Super><Control>Right"
                ],
                "org.gnome.shell.extensions.tiling-assistant.tile-bottomleft-quarter": [
                    "<Super><Alt>Left"
                ],
                "org.gnome.shell.extensions.tiling-assistant.tile-bottomright-quarter": [
                    "<Super><Alt>Right"
                ],
            },
        },
        # Add-on packages (stackable)
        "turbo": {
            "name": "Turbo",
            "subtitle": "Super+1-4 workspace switching",
            "icon": "speedometer-symbolic",
            "group": "addon",
            "shortcuts": {
                "org.gnome.desktop.wm.keybindings.switch-to-workspace-1": ["<Super>1"],
                "org.gnome.desktop.wm.keybindings.switch-to-workspace-2": ["<Super>2"],
                "org.gnome.desktop.wm.keybindings.switch-to-workspace-3": ["<Super>3"],
                "org.gnome.desktop.wm.keybindings.switch-to-workspace-4": ["<Super>4"],
                "org.gnome.desktop.wm.keybindings.move-to-workspace-1": ["<Super><Shift>1"],
                "org.gnome.desktop.wm.keybindings.move-to-workspace-2": ["<Super><Shift>2"],
                "org.gnome.desktop.wm.keybindings.move-to-workspace-3": ["<Super><Shift>3"],
                "org.gnome.desktop.wm.keybindings.move-to-workspace-4": ["<Super><Shift>4"],
            },
        },
        "cupertino": {
            "name": "Cupertino",
            "subtitle": "Mac keyboard • Cmd↔Option swap",
            "icon": "input-keyboard-symbolic",
            "group": "addon",
            "mac_swap": True,  # Special flag for hid_apple
        },
        "sport": {
            "name": "Sport",
            "subtitle": "Super+Q close • faster shortcuts",
            "icon": "media-playback-start-symbolic",
            "group": "addon",
            "shortcuts": {
                "org.gnome.desktop.wm.keybindings.close": ["<Super>q", "<Alt>F4"],
                "org.gnome.desktop.wm.keybindings.maximize": ["<Super>Up", "<Super>f"],
                "org.gnome.shell.keybindings.show-screenshot-ui": ["Print", "<Super><Shift>s"],
            },
        },
    }

    # Caps Lock options (mutually exclusive)
    CAPS_OPTIONS = {
        "stock": {
            "name": "Stock",
            "subtitle": "Caps Lock is Caps Lock",
            "behavior": CapsLockBehavior.CAPS_LOCK,
        },
        "escape": {
            "name": "Escape Package",
            "subtitle": "Caps → Esc • vim users rejoice",
            "behavior": CapsLockBehavior.ESCAPE,
        },
        "cruise": {
            "name": "Cruise Ctrl",
            "subtitle": "Caps → Control • ergonomic",
            "behavior": CapsLockBehavior.CTRL,
        },
    }

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._gsettings = GSettingsService()
        self._kbd_config = KeyboardConfigService()
        self._applying = False

        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)

        self._build_ui()
        self._load_current_state()

    def _build_ui(self) -> None:
        """Build the trim packages UI."""
        # Header
        header = Gtk.Label(label="Trim Packages")
        header.add_css_class("heading")
        header.set_xalign(0)
        self.append(header)

        subtitle = Gtk.Label(label="Mix and match your ride")
        subtitle.add_css_class("dim-label")
        subtitle.add_css_class("caption")
        subtitle.set_xalign(0)
        self.append(subtitle)

        # Base packages (radio style via check buttons in a group)
        base_group = Adw.PreferencesGroup()
        base_group.set_title("Base Model")
        self.append(base_group)

        self._base_checks: dict[str, Gtk.CheckButton] = {}
        first_base = None
        for pkg_id, pkg in self.PACKAGES.items():
            if pkg["group"] != "base":
                continue
            row = Adw.ActionRow()
            row.set_title(pkg["name"])
            row.set_subtitle(pkg["subtitle"])

            check = Gtk.CheckButton()
            if first_base is None:
                first_base = check
            else:
                check.set_group(first_base)
            check.connect("toggled", self._on_base_toggled, pkg_id)
            row.add_prefix(check)
            row.set_activatable_widget(check)

            self._base_checks[pkg_id] = check
            base_group.add(row)

        # Add-on packages (checkboxes)
        addon_group = Adw.PreferencesGroup()
        addon_group.set_title("Performance Packages")
        self.append(addon_group)

        self._addon_checks: dict[str, Gtk.CheckButton] = {}
        for pkg_id, pkg in self.PACKAGES.items():
            if pkg["group"] != "addon":
                continue
            row = Adw.ActionRow()
            row.set_title(pkg["name"])
            row.set_subtitle(pkg["subtitle"])

            check = Gtk.CheckButton()
            check.connect("toggled", self._on_addon_toggled, pkg_id)
            row.add_prefix(check)
            row.set_activatable_widget(check)

            self._addon_checks[pkg_id] = check
            addon_group.add(row)

        # Caps Lock options
        caps_group = Adw.PreferencesGroup()
        caps_group.set_title("Caps Lock")
        self.append(caps_group)

        self._caps_checks: dict[str, Gtk.CheckButton] = {}
        first_caps = None
        for opt_id, opt in self.CAPS_OPTIONS.items():
            row = Adw.ActionRow()
            row.set_title(opt["name"])
            row.set_subtitle(opt["subtitle"])

            check = Gtk.CheckButton()
            if first_caps is None:
                first_caps = check
            else:
                check.set_group(first_caps)
            check.connect("toggled", self._on_caps_toggled, opt_id)
            row.add_prefix(check)
            row.set_activatable_widget(check)

            self._caps_checks[opt_id] = check
            caps_group.add(row)

    def _load_current_state(self) -> None:
        """Load current configuration state into checkboxes."""
        self._applying = True  # Prevent triggering changes while loading

        # Detect base package (check if tiling shortcuts are set)
        # For now, default to Touring
        self._base_checks["touring"].set_active(True)

        # Detect Turbo (workspace numbers)
        try:
            ws1 = self._gsettings._get_keybinding(
                "org.gnome.desktop.wm.keybindings", "switch-to-workspace-1"
            )
            if ws1 and "<Super>1" in ws1:
                self._addon_checks["turbo"].set_active(True)
        except Exception:
            pass

        # Detect Cupertino (Mac keyboard swap)
        if self._kbd_config.get_apple_swap_cmd_opt():
            self._addon_checks["cupertino"].set_active(True)

        # Detect current caps lock behavior
        caps_behavior = self._kbd_config.get_caps_lock_behavior()
        for opt_id, opt in self.CAPS_OPTIONS.items():
            if opt["behavior"] == caps_behavior:
                self._caps_checks[opt_id].set_active(True)
                break

        self._applying = False

    def _on_base_toggled(self, check: Gtk.CheckButton, pkg_id: str) -> None:
        """Handle base package selection."""
        if self._applying or not check.get_active():
            return
        self._apply_package(pkg_id)

    def _on_addon_toggled(self, check: Gtk.CheckButton, pkg_id: str) -> None:
        """Handle add-on package toggle."""
        if self._applying:
            return
        if check.get_active():
            self._apply_package(pkg_id)
        else:
            self._remove_package(pkg_id)

    def _on_caps_toggled(self, check: Gtk.CheckButton, opt_id: str) -> None:
        """Handle caps lock option selection."""
        if self._applying or not check.get_active():
            return
        opt = self.CAPS_OPTIONS[opt_id]
        self._kbd_config.set_caps_lock_behavior(opt["behavior"])
        self.emit("config-changed")

    def _apply_package(self, pkg_id: str) -> None:
        """Apply a trim package."""
        pkg = self.PACKAGES.get(pkg_id)
        if not pkg:
            return

        # Handle Mac keyboard swap specially
        if pkg.get("mac_swap"):
            from dailydriver.models import FnMode, MacKeyboardConfig
            from dailydriver.services.hid_apple_service import HidAppleService

            hid = HidAppleService()
            if hid.is_module_loaded():
                config = MacKeyboardConfig(
                    fn_mode=FnMode.MEDIA,
                    swap_opt_cmd=True,
                )
                hid.apply_config(config)
            self.emit("config-changed")
            return

        # Apply shortcuts
        shortcuts = pkg.get("shortcuts", {})
        for key, accelerators in shortcuts.items():
            parts = key.rsplit(".", 1)
            if len(parts) == 2:
                schema, setting = parts
                self._gsettings._set_keybinding(schema, setting, accelerators)

        self.emit("config-changed")

    def _remove_package(self, pkg_id: str) -> None:
        """Remove a trim package (revert to defaults)."""
        pkg = self.PACKAGES.get(pkg_id)
        if not pkg:
            return

        # Handle Mac keyboard swap specially
        if pkg.get("mac_swap"):
            from dailydriver.models import FnMode, MacKeyboardConfig
            from dailydriver.services.hid_apple_service import HidAppleService

            hid = HidAppleService()
            if hid.is_module_loaded():
                config = MacKeyboardConfig(
                    fn_mode=FnMode.MEDIA,
                    swap_opt_cmd=False,  # Disable swap
                )
                hid.apply_config(config)
            self.emit("config-changed")
            return

        # For shortcuts, we'd need to know the defaults to revert
        # For now, just emit changed and let user know
        self.emit("config-changed")
