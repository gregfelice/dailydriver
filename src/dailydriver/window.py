# SPDX-License-Identifier: GPL-3.0-or-later
"""Main application window."""

from pathlib import Path

from gi.repository import Adw, Gio, GLib, Gtk

from dailydriver.models import Shortcut, ShortcutCategory
from dailydriver.services.gsettings_service import GSettingsService
from dailydriver.services.hardware_service import HardwareService
from dailydriver.services.keyboard_config_service import CapsLockBehavior, KeyboardConfigService
from dailydriver.views.cheatsheet import CheatSheetView
from dailydriver.views.keyboard_view import KeyboardView
from dailydriver.views.preset_selector import PresetSelector
from dailydriver.views.shortcut_editor import ShortcutEditorDialog
from dailydriver.views.shortcut_list import ShortcutListView


class DailyDriverWindow(Adw.ApplicationWindow):
    """Main application window."""

    __gtype_name__ = "DailyDriverWindow"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Initialize services
        self._gsettings_service = GSettingsService()
        self._hardware = HardwareService()
        self._kbd_config = KeyboardConfigService()
        self._shortcuts: dict[str, Shortcut] = {}
        self._shortcut_views: dict[str, ShortcutListView] = {}
        self._current_category: str | None = None
        self._loading = True
        self._tiling_enabled = True
        self._show_unbound = False

        # Detect keyboard
        self._detected_keyboard = self._detect_keyboard()

        # Build UI
        self._build_ui()

        # Setup window actions
        self._setup_actions()

        # Load settings
        self._settings = Gio.Settings.new("io.github.gregfelice.DailyDriver")
        self._restore_window_state()

        # Load filter settings BEFORE loading shortcuts
        self._tiling_enabled = self._settings.get_boolean("tiling-enabled")
        self._show_unbound = self._settings.get_boolean("show-unbound")

        # Load shortcuts (uses tiling/unbound settings)
        GLib.idle_add(self._load_shortcuts)
        GLib.idle_add(self._load_config_state)

    def _detect_keyboard(self):
        """Detect connected keyboard."""
        keyboards = list(self._hardware.list_keyboards())
        mac_kbs = [kb for kb in keyboards if kb.is_mac]
        external_kbs = [kb for kb in keyboards if not kb.is_internal]
        internal_kbs = [kb for kb in keyboards if kb.is_internal]

        if mac_kbs:
            return mac_kbs[0]
        elif external_kbs:
            return external_kbs[0]
        elif internal_kbs:
            return internal_kbs[0]
        return None

    def _build_ui(self) -> None:
        """Build the UI."""
        self.set_title("Daily Driver")

        # Toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Main toolbar view
        toolbar_view = Adw.ToolbarView()
        self.toast_overlay.set_child(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()

        # View switcher in header
        self._view_switcher = Adw.ViewSwitcher()
        self._view_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(self._view_switcher)

        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(self._create_menu())
        menu_button.set_tooltip_text("Main Menu")
        header.pack_end(menu_button)

        toolbar_view.add_top_bar(header)

        # View stack
        self._view_stack = Adw.ViewStack()
        self._view_switcher.set_stack(self._view_stack)
        toolbar_view.set_content(self._view_stack)

        # === SHORTCUTS VIEW (main view) ===
        shortcuts_page = self._build_shortcuts_view()
        self._view_stack.add_titled_with_icon(
            shortcuts_page,
            "shortcuts",
            "Shortcuts",
            "preferences-desktop-keyboard-shortcuts-symbolic",
        )

        # === CHEAT SHEET VIEW ===
        self._cheatsheet_view = CheatSheetView()
        self._view_stack.add_titled_with_icon(
            self._cheatsheet_view, "cheatsheet", "Cheat Sheet", "accessories-dictionary-symbolic"
        )

    def _build_shortcuts_view(self) -> Gtk.Widget:
        """Build the shortcuts browser view with config sidebar."""
        # Split view for sidebar + content
        split_view = Adw.NavigationSplitView()
        split_view.set_sidebar_width_fraction(0.28)
        split_view.set_min_sidebar_width(240)
        split_view.set_max_sidebar_width(320)

        # === SIDEBAR ===
        sidebar_page = Adw.NavigationPage()
        sidebar_page.set_title("Daily Driver")
        sidebar_page.set_tag("sidebar")

        sidebar_toolbar = Adw.ToolbarView()
        sidebar_page.set_child(sidebar_toolbar)

        sidebar_header = Adw.HeaderBar()
        sidebar_header.set_show_title(False)
        sidebar_header.set_show_start_title_buttons(False)
        sidebar_header.set_show_end_title_buttons(False)
        sidebar_toolbar.add_top_bar(sidebar_header)

        # Sidebar content: categories + config
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_vexpand(True)

        sidebar_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar_scroll.set_child(sidebar_content)

        # --- Categories Section ---
        cat_header = Gtk.Label(label="Categories")
        cat_header.add_css_class("heading")
        cat_header.add_css_class("dim-label")
        cat_header.set_xalign(0)
        cat_header.set_margin_start(12)
        cat_header.set_margin_top(8)
        cat_header.set_margin_bottom(4)
        sidebar_content.append(cat_header)

        self.category_list = Gtk.ListBox()
        self.category_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.category_list.add_css_class("navigation-sidebar")
        self.category_list.connect("row-selected", self._on_category_selected)
        sidebar_content.append(self.category_list)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(12)
        sep.set_margin_bottom(8)
        sidebar_content.append(sep)

        # --- Settings Section Header ---
        settings_header = Gtk.Label(label="Settings")
        settings_header.add_css_class("heading")
        settings_header.add_css_class("dim-label")
        settings_header.set_xalign(0)
        settings_header.set_margin_start(12)
        settings_header.set_margin_bottom(4)
        sidebar_content.append(settings_header)

        # --- Configuration Section ---
        config_section = self._build_config_section()
        sidebar_content.append(config_section)

        sidebar_toolbar.set_content(sidebar_scroll)
        split_view.set_sidebar(sidebar_page)

        # === CONTENT ===
        content_page = Adw.NavigationPage()
        content_page.set_title("Shortcuts")
        content_page.set_tag("content")

        content_toolbar = Adw.ToolbarView()
        content_page.set_child(content_toolbar)

        content_header = Adw.HeaderBar()
        content_header.set_show_title(False)
        content_header.set_show_start_title_buttons(False)
        content_header.set_show_end_title_buttons(False)

        # Keyboard toggle button
        self.show_keyboard_button = Gtk.ToggleButton()
        self.show_keyboard_button.set_icon_name("input-keyboard-symbolic")
        self.show_keyboard_button.set_tooltip_text("Show Keyboard")
        self.show_keyboard_button.connect("toggled", self._on_keyboard_toggled)
        content_header.pack_start(self.show_keyboard_button)

        content_toolbar.add_top_bar(content_header)

        # Content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Keyboard revealer
        self.keyboard_revealer = Gtk.Revealer()
        self.keyboard_revealer.set_reveal_child(False)
        self.keyboard_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)

        keyboard_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        keyboard_container.set_margin_start(12)
        keyboard_container.set_margin_end(12)
        keyboard_container.set_margin_top(12)
        keyboard_container.set_margin_bottom(12)

        # Use detected keyboard type
        kbd_type = None
        if self._detected_keyboard:
            kbd_type = self._detected_keyboard.suggested_layout()
        self._keyboard_view = KeyboardView(keyboard_type=kbd_type)
        self._keyboard_view.set_size_request(-1, 200)
        keyboard_container.append(self._keyboard_view)

        self.keyboard_revealer.set_child(keyboard_container)
        content_box.append(self.keyboard_revealer)

        # Shortcuts scroll
        shortcuts_scroll = Gtk.ScrolledWindow()
        shortcuts_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        shortcuts_scroll.set_vexpand(True)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_start(12)
        clamp.set_margin_end(12)
        clamp.set_margin_top(12)
        clamp.set_margin_bottom(12)

        self.shortcuts_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(self.shortcuts_container)
        shortcuts_scroll.set_child(clamp)
        content_box.append(shortcuts_scroll)

        content_toolbar.set_content(content_box)
        split_view.set_content(content_page)

        return split_view

    def _build_config_section(self) -> Gtk.Widget:
        """Build the configuration options section with radio buttons."""
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        config_box.set_margin_start(12)
        config_box.set_margin_end(12)
        config_box.set_margin_top(8)

        # --- Keyboard & Preset Header (orange/accent) ---
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        header_box.set_margin_bottom(8)

        # Keyboard info row
        kbd_info = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        kbd_icon = Gtk.Image.new_from_icon_name("input-keyboard-symbolic")
        kbd_icon.add_css_class("dim-label")
        kbd_info.append(kbd_icon)

        kbd_name = (
            self._detected_keyboard.display_name if self._detected_keyboard else "Standard Keyboard"
        )
        kbd_label = Gtk.Label(label=kbd_name)
        kbd_label.add_css_class("dim-label")
        kbd_label.set_xalign(0)
        kbd_label.set_hexpand(True)
        kbd_info.append(kbd_label)
        header_box.append(kbd_info)

        # Current preset row
        preset_info = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        preset_icon = Gtk.Image.new_from_icon_name("document-properties-symbolic")
        preset_icon.add_css_class("dim-label")
        preset_info.append(preset_icon)

        self._current_preset_label = Gtk.Label(label="GNOME + Tiling Preset")
        self._current_preset_label.add_css_class("dim-label")
        self._current_preset_label.set_xalign(0)
        self._current_preset_label.set_hexpand(True)
        preset_info.append(self._current_preset_label)
        header_box.append(preset_info)

        config_box.append(header_box)

        # --- Preset Section (collapsible) ---
        preset_expander = Gtk.Expander(label="Shortcut Presets")
        preset_expander.set_expanded(False)

        preset_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        preset_content.set_margin_start(8)
        preset_content.set_margin_top(4)

        # Radio buttons for presets
        self._preset_radios: dict[str, Gtk.CheckButton] = {}
        preset_options = [
            ("vanilla-gnome", "Vanilla GNOME"),
            ("gnome-tiling", "GNOME + Tiling"),
            ("hyprland-style", "Hyprland Style"),
        ]

        first_radio = None
        for key, label in preset_options:
            radio = Gtk.CheckButton(label=label)
            if first_radio:
                radio.set_group(first_radio)
            else:
                first_radio = radio
            radio.connect("toggled", self._on_preset_radio_toggled, key)
            self._preset_radios[key] = radio
            preset_content.append(radio)

        preset_expander.set_child(preset_content)
        config_box.append(preset_expander)

        # --- User Section (collapsible) ---
        user_expander = Gtk.Expander(label="User Modifications")
        user_expander.set_expanded(False)

        user_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        user_content.set_margin_start(8)
        user_content.set_margin_top(4)

        # Set up launchers button
        launchers_button = Gtk.Button(label="Set Up Launchers")
        launchers_button.add_css_class("flat")
        launchers_button.connect("clicked", self._on_setup_launchers)
        user_content.append(launchers_button)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        user_content.append(sep)

        # Clear user modifications button
        clear_mods_button = Gtk.Button(label="Clear Modifications")
        clear_mods_button.add_css_class("flat")
        clear_mods_button.connect("clicked", self._on_clear_modifications)
        user_content.append(clear_mods_button)

        # Load user modifications button
        load_mods_button = Gtk.Button(label="Load Modifications")
        load_mods_button.add_css_class("flat")
        load_mods_button.connect("clicked", self._on_load_modifications)
        user_content.append(load_mods_button)

        user_expander.set_child(user_content)
        config_box.append(user_expander)

        # --- Keyboard Layout Section (collapsible) ---
        layout_expander = Gtk.Expander(label="Keyboard Layout")
        layout_expander.set_expanded(False)

        layout_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        layout_content.set_margin_start(8)
        layout_content.set_margin_top(4)

        # Radio buttons for layout
        self._layout_radios: dict[str, Gtk.CheckButton] = {}
        layout_options = [("pc", "PC Standard"), ("mac", "Mac Style"), ("custom", "Custom")]

        first_radio = None
        for key, label in layout_options:
            radio = Gtk.CheckButton(label=label)
            if first_radio:
                radio.set_group(first_radio)
            else:
                first_radio = radio
            radio.connect("toggled", self._on_layout_toggled, key)
            self._layout_radios[key] = radio
            layout_content.append(radio)

        layout_expander.set_child(layout_content)
        config_box.append(layout_expander)

        # --- Caps Lock Section (collapsible) ---
        caps_expander = Gtk.Expander(label="Caps Lock Behavior")
        caps_expander.set_expanded(False)

        caps_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        caps_content.set_margin_start(8)
        caps_content.set_margin_top(4)

        # Radio buttons for caps lock
        self._caps_radios: dict[str, Gtk.CheckButton] = {}
        caps_options = [
            ("caps", "Caps Lock"),
            ("escape", "Escape"),
            ("ctrl", "Control"),
            ("custom", "Custom"),
        ]

        first_radio = None
        for key, label in caps_options:
            radio = Gtk.CheckButton(label=label)
            if first_radio:
                radio.set_group(first_radio)
            else:
                first_radio = radio
            radio.connect("toggled", self._on_caps_toggled, key)
            self._caps_radios[key] = radio
            caps_content.append(radio)

        caps_expander.set_child(caps_content)
        config_box.append(caps_expander)

        # --- Show Unbound Section ---
        unbound_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        unbound_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        unbound_label = Gtk.Label(label="Show Unbound")
        unbound_label.set_xalign(0)
        unbound_label.set_hexpand(True)
        unbound_row.append(unbound_label)

        self._unbound_switch = Gtk.Switch()
        self._unbound_switch.set_valign(Gtk.Align.CENTER)
        self._unbound_switch.connect("notify::active", self._on_unbound_toggled)
        unbound_row.append(self._unbound_switch)

        unbound_group.append(unbound_row)

        unbound_desc = Gtk.Label(label="Include shortcuts with no key binding")
        unbound_desc.add_css_class("dim-label")
        unbound_desc.add_css_class("caption")
        unbound_desc.set_xalign(0)
        unbound_group.append(unbound_desc)

        config_box.append(unbound_group)

        return config_box

    def _load_config_state(self) -> bool:
        """Load current config state into radio buttons."""
        self._loading = True

        # Track current state for reverting failed changes
        self._current_layout = "pc"
        self._current_caps = "caps"

        # Layout - check actual system state
        from dailydriver.services.hid_apple_service import HidAppleService

        hid = HidAppleService()

        if hid.is_module_loaded():
            hid_config = hid.get_current_config()
            if (
                hid_config
                and hid_config.swap_opt_cmd
                or self._detected_keyboard
                and self._detected_keyboard.is_mac
            ):
                self._current_layout = "mac"
        elif self._detected_keyboard and self._detected_keyboard.is_mac:
            self._current_layout = "mac"

        self._layout_radios[self._current_layout].set_active(True)

        # Caps Lock
        caps = self._kbd_config.get_caps_lock_behavior()
        caps_map = {
            CapsLockBehavior.CAPS_LOCK: "caps",
            CapsLockBehavior.ESCAPE: "escape",
            CapsLockBehavior.CTRL: "ctrl",
        }
        self._current_caps = caps_map.get(caps, "caps")

        # Check if it's a non-standard config (custom)
        if caps not in caps_map:
            self._current_caps = "custom"

        self._caps_radios[self._current_caps].set_active(True)

        # Tiling - controlled by preset, not manual toggle
        self._tiling_enabled = self._settings.get_boolean("tiling-enabled")

        # Restore selected preset radio button
        current_preset = self._settings.get_string("current-preset")
        if current_preset and current_preset in self._preset_radios:
            self._preset_radios[current_preset].set_active(True)
            preset_names = {
                "vanilla-gnome": "Vanilla GNOME",
                "gnome-tiling": "GNOME + Tiling",
                "hyprland-style": "Hyprland Style",
            }
            self._current_preset_label.set_label(
                f"{preset_names.get(current_preset, current_preset)} Preset"
            )

        # Show unbound
        self._show_unbound = self._settings.get_boolean("show-unbound")
        self._unbound_switch.set_active(self._show_unbound)

        self._loading = False
        return False

    def _on_unbound_toggled(self, switch: Gtk.Switch, param) -> None:
        """Handle unbound switch toggle."""
        if self._loading:
            return

        self._show_unbound = switch.get_active()
        self._settings.set_boolean("show-unbound", self._show_unbound)

        # Reload shortcuts to show/hide unbound
        self._reload_shortcuts()

    def _on_layout_toggled(self, radio: Gtk.CheckButton, key: str) -> None:
        """Handle layout radio toggle."""
        if self._loading or not radio.get_active():
            return

        if key == "custom":
            # Custom means user manages it externally
            self._current_layout = "custom"
            self._show_toast("Using custom layout")
            return

        from dailydriver.models import FnMode, MacKeyboardConfig
        from dailydriver.services.hid_apple_service import HidAppleService

        hid = HidAppleService()
        if not hid.is_module_loaded():
            self._current_layout = key
            self._show_toast("Layout updated (no Mac keyboard)")
            return

        is_mac = key == "mac"
        config = MacKeyboardConfig(
            fn_mode=FnMode.MEDIA,
            swap_opt_cmd=is_mac,
        )

        success = hid.apply_config(config)

        if success:
            self._current_layout = key
            self._show_toast("Layout updated")
        else:
            # Revert to previous selection
            self._loading = True
            self._layout_radios[self._current_layout].set_active(True)
            self._loading = False
            self._show_toast("Layout change cancelled")

    def _on_caps_toggled(self, radio: Gtk.CheckButton, key: str) -> None:
        """Handle caps lock radio toggle."""
        if self._loading or not radio.get_active():
            return

        if key == "custom":
            # Custom means user manages it externally
            self._current_caps = "custom"
            self._show_toast("Using custom caps lock")
            return

        caps_map = {
            "caps": CapsLockBehavior.CAPS_LOCK,
            "escape": CapsLockBehavior.ESCAPE,
            "ctrl": CapsLockBehavior.CTRL,
        }

        behavior = caps_map.get(key, CapsLockBehavior.CAPS_LOCK)
        success = self._kbd_config.set_caps_lock_behavior(behavior)

        if success:
            self._current_caps = key
            self._show_toast("Caps Lock updated")
        else:
            # Revert to previous selection
            self._loading = True
            self._caps_radios[self._current_caps].set_active(True)
            self._loading = False
            self._show_toast("Caps Lock change cancelled")

    def _show_toast(self, message: str) -> None:
        """Show a toast notification."""
        toast = Adw.Toast(title=message)
        toast.set_timeout(1)
        self.toast_overlay.add_toast(toast)

    def _create_menu(self) -> Gio.Menu:
        """Create the primary menu."""
        menu = Gio.Menu()

        section1 = Gio.Menu()
        section1.append("Import Profile...", "win.import-profile")
        section1.append("Export Profile...", "win.export-profile")
        menu.append_section(None, section1)

        section2 = Gio.Menu()
        section2.append("About Daily Driver", "app.about")
        menu.append_section(None, section2)

        return menu

    def _setup_actions(self) -> None:
        """Set up window actions."""
        import_action = Gio.SimpleAction.new("import-profile", None)
        import_action.connect("activate", self._on_import_profile)
        self.add_action(import_action)

        export_action = Gio.SimpleAction.new("export-profile", None)
        export_action.connect("activate", self._on_export_profile)
        self.add_action(export_action)

        # Escape key to toggle views (capture phase to get it before focused widgets)
        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

    def _on_key_pressed(
        self, controller: Gtk.EventControllerKey, keyval: int, keycode: int, state: int
    ) -> bool:
        """Handle key press events."""
        from gi.repository import Gdk

        # Escape toggles views
        if keyval == Gdk.KEY_Escape:
            self._toggle_view()
            return True

        return False

    def _toggle_view(self) -> None:
        """Toggle between shortcuts and cheat sheet views."""
        current = self._view_stack.get_visible_child_name()
        if current == "shortcuts":
            self._view_stack.set_visible_child_name("cheatsheet")
        else:
            self._view_stack.set_visible_child_name("shortcuts")

        return True

    def _restore_window_state(self) -> None:
        """Restore window size and state from settings."""
        width = self._settings.get_int("window-width")
        height = self._settings.get_int("window-height")
        maximized = self._settings.get_boolean("window-maximized")

        self.set_default_size(width, height)
        if maximized:
            self.maximize()

        self.connect("close-request", self._save_window_state)

    def _save_window_state(self, window: Gtk.Window) -> bool:
        """Save window state to settings."""
        if not self.is_maximized():
            width, height = self.get_default_size()
            self._settings.set_int("window-width", width)
            self._settings.set_int("window-height", height)

        self._settings.set_boolean("window-maximized", self.is_maximized())
        return False

    def _reload_shortcuts(self) -> bool:
        """Reload shortcuts after configuration change."""
        self._shortcut_views.clear()

        while child := self.category_list.get_first_child():
            self.category_list.remove(child)

        while child := self.shortcuts_container.get_first_child():
            self.shortcuts_container.remove(child)

        self._current_category = None
        self._load_shortcuts()

        # Refresh cheat sheet
        self._cheatsheet_view.refresh()

        return False

    def _load_shortcuts(self) -> bool:
        """Load shortcuts from GSettings."""
        self._shortcuts = self._gsettings_service.load_all_shortcuts()
        all_categories = self._gsettings_service.get_categories()

        # Tiling-related groups to hide when tiling disabled
        tiling_groups = {"Tile Halves", "Tile Quarters", "Tile Actions", "Layouts"}

        # Filter categories based on tiling setting
        categories = [c for c in all_categories if self._tiling_enabled or c.id != "tiling"]

        # Build shortcut views and track which categories have visible shortcuts
        visible_categories = []
        for category in categories:
            category_shortcuts = [
                s
                for s in self._shortcuts.values()
                if s.category == category.id
                and (self._tiling_enabled or s.group not in tiling_groups)
                and (self._show_unbound or s.bindings)  # Filter unbound
            ]
            if category_shortcuts:
                view = ShortcutListView(category, category_shortcuts)
                view.connect("shortcut-edit-requested", self._on_shortcut_edit)
                view.connect("shortcut-reset-requested", self._on_shortcut_reset)
                self._shortcut_views[category.id] = view
                visible_categories.append((category, len(category_shortcuts)))

        # Disable selection during population to prevent auto-focus
        self.category_list.set_selection_mode(Gtk.SelectionMode.NONE)

        # Add category rows only for categories with visible shortcuts
        for category, shortcut_count in visible_categories:
            row = self._create_category_row(category, shortcut_count)
            row.set_can_focus(False)  # Prevent focus during add
            self.category_list.append(row)

        # Show first category content directly
        if visible_categories:
            first_cat = visible_categories[0][0]
            self._current_category = first_cat.id
            if first_cat.id in self._shortcut_views:
                self.shortcuts_container.append(self._shortcut_views[first_cat.id])

        # Re-enable selection and focus after population
        GLib.timeout_add(50, self._finalize_category_list)

        return False

    def _finalize_category_list(self) -> bool:
        """Re-enable selection after rows are realized."""
        # Enable focus on all rows
        index = 0
        while row := self.category_list.get_row_at_index(index):
            row.set_can_focus(True)
            index += 1

        # Re-enable selection mode
        self.category_list.set_selection_mode(Gtk.SelectionMode.SINGLE)

        # Select first row
        first_row = self.category_list.get_row_at_index(0)
        if first_row:
            self.category_list.select_row(first_row)

        return False

    def _create_category_row(self, category: ShortcutCategory, count: int) -> Gtk.ListBoxRow:
        """Create a sidebar row for a category."""
        row = Gtk.ListBoxRow()
        row.category_id = category.id

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.add_css_class("category-row")
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        icon = Gtk.Image.new_from_icon_name(category.icon)
        box.append(icon)

        label = Gtk.Label(label=category.name)
        label.set_xalign(0)
        label.set_hexpand(True)
        box.append(label)

        if count > 0:
            badge = Gtk.Label(label=str(count))
            badge.add_css_class("dim-label")
            box.append(badge)

        row.set_child(box)
        return row

    def _on_category_selected(self, list_box: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        """Handle category selection."""
        if not row:
            return

        category_id = row.category_id
        if category_id == self._current_category:
            return

        self._current_category = category_id

        while child := self.shortcuts_container.get_first_child():
            self.shortcuts_container.remove(child)

        if category_id in self._shortcut_views:
            self.shortcuts_container.append(self._shortcut_views[category_id])

    def _on_keyboard_toggled(self, button: Gtk.ToggleButton) -> None:
        """Handle keyboard view toggle."""
        self.keyboard_revealer.set_reveal_child(button.get_active())

    def _on_shortcut_edit(self, view: ShortcutListView, shortcut: Shortcut) -> None:
        """Handle shortcut edit request."""
        dialog = ShortcutEditorDialog(shortcut, self._shortcuts, self)
        dialog.connect("shortcut-changed", self._on_shortcut_changed)
        dialog.present()

    def _on_shortcut_changed(self, dialog: ShortcutEditorDialog, shortcut: Shortcut) -> None:
        """Handle shortcut change from editor."""
        self._gsettings_service.save_shortcut(shortcut)

        if shortcut.category in self._shortcut_views:
            self._shortcut_views[shortcut.category].update_shortcut(shortcut)

        self._keyboard_view.highlight_shortcut(shortcut)
        self._cheatsheet_view.refresh()

        toast = Adw.Toast(title=f"Shortcut updated: {shortcut.name}")
        self.toast_overlay.add_toast(toast)

    def _on_shortcut_reset(self, view: ShortcutListView, shortcut: Shortcut) -> None:
        """Handle shortcut reset request."""
        shortcut.reset()
        self._gsettings_service.save_shortcut(shortcut)
        view.update_shortcut(shortcut)

        toast = Adw.Toast(title=f"Shortcut reset: {shortcut.name}")
        self.toast_overlay.add_toast(toast)

    def _on_preset_radio_toggled(self, radio: Gtk.CheckButton, preset_key: str) -> None:
        """Handle preset radio button toggle."""
        if self._loading or not radio.get_active():
            return

        # Get display name
        preset_names = {
            "vanilla-gnome": "Vanilla GNOME",
            "gnome-tiling": "GNOME + Tiling",
            "hyprland-style": "Hyprland Style",
        }
        display_name = preset_names.get(preset_key, preset_key)

        # Get old preset to know what to reset
        old_preset_key = self._settings.get_string("current-preset")

        # Set tiling based on preset (vanilla-gnome has no tiling)
        self._tiling_enabled = preset_key != "vanilla-gnome"
        self._settings.set_boolean("tiling-enabled", self._tiling_enabled)
        self._settings.set_string("current-preset", preset_key)

        # Apply the preset (with cleanup of old preset shortcuts)
        from dailydriver.services.profile_service import ProfileService

        profile_service = ProfileService(self._gsettings_service)
        profile = profile_service.get_profile(preset_key)

        if profile:
            # Reset shortcuts from old preset that aren't in new preset
            if old_preset_key and old_preset_key != preset_key:
                old_profile = profile_service.get_profile(old_preset_key)
                if old_profile:
                    profile_service.reset_orphaned_shortcuts(old_profile, profile)

            profile_service.apply_profile(profile)
            self._current_preset_label.set_label(f"{display_name} Preset")
            self._reload_shortcuts()
            toast = Adw.Toast(title=f"Applied: {display_name}")
            self.toast_overlay.add_toast(toast)
        else:
            self._show_toast(f"Preset not found: {preset_key}")

    def _on_choose_preset(self, action: Gio.SimpleAction, param: GLib.Variant | None) -> None:
        """Show the preset selector dialog (from menu)."""
        self._show_preset_selector()

    def _show_preset_selector(self) -> None:
        """Show the preset selector dialog."""
        dialog = PresetSelector()
        dialog.connect("preset-applied", self._on_preset_applied)
        dialog.present(self)

    def _on_preset_applied(self, dialog: PresetSelector, preset_name: str) -> None:
        """Handle preset application - reload shortcuts."""
        # Get old preset to know what to reset
        old_preset_key = self._settings.get_string("current-preset")

        # Set tiling based on preset (vanilla-gnome has no tiling)
        self._tiling_enabled = preset_name != "vanilla-gnome"
        self._settings.set_boolean("tiling-enabled", self._tiling_enabled)
        self._settings.set_string("current-preset", preset_name)

        # Reset orphaned shortcuts from old preset
        from dailydriver.services.profile_service import ProfileService

        profile_service = ProfileService(self._gsettings_service)

        if old_preset_key and old_preset_key != preset_name:
            old_profile = profile_service.get_profile(old_preset_key)
            new_profile = profile_service.get_profile(preset_name)
            if old_profile and new_profile:
                profile_service.reset_orphaned_shortcuts(old_profile, new_profile)

        self._reload_shortcuts()
        # Update the radio button and label
        if preset_name in self._preset_radios:
            self._loading = True
            self._preset_radios[preset_name].set_active(True)
            self._loading = False
        preset_names = {
            "vanilla-gnome": "Vanilla GNOME",
            "gnome-tiling": "GNOME + Tiling",
            "hyprland-style": "Hyprland Style",
        }
        self._current_preset_label.set_label(f"{preset_names.get(preset_name, preset_name)} Preset")
        toast = Adw.Toast(title=f"Applied: {preset_names.get(preset_name, preset_name)}")
        self.toast_overlay.add_toast(toast)

    def _on_import_profile(self, action: Gio.SimpleAction, param: GLib.Variant | None) -> None:
        """Import a profile from file."""
        self._show_toast("Import: Coming soon")

    def _on_export_profile(self, action: Gio.SimpleAction, param: GLib.Variant | None) -> None:
        """Export current profile to file."""
        self._show_toast("Export: Coming soon")

    def _on_clear_modifications(self, button: Gtk.Button) -> None:
        """Clear user modifications, saving them to a file first."""
        # Get current preset
        current_preset = self._settings.get_string("current-preset")
        if not current_preset:
            current_preset = "gnome-tiling"

        # Check if there are any USER modifications (compared to current preset)
        from dailydriver.services.profile_service import ProfileService

        profile_service = ProfileService(self._gsettings_service)
        user_mods = profile_service.get_user_modifications(current_preset)

        if not user_mods:
            self._show_toast("No user modifications to clear")
            return

        modified_count = len(user_mods)

        # Show confirmation dialog
        dialog = Adw.AlertDialog()
        dialog.set_heading("Clear User Modifications?")
        dialog.set_body(
            f"This will save your {modified_count} modification(s) to a file and "
            f"reset all shortcuts to the {self._get_preset_display_name(current_preset)} preset.\n\n"
            "You can import the saved modifications later."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear Modifications")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_clear_mods_response, current_preset)
        dialog.present(self)

    def _on_clear_mods_response(
        self, dialog: Adw.AlertDialog, response: str, preset_name: str
    ) -> None:
        """Handle clear modifications confirmation response."""
        if response != "clear":
            return

        from dailydriver.services.profile_service import ProfileService

        profile_service = ProfileService(self._gsettings_service)

        export_path, num_mods = profile_service.export_and_clear_modifications(preset_name)

        if export_path:
            self._reload_shortcuts()
            # Show toast with file location
            toast = Adw.Toast(title=f"Saved {num_mods} modification(s) to {export_path.name}")
            toast.set_timeout(5)
            self.toast_overlay.add_toast(toast)
        else:
            self._show_toast("No modifications to clear")

    def _get_preset_display_name(self, preset_key: str) -> str:
        """Get display name for a preset key."""
        preset_names = {
            "vanilla-gnome": "Vanilla GNOME",
            "gnome-tiling": "GNOME + Tiling",
            "hyprland-style": "Hyprland Style",
        }
        return preset_names.get(preset_key, preset_key)

    def _on_setup_launchers(self, button: Gtk.Button) -> None:
        """Set up default application launchers."""
        results = self._gsettings_service.setup_default_custom_shortcuts()

        # Build result message
        lines = []
        if "terminal" in results:
            lines.append(f"• Terminal: {results['terminal']}")
        if "file_manager" in results:
            lines.append(f"• Files: {results['file_manager']}")
        if "browser" in results:
            lines.append(f"• Browser: {results['browser']}")
        if "music" in results:
            lines.append(f"• Music: {results['music']}")
        if "cheat_sheet" in results:
            lines.append(f"• Cheat Sheet: {results['cheat_sheet']}")

        result_text = "\n".join(lines) if lines else "No applications detected"

        # Show dialog with results
        dialog = Adw.AlertDialog()
        dialog.set_heading("Launchers Configured")
        dialog.set_body(
            f"Custom shortcuts have been set up:\n\n"
            f"{result_text}\n\n"
            "Shortcuts:\n"
            "• Super+Return → Terminal\n"
            "• Super+E → File Manager\n"
            "• Super+B → Browser\n"
            "• Super+P → Music Player\n"
            "• Super+/ → Cheat Sheet"
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self)

        # Reload to show custom shortcuts
        self._reload_shortcuts()

    def _on_load_modifications(self, button: Gtk.Button) -> None:
        """Load user modifications from a file."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Load User Modifications")

        # Set up file filter for TOML files
        filter_toml = Gtk.FileFilter()
        filter_toml.set_name("TOML files")
        filter_toml.add_pattern("*.toml")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_toml)
        dialog.set_filters(filters)
        dialog.set_default_filter(filter_toml)

        # Start in user profiles directory
        from pathlib import Path

        profiles_dir = Path(GLib.get_user_config_dir()) / "dailydriver" / "profiles"
        if profiles_dir.exists():
            dialog.set_initial_folder(Gio.File.new_for_path(str(profiles_dir)))

        dialog.open(self, None, self._on_load_mods_response)

    def _on_load_mods_response(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        """Handle file selection for loading modifications."""
        try:
            file = dialog.open_finish(result)
            if not file:
                return

            path = Path(file.get_path())

            from dailydriver.services.profile_service import ProfileService

            profile_service = ProfileService(self._gsettings_service)

            # Load and apply the profile
            profile = profile_service.import_profile(path)
            changed = profile_service.apply_profile(profile)

            self._reload_shortcuts()

            num_applied = len(changed)
            toast = Adw.Toast(title=f"Applied {num_applied} modification(s) from {path.name}")
            self.toast_overlay.add_toast(toast)

        except GLib.Error as e:
            if e.code != Gtk.DialogError.DISMISSED:
                self._show_toast(f"Error loading file: {e.message}")
        except Exception as e:
            self._show_toast(f"Error loading profile: {e}")

    def show_cheat_sheet(self) -> None:
        """Show the cheat sheet view."""
        self._view_stack.set_visible_child_name("cheatsheet")
