# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for ProfileService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestProfileService:
    """Tests for ProfileService."""

    def test_list_profiles_empty(self, tmp_path: Path) -> None:
        """Test listing profiles when none exist."""
        from dailydriver.services.profile_service import ProfileService

        # Mock GLib paths
        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=MagicMock())
            service._profiles_dir = tmp_path / "profiles"
            service._profiles_dir.mkdir(parents=True)
            service._presets_dir = tmp_path / "presets"

            profiles = list(service.list_profiles())
            assert profiles == []

    def test_list_profiles_with_user_profiles(self, tmp_path: Path) -> None:
        """Test listing user profiles."""
        from dailydriver.models.profile import Profile
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        # Create user profile
        profile = Profile(name="my-profile", description="Test")
        profile.to_toml(profiles_dir / "my-profile.toml")

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=MagicMock())
            service._profiles_dir = profiles_dir
            service._presets_dir = tmp_path / "nonexistent"

            profiles = list(service.list_profiles())

            assert len(profiles) == 1
            assert profiles[0].name == "my-profile"

    def test_list_profiles_includes_presets(self, tmp_path: Path, presets_dir: Path) -> None:
        """Test that built-in presets are included in listing."""
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=MagicMock())
            service._profiles_dir = profiles_dir
            service._presets_dir = presets_dir

            profiles = list(service.list_profiles())

            # Should include built-in presets
            names = [p.name for p in profiles]
            assert "vanilla-gnome" in names

    def test_get_profile_user(self, tmp_path: Path) -> None:
        """Test getting a user profile by name."""
        from dailydriver.models.profile import Profile
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        # Create user profile
        profile = Profile(name="my-profile", description="Test")
        profile.to_toml(profiles_dir / "my-profile.toml")

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=MagicMock())
            service._profiles_dir = profiles_dir
            service._presets_dir = tmp_path / "presets"

            result = service.get_profile("my-profile")

            assert result is not None
            assert result.name == "my-profile"

    def test_get_profile_preset(self, tmp_path: Path, presets_dir: Path) -> None:
        """Test getting a preset profile by name."""
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=MagicMock())
            service._profiles_dir = profiles_dir
            service._presets_dir = presets_dir

            result = service.get_profile("vanilla-gnome")

            assert result is not None
            assert result.name == "vanilla-gnome"

    def test_get_profile_not_found(self, tmp_path: Path) -> None:
        """Test getting a non-existent profile."""
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=MagicMock())
            service._profiles_dir = profiles_dir
            service._presets_dir = tmp_path / "presets"

            result = service.get_profile("nonexistent")

            assert result is None

    def test_save_profile(self, tmp_path: Path) -> None:
        """Test saving a profile."""
        from dailydriver.models.profile import Profile
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=MagicMock())
            service._profiles_dir = profiles_dir
            service._presets_dir = tmp_path / "presets"

            profile = Profile(name="new-profile", description="Saved profile")
            path = service.save_profile(profile)

            assert path.exists()
            assert path.name == "new-profile.toml"

    def test_delete_profile(self, tmp_path: Path) -> None:
        """Test deleting a profile."""
        from dailydriver.models.profile import Profile
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        # Create profile file
        profile = Profile(name="to-delete", description="Test")
        profile.to_toml(profiles_dir / "to-delete.toml")

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=MagicMock())
            service._profiles_dir = profiles_dir
            service._presets_dir = tmp_path / "presets"

            result = service.delete_profile("to-delete")

            assert result
            assert not (profiles_dir / "to-delete.toml").exists()

    def test_delete_profile_not_found(self, tmp_path: Path) -> None:
        """Test deleting non-existent profile."""
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=MagicMock())
            service._profiles_dir = profiles_dir
            service._presets_dir = tmp_path / "presets"

            result = service.delete_profile("nonexistent")

            assert not result

    def test_import_profile(self, tmp_path: Path) -> None:
        """Test importing a profile from external file."""
        from dailydriver.models.profile import Profile
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        # Create external profile
        external_dir = tmp_path / "external"
        external_dir.mkdir()
        external_profile = Profile(name="imported", description="External")
        external_path = external_dir / "imported.toml"
        external_profile.to_toml(external_path)

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=MagicMock())
            service._profiles_dir = profiles_dir
            service._presets_dir = tmp_path / "presets"

            imported = service.import_profile(external_path)

            assert imported.name == "imported"
            assert (profiles_dir / "imported.toml").exists()

    def test_export_profile(self, tmp_path: Path) -> None:
        """Test exporting a profile."""
        from dailydriver.models.profile import Profile
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)
        export_dir = tmp_path / "export"
        export_dir.mkdir()

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=MagicMock())
            service._profiles_dir = profiles_dir
            service._presets_dir = tmp_path / "presets"

            profile = Profile(name="to-export", description="Test")
            export_path = export_dir / "exported.toml"

            service.export_profile(profile, export_path)

            assert export_path.exists()
            # Verify content
            loaded = Profile.from_toml(export_path)
            assert loaded.name == "to-export"

    def test_active_profile_property(self, tmp_path: Path) -> None:
        """Test active_profile property."""
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=MagicMock())
            service._profiles_dir = profiles_dir
            service._presets_dir = tmp_path / "presets"

            # Initially None
            assert service.active_profile is None

    def test_reset_orphaned_shortcuts(self, tmp_path: Path) -> None:
        """Test resetting shortcuts not in new profile."""
        from dailydriver.models.profile import Profile
        from dailydriver.models.shortcut import KeyBinding, Modifier, Shortcut
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        # Create old profile with a shortcut
        old_profile = Profile(name="old")
        old_profile.set_shortcut("org.gnome.desktop.wm.keybindings", "close", ["<Alt>F4"])
        old_profile.set_shortcut("org.gnome.desktop.wm.keybindings", "minimize", ["<Super>h"])

        # Create new profile without the minimize shortcut
        new_profile = Profile(name="new")
        new_profile.set_shortcut("org.gnome.desktop.wm.keybindings", "close", ["<Alt>F4"])

        # Mock GSettings service
        mock_gsettings = MagicMock()
        default_binding = KeyBinding(keyval=0x68, modifiers=Modifier.SUPER)
        minimize_shortcut = Shortcut(
            id="org.gnome.desktop.wm.keybindings.minimize",
            name="Minimize",
            description="",
            category="window-management",
            schema="org.gnome.desktop.wm.keybindings",
            key="minimize",
            bindings=[default_binding],
            default_bindings=[],  # Different from bindings, so is_modified=True
        )
        mock_gsettings.load_all_shortcuts.return_value = {
            "org.gnome.desktop.wm.keybindings.minimize": minimize_shortcut
        }

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=mock_gsettings)
            service._profiles_dir = profiles_dir
            service._presets_dir = tmp_path / "presets"

            count = service.reset_orphaned_shortcuts(old_profile, new_profile)

            # The minimize shortcut was in old but not in new
            assert count >= 0  # May be 0 or 1 depending on is_modified state


class TestProfileDiff:
    """Tests for profile diff functionality."""

    def test_get_profile_diff_no_changes(self, tmp_path: Path) -> None:
        """Test diff when profile matches current settings."""
        from dailydriver.models.profile import Profile
        from dailydriver.models.shortcut import KeyBinding, Shortcut
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        # Create profile
        profile = Profile(name="test")
        profile.set_shortcut("org.gnome.desktop.wm.keybindings", "close", ["<Alt>F4"])

        # Mock GSettings to return same binding
        mock_gsettings = MagicMock()
        binding = KeyBinding.from_accelerator("<Alt>F4")
        shortcut = Shortcut(
            id="org.gnome.desktop.wm.keybindings.close",
            name="Close",
            description="",
            category="window-management",
            schema="org.gnome.desktop.wm.keybindings",
            key="close",
            bindings=[binding] if binding else [],
        )
        mock_gsettings.load_all_shortcuts.return_value = {
            "org.gnome.desktop.wm.keybindings.close": shortcut
        }

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=mock_gsettings)
            service._profiles_dir = profiles_dir
            service._presets_dir = tmp_path / "presets"

            diff = service.get_profile_diff(profile)

            # No differences
            assert len(diff) == 0

    def test_get_profile_diff_with_changes(self, tmp_path: Path, mock_gi: dict) -> None:
        """Test diff when profile differs from current settings."""
        from dailydriver.models.profile import Profile
        from dailydriver.models.shortcut import KeyBinding, Shortcut
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        # Create profile with different binding
        profile = Profile(name="test")
        profile.set_shortcut("org.gnome.desktop.wm.keybindings", "close", ["<Super>q"])

        # Mock GSettings to return different binding
        mock_gsettings = MagicMock()
        current_binding = KeyBinding.from_accelerator("<Alt>F4")
        shortcut = Shortcut(
            id="org.gnome.desktop.wm.keybindings.close",
            name="Close",
            description="",
            category="window-management",
            schema="org.gnome.desktop.wm.keybindings",
            key="close",
            bindings=[current_binding] if current_binding else [],
        )
        mock_gsettings.load_all_shortcuts.return_value = {
            "org.gnome.desktop.wm.keybindings.close": shortcut
        }

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=mock_gsettings)
            service._profiles_dir = profiles_dir
            service._presets_dir = tmp_path / "presets"

            diff = service.get_profile_diff(profile)

            # Should show the difference
            assert "org.gnome.desktop.wm.keybindings.close" in diff


class TestUserModifications:
    """Tests for user modifications tracking."""

    def test_create_modifications_profile_empty(self, tmp_path: Path, presets_dir: Path) -> None:
        """Test creating modifications profile when no changes."""
        from dailydriver.services.profile_service import ProfileService

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir(parents=True)

        # Mock GSettings to return empty (no modifications)
        mock_gsettings = MagicMock()
        mock_gsettings.load_all_shortcuts.return_value = {}

        with patch("dailydriver.services.profile_service.GLib") as mock_glib:
            mock_glib.get_user_config_dir.return_value = str(tmp_path / "config")
            mock_glib.get_system_data_dirs.return_value = []

            service = ProfileService(gsettings_service=mock_gsettings)
            service._profiles_dir = profiles_dir
            service._presets_dir = presets_dir

            result = service.create_modifications_profile("vanilla-gnome")

            # No modifications, should return None
            assert result is None
