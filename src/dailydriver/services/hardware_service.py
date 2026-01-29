# SPDX-License-Identifier: GPL-3.0-or-later
"""Service for detecting and managing keyboard hardware."""

from collections.abc import Generator
from pathlib import Path

from dailydriver.models import DetectedKeyboard

# Keyboard vendor database
KEYBOARD_VENDORS = {
    0x05AC: ("Apple", "apple"),  # Apple Inc.
    0x046D: ("Logitech", "logitech"),  # Logitech
    0x1532: ("Razer", "razer"),  # Razer
    0x04D9: ("Holtek", "generic"),  # Holtek (many cheap keyboards)
    0x04F2: ("Chicony", "generic"),  # Chicony (OEM)
    0x0951: ("Kingston", "hyperx"),  # Kingston/HyperX
    0x1B1C: ("Corsair", "corsair"),  # Corsair
    0x2516: ("Cooler Master", "generic"),  # Cooler Master
    0x28DA: ("Glorious", "generic"),  # Glorious
    0x320F: ("Ducky", "ducky"),  # Ducky
    0x04B4: ("Keychron", "keychron"),  # Keychron
    0x3434: ("Keychron", "keychron"),  # Keychron (alternate)
    0x0C45: ("Microdia", "generic"),  # Microdia (OEM)
    0x258A: ("SINO WEALTH", "generic"),  # Many mechanical keyboards
    0x1EA7: ("SHARKOON", "generic"),  # Sharkoon
    0x1D50: ("OpenMoko", "generic"),  # Open hardware keyboards
    0x16C0: ("Van Ooijen", "generic"),  # Teensy/custom keyboards
    0xFEED: ("ErgoDox", "ergodox"),  # ErgoDox
}

# Known Apple keyboard product IDs
APPLE_KEYBOARD_PRODUCTS = {
    0x0221: "Magic Keyboard (Aluminum)",
    0x022C: "Magic Keyboard",
    0x0267: "Magic Keyboard with Numeric Keypad",
    0x024F: "Magic Keyboard with Touch ID",
    0x0256: "Magic Keyboard with Touch ID and Numeric Keypad",
    0x0314: "Magic Keyboard with Touch ID (M1)",
    0x0315: "Magic Keyboard with Touch ID and Numeric Keypad (M1)",
}

# Known Apple vendor IDs
APPLE_VENDOR_IDS = {0x05AC}


class HardwareService:
    """Service for detecting keyboard hardware via evdev/sysfs."""

    def __init__(self) -> None:
        self._input_path = Path("/sys/class/input")

    def list_keyboards(self) -> Generator[DetectedKeyboard, None, None]:
        """List all detected keyboards."""
        if not self._input_path.exists():
            return

        for event_dir in sorted(self._input_path.glob("event*")):
            device = self._parse_device(event_dir)
            if device and self._is_keyboard(event_dir):
                yield device

    def _parse_device(self, event_dir: Path) -> DetectedKeyboard | None:
        """Parse device information from sysfs."""
        device_dir = event_dir / "device"
        if not device_dir.exists():
            return None

        # Get device name
        name_file = device_dir / "name"
        if not name_file.exists():
            return None

        try:
            name = name_file.read_text().strip()
        except (OSError, PermissionError):
            return None

        # Get vendor/product IDs
        vendor_id = 0
        product_id = 0

        id_dir = device_dir / "id"
        if id_dir.exists():
            try:
                vendor_file = id_dir / "vendor"
                if vendor_file.exists():
                    vendor_id = int(vendor_file.read_text().strip(), 16)

                product_file = id_dir / "product"
                if product_file.exists():
                    product_id = int(product_file.read_text().strip(), 16)
            except (OSError, ValueError):
                pass

        # Determine device path
        dev_path = f"/dev/input/{event_dir.name}"

        # Detect device type
        is_mac = vendor_id in APPLE_VENDOR_IDS
        is_bluetooth = "bluetooth" in name.lower() or self._is_bluetooth_device(device_dir)
        is_internal = "AT Translated" in name or "laptop" in name.lower()

        # Get brand info
        brand_name, brand_id = KEYBOARD_VENDORS.get(vendor_id, ("Generic", "generic"))

        # Get model name for known keyboards
        model_name = ""
        if is_mac and product_id in APPLE_KEYBOARD_PRODUCTS:
            model_name = APPLE_KEYBOARD_PRODUCTS[product_id]

        # Detect capabilities
        has_numpad = self._has_numpad(device_dir)
        has_media_keys = self._has_media_keys(device_dir)
        has_fn_key = self._has_fn_key(device_dir)

        return DetectedKeyboard(
            name=name,
            path=dev_path,
            vendor_id=vendor_id,
            product_id=product_id,
            is_mac=is_mac,
            is_bluetooth=is_bluetooth,
            is_internal=is_internal,
            brand_name=brand_name,
            brand_id=brand_id,
            model_name=model_name,
            has_numpad=has_numpad,
            has_media_keys=has_media_keys,
            has_fn_key=has_fn_key,
        )

    def _is_keyboard(self, event_dir: Path) -> bool:
        """Check if device is a keyboard (has KEY capabilities, not a mouse/trackpad)."""
        device_dir = event_dir / "device"

        # First check device name to filter out non-keyboards
        name_file = device_dir / "name"
        if name_file.exists():
            try:
                name = name_file.read_text().strip().lower()
                # Exclude mice, trackpads, touchscreens, etc.
                exclude_patterns = [
                    "trackpad",
                    "touchpad",
                    "mouse",
                    "trackball",
                    "touchscreen",
                    "touch screen",
                    "tablet",
                    "gamepad",
                    "joystick",
                    "controller",
                    "power button",
                    "sleep button",
                    "lid switch",
                    "video bus",
                    "pc speaker",
                    "gpio",
                ]
                if any(pattern in name for pattern in exclude_patterns):
                    return False
            except (OSError, PermissionError):
                pass

        caps_file = device_dir / "capabilities" / "key"
        if not caps_file.exists():
            return False

        try:
            caps = caps_file.read_text().strip()
            # A keyboard should have non-zero key capabilities
            # and should have alphabetic keys (not just buttons)
            # Real keyboards have extensive key capabilities
            parts = caps.split()
            if not parts:
                return False
            # Check that we have enough capability bits for a real keyboard
            # Mice/trackpads have minimal key caps, keyboards have many
            total_bits = sum(bin(int(p, 16)).count("1") for p in parts)
            return total_bits > 20  # Real keyboards have 50+ keys mapped
        except (OSError, ValueError):
            return False

    def _is_bluetooth_device(self, device_dir: Path) -> bool:
        """Check if device is connected via Bluetooth."""
        # Follow symlinks to check device path
        try:
            uevent_file = device_dir / "uevent"
            if uevent_file.exists():
                content = uevent_file.read_text()
                return "bluetooth" in content.lower()
        except (OSError, PermissionError):
            pass
        return False

    def _has_numpad(self, device_dir: Path) -> bool:
        """Check if keyboard has a numpad."""
        # This is a heuristic based on key capabilities
        # Numpad keys are typically KEY_KP0-KEY_KPDOT (71-83)
        caps_file = device_dir / "capabilities" / "key"
        if not caps_file.exists():
            return False

        try:
            caps = caps_file.read_text().strip()
            # Check if numpad range has bits set
            # This is a simplified check
            return len(caps) > 20  # Full keyboards have more capability bits
        except (OSError, ValueError):
            return False

    def _has_media_keys(self, device_dir: Path) -> bool:
        """Check if keyboard has media keys."""
        # Media keys are in the extended key range
        caps_file = device_dir / "capabilities" / "key"
        if not caps_file.exists():
            return False

        try:
            caps = caps_file.read_text().strip()
            # Check for extended key capabilities
            parts = caps.split()
            return len(parts) > 3  # Media keys require extended capability bits
        except (OSError, ValueError):
            return False

    def _has_fn_key(self, device_dir: Path) -> bool:
        """Check if keyboard has an Fn key (common on laptops and Mac keyboards)."""
        # Fn key is typically exposed through hid-apple or similar drivers
        name_file = device_dir / "name"
        if not name_file.exists():
            return False

        try:
            name = name_file.read_text().strip().lower()
            return "apple" in name or "fn" in name
        except (OSError, PermissionError):
            return False

    def get_mac_keyboards(self) -> list[DetectedKeyboard]:
        """Get all detected Apple/Mac keyboards."""
        return [kb for kb in self.list_keyboards() if kb.is_mac]
