# SPDX-License-Identifier: GPL-3.0-or-later
"""Main application class."""

import logging
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from dailydriver.window import DailyDriverWindow

logger = logging.getLogger(__name__)


class DailyDriverApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self, version: str) -> None:
        super().__init__(
            application_id="io.github.gregfelice.DailyDriver",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.version = version
        self._window: DailyDriverWindow | None = None
        self._show_cheat_sheet = False

        # Add command line options
        self.add_main_option(
            "cheat-sheet",
            ord("c"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Show the keyboard shortcut cheat sheet",
            None,
        )

        # Setup actions
        self._setup_actions()

    def _setup_actions(self) -> None:
        """Set up application actions."""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<primary>q"])

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        """Handle command line arguments."""
        options = command_line.get_options_dict()

        # Check for --cheat-sheet flag
        self._show_cheat_sheet = options.contains("cheat-sheet")

        self.activate()
        return 0

    def do_activate(self) -> None:
        """Activate the application."""
        if not self._window:
            self._window = DailyDriverWindow(application=self)

        # Show cheat sheet if requested
        if self._show_cheat_sheet:
            self._window.show_cheat_sheet()
            self._show_cheat_sheet = False  # Reset for next activation

        self._window.present()

    def do_shutdown(self) -> None:
        """Clean up on application shutdown."""
        Adw.Application.do_shutdown(self)

    def _on_about(self, action: Gio.SimpleAction, param: GLib.Variant | None) -> None:
        """Show about dialog."""
        about = Adw.AboutDialog(
            application_name="Daily Driver",
            application_icon="io.github.gregfelice.DailyDriver",
            developer_name="Greg Felice",
            version=self.version,
            developers=["Greg Felice"],
            copyright="Copyright 2025 Greg Felice",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/gregfelice/dailydriver",
            issue_url="https://github.com/gregfelice/dailydriver/issues",
        )
        about.present(self._window)


def main(version: str | None = None) -> int:
    """Application entry point.

    Args:
        version: Version string. If None, reads from package metadata.
            The meson launcher script passes the version from configure_file.
    """
    if version is None:
        try:
            from importlib.metadata import version as get_version

            version = get_version("dailydriver")
        except Exception:
            version = "0.1.0"
    app = DailyDriverApplication(version)
    return app.run(sys.argv)
