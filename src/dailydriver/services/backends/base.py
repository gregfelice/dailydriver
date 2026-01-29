# SPDX-License-Identifier: GPL-3.0-or-later
"""Abstract base class for desktop shortcuts backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dailydriver.models import KeyBinding, Shortcut, ShortcutCategory


class ShortcutsBackend(ABC):
    """Abstract interface for reading and writing desktop shortcuts.

    Implementations exist for different desktop environments:
    - GnomeShortcutsBackend: GNOME (gsettings/dconf)
    - KDEShortcutsBackend: KDE Plasma (kglobalshortcutsrc/kglobalacceld)
    """

    # --- Categories ---

    @abstractmethod
    def get_categories(self) -> list[ShortcutCategory]:
        """Get all shortcut categories.

        Returns:
            List of ShortcutCategory objects defining the available categories.
        """
        ...

    # --- Shortcuts ---

    @abstractmethod
    def load_all_shortcuts(self) -> dict[str, Shortcut]:
        """Load all shortcuts from the desktop environment.

        Returns:
            Dict mapping shortcut ID to Shortcut object.
        """
        ...

    @abstractmethod
    def save_shortcut(self, shortcut: Shortcut) -> bool:
        """Save a shortcut binding.

        Args:
            shortcut: The shortcut with updated bindings to save.

        Returns:
            True if saved successfully, False otherwise.
        """
        ...

    @abstractmethod
    def reset_shortcut(self, shortcut: Shortcut) -> bool:
        """Reset a shortcut to its default binding.

        Args:
            shortcut: The shortcut to reset.

        Returns:
            True if reset successfully, False otherwise.
        """
        ...

    @abstractmethod
    def find_conflicts(
        self, binding: KeyBinding, exclude_id: str | None = None
    ) -> list[Shortcut]:
        """Find shortcuts that conflict with a given binding.

        Args:
            binding: The key binding to check for conflicts.
            exclude_id: Optional shortcut ID to exclude from conflict check.

        Returns:
            List of shortcuts that use the same binding.
        """
        ...

    # --- Custom Keybindings ---

    @abstractmethod
    def get_custom_keybindings(self) -> list[dict]:
        """Get all custom (user-defined) keybindings.

        Returns:
            List of dicts with keys: path, name, command, binding
        """
        ...

    @abstractmethod
    def add_custom_keybinding(
        self, name: str, command: str, binding: str
    ) -> str | None:
        """Add a new custom keybinding.

        Args:
            name: Display name for the shortcut.
            command: Shell command to execute.
            binding: GTK accelerator string (e.g., '<Super>Return').

        Returns:
            The path/ID of the new binding, or None on failure.
        """
        ...

    @abstractmethod
    def update_custom_keybinding(
        self,
        path: str,
        name: str | None = None,
        command: str | None = None,
        binding: str | None = None,
    ) -> bool:
        """Update an existing custom keybinding.

        Args:
            path: The path/ID of the binding to update.
            name: New display name (or None to keep existing).
            command: New command (or None to keep existing).
            binding: New binding (or None to keep existing).

        Returns:
            True if updated successfully, False otherwise.
        """
        ...

    @abstractmethod
    def delete_custom_keybinding(self, path: str) -> bool:
        """Delete a custom keybinding.

        Args:
            path: The path/ID of the binding to delete.

        Returns:
            True if deleted successfully, False otherwise.
        """
        ...

    # --- Utility Methods ---

    def find_custom_keybinding(self, name: str) -> dict | None:
        """Find a custom keybinding by name.

        Args:
            name: The display name to search for.

        Returns:
            The binding dict if found, None otherwise.
        """
        for binding in self.get_custom_keybindings():
            if binding["name"] == name:
                return binding
        return None

    def find_custom_keybinding_by_type(self, app_type: str) -> dict | None:
        """Find a custom keybinding by application type.

        Args:
            app_type: One of 'terminal', 'file_manager', 'browser', 'music', 'cheat_sheet'.

        Returns:
            The binding dict if found, None otherwise.
        """
        patterns = {
            "terminal": ["terminal", "term", "console", "shell"],
            "file_manager": [
                "file",
                "files",
                "folder",
                "nautilus",
                "thunar",
                "dolphin",
                "manager",
            ],
            "browser": ["browser", "firefox", "chrome", "chromium", "web", "internet"],
            "cheat_sheet": ["cheat", "dailydriver", "shortcut", "help"],
            "music": ["music", "spotify", "player", "rhythmbox", "tidal", "audio"],
        }

        search_terms = patterns.get(app_type, [])
        for binding in self.get_custom_keybindings():
            name_lower = binding["name"].lower()
            cmd_lower = binding["command"].lower()
            if any(term in name_lower or term in cmd_lower for term in search_terms):
                return binding
        return None
