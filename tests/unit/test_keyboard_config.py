# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for KeyboardConfigService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch


class TestCapsLockBehavior:
    """Tests for CapsLockBehavior enum."""

    def test_all_behaviors_have_display_names(self) -> None:
        """Test that all behaviors have display names."""
        from dailydriver.services.keyboard_config_service import CapsLockBehavior

        for behavior in CapsLockBehavior:
            assert behavior.display_name
            assert isinstance(behavior.display_name, str)

    def test_display_name_values(self) -> None:
        """Test specific display name values."""
        from dailydriver.services.keyboard_config_service import CapsLockBehavior

        assert CapsLockBehavior.CAPS_LOCK.display_name == "Caps Lock (default)"
        assert CapsLockBehavior.CTRL.display_name == "Control"
        assert CapsLockBehavior.ESCAPE.display_name == "Escape (vim)"
        assert CapsLockBehavior.BACKSPACE.display_name == "Backspace"
        assert CapsLockBehavior.SUPER.display_name == "Super"
        assert CapsLockBehavior.DISABLED.display_name == "Disabled"

    def test_xkb_option_default_is_none(self) -> None:
        """Test that CAPS_LOCK (default) returns None for xkb_option."""
        from dailydriver.services.keyboard_config_service import CapsLockBehavior

        assert CapsLockBehavior.CAPS_LOCK.xkb_option is None

    def test_xkb_option_non_default(self) -> None:
        """Test xkb_option for non-default behaviors."""
        from dailydriver.services.keyboard_config_service import CapsLockBehavior

        assert CapsLockBehavior.CTRL.xkb_option == "caps:ctrl_modifier"
        assert CapsLockBehavior.ESCAPE.xkb_option == "caps:escape"
        assert CapsLockBehavior.BACKSPACE.xkb_option == "caps:backspace"
        assert CapsLockBehavior.SUPER.xkb_option == "caps:super"
        assert CapsLockBehavior.DISABLED.xkb_option == "caps:none"

    def test_enum_values(self) -> None:
        """Test enum value strings."""
        from dailydriver.services.keyboard_config_service import CapsLockBehavior

        assert CapsLockBehavior.CAPS_LOCK.value == "default"
        assert CapsLockBehavior.CTRL.value == "caps:ctrl_modifier"
        assert CapsLockBehavior.ESCAPE.value == "caps:escape"


class TestModifierConfig:
    """Tests for ModifierConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default ModifierConfig values."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            ModifierConfig,
        )

        config = ModifierConfig()

        assert config.swap_cmd_opt is False
        assert config.swap_fn_ctrl is False
        assert config.caps_lock == CapsLockBehavior.CAPS_LOCK
        assert config.fn_keys_primary is False

    def test_custom_values(self) -> None:
        """Test ModifierConfig with custom values."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            ModifierConfig,
        )

        config = ModifierConfig(
            swap_cmd_opt=True,
            swap_fn_ctrl=True,
            caps_lock=CapsLockBehavior.ESCAPE,
            fn_keys_primary=True,
        )

        assert config.swap_cmd_opt is True
        assert config.swap_fn_ctrl is True
        assert config.caps_lock == CapsLockBehavior.ESCAPE
        assert config.fn_keys_primary is True

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            ModifierConfig,
        )

        config = ModifierConfig(
            swap_cmd_opt=True,
            swap_fn_ctrl=False,
            caps_lock=CapsLockBehavior.CTRL,
            fn_keys_primary=True,
        )

        data = config.to_dict()

        assert data["swap_cmd_opt"] is True
        assert data["swap_fn_ctrl"] is False
        assert data["caps_lock"] == "caps:ctrl_modifier"
        assert data["fn_keys_primary"] is True

    def test_from_dict_full(self) -> None:
        """Test deserialization from dict with all values."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            ModifierConfig,
        )

        data = {
            "swap_cmd_opt": True,
            "swap_fn_ctrl": True,
            "caps_lock": "caps:escape",
            "fn_keys_primary": True,
        }

        config = ModifierConfig.from_dict(data)

        assert config.swap_cmd_opt is True
        assert config.swap_fn_ctrl is True
        assert config.caps_lock == CapsLockBehavior.ESCAPE
        assert config.fn_keys_primary is True

    def test_from_dict_empty(self) -> None:
        """Test deserialization from empty dict uses defaults."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            ModifierConfig,
        )

        config = ModifierConfig.from_dict({})

        assert config.swap_cmd_opt is False
        assert config.swap_fn_ctrl is False
        assert config.caps_lock == CapsLockBehavior.CAPS_LOCK
        assert config.fn_keys_primary is False

    def test_from_dict_partial(self) -> None:
        """Test deserialization with partial data."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            ModifierConfig,
        )

        data = {"swap_cmd_opt": True, "caps_lock": "caps:super"}

        config = ModifierConfig.from_dict(data)

        assert config.swap_cmd_opt is True
        assert config.swap_fn_ctrl is False  # Default
        assert config.caps_lock == CapsLockBehavior.SUPER
        assert config.fn_keys_primary is False  # Default

    def test_from_dict_unknown_caps_lock(self) -> None:
        """Test deserialization with unknown caps_lock value defaults to CAPS_LOCK."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            ModifierConfig,
        )

        data = {"caps_lock": "unknown_value"}

        config = ModifierConfig.from_dict(data)

        assert config.caps_lock == CapsLockBehavior.CAPS_LOCK

    def test_round_trip(self) -> None:
        """Test serialization round-trip."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            ModifierConfig,
        )

        original = ModifierConfig(
            swap_cmd_opt=True,
            swap_fn_ctrl=True,
            caps_lock=CapsLockBehavior.DISABLED,
            fn_keys_primary=True,
        )

        data = original.to_dict()
        restored = ModifierConfig.from_dict(data)

        assert restored.swap_cmd_opt == original.swap_cmd_opt
        assert restored.swap_fn_ctrl == original.swap_fn_ctrl
        assert restored.caps_lock == original.caps_lock
        assert restored.fn_keys_primary == original.fn_keys_primary


class TestKeyboardConfigService:
    """Tests for KeyboardConfigService."""

    def test_init_no_schemas(self) -> None:
        """Test initialization when schemas don't exist."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source
            mock_gio.Settings.new.side_effect = Exception("Schema not found")

            service = KeyboardConfigService()

            assert service._app_settings is None
            assert service._input_settings is None

    def test_init_with_schemas(self) -> None:
        """Test initialization when schemas exist."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()  # Schema exists
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_app_settings = MagicMock()
            mock_input_settings = MagicMock()
            mock_gio.Settings.new.side_effect = [mock_app_settings, mock_input_settings]

            service = KeyboardConfigService()

            assert service._app_settings == mock_app_settings
            assert service._input_settings == mock_input_settings


class TestKeyboardType:
    """Tests for keyboard type get/set."""

    def test_get_keyboard_type_default(self) -> None:
        """Test getting default keyboard type when no settings."""
        from dailydriver.models.keyboard import KeyboardType
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source
            mock_gio.Settings.new.side_effect = Exception("No schema")

            service = KeyboardConfigService()
            result = service.get_keyboard_type()

            assert result == KeyboardType.ANSI_104

    def test_get_keyboard_type_from_settings(self) -> None:
        """Test getting keyboard type from settings."""
        from dailydriver.models.keyboard import KeyboardType
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_app_settings = MagicMock()
            mock_app_settings.get_string.return_value = "mac-ansi"
            mock_gio.Settings.new.return_value = mock_app_settings

            service = KeyboardConfigService()
            result = service.get_keyboard_type()

            assert result == KeyboardType.MAC_ANSI

    def test_set_keyboard_type_success(self) -> None:
        """Test setting keyboard type successfully."""
        from dailydriver.models.keyboard import KeyboardType
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_app_settings = MagicMock()
            mock_gio.Settings.new.return_value = mock_app_settings

            service = KeyboardConfigService()
            result = service.set_keyboard_type(KeyboardType.ISO_105)

            assert result is True
            mock_app_settings.set_string.assert_called_with("keyboard-type", "iso-105")

    def test_set_keyboard_type_no_settings(self) -> None:
        """Test setting keyboard type when settings unavailable."""
        from dailydriver.models.keyboard import KeyboardType
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source
            mock_gio.Settings.new.side_effect = Exception("No schema")

            service = KeyboardConfigService()
            result = service.set_keyboard_type(KeyboardType.ISO_105)

            assert result is False


class TestXkbOptions:
    """Tests for XKB options get/set."""

    def test_get_xkb_options_empty(self) -> None:
        """Test getting XKB options when none set."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_settings.get_strv.return_value = []
            mock_gio.Settings.new.return_value = mock_settings

            service = KeyboardConfigService()
            result = service.get_xkb_options()

            assert result == []

    def test_get_xkb_options_with_values(self) -> None:
        """Test getting XKB options with values."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_settings.get_strv.return_value = ["caps:escape", "compose:ralt"]
            mock_gio.Settings.new.return_value = mock_settings

            service = KeyboardConfigService()
            result = service.get_xkb_options()

            assert result == ["caps:escape", "compose:ralt"]

    def test_get_xkb_options_no_settings(self) -> None:
        """Test getting XKB options when settings unavailable."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source
            mock_gio.Settings.new.side_effect = Exception("No schema")

            service = KeyboardConfigService()
            result = service.get_xkb_options()

            assert result == []

    def test_set_xkb_options_success(self) -> None:
        """Test setting XKB options successfully."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_gio.Settings.new.return_value = mock_settings

            service = KeyboardConfigService()
            result = service.set_xkb_options(["caps:escape"])

            assert result is True
            mock_settings.set_strv.assert_called_with("xkb-options", ["caps:escape"])

    def test_set_xkb_options_no_settings(self) -> None:
        """Test setting XKB options when settings unavailable."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source
            mock_gio.Settings.new.side_effect = Exception("No schema")

            service = KeyboardConfigService()
            result = service.set_xkb_options(["caps:escape"])

            assert result is False


class TestCapsLockBehaviorService:
    """Tests for Caps Lock behavior get/set in service."""

    def test_get_caps_lock_behavior_default(self) -> None:
        """Test getting Caps Lock behavior when no caps option set."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            KeyboardConfigService,
        )

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_settings.get_strv.return_value = ["compose:ralt"]  # No caps option
            mock_gio.Settings.new.return_value = mock_settings

            service = KeyboardConfigService()
            result = service.get_caps_lock_behavior()

            assert result == CapsLockBehavior.CAPS_LOCK

    def test_get_caps_lock_behavior_escape(self) -> None:
        """Test getting Caps Lock behavior when set to escape."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            KeyboardConfigService,
        )

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_settings.get_strv.return_value = ["caps:escape", "compose:ralt"]
            mock_gio.Settings.new.return_value = mock_settings

            service = KeyboardConfigService()
            result = service.get_caps_lock_behavior()

            assert result == CapsLockBehavior.ESCAPE

    def test_get_caps_lock_behavior_ctrl(self) -> None:
        """Test getting Caps Lock behavior when set to Ctrl."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            KeyboardConfigService,
        )

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_settings.get_strv.return_value = ["caps:ctrl_modifier"]
            mock_gio.Settings.new.return_value = mock_settings

            service = KeyboardConfigService()
            result = service.get_caps_lock_behavior()

            assert result == CapsLockBehavior.CTRL

    def test_set_caps_lock_behavior_adds_option(self) -> None:
        """Test setting Caps Lock adds xkb option."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            KeyboardConfigService,
        )

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_settings.get_strv.return_value = ["compose:ralt"]
            mock_gio.Settings.new.return_value = mock_settings

            service = KeyboardConfigService()
            result = service.set_caps_lock_behavior(CapsLockBehavior.ESCAPE)

            assert result is True
            mock_settings.set_strv.assert_called_with(
                "xkb-options", ["compose:ralt", "caps:escape"]
            )

    def test_set_caps_lock_behavior_replaces_existing(self) -> None:
        """Test setting Caps Lock replaces existing caps option."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            KeyboardConfigService,
        )

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_settings.get_strv.return_value = ["caps:escape", "compose:ralt"]
            mock_gio.Settings.new.return_value = mock_settings

            service = KeyboardConfigService()
            result = service.set_caps_lock_behavior(CapsLockBehavior.CTRL)

            assert result is True
            mock_settings.set_strv.assert_called_with(
                "xkb-options", ["compose:ralt", "caps:ctrl_modifier"]
            )

    def test_set_caps_lock_behavior_default_removes_option(self) -> None:
        """Test setting Caps Lock to default removes caps option."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            KeyboardConfigService,
        )

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_settings.get_strv.return_value = ["caps:escape", "compose:ralt"]
            mock_gio.Settings.new.return_value = mock_settings

            service = KeyboardConfigService()
            result = service.set_caps_lock_behavior(CapsLockBehavior.CAPS_LOCK)

            assert result is True
            # Should remove caps:escape but keep compose:ralt
            mock_settings.set_strv.assert_called_with("xkb-options", ["compose:ralt"])


class TestAppleKeyboard:
    """Tests for Apple keyboard sysfs reads."""

    def test_get_apple_swap_cmd_opt_enabled(self, tmp_path: Path) -> None:
        """Test detecting Cmd/Option swap enabled."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source
            mock_gio.Settings.new.side_effect = Exception("No schema")

            service = KeyboardConfigService()

            # Mock file read
            with patch("builtins.open", mock_open(read_data="1\n")):
                result = service.get_apple_swap_cmd_opt()

            assert result is True

    def test_get_apple_swap_cmd_opt_disabled(self) -> None:
        """Test detecting Cmd/Option swap disabled."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source
            mock_gio.Settings.new.side_effect = Exception("No schema")

            service = KeyboardConfigService()

            with patch("builtins.open", mock_open(read_data="0\n")):
                result = service.get_apple_swap_cmd_opt()

            assert result is False

    def test_get_apple_swap_cmd_opt_not_found(self) -> None:
        """Test when hid_apple module not loaded."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source
            mock_gio.Settings.new.side_effect = Exception("No schema")

            service = KeyboardConfigService()

            with patch("builtins.open", side_effect=FileNotFoundError):
                result = service.get_apple_swap_cmd_opt()

            assert result is False

    def test_get_apple_fn_mode_fkeys(self) -> None:
        """Test getting fn mode as fkeys (1)."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source
            mock_gio.Settings.new.side_effect = Exception("No schema")

            service = KeyboardConfigService()

            with patch("builtins.open", mock_open(read_data="1\n")):
                result = service.get_apple_fn_mode()

            assert result == 1

    def test_get_apple_fn_mode_media(self) -> None:
        """Test getting fn mode as media (2)."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source
            mock_gio.Settings.new.side_effect = Exception("No schema")

            service = KeyboardConfigService()

            with patch("builtins.open", mock_open(read_data="2\n")):
                result = service.get_apple_fn_mode()

            assert result == 2

    def test_get_apple_fn_mode_default_on_error(self) -> None:
        """Test fn mode defaults to 2 (media) on error."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source
            mock_gio.Settings.new.side_effect = Exception("No schema")

            service = KeyboardConfigService()

            with patch("builtins.open", side_effect=FileNotFoundError):
                result = service.get_apple_fn_mode()

            assert result == 2


class TestModifierConfigApplication:
    """Tests for applying and getting modifier config."""

    def test_apply_modifier_config_success(self) -> None:
        """Test applying modifier config successfully."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            KeyboardConfigService,
            ModifierConfig,
        )

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_settings.get_strv.return_value = []
            mock_gio.Settings.new.return_value = mock_settings

            service = KeyboardConfigService()
            config = ModifierConfig(caps_lock=CapsLockBehavior.ESCAPE)

            result = service.apply_modifier_config(config)

            assert result is True
            mock_settings.set_strv.assert_called_with("xkb-options", ["caps:escape"])

    def test_apply_modifier_config_failure(self) -> None:
        """Test applying modifier config when settings unavailable."""
        from dailydriver.services.keyboard_config_service import (
            KeyboardConfigService,
            ModifierConfig,
        )

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source
            mock_gio.Settings.new.side_effect = Exception("No schema")

            service = KeyboardConfigService()
            config = ModifierConfig()

            result = service.apply_modifier_config(config)

            assert result is False

    def test_get_current_modifier_config(self) -> None:
        """Test getting current modifier config from system state."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            KeyboardConfigService,
        )

        with patch("dailydriver.services.keyboard_config_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_settings.get_strv.return_value = ["caps:ctrl_modifier"]
            mock_gio.Settings.new.return_value = mock_settings

            service = KeyboardConfigService()

            # Mock Apple keyboard reads
            with patch("builtins.open") as mock_file:

                def open_side_effect(path, *args, **kwargs):
                    if "swap_opt_cmd" in str(path) or "fnmode" in str(path):
                        return mock_open(read_data="1\n")()
                    raise FileNotFoundError

                mock_file.side_effect = open_side_effect

                config = service.get_current_modifier_config()

            assert config.swap_cmd_opt is True
            assert config.caps_lock == CapsLockBehavior.CTRL
            assert config.fn_keys_primary is True


class TestPresetConfigs:
    """Tests for preset configurations."""

    def test_get_preset_configs_returns_dict(self) -> None:
        """Test that get_preset_configs returns a dict."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        presets = KeyboardConfigService.get_preset_configs()

        assert isinstance(presets, dict)
        assert len(presets) > 0

    def test_preset_names(self) -> None:
        """Test expected preset names exist."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        presets = KeyboardConfigService.get_preset_configs()

        assert "default" in presets
        assert "mac-native" in presets
        assert "mac-to-pc" in presets
        assert "developer" in presets
        assert "vim" in presets

    def test_default_preset(self) -> None:
        """Test default preset has default values."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            KeyboardConfigService,
        )

        presets = KeyboardConfigService.get_preset_configs()
        default = presets["default"]

        assert default.swap_cmd_opt is False
        assert default.swap_fn_ctrl is False
        assert default.caps_lock == CapsLockBehavior.CAPS_LOCK
        assert default.fn_keys_primary is False

    def test_vim_preset(self) -> None:
        """Test vim preset has Escape for Caps Lock."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            KeyboardConfigService,
        )

        presets = KeyboardConfigService.get_preset_configs()
        vim = presets["vim"]

        assert vim.caps_lock == CapsLockBehavior.ESCAPE
        assert vim.fn_keys_primary is True

    def test_developer_preset(self) -> None:
        """Test developer preset has Ctrl for Caps Lock."""
        from dailydriver.services.keyboard_config_service import (
            CapsLockBehavior,
            KeyboardConfigService,
        )

        presets = KeyboardConfigService.get_preset_configs()
        dev = presets["developer"]

        assert dev.caps_lock == CapsLockBehavior.CTRL
        assert dev.fn_keys_primary is True

    def test_mac_to_pc_preset(self) -> None:
        """Test mac-to-pc preset swaps Cmd/Option."""
        from dailydriver.services.keyboard_config_service import KeyboardConfigService

        presets = KeyboardConfigService.get_preset_configs()
        mac_to_pc = presets["mac-to-pc"]

        assert mac_to_pc.swap_cmd_opt is True
