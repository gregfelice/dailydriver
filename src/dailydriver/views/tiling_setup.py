# SPDX-License-Identifier: GPL-3.0-or-later
"""Tiling setup banner for first-time configuration."""

from gi.repository import GLib, GObject, Gtk

from dailydriver.services.tiling_service import TilingInfo, TilingService, TilingStatus


class TilingSetupBanner(Gtk.Box):
    """Banner prompting user to set up tiling."""

    __gtype_name__ = "TilingSetupBanner"

    __gsignals__ = {
        "tiling-configured": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str,),  # Configuration type: "native" or "extension"
        ),
    }

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._service = TilingService()
        self._tiling_info: TilingInfo | None = None

        self.add_css_class("card")
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the banner UI."""
        # Main content box with padding
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        self.append(content)

        # Header with icon
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        header_box.set_halign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name("view-grid-symbolic")
        icon.set_icon_size(Gtk.IconSize.LARGE)
        icon.add_css_class("dim-label")
        header_box.append(icon)

        title = Gtk.Label(label="Tiling Not Configured")
        title.add_css_class("title-2")
        header_box.append(title)

        content.append(header_box)

        # Description
        self._description = Gtk.Label(
            label="Snap windows to screen edges and corners with keyboard shortcuts.\n"
            "Choose basic tiling or a full-featured extension."
        )
        self._description.set_wrap(True)
        self._description.set_justify(Gtk.Justification.CENTER)
        self._description.add_css_class("dim-label")
        content.append(self._description)

        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        content.append(button_box)

        # Basic tiling button
        self._basic_button = Gtk.Button(label="Enable Basic Tiling")
        self._basic_button.set_tooltip_text("Bind Super+Arrow keys for half-screen tiling")
        self._basic_button.connect("clicked", self._on_enable_basic)
        button_box.append(self._basic_button)

        # Extension button (shown conditionally)
        self._extension_button = Gtk.Button(label="Setup Tiling Assistant")
        self._extension_button.add_css_class("suggested-action")
        self._extension_button.set_tooltip_text("Enable Tiling Assistant with smart defaults")
        self._extension_button.connect("clicked", self._on_enable_extension)
        button_box.append(self._extension_button)

        # Dismiss button
        dismiss_button = Gtk.Button(label="Not Now")
        dismiss_button.add_css_class("flat")
        dismiss_button.connect("clicked", self._on_dismiss)
        button_box.append(dismiss_button)

    def check_and_update(self) -> bool:
        """Check tiling status and update visibility.

        Returns True if banner should be shown.
        """
        self._tiling_info = self._service.detect_status()

        if self._tiling_info.status != TilingStatus.NONE:
            self.set_visible(False)
            return False

        # Update UI based on what's available
        if self._tiling_info.extension_installed:
            self._extension_button.set_label(f"Enable {self._tiling_info.extension_installed}")
            self._extension_button.set_visible(True)
            self._description.set_label(
                f"Snap windows to screen edges and corners with keyboard shortcuts.\n"
                f"{self._tiling_info.extension_installed} is installed but not enabled."
            )
        else:
            self._extension_button.set_visible(False)
            self._description.set_label(
                "Snap windows to screen edges and corners with keyboard shortcuts.\n"
                "Enable basic tiling with Super+Arrow keys."
            )

        self.set_visible(True)
        return True

    def _on_enable_basic(self, button: Gtk.Button) -> None:
        """Enable basic native GNOME tiling."""
        button.set_sensitive(False)
        button.set_label("Enabling...")

        # Run in background to not block UI
        def enable():
            success = self._service.enable_native_tiling()
            GLib.idle_add(self._on_basic_complete, success)

        GLib.Thread.new("enable-tiling", enable)

    def _on_basic_complete(self, success: bool) -> None:
        """Handle basic tiling enable completion."""
        if success:
            self.set_visible(False)
            self.emit("tiling-configured", "native")
        else:
            self._basic_button.set_sensitive(True)
            self._basic_button.set_label("Enable Basic Tiling")
            # TODO: Show error toast

    def _on_enable_extension(self, button: Gtk.Button) -> None:
        """Enable tiling extension."""
        button.set_sensitive(False)
        button.set_label("Enabling...")

        def enable():
            ext_id = self._service.get_tiling_assistant_id()
            if ext_id:
                success = self._service.enable_extension(ext_id)
                if success:
                    # Apply good defaults
                    self._service.apply_tiling_assistant_defaults()
                GLib.idle_add(self._on_extension_complete, success)
            else:
                GLib.idle_add(self._on_extension_complete, False)

        GLib.Thread.new("enable-extension", enable)

    def _on_extension_complete(self, success: bool) -> None:
        """Handle extension enable completion."""
        if success:
            self.set_visible(False)
            self.emit("tiling-configured", "extension")
        else:
            self._extension_button.set_sensitive(True)
            if self._tiling_info and self._tiling_info.extension_installed:
                self._extension_button.set_label(f"Enable {self._tiling_info.extension_installed}")
            else:
                self._extension_button.set_label("Setup Tiling Assistant")

    def _on_dismiss(self, button: Gtk.Button) -> None:
        """Dismiss the banner."""
        self.set_visible(False)
