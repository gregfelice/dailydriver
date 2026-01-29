# SPDX-License-Identifier: GPL-3.0-or-later
"""Shortcut editor dialog for capturing key combinations."""

from gi.repository import Adw, Gdk, GLib, GObject, Gtk

from dailydriver.models import KeyBinding, Modifier, Shortcut


class ShortcutEditorWindow(Gtk.Window):
    """Window for editing a keyboard shortcut.

    Uses a separate Gtk.Window instead of Adw.Dialog to get our own
    toplevel surface, which allows proper shortcut inhibition on Wayland.
    """

    __gtype_name__ = "ShortcutEditorWindow"

    __gsignals__ = {
        "shortcut-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),  # Shortcut
        ),
    }

    def __init__(
        self, shortcut: Shortcut, all_shortcuts: dict[str, Shortcut], parent: Gtk.Window
    ) -> None:
        super().__init__()
        self.shortcut = shortcut
        self._all_shortcuts = all_shortcuts
        self._pending_binding: KeyBinding | None = None
        self._conflict_shortcut: Shortcut | None = None
        self._inhibit_active = False

        # Window setup
        self.set_title("Set Shortcut")
        self.set_default_size(400, 300)
        self.set_modal(True)
        self.set_transient_for(parent)
        self.set_resizable(False)
        self.set_deletable(True)

        self._build_ui()

        # Setup key capture with CAPTURE phase to get keys before anything else
        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        # Handle window lifecycle
        self.connect("realize", self._on_realize)
        self.connect("close-request", self._on_close_request)

    def _build_ui(self) -> None:
        """Build the dialog UI."""
        # Main container with Adw styling
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", self._on_cancel)
        header.pack_start(cancel_button)

        self.set_button = Gtk.Button(label="Set")
        self.set_button.set_sensitive(False)
        self.set_button.add_css_class("suggested-action")
        self.set_button.connect("clicked", self._on_set)
        header.pack_end(self.set_button)

        toolbar_view.add_top_bar(header)

        # Content
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_valign(Gtk.Align.CENTER)
        content_box.set_vexpand(True)

        # Shortcut name
        name_label = Gtk.Label(label=self.shortcut.name)
        name_label.add_css_class("title-2")
        content_box.append(name_label)

        # Instructions
        self.instruction_label = Gtk.Label(
            label="Press a key combination or press Backspace to clear"
        )
        self.instruction_label.add_css_class("dim-label")
        content_box.append(self.instruction_label)

        # Shortcut display
        self.shortcut_label = Gtk.ShortcutLabel()
        self.shortcut_label.set_accelerator(self.shortcut.accelerator)
        self.shortcut_label.set_halign(Gtk.Align.CENTER)
        content_box.append(self.shortcut_label)

        # Conflict banner
        self.conflict_revealer = Gtk.Revealer()
        self.conflict_revealer.set_reveal_child(False)
        self.conflict_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)

        self.conflict_banner = Adw.Banner()
        self.conflict_banner.set_title("This shortcut is already in use")
        self.conflict_banner.set_button_label("Replace")
        self.conflict_banner.set_revealed(True)
        self.conflict_banner.connect("button-clicked", self._on_replace_conflict)
        self.conflict_revealer.set_child(self.conflict_banner)

        content_box.append(self.conflict_revealer)

        toolbar_view.set_content(content_box)

    def _on_realize(self, widget) -> None:
        """Called when window is realized - inhibit system shortcuts."""
        # Delay to ensure surface is fully set up
        GLib.timeout_add(50, self._inhibit_shortcuts)

    def _inhibit_shortcuts(self) -> bool:
        """Inhibit system shortcuts so we can capture all key combos."""
        if self._inhibit_active:
            return False  # Already inhibited

        surface = self.get_surface()
        if not surface:
            return False

        # GdkToplevel has inhibit_system_shortcuts on Wayland
        if isinstance(surface, Gdk.Toplevel):
            try:
                surface.inhibit_system_shortcuts(None)
                self._inhibit_active = True
                print("System shortcuts inhibited for capture")
            except Exception as e:
                print(f"Could not inhibit shortcuts: {e}")

        return False  # Don't repeat

    def _uninhibit_shortcuts(self) -> None:
        """Restore system shortcuts."""
        if not self._inhibit_active:
            return

        surface = self.get_surface()
        if surface and isinstance(surface, Gdk.Toplevel):
            try:
                surface.restore_system_shortcuts()
                print("System shortcuts restored")
            except Exception:
                pass

        self._inhibit_active = False

    def _on_key_pressed(
        self,
        controller: Gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        """Handle key press for shortcut capture."""
        # Get key name
        key_name = Gdk.keyval_name(keyval)
        if not key_name:
            return False

        # Handle Escape - cancel
        if keyval == Gdk.KEY_Escape:
            self._close_window()
            return True

        # Handle Backspace - clear shortcut
        if keyval == Gdk.KEY_BackSpace:
            self._pending_binding = None
            self.shortcut_label.set_accelerator("")
            self.instruction_label.set_label("Shortcut disabled")
            self.set_button.set_sensitive(True)
            self.conflict_revealer.set_reveal_child(False)
            return True

        # Ignore lone modifier keys
        if key_name in (
            "Shift_L",
            "Shift_R",
            "Control_L",
            "Control_R",
            "Alt_L",
            "Alt_R",
            "Super_L",
            "Super_R",
            "Meta_L",
            "Meta_R",
            "Hyper_L",
            "Hyper_R",
            "ISO_Level3_Shift",
            "Caps_Lock",
            "Num_Lock",
        ):
            return False

        # Clean up state (remove lock modifiers, etc.)
        clean_state = state & Gtk.accelerator_get_default_mod_mask()

        # Create binding
        modifiers = Modifier.from_gtk(clean_state)

        # Require at least one modifier for most keys
        if modifiers == Modifier.NONE:
            # Allow function keys and special keys without modifiers
            if not (Gdk.KEY_F1 <= keyval <= Gdk.KEY_F35):
                self.instruction_label.set_label("Shortcuts require at least one modifier key")
                return True

        self._pending_binding = KeyBinding(keyval=keyval, modifiers=modifiers)

        # Update display
        accel = self._pending_binding.to_accelerator()
        self.shortcut_label.set_accelerator(accel)
        self.instruction_label.set_label("Press Set to apply")

        # Check for conflicts
        self._check_conflicts()

        return True

    def _check_conflicts(self) -> None:
        """Check if pending binding conflicts with other shortcuts."""
        if not self._pending_binding:
            self.conflict_revealer.set_reveal_child(False)
            self.set_button.set_sensitive(True)
            return

        self._conflict_shortcut = None

        for other in self._all_shortcuts.values():
            if other.id == self.shortcut.id:
                continue

            if self._pending_binding in other.bindings:
                self._conflict_shortcut = other
                self.conflict_banner.set_title(f"Already used by: {other.name}")
                self.conflict_revealer.set_reveal_child(True)
                self.set_button.set_sensitive(False)
                return

        self.conflict_revealer.set_reveal_child(False)
        self.set_button.set_sensitive(True)

    def _on_replace_conflict(self, banner: Adw.Banner) -> None:
        """Handle replacing conflicting shortcut."""
        if self._conflict_shortcut:
            # Clear the conflicting shortcut's binding
            if self._pending_binding:
                self._conflict_shortcut.remove_binding(self._pending_binding)

            self.conflict_revealer.set_reveal_child(False)
            self.set_button.set_sensitive(True)

    def _on_set(self, button: Gtk.Button) -> None:
        """Handle set button - apply the shortcut."""
        # Update shortcut with new binding
        self.shortcut.set_binding(self._pending_binding)

        # Emit signal
        self.emit("shortcut-changed", self.shortcut)

        self._close_window()

    def _on_close_request(self, window) -> bool:
        """Handle window close request."""
        self._uninhibit_shortcuts()
        return False  # Allow close

    def _close_window(self) -> None:
        """Close the window properly."""
        self._uninhibit_shortcuts()
        self.close()

    def _on_cancel(self, button: Gtk.Button) -> None:
        """Handle cancel button."""
        self._close_window()


# Keep the old class name as an alias for backwards compatibility
ShortcutEditorDialog = ShortcutEditorWindow
