# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for HardwareService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from tests.conftest import create_mock_keyboard


class TestHardwareService:
    """Tests for HardwareService."""

    def test_list_keyboards_empty(self, mock_sysfs: Path) -> None:
        """Test listing keyboards when none are present."""
        from dailydriver.services.hardware_service import HardwareService

        service = HardwareService()
        service._input_path = mock_sysfs / "class" / "input"

        keyboards = list(service.list_keyboards())
        assert keyboards == []

    def test_list_keyboards_with_apple(self, mock_sysfs: Path) -> None:
        """Test detecting Apple Magic Keyboard."""
        from dailydriver.services.hardware_service import HardwareService

        # Create Apple keyboard
        create_mock_keyboard(
            mock_sysfs,
            event_num=0,
            name="Apple Inc. Magic Keyboard",
            vendor_id=0x05AC,
            product_id=0x0267,
            key_capabilities="fffffffe ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff 0 0 0 0 0 0 0 0",
        )

        service = HardwareService()
        service._input_path = mock_sysfs / "class" / "input"

        keyboards = list(service.list_keyboards())

        assert len(keyboards) == 1
        kb = keyboards[0]
        assert kb.vendor_id == 0x05AC
        assert kb.is_mac
        assert kb.brand_name == "Apple"

    def test_list_keyboards_multiple(self, mock_sysfs: Path) -> None:
        """Test detecting multiple keyboards."""
        from dailydriver.services.hardware_service import HardwareService

        # Create Apple keyboard
        create_mock_keyboard(
            mock_sysfs,
            event_num=0,
            name="Apple Inc. Magic Keyboard",
            vendor_id=0x05AC,
            product_id=0x0267,
            key_capabilities="fffffffe ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff 0 0 0 0 0 0 0 0",
        )

        # Create generic USB keyboard
        create_mock_keyboard(
            mock_sysfs,
            event_num=1,
            name="USB Keyboard",
            vendor_id=0x04D9,
            product_id=0x0001,
            key_capabilities="fffffffe ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff 0 0 0 0 0 0 0 0",
        )

        service = HardwareService()
        service._input_path = mock_sysfs / "class" / "input"

        keyboards = list(service.list_keyboards())

        assert len(keyboards) == 2

    def test_filter_non_keyboards(self, mock_sysfs: Path) -> None:
        """Test that non-keyboard devices are filtered out."""
        from dailydriver.services.hardware_service import HardwareService

        # Create a trackpad (should be filtered)
        create_mock_keyboard(
            mock_sysfs,
            event_num=0,
            name="Apple Trackpad",
            vendor_id=0x05AC,
            product_id=0x1234,
            key_capabilities="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
        )

        # Create a mouse (should be filtered)
        create_mock_keyboard(
            mock_sysfs,
            event_num=1,
            name="Logitech USB Mouse",
            vendor_id=0x046D,
            product_id=0x5678,
            key_capabilities="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
        )

        # Create actual keyboard
        create_mock_keyboard(
            mock_sysfs,
            event_num=2,
            name="USB Keyboard",
            vendor_id=0x04D9,
            product_id=0x0001,
            key_capabilities="fffffffe ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff 0 0 0 0 0 0 0 0",
        )

        service = HardwareService()
        service._input_path = mock_sysfs / "class" / "input"

        keyboards = list(service.list_keyboards())

        # Only the USB keyboard should be detected
        assert len(keyboards) == 1
        assert keyboards[0].name == "USB Keyboard"

    def test_vendor_detection(self, mock_sysfs: Path) -> None:
        """Test vendor name detection from vendor ID."""
        from dailydriver.services.hardware_service import HardwareService

        # Create Logitech keyboard
        create_mock_keyboard(
            mock_sysfs,
            event_num=0,
            name="USB Keyboard",
            vendor_id=0x046D,
            product_id=0x1234,
            key_capabilities="fffffffe ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff 0 0 0 0 0 0 0 0",
        )

        service = HardwareService()
        service._input_path = mock_sysfs / "class" / "input"

        keyboards = list(service.list_keyboards())

        assert len(keyboards) == 1
        kb = keyboards[0]
        assert kb.brand_name == "Logitech"
        assert kb.brand_id == "logitech"

    def test_bluetooth_detection(self, mock_sysfs: Path) -> None:
        """Test Bluetooth device detection."""
        from dailydriver.services.hardware_service import HardwareService

        create_mock_keyboard(
            mock_sysfs,
            event_num=0,
            name="BT Keyboard",
            vendor_id=0x05AC,
            product_id=0x0267,
            key_capabilities="fffffffe ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff 0 0 0 0 0 0 0 0",
            is_bluetooth=True,
        )

        service = HardwareService()
        service._input_path = mock_sysfs / "class" / "input"

        keyboards = list(service.list_keyboards())

        assert len(keyboards) == 1
        assert keyboards[0].is_bluetooth

    def test_internal_keyboard_detection(self, mock_sysfs: Path) -> None:
        """Test internal/laptop keyboard detection."""
        from dailydriver.services.hardware_service import HardwareService

        create_mock_keyboard(
            mock_sysfs,
            event_num=0,
            name="AT Translated Set 2 keyboard",
            vendor_id=0x0001,
            product_id=0x0001,
            key_capabilities="fffffffe ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff 0 0 0 0 0 0 0 0",
        )

        service = HardwareService()
        service._input_path = mock_sysfs / "class" / "input"

        keyboards = list(service.list_keyboards())

        assert len(keyboards) == 1
        assert keyboards[0].is_internal

    def test_get_mac_keyboards(self, mock_sysfs: Path) -> None:
        """Test filtering for Mac keyboards only."""
        from dailydriver.services.hardware_service import HardwareService

        # Create Apple keyboard
        create_mock_keyboard(
            mock_sysfs,
            event_num=0,
            name="Apple Inc. Magic Keyboard",
            vendor_id=0x05AC,
            product_id=0x0267,
            key_capabilities="fffffffe ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff 0 0 0 0 0 0 0 0",
        )

        # Create generic keyboard
        create_mock_keyboard(
            mock_sysfs,
            event_num=1,
            name="USB Keyboard",
            vendor_id=0x04D9,
            product_id=0x0001,
            key_capabilities="fffffffe ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff 0 0 0 0 0 0 0 0",
        )

        service = HardwareService()
        service._input_path = mock_sysfs / "class" / "input"

        mac_keyboards = service.get_mac_keyboards()

        assert len(mac_keyboards) == 1
        assert mac_keyboards[0].is_mac

    def test_model_name_for_known_product(self, mock_sysfs: Path) -> None:
        """Test model name detection for known Apple products."""
        from dailydriver.services.hardware_service import HardwareService

        create_mock_keyboard(
            mock_sysfs,
            event_num=0,
            name="Apple Inc. Internal Keyboard",
            vendor_id=0x05AC,
            product_id=0x0267,  # Magic Keyboard with Numeric Keypad
            key_capabilities="fffffffe ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff 0 0 0 0 0 0 0 0",
        )

        service = HardwareService()
        service._input_path = mock_sysfs / "class" / "input"

        keyboards = list(service.list_keyboards())

        assert len(keyboards) == 1
        assert keyboards[0].model_name == "Magic Keyboard with Numeric Keypad"

    def test_device_path(self, mock_sysfs: Path) -> None:
        """Test device path generation."""
        from dailydriver.services.hardware_service import HardwareService

        create_mock_keyboard(
            mock_sysfs,
            event_num=5,
            name="USB Keyboard",
            vendor_id=0x04D9,
            product_id=0x0001,
            key_capabilities="fffffffe ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff 0 0 0 0 0 0 0 0",
        )

        service = HardwareService()
        service._input_path = mock_sysfs / "class" / "input"

        keyboards = list(service.list_keyboards())

        assert len(keyboards) == 1
        assert keyboards[0].path == "/dev/input/event5"

    def test_missing_sysfs(self) -> None:
        """Test behavior when /sys/class/input doesn't exist."""
        from dailydriver.services.hardware_service import HardwareService

        service = HardwareService()
        service._input_path = Path("/nonexistent/path")

        keyboards = list(service.list_keyboards())
        assert keyboards == []

    def test_permission_errors(self, mock_sysfs: Path) -> None:
        """Test handling of permission errors."""
        from dailydriver.services.hardware_service import HardwareService

        # Create keyboard with unreadable name file
        event_dir = mock_sysfs / "class" / "input" / "event0"
        device_dir = event_dir / "device"
        device_dir.mkdir(parents=True)

        # Create name file but make it raise OSError when read
        name_file = device_dir / "name"
        name_file.write_text("Test Keyboard")

        # Mock file reading to raise OSError
        service = HardwareService()
        service._input_path = mock_sysfs / "class" / "input"

        with patch.object(Path, "read_text", side_effect=PermissionError):
            keyboards = list(service.list_keyboards())
            # Should gracefully handle the error
            assert len(keyboards) == 0
