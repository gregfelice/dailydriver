# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration tests for preset application workflow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestPresetLoading:
    """Tests for preset loading."""

    def test_all_presets_load_successfully(self, presets_dir: Path) -> None:
        """Test that all preset files load without errors."""
        from dailydriver.models.profile import Profile

        for preset_path in presets_dir.glob("*.toml"):
            profile = Profile.from_toml(preset_path)

            # Basic validation
            assert profile.name, f"Preset {preset_path.name} has no name"
            assert isinstance(profile.shortcuts, dict)
            assert len(profile.shortcuts) > 0, f"Preset {preset_path.name} has no shortcuts"

    def test_preset_shortcut_format_valid(self, presets_dir: Path, mock_gi: dict) -> None:
        """Test that all shortcuts in presets have valid format."""
        from dailydriver.models.profile import Profile
        from dailydriver.models.shortcut import KeyBinding

        for preset_path in presets_dir.glob("*.toml"):
            profile = Profile.from_toml(preset_path)

            for storage_key, accelerators in profile.shortcuts.items():
                # Verify storage key format
                assert "." in storage_key, f"Invalid key format: {storage_key}"

                # Verify accelerators (empty list is valid for disabled)
                for accel in accelerators:
                    if accel:  # Non-empty should parse
                        binding = KeyBinding.from_accelerator(accel)
                        assert binding is not None, (
                            f"Invalid accelerator in {preset_path.name}: {accel}"
                        )


class TestPresetApplication:
    """Tests for applying presets to system."""

    def test_vanilla_gnome_applies(self, tmp_path: Path, presets_dir: Path) -> None:
        """Test applying vanilla-gnome preset."""
        from dailydriver.models.profile import Profile
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        # Load preset
        preset = Profile.from_toml(presets_dir / "vanilla-gnome.toml")

        # Create mock GSettings service that records saves
        saved_shortcuts: dict[str, list[str]] = {}

        def mock_save(shortcut: MagicMock) -> bool:
            saved_shortcuts[shortcut.id] = shortcut.accelerators
            return True

        mock_gsettings = MagicMock()
        mock_gsettings.load_all_shortcuts.return_value = {}
        mock_gsettings.save_shortcut.side_effect = mock_save

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=mock_gsettings)
            service._profiles_dir = profiles_dir
            service._presets_dir = presets_dir

            # Apply would work if there were matching shortcuts
            # This is a smoke test that the code path runs
            service.apply_profile(preset)

            # The profile is now active
            assert service.active_profile == preset


class TestPresetDiff:
    """Tests for comparing presets with current settings."""

    def test_diff_shows_changes(self, tmp_path: Path, presets_dir: Path, mock_gi: dict) -> None:
        """Test that diff correctly identifies changes."""
        from dailydriver.models.profile import Profile
        from dailydriver.models.shortcut import KeyBinding, Shortcut
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        # Load preset
        preset = Profile.from_toml(presets_dir / "vanilla-gnome.toml")

        # Create mock GSettings that returns different value
        mock_gsettings = MagicMock()

        # Return a shortcut with different binding
        current_binding = KeyBinding.from_accelerator("<Super>c")  # Different from preset
        mock_shortcut = Shortcut(
            id="org.gnome.desktop.wm.keybindings.close",
            name="Close",
            description="",
            category="window-management",
            schema="org.gnome.desktop.wm.keybindings",
            key="close",
            bindings=[current_binding] if current_binding else [],
        )
        mock_gsettings.load_all_shortcuts.return_value = {
            "org.gnome.desktop.wm.keybindings.close": mock_shortcut
        }

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=mock_gsettings)
            service._profiles_dir = profiles_dir
            service._presets_dir = presets_dir

            diff = service.get_profile_diff(preset)

            # Should find the difference for close shortcut
            assert "org.gnome.desktop.wm.keybindings.close" in diff


class TestPresetSwitching:
    """Tests for switching between presets."""

    def test_switch_presets(self, tmp_path: Path, presets_dir: Path) -> None:
        """Test switching from one preset to another."""
        from dailydriver.models.profile import Profile

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        # Load both presets
        vanilla = Profile.from_toml(presets_dir / "vanilla-gnome.toml")
        hyprland = Profile.from_toml(presets_dir / "hyprland-style.toml")

        # Both should have some shortcuts
        assert len(vanilla.shortcuts) > 0
        assert len(hyprland.shortcuts) > 0

        # Some shortcuts should be different between presets
        # (This is a basic sanity check)
        vanilla_keys = set(vanilla.shortcuts.keys())
        hyprland_keys = set(hyprland.shortcuts.keys())

        # There should be overlap
        overlap = vanilla_keys & hyprland_keys
        assert len(overlap) > 0, "Presets should have some common shortcuts"
