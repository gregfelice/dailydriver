# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for HidAppleService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestHidAppleService:
    """Tests for HidAppleService."""

    def test_is_module_loaded_true(self, mock_hid_apple: Path) -> None:
        """Test module loaded detection when params exist."""
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = mock_hid_apple

        assert service.is_module_loaded()

    def test_is_module_loaded_false(self, tmp_path: Path) -> None:
        """Test module loaded detection when params don't exist."""
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = tmp_path / "nonexistent"

        assert not service.is_module_loaded()

    def test_is_available_when_loaded(self, mock_hid_apple: Path) -> None:
        """Test module availability when loaded."""
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = mock_hid_apple

        assert service.is_available()

    def test_is_available_with_modinfo(self, tmp_path: Path) -> None:
        """Test module availability via modinfo."""
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = tmp_path / "nonexistent"

        # Mock successful modinfo
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert service.is_available()

    def test_is_available_not_installed(self, tmp_path: Path) -> None:
        """Test module unavailable when not installed."""
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = tmp_path / "nonexistent"

        # Mock failed modinfo
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert not service.is_available()

    def test_get_current_config_default(self, mock_hid_apple: Path) -> None:
        """Test reading default configuration."""
        from dailydriver.models.profile import FnMode
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = mock_hid_apple

        config = service.get_current_config()

        assert config is not None
        assert config.fn_mode == FnMode.MEDIA  # Default fnmode=2
        assert not config.swap_opt_cmd
        assert not config.swap_fn_leftctrl
        assert not config.iso_layout

    def test_get_current_config_custom(self, mock_hid_apple: Path) -> None:
        """Test reading custom configuration."""
        from dailydriver.models.profile import FnMode
        from dailydriver.services.hid_apple_service import HidAppleService

        # Set custom values
        (mock_hid_apple / "fnmode").write_text("1\n")
        (mock_hid_apple / "swap_opt_cmd").write_text("Y\n")
        (mock_hid_apple / "swap_fn_leftctrl").write_text("Y\n")
        (mock_hid_apple / "iso_layout").write_text("Y\n")

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = mock_hid_apple

        config = service.get_current_config()

        assert config is not None
        assert config.fn_mode == FnMode.FKEYS
        assert config.swap_opt_cmd
        assert config.swap_fn_leftctrl
        assert config.iso_layout

    def test_get_current_config_not_loaded(self, tmp_path: Path) -> None:
        """Test reading config when module not loaded."""
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = tmp_path / "nonexistent"

        config = service.get_current_config()
        assert config is None

    def test_get_persistent_config(self, tmp_path: Path) -> None:
        """Test reading persistent modprobe.d configuration."""
        from dailydriver.models.profile import FnMode
        from dailydriver.services.hid_apple_service import HidAppleService

        # Create mock modprobe.d config
        modprobe_conf = tmp_path / "hid_apple.conf"
        modprobe_conf.write_text("options hid_apple fnmode=1 swap_opt_cmd=1 iso_layout=0\n")

        service = HidAppleService()
        service.MODPROBE_CONF_PATH = modprobe_conf

        config = service.get_persistent_config()

        assert config is not None
        assert config.fn_mode == FnMode.FKEYS
        assert config.swap_opt_cmd
        assert not config.iso_layout

    def test_get_persistent_config_not_exists(self, tmp_path: Path) -> None:
        """Test reading persistent config when file doesn't exist."""
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODPROBE_CONF_PATH = tmp_path / "nonexistent.conf"

        config = service.get_persistent_config()
        assert config is None

    def test_apply_config_not_loaded(self, tmp_path: Path) -> None:
        """Test applying config when module not loaded."""
        from dailydriver.models.profile import MacKeyboardConfig
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = tmp_path / "nonexistent"

        config = MacKeyboardConfig()
        result = service.apply_config(config)

        assert not result

    def test_apply_config_with_pkexec(self, mock_hid_apple: Path, tmp_path: Path) -> None:
        """Test applying config with pkexec."""
        from dailydriver.models.profile import FnMode, MacKeyboardConfig
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = mock_hid_apple
        service.MODPROBE_CONF_PATH = tmp_path / "hid_apple.conf"

        config = MacKeyboardConfig(
            fn_mode=FnMode.FKEYS,
            swap_opt_cmd=True,
        )

        # Mock pkexec to succeed
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = service.apply_config(config, persistent=True)

            assert result
            # Verify pkexec was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0][0] == "pkexec"

    def test_apply_config_pkexec_failure(self, mock_hid_apple: Path, tmp_path: Path) -> None:
        """Test handling pkexec failure."""
        from dailydriver.models.profile import MacKeyboardConfig
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = mock_hid_apple
        service.MODPROBE_CONF_PATH = tmp_path / "hid_apple.conf"

        config = MacKeyboardConfig()

        # Mock pkexec to fail
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = service.apply_config(config)

            assert not result

    def test_reload_module(self) -> None:
        """Test module reload."""
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()

        # Mock successful reload
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = service.reload_module()

            assert result
            # Should be called twice: modprobe -r, then modprobe
            assert mock_run.call_count == 2

    def test_reload_module_failure(self) -> None:
        """Test handling module reload failure."""
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()

        # Mock failed reload
        with patch("subprocess.run") as mock_run:
            from subprocess import CalledProcessError

            mock_run.side_effect = CalledProcessError(1, "modprobe")
            result = service.reload_module()

            assert not result

    def test_fnmode_mapping(self, mock_hid_apple: Path) -> None:
        """Test fnmode value to FnMode enum mapping."""
        from dailydriver.models.profile import FnMode
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = mock_hid_apple

        # Test fnmode=0 (DISABLED)
        (mock_hid_apple / "fnmode").write_text("0\n")
        config = service.get_current_config()
        assert config is not None
        assert config.fn_mode == FnMode.DISABLED

        # Test fnmode=1 (FKEYS)
        (mock_hid_apple / "fnmode").write_text("1\n")
        config = service.get_current_config()
        assert config is not None
        assert config.fn_mode == FnMode.FKEYS

        # Test fnmode=2 (MEDIA)
        (mock_hid_apple / "fnmode").write_text("2\n")
        config = service.get_current_config()
        assert config is not None
        assert config.fn_mode == FnMode.MEDIA

    def test_caching(self, mock_hid_apple: Path) -> None:
        """Test configuration caching after apply."""
        from dailydriver.models.profile import FnMode, MacKeyboardConfig
        from dailydriver.services.hid_apple_service import HidAppleService

        service = HidAppleService()
        service.MODULE_PARAMS_PATH = mock_hid_apple

        config = MacKeyboardConfig(fn_mode=FnMode.FKEYS)

        # Apply config with mocked pkexec
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            service.apply_config(config, persistent=False)

        # Check cached config
        assert service._cached_config is not None
        assert service._cached_config.fn_mode == FnMode.FKEYS
