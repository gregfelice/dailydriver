# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for TilingService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestTilingStatus:
    """Tests for TilingStatus enum."""

    def test_tiling_status_values(self) -> None:
        """Test TilingStatus enum exists with expected values."""
        from dailydriver.services.tiling_service import TilingStatus

        assert TilingStatus.NONE
        assert TilingStatus.NATIVE_BASIC
        assert TilingStatus.TILING_ASSISTANT


class TestTilingInfo:
    """Tests for TilingInfo dataclass."""

    def test_tiling_info_creation(self) -> None:
        """Test TilingInfo creation."""
        from dailydriver.services.tiling_service import TilingInfo, TilingStatus

        info = TilingInfo(status=TilingStatus.NONE)
        assert info.status == TilingStatus.NONE
        assert info.extension_installed is None
        assert not info.native_keys_bound

    def test_tiling_info_with_extension(self) -> None:
        """Test TilingInfo with extension info."""
        from dailydriver.services.tiling_service import TilingInfo, TilingStatus

        info = TilingInfo(
            status=TilingStatus.NONE,
            extension_installed="Tiling Assistant",
            native_keys_bound=False,
        )
        assert info.extension_installed == "Tiling Assistant"


class TestNativeTilingDefaults:
    """Tests for native tiling default keybindings."""

    def test_native_tiling_defaults_defined(self) -> None:
        """Test that native tiling defaults are defined."""
        from dailydriver.services.tiling_service import NATIVE_TILING_DEFAULTS

        assert "org.gnome.mutter.keybindings" in NATIVE_TILING_DEFAULTS
        assert "org.gnome.desktop.wm.keybindings" in NATIVE_TILING_DEFAULTS

        # Check mutter bindings
        mutter = NATIVE_TILING_DEFAULTS["org.gnome.mutter.keybindings"]
        assert "toggle-tiled-left" in mutter
        assert "toggle-tiled-right" in mutter

        # Check WM bindings
        wm = NATIVE_TILING_DEFAULTS["org.gnome.desktop.wm.keybindings"]
        assert "move-to-corner-nw" in wm


class TestTilingService:
    """Tests for TilingService."""

    def test_detect_status_no_tiling(self) -> None:
        """Test detecting no tiling configuration."""
        from dailydriver.services.tiling_service import TilingService, TilingStatus

        with patch("dailydriver.services.tiling_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            # Mock Settings to return empty values
            mock_settings = MagicMock()
            mock_settings.get_strv.return_value = []
            mock_gio.Settings.new.return_value = mock_settings

            with patch("subprocess.run") as mock_run:
                # No extensions
                mock_run.return_value = MagicMock(returncode=0, stdout="")

                service = TilingService()
                info = service.detect_status()

                assert info.status == TilingStatus.NONE

    def test_detect_status_tiling_assistant_enabled(self) -> None:
        """Test detecting Tiling Assistant enabled."""
        from dailydriver.services.tiling_service import TilingService, TilingStatus

        with patch("dailydriver.services.tiling_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            with patch("subprocess.run") as mock_run:
                # Tiling Assistant enabled
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="tiling-assistant@ubuntu.com\n"
                )

                service = TilingService()
                info = service.detect_status()

                assert info.status == TilingStatus.TILING_ASSISTANT

    def test_detect_status_native_tiling_bound(self) -> None:
        """Test detecting native GNOME tiling keys bound."""
        from dailydriver.services.tiling_service import TilingService, TilingStatus

        with patch("dailydriver.services.tiling_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            # Mock Settings to return bound keys
            mock_settings = MagicMock()
            mock_settings.get_strv.return_value = ["<Super>Left"]
            mock_gio.Settings.new.return_value = mock_settings

            with patch("subprocess.run") as mock_run:
                # No extensions
                mock_run.return_value = MagicMock(returncode=0, stdout="")

                service = TilingService()
                info = service.detect_status()

                assert info.status == TilingStatus.NATIVE_BASIC
                assert info.native_keys_bound

    def test_enable_extension(self) -> None:
        """Test enabling GNOME extension."""
        from dailydriver.services.tiling_service import TilingService

        with patch("dailydriver.services.tiling_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                service = TilingService()
                result = service.enable_extension("tiling-assistant@test.com")

                assert result
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert "gnome-extensions" in call_args
                assert "enable" in call_args

    def test_enable_extension_failure(self) -> None:
        """Test handling extension enable failure."""
        from dailydriver.services.tiling_service import TilingService

        with patch("dailydriver.services.tiling_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)

                service = TilingService()
                result = service.enable_extension("nonexistent@test.com")

                assert not result

    def test_get_tiling_assistant_id_found(self) -> None:
        """Test finding Tiling Assistant extension ID."""
        from dailydriver.services.tiling_service import TilingService

        with patch("dailydriver.services.tiling_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="some-other-extension@test.com\ntiling-assistant@leleat\nanother@test.com\n",
                )

                service = TilingService()
                ext_id = service.get_tiling_assistant_id()

                assert ext_id == "tiling-assistant@leleat"

    def test_get_tiling_assistant_id_not_found(self) -> None:
        """Test when Tiling Assistant is not installed."""
        from dailydriver.services.tiling_service import TilingService

        with patch("dailydriver.services.tiling_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="some-other-extension@test.com\n"
                )

                service = TilingService()
                ext_id = service.get_tiling_assistant_id()

                assert ext_id is None

    def test_enable_native_tiling(self) -> None:
        """Test enabling native GNOME tiling."""
        from dailydriver.services.tiling_service import TilingService

        with patch("dailydriver.services.tiling_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_gio.Settings.new.return_value = mock_settings

            service = TilingService()
            result = service.enable_native_tiling()

            assert result
            # Should have set some keys
            assert mock_settings.set_strv.called

    def test_apply_tiling_assistant_defaults_schema_missing(self) -> None:
        """Test applying defaults when schema doesn't exist."""
        from dailydriver.services.tiling_service import TilingService

        with patch("dailydriver.services.tiling_service.Gio") as mock_gio:
            mock_source = MagicMock()
            # Schema doesn't exist
            mock_source.lookup.return_value = None
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            service = TilingService()
            result = service.apply_tiling_assistant_defaults()

            assert not result

    def test_apply_tiling_assistant_defaults_success(self) -> None:
        """Test applying Tiling Assistant defaults."""
        from dailydriver.services.tiling_service import TilingService

        with patch("dailydriver.services.tiling_service.Gio") as mock_gio:
            mock_source = MagicMock()
            mock_source.lookup.return_value = MagicMock()
            mock_gio.SettingsSchemaSource.get_default.return_value = mock_source

            mock_settings = MagicMock()
            mock_gio.Settings.new.return_value = mock_settings

            service = TilingService()
            result = service.apply_tiling_assistant_defaults()

            assert result
            # Should have set multiple keys
            assert mock_settings.set_strv.call_count > 0
