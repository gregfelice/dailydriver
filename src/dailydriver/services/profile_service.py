# SPDX-License-Identifier: GPL-3.0-or-later
"""Service for managing keyboard configuration profiles."""

from collections.abc import Generator
from pathlib import Path

from gi.repository import GLib

from dailydriver.models import Profile, Shortcut
from dailydriver.services.gsettings_service import GSettingsService


class ProfileService:
    """Service for loading, saving, and applying profiles."""

    def __init__(self, gsettings_service: GSettingsService | None = None) -> None:
        self._gsettings = gsettings_service or GSettingsService()
        self._profiles_dir = self._get_profiles_dir()
        self._presets_dir = self._get_presets_dir()
        self._active_profile: Profile | None = None

    def _get_profiles_dir(self) -> Path:
        """Get the user profiles directory."""
        config_dir = Path(GLib.get_user_config_dir()) / "dailydriver" / "profiles"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def _get_presets_dir(self) -> Path:
        """Get the built-in presets directory."""
        # In installed mode, this would be in the data directory
        # For development, use the source tree
        data_dirs = GLib.get_system_data_dirs()
        for data_dir in data_dirs:
            preset_dir = Path(data_dir) / "dailydriver" / "presets"
            if preset_dir.exists():
                return preset_dir

        # Fallback to relative path for development
        return Path(__file__).parent.parent / "resources" / "presets"

    def list_profiles(self) -> Generator[Profile, None, None]:
        """List all available profiles (user + presets)."""
        # User profiles
        for path in sorted(self._profiles_dir.glob("*.toml")):
            try:
                yield Profile.from_toml(path)
            except Exception:
                continue  # Skip invalid profiles

        # Built-in presets
        if self._presets_dir.exists():
            for path in sorted(self._presets_dir.glob("*.toml")):
                try:
                    yield Profile.from_toml(path)
                except Exception:
                    continue

    def get_profile(self, name: str) -> Profile | None:
        """Get a profile by name."""
        # Check user profiles first
        user_path = self._profiles_dir / f"{name}.toml"
        if user_path.exists():
            return Profile.from_toml(user_path)

        # Check presets
        preset_path = self._presets_dir / f"{name}.toml"
        if preset_path.exists():
            return Profile.from_toml(preset_path)

        return None

    def save_profile(self, profile: Profile) -> Path:
        """Save a profile to disk."""
        path = self._profiles_dir / f"{profile.name}.toml"
        profile.to_toml(path)
        return path

    def delete_profile(self, name: str) -> bool:
        """Delete a user profile."""
        path = self._profiles_dir / f"{name}.toml"
        if path.exists():
            path.unlink()
            return True
        return False

    def create_from_current(self, name: str, description: str = "") -> Profile:
        """Create a profile from current GSettings state."""
        shortcuts = self._gsettings.load_all_shortcuts()

        profile = Profile(name=name, description=description)

        for shortcut in shortcuts.values():
            if shortcut.bindings:
                profile.set_shortcut(shortcut.schema, shortcut.key, shortcut.accelerators)

        return profile

    def apply_profile(self, profile: Profile, clean_slate: bool | None = None) -> dict[str, Shortcut]:
        """Apply a profile, returning shortcuts that were changed.

        Args:
            profile: The profile to apply.
            clean_slate: If True, disable ALL shortcuts first, then apply only
                what's defined in the profile. If None, auto-detect based on
                whether profile is a preset (has metadata.preset = True).
        """
        # Auto-detect clean slate mode for presets
        if clean_slate is None:
            clean_slate = profile.metadata.get("preset", False)

        current_shortcuts = self._gsettings.load_all_shortcuts()
        changed: dict[str, Shortcut] = {}

        # Phase 1: If clean slate, disable all shortcuts first
        if clean_slate:
            for shortcut_id, shortcut in current_shortcuts.items():
                # Skip custom keybindings - they're user-defined, not system shortcuts
                if shortcut.schema == "custom":
                    continue

                # Only clear if shortcut currently has bindings
                if shortcut.bindings:
                    shortcut.bindings = []
                    if self._gsettings.save_shortcut(shortcut):
                        changed[shortcut_id] = shortcut

        # Phase 2: Apply shortcuts from profile
        from dailydriver.models import KeyBinding

        for storage_key, accelerators in profile.shortcuts.items():
            # Parse storage key
            parts = storage_key.rsplit(".", 1)
            if len(parts) != 2:
                continue
            schema, key = parts

            # Find matching shortcut
            shortcut_id = f"{schema}.{key}"
            if shortcut_id not in current_shortcuts:
                continue

            shortcut = current_shortcuts[shortcut_id]
            old_accelerators = shortcut.accelerators

            # Normalize profile accelerators for comparison (GTK reorders modifiers)
            normalized_profile = set(
                b.to_accelerator()
                for accel in accelerators
                if (b := KeyBinding.from_accelerator(accel))
            )

            # Check if different (in clean_slate mode, old_accelerators is [] so always apply)
            if set(old_accelerators) != normalized_profile:
                # Update bindings
                shortcut.bindings = [
                    b for accel in accelerators if (b := KeyBinding.from_accelerator(accel))
                ]

                # Save to GSettings
                if self._gsettings.save_shortcut(shortcut):
                    changed[shortcut_id] = shortcut

        self._active_profile = profile
        return changed

    def _normalize_accelerator(self, accel: str) -> str:
        """Normalize accelerator string through GTK parsing."""
        from dailydriver.models import KeyBinding

        binding = KeyBinding.from_accelerator(accel)
        return binding.to_accelerator() if binding else accel

    def get_profile_diff(self, profile: Profile) -> dict[str, tuple[list[str], list[str]]]:
        """
        Compare a profile with current settings.

        Returns dict of shortcut_id -> (current_accelerators, profile_accelerators)
        """
        current_shortcuts = self._gsettings.load_all_shortcuts()
        diff: dict[str, tuple[list[str], list[str]]] = {}

        for storage_key, profile_accels in profile.shortcuts.items():
            # Parse storage key
            parts = storage_key.rsplit(".", 1)
            if len(parts) != 2:
                continue
            schema, key = parts

            shortcut_id = f"{schema}.{key}"
            if shortcut_id not in current_shortcuts:
                continue

            current_accels = current_shortcuts[shortcut_id].accelerators

            # Normalize both sides for comparison (GTK reorders modifiers)
            current_normalized = set(current_accels)
            profile_normalized = set(self._normalize_accelerator(a) for a in profile_accels)

            if current_normalized != profile_normalized:
                diff[shortcut_id] = (current_accels, profile_accels)

        return diff

    def import_profile(self, path: Path) -> Profile:
        """Import a profile from an external file."""
        profile = Profile.from_toml(path)

        # Save to user profiles directory
        self.save_profile(profile)

        return profile

    def export_profile(self, profile: Profile, path: Path) -> None:
        """Export a profile to an external file."""
        profile.to_toml(path)

    def reset_orphaned_shortcuts(self, old_profile: Profile, new_profile: Profile) -> int:
        """
        Reset shortcuts that were in old_profile but not in new_profile to GNOME defaults.

        Returns the number of shortcuts reset.
        """
        old_keys = set(old_profile.shortcuts.keys())
        new_keys = set(new_profile.shortcuts.keys())
        orphaned_keys = old_keys - new_keys

        if not orphaned_keys:
            return 0

        current_shortcuts = self._gsettings.load_all_shortcuts()
        reset_count = 0

        for storage_key in orphaned_keys:
            if storage_key in current_shortcuts:
                shortcut = current_shortcuts[storage_key]
                # Only reset if it's currently modified from GNOME default
                if shortcut.is_modified:
                    shortcut.reset()
                    self._gsettings.save_shortcut(shortcut)
                    reset_count += 1

        return reset_count

    @property
    def active_profile(self) -> Profile | None:
        """Get the currently active profile."""
        return self._active_profile

    def get_user_modifications(
        self, base_preset_name: str
    ) -> dict[str, tuple[list[str], list[str]]]:
        """
        Get user modifications compared to a base preset.

        Returns dict of shortcut_id -> (current_accelerators, expected_accelerators)
        Includes:
        - Shortcuts defined in preset that differ from preset values
        - Shortcuts NOT in preset that differ from GNOME defaults (preset expects defaults)
        """
        preset = self.get_profile(base_preset_name)
        if not preset:
            return {}

        current_shortcuts = self._gsettings.load_all_shortcuts()
        diff: dict[str, tuple[list[str], list[str]]] = {}

        # Normalize preset shortcuts for comparison
        preset_normalized = {}
        for storage_key, accels in preset.shortcuts.items():
            preset_normalized[storage_key] = set(self._normalize_accelerator(a) for a in accels)

        for shortcut_id, shortcut in current_shortcuts.items():
            current_accels = set(shortcut.accelerators)

            if shortcut_id in preset_normalized:
                # Shortcut is defined in preset - compare against preset value
                expected = preset_normalized[shortcut_id]
                if current_accels != expected:
                    diff[shortcut_id] = (shortcut.accelerators, list(expected))
            else:
                # Shortcut not in preset - preset expects GNOME default
                if shortcut.is_modified:
                    # User changed it from GNOME default
                    default_accels = [b.to_accelerator() for b in shortcut.default_bindings]
                    diff[shortcut_id] = (shortcut.accelerators, default_accels)

        return diff

    def create_modifications_profile(
        self, base_preset_name: str, name: str = "", description: str = ""
    ) -> Profile | None:
        """
        Create a profile containing only user modifications from a base preset.

        Returns None if there are no modifications.
        """
        diff = self.get_user_modifications(base_preset_name)
        if not diff:
            return None

        if not name:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            name = f"user-mods-{base_preset_name}-{timestamp}"

        if not description:
            description = f"User modifications from {base_preset_name} preset"

        profile = Profile(
            name=name,
            description=description,
            metadata={"base_preset": base_preset_name, "type": "user-modifications"},
        )

        # Only include the modified shortcuts (current values, not preset values)
        for shortcut_id, (current_accels, _preset_accels) in diff.items():
            parts = shortcut_id.rsplit(".", 1)
            if len(parts) == 2:
                schema, key = parts
                profile.set_shortcut(schema, key, current_accels)

        return profile

    def export_and_clear_modifications(self, base_preset_name: str) -> tuple[Path | None, int]:
        """
        Export user modifications (deviations from current preset) and reset them.

        Returns (export_path, num_modifications).
        If no modifications, returns (None, 0).
        """
        # Get user modifications compared to the current preset
        user_mods = self.get_user_modifications(base_preset_name)

        if not user_mods:
            return None, 0

        # Create profile with user modifications (current values)
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = f"user-mods-{base_preset_name}-{timestamp}"

        mods_profile = Profile(
            name=name,
            description=f"User modifications exported from {base_preset_name} preset",
            metadata={"base_preset": base_preset_name, "type": "user-modifications"},
        )

        for shortcut_id, (current_accels, _expected_accels) in user_mods.items():
            parts = shortcut_id.rsplit(".", 1)
            if len(parts) == 2:
                schema, key = parts
                mods_profile.set_shortcut(schema, key, current_accels)

        num_mods = len(mods_profile.shortcuts)

        # Save to user profiles directory
        export_path = self.save_profile(mods_profile)

        # Reset shortcuts not in preset to GNOME defaults
        base_preset = self.get_profile(base_preset_name)
        preset_keys = set(base_preset.shortcuts.keys()) if base_preset else set()

        current_shortcuts = self._gsettings.load_all_shortcuts()
        for shortcut_id in user_mods.keys():
            if shortcut_id not in preset_keys:
                # Not in preset - reset to GNOME default
                if shortcut_id in current_shortcuts:
                    shortcut = current_shortcuts[shortcut_id]
                    shortcut.reset()
                    self._gsettings.save_shortcut(shortcut)

        # Apply the base preset (for shortcuts defined in preset)
        if base_preset:
            self.apply_profile(base_preset)

        return export_path, num_mods
