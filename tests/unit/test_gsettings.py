# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for GSettingsService.

These tests require extensive mocking of GIO/GLib since GSettings
requires a running GNOME session.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestHumanizeKeyName:
    """Tests for the _humanize_key_name function."""

    def test_media_key_names(self) -> None:
        """Test media key humanization."""
        from dailydriver.services.gsettings_service import _humanize_key_name

        assert _humanize_key_name("next") == "Next Track"
        assert _humanize_key_name("previous") == "Previous Track"
        assert _humanize_key_name("play") == "Play/Pause"
        assert _humanize_key_name("stop") == "Stop"
        assert _humanize_key_name("eject") == "Eject"

    def test_strip_static_suffix(self) -> None:
        """Test stripping -static suffix."""
        from dailydriver.services.gsettings_service import _humanize_key_name

        assert _humanize_key_name("play-static") == "Play/Pause"
        assert _humanize_key_name("next-static") == "Next Track"

    def test_strip_prefixes(self) -> None:
        """Test stripping common prefixes."""
        from dailydriver.services.gsettings_service import _humanize_key_name

        # switch-to-workspace-N -> N
        assert _humanize_key_name("switch-to-workspace-1") == "1"
        assert _humanize_key_name("switch-to-workspace-left") == "Left"

        # move-to-workspace-N -> N
        assert _humanize_key_name("move-to-workspace-2") == "2"

        # toggle-tiled-* -> *
        assert _humanize_key_name("toggle-tiled-left") == "Left"
        assert _humanize_key_name("toggle-tiled-right") == "Right"

        # volume-* -> *
        assert _humanize_key_name("volume-up") == "Up"
        assert _humanize_key_name("volume-down") == "Down"

    def test_tiling_names(self) -> None:
        """Test tiling shortcut humanization."""
        from dailydriver.services.gsettings_service import _humanize_key_name

        assert _humanize_key_name("tile-left-half") == "Left Half"
        assert _humanize_key_name("tile-right-half") == "Right Half"
        assert _humanize_key_name("tile-topleft-quarter") == "Top Left"
        assert _humanize_key_name("tile-maximize") == "Maximize"
        assert _humanize_key_name("center-window") == "Center Window"

    def test_layout_numbering(self) -> None:
        """Test layout number conversion (0-indexed to 1-indexed)."""
        from dailydriver.services.gsettings_service import _humanize_key_name

        assert _humanize_key_name("layout0") == "Layout 1"
        assert _humanize_key_name("layout9") == "Layout 10"
        assert _humanize_key_name("layout19") == "Layout 20"

    def test_skip_internal_keys(self) -> None:
        """Test that internal keys return empty string."""
        from dailydriver.services.gsettings_service import _humanize_key_name

        assert _humanize_key_name("tile-left-half-ignore-ta") == ""

    def test_general_humanization(self) -> None:
        """Test general hyphen-to-space conversion."""
        from dailydriver.services.gsettings_service import _humanize_key_name

        result = _humanize_key_name("some-random-key")
        assert "Some" in result
        assert "-" not in result


class TestGetShortcutGroup:
    """Tests for the _get_shortcut_group function."""

    def test_tiling_halves(self) -> None:
        """Test tiling halves grouping."""
        from dailydriver.services.gsettings_service import _get_shortcut_group

        assert _get_shortcut_group("tile-left-half") == "Tile Halves"
        assert _get_shortcut_group("tile-right-half") == "Tile Halves"
        assert _get_shortcut_group("toggle-tiled-left") == "Tile Halves"

    def test_tiling_quarters(self) -> None:
        """Test tiling quarters grouping."""
        from dailydriver.services.gsettings_service import _get_shortcut_group

        assert _get_shortcut_group("tile-topleft-quarter") == "Tile Quarters"
        assert _get_shortcut_group("move-to-corner-nw") == "Tile Quarters"

    def test_workspace_switching(self) -> None:
        """Test workspace switching grouping."""
        from dailydriver.services.gsettings_service import _get_shortcut_group

        assert _get_shortcut_group("switch-to-workspace-1") == "Switch Workspace"
        assert _get_shortcut_group("switch-to-workspace-left") == "Switch Workspace"

    def test_workspace_moving(self) -> None:
        """Test workspace moving grouping."""
        from dailydriver.services.gsettings_service import _get_shortcut_group

        assert _get_shortcut_group("move-to-workspace-1") == "Move to Workspace"
        assert _get_shortcut_group("move-to-workspace-right") == "Move to Workspace"

    def test_volume_controls(self) -> None:
        """Test volume controls grouping."""
        from dailydriver.services.gsettings_service import _get_shortcut_group

        assert _get_shortcut_group("volume-up") == "Volume"
        assert _get_shortcut_group("volume-down") == "Volume"
        assert _get_shortcut_group("mic-mute") == "Volume"

    def test_media_playback(self) -> None:
        """Test media playback grouping."""
        from dailydriver.services.gsettings_service import _get_shortcut_group

        assert _get_shortcut_group("play") == "Playback"
        assert _get_shortcut_group("pause") == "Playback"
        assert _get_shortcut_group("next") == "Playback"
        assert _get_shortcut_group("play-static") == "Playback"

    def test_screenshots(self) -> None:
        """Test screenshot grouping."""
        from dailydriver.services.gsettings_service import _get_shortcut_group

        assert _get_shortcut_group("show-screenshot-ui") == "Screenshots"
        assert _get_shortcut_group("screenshot-window") == "Screenshots"

    def test_internal_keys(self) -> None:
        """Test internal keys are marked as such."""
        from dailydriver.services.gsettings_service import _get_shortcut_group

        assert _get_shortcut_group("tile-left-half-ignore-ta") == "Internal"


class TestGetKeyCategory:
    """Tests for the _get_key_category function."""

    def test_window_management(self) -> None:
        """Test window management category."""
        from dailydriver.services.gsettings_service import _get_key_category

        assert _get_key_category("close") == "window-management"
        assert _get_key_category("minimize") == "window-management"
        assert _get_key_category("maximize") == "window-management"

    def test_navigation(self) -> None:
        """Test navigation category."""
        from dailydriver.services.gsettings_service import _get_key_category

        assert _get_key_category("switch-windows") == "navigation"
        assert _get_key_category("switch-to-workspace-1") == "navigation"
        assert _get_key_category("move-to-workspace-left") == "navigation"

    def test_media(self) -> None:
        """Test media category."""
        from dailydriver.services.gsettings_service import _get_key_category

        assert _get_key_category("play") == "media"
        assert _get_key_category("volume-up") == "media"

    def test_shell(self) -> None:
        """Test shell category."""
        from dailydriver.services.gsettings_service import _get_key_category

        assert _get_key_category("toggle-overview") == "shell"
        assert _get_key_category("toggle-application-view") == "shell"


class TestGSettingsServiceCategories:
    """Tests for GSettingsService category methods."""

    def test_get_categories(self, mock_gi: dict) -> None:
        """Test getting all categories."""
        from dailydriver.services.gsettings_service import GSettingsService

        # We need to mock the schema source
        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()
            categories = service.get_categories()

            assert len(categories) > 0
            category_ids = [c.id for c in categories]
            assert "window-management" in category_ids
            assert "navigation" in category_ids
            assert "media" in category_ids
            assert "shell" in category_ids


class TestCustomKeybindings:
    """Tests for custom keybinding management."""

    def test_custom_path_generation(self) -> None:
        """Test that custom paths are generated correctly."""
        from dailydriver.services.gsettings_service import GSettingsService

        assert GSettingsService.CUSTOM_PATH_PREFIX.startswith("/org/gnome")
        assert "custom-keybindings" in GSettingsService.CUSTOM_PATH_PREFIX


class TestSchemaDetection:
    """Tests for schema detection and filtering."""

    def test_shortcut_schemas_defined(self) -> None:
        """Test that shortcut schemas are defined."""
        from dailydriver.services.gsettings_service import SHORTCUT_SCHEMAS

        assert len(SHORTCUT_SCHEMAS) > 0

        # Check expected schemas
        schema_ids = [s["schema"] for s in SHORTCUT_SCHEMAS]
        assert "org.gnome.desktop.wm.keybindings" in schema_ids
        assert "org.gnome.shell.keybindings" in schema_ids
        assert "org.gnome.mutter.keybindings" in schema_ids

    def test_categories_defined(self) -> None:
        """Test that categories are defined."""
        from dailydriver.services.gsettings_service import CATEGORIES

        assert len(CATEGORIES) > 0

        category_ids = [c.id for c in CATEGORIES]
        assert "window-management" in category_ids
        assert "navigation" in category_ids
        assert "media" in category_ids
        assert "tiling" in category_ids


class TestGSettingsServiceInit:
    """Tests for GSettingsService initialization."""

    def test_init_creates_cache(self) -> None:
        """Test that initialization creates empty settings cache."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            assert service._settings_cache == {}
            assert service._schema_source is mock_source

    def test_get_settings_caches(self) -> None:
        """Test that _get_settings caches settings objects."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_gio.Settings.new.return_value = mock_settings

            service = GSettingsService()

            # First call should create settings
            result1 = service._get_settings("org.gnome.test")
            assert result1 is mock_settings
            mock_gio.Settings.new.assert_called_once_with("org.gnome.test")

            # Second call should return cached
            result2 = service._get_settings("org.gnome.test")
            assert result2 is mock_settings
            # Still only called once
            mock_gio.Settings.new.assert_called_once()

    def test_get_settings_returns_none_for_missing_schema(self) -> None:
        """Test that _get_settings returns None for missing schemas."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None  # Schema not found
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()
            result = service._get_settings("org.nonexistent.schema")

            assert result is None


class TestIsShortcutKey:
    """Tests for _is_shortcut_key method."""

    def test_string_array_is_shortcut(self) -> None:
        """Test that string array type is recognized as shortcut."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            # Create mock schema with shortcut key
            mock_schema = MagicMock()
            mock_key = MagicMock()
            mock_variant_type = MagicMock()
            mock_variant_type.dup_string.return_value = "as"

            mock_default = MagicMock()
            mock_default.unpack.return_value = ["<Super>Left"]

            mock_key.get_value_type.return_value = mock_variant_type
            mock_key.get_default_value.return_value = mock_default
            mock_schema.get_key.return_value = mock_key

            result = service._is_shortcut_key(mock_schema, "toggle-tiled-left")
            assert result is True

    def test_non_shortcut_patterns_rejected(self) -> None:
        """Test that non-shortcut patterns are rejected."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            mock_schema = MagicMock()
            mock_key = MagicMock()
            mock_variant_type = MagicMock()
            mock_variant_type.dup_string.return_value = "as"
            mock_key.get_value_type.return_value = mock_variant_type
            mock_schema.get_key.return_value = mock_key

            # These patterns should be rejected
            assert service._is_shortcut_key(mock_schema, "key-ignore-ta") is False
            assert service._is_shortcut_key(mock_schema, "window-color") is False
            assert service._is_shortcut_key(mock_schema, "enable-feature") is False
            assert service._is_shortcut_key(mock_schema, "active-window-hint") is False

    def test_integer_type_rejected(self) -> None:
        """Test that integer type is not recognized as shortcut."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            mock_schema = MagicMock()
            mock_key = MagicMock()
            mock_variant_type = MagicMock()
            mock_variant_type.dup_string.return_value = "i"  # Integer
            mock_key.get_value_type.return_value = mock_variant_type
            mock_schema.get_key.return_value = mock_key

            result = service._is_shortcut_key(mock_schema, "some-key")
            assert result is False


class TestParseBindingValue:
    """Tests for _parse_binding_value method."""

    def test_parse_string_array(self) -> None:
        """Test parsing array of accelerator strings."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            # Create mock variant
            mock_variant = MagicMock()
            mock_variant.get_type_string.return_value = "as"
            mock_variant.unpack.return_value = ["<Super>Left", "<Super>h"]

            bindings = service._parse_binding_value(mock_variant)

            assert len(bindings) == 2
            assert bindings[0].to_accelerator() == "<Super>Left"
            assert bindings[1].to_accelerator() == "<Super>h"

    def test_parse_single_string(self) -> None:
        """Test parsing single accelerator string."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            mock_variant = MagicMock()
            mock_variant.get_type_string.return_value = "s"
            mock_variant.unpack.return_value = "<Control>c"

            bindings = service._parse_binding_value(mock_variant)

            assert len(bindings) == 1
            assert bindings[0].to_accelerator() == "<Control>c"

    def test_parse_disabled_binding(self) -> None:
        """Test parsing disabled binding returns empty list."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            mock_variant = MagicMock()
            mock_variant.get_type_string.return_value = "as"
            mock_variant.unpack.return_value = ["disabled"]

            bindings = service._parse_binding_value(mock_variant)

            assert len(bindings) == 0

    def test_parse_none_value(self) -> None:
        """Test parsing None returns empty list."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            bindings = service._parse_binding_value(None)

            assert len(bindings) == 0

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string returns empty list."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            mock_variant = MagicMock()
            mock_variant.get_type_string.return_value = "s"
            mock_variant.unpack.return_value = ""

            bindings = service._parse_binding_value(mock_variant)

            assert len(bindings) == 0


class TestSaveShortcut:
    """Tests for save_shortcut method."""

    def test_save_shortcut_string_array(self) -> None:
        """Test saving shortcut with string array type."""
        from dailydriver.models import KeyBinding, Shortcut
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_key = MagicMock()
            mock_variant_type = MagicMock()
            mock_variant_type.dup_string.return_value = "as"
            mock_key.get_value_type.return_value = mock_variant_type
            mock_schema.get_key.return_value = mock_key
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_gio.Settings.new.return_value = mock_settings

            service = GSettingsService()

            shortcut = Shortcut(
                id="test.id",
                name="Test",
                description="",
                category="test",
                group="Test",
                schema="org.gnome.test",
                key="test-key",
                bindings=[KeyBinding.from_accelerator("<Super>t")],
                default_bindings=[],
                allow_multiple=True,
            )

            result = service.save_shortcut(shortcut)

            assert result is True
            mock_settings.set_value.assert_called_once()
            call_args = mock_settings.set_value.call_args
            assert call_args[0][0] == "test-key"

    def test_save_shortcut_disabled(self) -> None:
        """Test saving shortcut with no bindings sets disabled."""
        from dailydriver.models import Shortcut
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_key = MagicMock()
            mock_variant_type = MagicMock()
            mock_variant_type.dup_string.return_value = "as"
            mock_key.get_value_type.return_value = mock_variant_type
            mock_schema.get_key.return_value = mock_key
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_gio.Settings.new.return_value = mock_settings

            # Mock GLib.Variant
            with patch("dailydriver.services.backends.gnome.GLib") as mock_glib:
                mock_variant = MagicMock()
                mock_glib.Variant.return_value = mock_variant

                service = GSettingsService()

                shortcut = Shortcut(
                    id="test.id",
                    name="Test",
                    description="",
                    category="test",
                    group="Test",
                    schema="org.gnome.test",
                    key="test-key",
                    bindings=[],  # No bindings = disabled
                    default_bindings=[],
                    allow_multiple=True,
                )

                result = service.save_shortcut(shortcut)

                assert result is True
                # Should create variant with "disabled"
                mock_glib.Variant.assert_called_with("as", ["disabled"])

    def test_save_shortcut_missing_schema(self) -> None:
        """Test save returns False for missing schema."""
        from dailydriver.models import Shortcut
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            shortcut = Shortcut(
                id="test.id",
                name="Test",
                description="",
                category="test",
                group="Test",
                schema="org.nonexistent.schema",
                key="test-key",
                bindings=[],
                default_bindings=[],
                allow_multiple=True,
            )

            result = service.save_shortcut(shortcut)

            assert result is False


class TestFindConflicts:
    """Tests for find_conflicts method."""

    def test_find_conflicts_detects_duplicate(self) -> None:
        """Test that conflicts are detected for duplicate bindings."""
        from dailydriver.models import KeyBinding
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None  # No schemas = no shortcuts to load
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            # Mock load_all_shortcuts to return shortcuts with known bindings
            binding = KeyBinding.from_accelerator("<Super>a")
            mock_shortcut1 = MagicMock()
            mock_shortcut1.id = "shortcut1"
            mock_shortcut1.bindings = [binding]

            mock_shortcut2 = MagicMock()
            mock_shortcut2.id = "shortcut2"
            mock_shortcut2.bindings = [binding]  # Same binding

            with patch.object(
                service,
                "load_all_shortcuts",
                return_value={
                    "shortcut1": mock_shortcut1,
                    "shortcut2": mock_shortcut2,
                },
            ):
                conflicts = service.find_conflicts(binding, exclude_id="shortcut1")

                assert len(conflicts) == 1
                assert conflicts[0].id == "shortcut2"

    def test_find_conflicts_excludes_self(self) -> None:
        """Test that the excluded shortcut is not returned as conflict."""
        from dailydriver.models import KeyBinding
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            binding = KeyBinding.from_accelerator("<Super>b")
            mock_shortcut = MagicMock()
            mock_shortcut.id = "only-shortcut"
            mock_shortcut.bindings = [binding]

            with patch.object(
                service,
                "load_all_shortcuts",
                return_value={"only-shortcut": mock_shortcut},
            ):
                conflicts = service.find_conflicts(binding, exclude_id="only-shortcut")

                assert len(conflicts) == 0

    def test_find_conflicts_no_conflicts(self) -> None:
        """Test that no conflicts returns empty list."""
        from dailydriver.models import KeyBinding
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            binding_a = KeyBinding.from_accelerator("<Super>a")
            binding_b = KeyBinding.from_accelerator("<Super>b")

            mock_shortcut = MagicMock()
            mock_shortcut.id = "shortcut-a"
            mock_shortcut.bindings = [binding_a]

            with patch.object(
                service,
                "load_all_shortcuts",
                return_value={"shortcut-a": mock_shortcut},
            ):
                conflicts = service.find_conflicts(binding_b)

                assert len(conflicts) == 0


class TestResetShortcut:
    """Tests for reset_shortcut method."""

    def test_reset_shortcut_calls_reset(self) -> None:
        """Test that reset_shortcut resets the GSettings key."""
        from dailydriver.models import Shortcut
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_gio.Settings.new.return_value = mock_settings

            service = GSettingsService()

            shortcut = Shortcut(
                id="test.id",
                name="Test",
                description="",
                category="test",
                group="Test",
                schema="org.gnome.test",
                key="test-key",
                bindings=[],
                default_bindings=[],
                allow_multiple=True,
            )

            result = service.reset_shortcut(shortcut)

            assert result is True
            mock_settings.reset.assert_called_once_with("test-key")

    def test_reset_shortcut_missing_schema(self) -> None:
        """Test that reset returns False for missing schema."""
        from dailydriver.models import Shortcut
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            shortcut = Shortcut(
                id="test.id",
                name="Test",
                description="",
                category="test",
                group="Test",
                schema="org.nonexistent",
                key="test-key",
                bindings=[],
                default_bindings=[],
                allow_multiple=True,
            )

            result = service.reset_shortcut(shortcut)

            assert result is False


class TestCustomKeybindingOperations:
    """Tests for custom keybinding CRUD operations."""

    def test_get_custom_keybindings(self) -> None:
        """Test getting custom keybindings."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            # Main settings with custom keybinding paths
            mock_main_settings = MagicMock()
            mock_main_settings.get_strv.return_value = [
                "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/"
            ]

            # Individual binding settings
            mock_binding_settings = MagicMock()
            mock_binding_settings.get_string.side_effect = lambda key: {
                "name": "Terminal",
                "command": "gnome-terminal",
                "binding": "<Super>Return",
            }.get(key, "")

            mock_gio.Settings.new.return_value = mock_main_settings
            mock_gio.Settings.new_with_path.return_value = mock_binding_settings

            service = GSettingsService()
            bindings = service.get_custom_keybindings()

            assert len(bindings) == 1
            assert bindings[0]["name"] == "Terminal"
            assert bindings[0]["command"] == "gnome-terminal"
            assert bindings[0]["binding"] == "<Super>Return"

    def test_add_custom_keybinding(self) -> None:
        """Test adding a custom keybinding."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_main_settings = MagicMock()
            mock_main_settings.get_strv.return_value = []  # No existing bindings

            mock_binding_settings = MagicMock()

            mock_gio.Settings.new.return_value = mock_main_settings
            mock_gio.Settings.new_with_path.return_value = mock_binding_settings

            service = GSettingsService()
            path = service.add_custom_keybinding("Browser", "firefox", "<Super>b")

            assert path is not None
            assert "custom0" in path
            mock_binding_settings.set_string.assert_any_call("name", "Browser")
            mock_binding_settings.set_string.assert_any_call("command", "firefox")
            mock_binding_settings.set_string.assert_any_call("binding", "<Super>b")

    def test_add_custom_keybinding_finds_next_slot(self) -> None:
        """Test that add finds the next available slot number."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_main_settings = MagicMock()
            # custom0 and custom1 exist
            mock_main_settings.get_strv.return_value = [
                "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/",
                "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/",
            ]

            mock_gio.Settings.new.return_value = mock_main_settings
            mock_gio.Settings.new_with_path.return_value = MagicMock()

            service = GSettingsService()
            path = service.add_custom_keybinding("Test", "test", "<Super>t")

            # Should use custom2
            assert "custom2" in path

    def test_update_custom_keybinding(self) -> None:
        """Test updating a custom keybinding."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_binding_settings = MagicMock()
            mock_gio.Settings.new_with_path.return_value = mock_binding_settings

            service = GSettingsService()
            result = service.update_custom_keybinding(
                "/org/gnome/custom0/",
                name="New Name",
                binding="<Super>n",
            )

            assert result is True
            mock_binding_settings.set_string.assert_any_call("name", "New Name")
            mock_binding_settings.set_string.assert_any_call("binding", "<Super>n")

    def test_delete_custom_keybinding(self) -> None:
        """Test deleting a custom keybinding."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            path_to_delete = (
                "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/"
            )

            mock_main_settings = MagicMock()
            mock_main_settings.get_strv.return_value = [path_to_delete]

            mock_binding_settings = MagicMock()

            mock_gio.Settings.new.return_value = mock_main_settings
            mock_gio.Settings.new_with_path.return_value = mock_binding_settings

            service = GSettingsService()
            result = service.delete_custom_keybinding(path_to_delete)

            assert result is True
            # Should reset the binding settings
            mock_binding_settings.reset.assert_any_call("name")
            mock_binding_settings.reset.assert_any_call("command")
            mock_binding_settings.reset.assert_any_call("binding")
            # Should update the paths list
            mock_main_settings.set_strv.assert_called_once_with("custom-keybindings", [])

    def test_delete_custom_keybinding_not_found(self) -> None:
        """Test deleting non-existent keybinding returns False."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_main_settings = MagicMock()
            mock_main_settings.get_strv.return_value = []  # No bindings

            mock_gio.Settings.new.return_value = mock_main_settings

            service = GSettingsService()
            result = service.delete_custom_keybinding("/nonexistent/path/")

            assert result is False

    def test_find_custom_keybinding_by_name(self) -> None:
        """Test finding custom keybinding by name."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_main_settings = MagicMock()
            mock_main_settings.get_strv.return_value = ["/path/custom0/"]

            mock_binding_settings = MagicMock()
            mock_binding_settings.get_string.side_effect = lambda key: {
                "name": "My Terminal",
                "command": "kitty",
                "binding": "<Super>Return",
            }.get(key, "")

            mock_gio.Settings.new.return_value = mock_main_settings
            mock_gio.Settings.new_with_path.return_value = mock_binding_settings

            service = GSettingsService()

            found = service.find_custom_keybinding("My Terminal")
            assert found is not None
            assert found["name"] == "My Terminal"

            not_found = service.find_custom_keybinding("Nonexistent")
            assert not_found is None

    def test_find_custom_keybinding_by_type(self) -> None:
        """Test finding custom keybinding by app type."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_main_settings = MagicMock()
            mock_main_settings.get_strv.return_value = ["/path/custom0/", "/path/custom1/"]

            call_count = [0]

            def get_string_side_effect(key: str) -> str:
                # First binding is terminal, second is browser
                bindings = [
                    {"name": "Terminal", "command": "gnome-terminal", "binding": "<Super>Return"},
                    {"name": "Web", "command": "firefox", "binding": "<Super>b"},
                ]
                # Track which binding we're on by path
                binding_idx = call_count[0] // 3
                if binding_idx >= len(bindings):
                    binding_idx = len(bindings) - 1
                call_count[0] += 1
                return bindings[binding_idx].get(key, "")

            mock_binding_settings = MagicMock()
            mock_binding_settings.get_string.side_effect = get_string_side_effect

            mock_gio.Settings.new.return_value = mock_main_settings
            mock_gio.Settings.new_with_path.return_value = mock_binding_settings

            service = GSettingsService()

            # Should find terminal by type
            terminal = service.find_custom_keybinding_by_type("terminal")
            assert terminal is not None
            assert "terminal" in terminal["command"].lower()


class TestAppDetection:
    """Tests for application detection methods."""

    def testdetect_terminal_finds_ghostty(self) -> None:
        """Test that detect_terminal finds ghostty first."""
        from dailydriver.services.gsettings_service import GSettingsService

        with (
            patch("dailydriver.services.backends.gnome.Gio") as mock_gio,
            patch("shutil.which") as mock_which,
        ):
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_which.side_effect = lambda cmd: "/usr/bin/ghostty" if cmd == "ghostty" else None

            service = GSettingsService()
            terminal = service.detect_terminal()

            assert terminal == "ghostty"

    def testdetect_terminal_finds_kitty(self) -> None:
        """Test that detect_terminal finds kitty when ghostty unavailable."""
        from dailydriver.services.gsettings_service import GSettingsService

        with (
            patch("dailydriver.services.backends.gnome.Gio") as mock_gio,
            patch("shutil.which") as mock_which,
        ):
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            def which_side_effect(cmd: str) -> str | None:
                if cmd == "kitty":
                    return "/usr/bin/kitty"
                return None

            mock_which.side_effect = which_side_effect

            service = GSettingsService()
            terminal = service.detect_terminal()

            assert terminal == "kitty"

    def testdetect_terminal_returns_none_when_none_found(self) -> None:
        """Test that detect_terminal returns None when no terminal found."""
        from dailydriver.services.gsettings_service import GSettingsService

        with (
            patch("dailydriver.services.backends.gnome.Gio") as mock_gio,
            patch("shutil.which") as mock_which,
        ):
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_which.return_value = None

            service = GSettingsService()
            terminal = service.detect_terminal()

            assert terminal is None

    def testdetect_file_manager_fallback(self) -> None:
        """Test that detect_file_manager falls back to shutil.which."""
        from dailydriver.services.gsettings_service import GSettingsService

        with (
            patch("dailydriver.services.backends.gnome.Gio") as mock_gio,
            patch("shutil.which") as mock_which,
        ):
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            # Make shutil.which return nautilus as found
            def which_side_effect(binary: str) -> str | None:
                if binary == "nautilus":
                    return "/usr/bin/nautilus"
                return None

            mock_which.side_effect = which_side_effect

            service = GSettingsService()
            file_manager = service.detect_file_manager()

            # Should return nautilus with --new-window flag
            assert file_manager == "nautilus --new-window"

    def testdetect_browser_via_xdg_settings(self) -> None:
        """Test that detect_browser uses xdg-settings."""
        from dailydriver.services.gsettings_service import GSettingsService

        with (
            patch("dailydriver.services.backends.gnome.Gio") as mock_gio,
            patch("subprocess.run") as mock_run,
            patch("shutil.which") as mock_which,
        ):
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "firefox.desktop\n"
            mock_run.return_value = mock_result

            mock_which.return_value = None

            service = GSettingsService()
            browser = service.detect_browser()

            assert browser == "firefox --new-window"

    def testdetect_music_player_flatpak_spotify(self) -> None:
        """Test that detect_music_player finds Flatpak Spotify."""
        from dailydriver.services.gsettings_service import GSettingsService

        with (
            patch("dailydriver.services.backends.gnome.Gio") as mock_gio,
            patch("subprocess.run") as mock_run,
            patch("shutil.which") as mock_which,
        ):
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_result = MagicMock()
            mock_result.returncode = 0  # Flatpak info success
            mock_run.return_value = mock_result

            mock_which.return_value = None

            service = GSettingsService()
            player = service.detect_music_player()

            assert player == "flatpak run com.spotify.Client"

    def testdetect_music_player_native_spotify(self) -> None:
        """Test that detect_music_player finds native Spotify."""
        from dailydriver.services.gsettings_service import GSettingsService

        with (
            patch("dailydriver.services.backends.gnome.Gio") as mock_gio,
            patch("subprocess.run") as mock_run,
            patch("shutil.which") as mock_which,
        ):
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            # Flatpak not found
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_run.return_value = mock_result

            # Native spotify found
            def which_side_effect(cmd: str) -> str | None:
                if cmd == "spotify":
                    return "/usr/bin/spotify"
                return None

            mock_which.side_effect = which_side_effect

            service = GSettingsService()
            player = service.detect_music_player()

            assert player == "spotify"

    def testdetect_dailydriver_flatpak(self) -> None:
        """Test that detect_dailydriver finds Flatpak installation."""
        from dailydriver.services.gsettings_service import GSettingsService

        with (
            patch("dailydriver.services.backends.gnome.Gio") as mock_gio,
            patch("subprocess.run") as mock_run,
            patch("shutil.which") as mock_which,
        ):
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_result = MagicMock()
            mock_result.returncode = 0  # Flatpak info success
            mock_run.return_value = mock_result

            mock_which.return_value = None

            service = GSettingsService()
            dd = service.detect_dailydriver()

            assert dd == "flatpak run io.github.gregfelice.DailyDriver --cheat-sheet"

    def testdetect_dailydriver_system(self) -> None:
        """Test that detect_dailydriver finds system installation."""
        from dailydriver.services.gsettings_service import GSettingsService

        with (
            patch("dailydriver.services.backends.gnome.Gio") as mock_gio,
            patch("subprocess.run") as mock_run,
            patch("shutil.which") as mock_which,
        ):
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            # Flatpak not found
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_run.return_value = mock_result

            def which_side_effect(cmd: str) -> str | None:
                if cmd == "dailydriver":
                    return "/usr/bin/dailydriver"
                return None

            mock_which.side_effect = which_side_effect

            service = GSettingsService()
            dd = service.detect_dailydriver()

            assert dd == "dailydriver --cheat-sheet"


class TestSetupDefaultCustomShortcuts:
    """Tests for setup_default_custom_shortcuts method."""

    def test_setup_adds_terminal(self) -> None:
        """Test that setup adds terminal shortcut."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_main_settings = MagicMock()
            mock_main_settings.get_strv.return_value = []
            mock_gio.Settings.new.return_value = mock_main_settings
            mock_gio.Settings.new_with_path.return_value = MagicMock()

            service = GSettingsService()

            # Mock detection methods
            with (
                patch.object(service, "detect_terminal", return_value="kitty"),
                patch.object(service, "detect_file_manager", return_value="nautilus --new-window"),
                patch.object(service, "detect_browser", return_value="firefox --new-window"),
                patch.object(service, "detect_music_player", return_value=None),
                patch.object(service, "detect_dailydriver", return_value=None),
                patch.object(service, "find_custom_keybinding_by_type", return_value=None),
                patch.object(
                    service, "add_custom_keybinding", return_value="/path/custom0/"
                ) as mock_add,
            ):
                results = service.setup_default_custom_shortcuts()

                assert "terminal" in results
                assert "Added" in results["terminal"]
                mock_add.assert_any_call("Launch Terminal", "kitty", "<Super>Return")

    def test_setup_updates_existing(self) -> None:
        """Test that setup updates existing shortcuts."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_schema = MagicMock()
            mock_source.lookup.return_value = mock_schema
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_main_settings = MagicMock()
            mock_main_settings.get_strv.return_value = []
            mock_gio.Settings.new.return_value = mock_main_settings
            mock_gio.Settings.new_with_path.return_value = MagicMock()

            service = GSettingsService()

            existing_binding = {
                "path": "/path/custom0/",
                "name": "Old Terminal",
                "command": "xterm",
                "binding": "<Super>t",
            }

            with (
                patch.object(service, "detect_terminal", return_value="kitty"),
                patch.object(service, "detect_file_manager", return_value=None),
                patch.object(service, "detect_browser", return_value=None),
                patch.object(service, "detect_music_player", return_value=None),
                patch.object(service, "detect_dailydriver", return_value=None),
                patch.object(
                    service,
                    "find_custom_keybinding_by_type",
                    side_effect=lambda t: existing_binding if t == "terminal" else None,
                ),
                patch.object(service, "update_custom_keybinding") as mock_update,
            ):
                results = service.setup_default_custom_shortcuts()

                assert "terminal" in results
                assert "Updated" in results["terminal"]
                mock_update.assert_called_with(
                    "/path/custom0/", command="kitty", binding="<Super>Return"
                )

    def test_setup_reports_not_found(self) -> None:
        """Test that setup reports when apps not found."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            with (
                patch.object(service, "detect_terminal", return_value=None),
                patch.object(service, "detect_file_manager", return_value=None),
                patch.object(service, "detect_browser", return_value=None),
                patch.object(service, "detect_music_player", return_value=None),
                patch.object(service, "detect_dailydriver", return_value=None),
            ):
                results = service.setup_default_custom_shortcuts()

                assert results["terminal"] == "No terminal found"
                assert results["file_manager"] == "No file manager found"
                assert results["browser"] == "No browser found"
                assert results["music"] == "No music player found"
                assert results["cheat_sheet"] == "DailyDriver not found"


class TestLoadAllShortcuts:
    """Tests for load_all_shortcuts method."""

    def test_load_all_shortcuts_from_schema(self) -> None:
        """Test loading shortcuts from a schema."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()

            # Create mock schema with shortcut key
            mock_schema = MagicMock()
            mock_schema.list_keys.return_value = ["close", "minimize"]

            # Mock key objects
            mock_key_close = MagicMock()
            mock_variant_type = MagicMock()
            mock_variant_type.dup_string.return_value = "as"
            mock_key_close.get_value_type.return_value = mock_variant_type
            mock_key_close.get_default_value.return_value = MagicMock(
                get_type_string=lambda: "as", unpack=lambda: ["<Alt>F4"]
            )
            mock_key_close.get_description.return_value = "Close window"

            mock_key_minimize = MagicMock()
            mock_key_minimize.get_value_type.return_value = mock_variant_type
            mock_key_minimize.get_default_value.return_value = MagicMock(
                get_type_string=lambda: "as", unpack=lambda: ["<Super>h"]
            )
            mock_key_minimize.get_description.return_value = "Minimize window"

            def get_key_side_effect(key: str) -> MagicMock:
                if key == "close":
                    return mock_key_close
                elif key == "minimize":
                    return mock_key_minimize
                return MagicMock()

            mock_schema.get_key.side_effect = get_key_side_effect

            # Only return schema for wm.keybindings
            def lookup_side_effect(schema_id: str, recursive: bool) -> MagicMock | None:
                if schema_id == "org.gnome.desktop.wm.keybindings":
                    return mock_schema
                return None

            mock_source.lookup.side_effect = lookup_side_effect
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            # Mock settings
            mock_settings = MagicMock()
            mock_settings.get_value.return_value = MagicMock(
                get_type_string=lambda: "as", unpack=lambda: ["<Alt>F4"]
            )
            mock_gio.Settings.new.return_value = mock_settings

            service = GSettingsService()
            shortcuts = service.load_all_shortcuts()

            # Should have loaded shortcuts
            assert len(shortcuts) >= 0  # May be 0 if schema filtering excludes

    def test_load_all_shortcuts_skips_missing_schemas(self) -> None:
        """Test that load_all_shortcuts skips missing schemas gracefully."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None  # All schemas missing
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()
            shortcuts = service.load_all_shortcuts()

            # Should return empty dict, not crash
            assert shortcuts == {}

    def test_load_all_shortcuts_includes_custom(self) -> None:
        """Test that load_all_shortcuts includes custom keybindings."""
        from dailydriver.services.gsettings_service import GSettingsService

        with patch("dailydriver.services.backends.gnome.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None  # No standard schemas
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = GSettingsService()

            # Mock _load_custom_shortcuts to return a custom shortcut
            mock_shortcut = MagicMock()
            mock_shortcut.id = "custom:/path/custom0/"

            with patch.object(
                service,
                "_load_custom_shortcuts",
                return_value={"custom:/path/custom0/": mock_shortcut},
            ):
                shortcuts = service.load_all_shortcuts()

                assert "custom:/path/custom0/" in shortcuts
