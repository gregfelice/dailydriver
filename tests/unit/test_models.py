# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for DailyDriver models."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class TestKeyboardType:
    """Tests for KeyboardType enum."""

    def test_display_names(self) -> None:
        """Test that all keyboard types have display names."""
        from dailydriver.models.keyboard import KeyboardType

        for kb_type in KeyboardType:
            assert kb_type.display_name
            assert isinstance(kb_type.display_name, str)

    def test_is_apple(self) -> None:
        """Test Apple keyboard detection."""
        from dailydriver.models.keyboard import KeyboardType

        assert KeyboardType.MAC_ANSI.is_apple
        assert KeyboardType.MAC_ISO.is_apple
        assert not KeyboardType.ANSI_104.is_apple
        assert not KeyboardType.ISO_105.is_apple

    def test_is_iso(self) -> None:
        """Test ISO layout detection."""
        from dailydriver.models.keyboard import KeyboardType

        assert KeyboardType.ISO_105.is_iso
        assert KeyboardType.MAC_ISO.is_iso
        assert not KeyboardType.ANSI_104.is_iso
        assert not KeyboardType.MAC_ANSI.is_iso


class TestKey:
    """Tests for Key dataclass."""

    def test_key_creation(self) -> None:
        """Test basic key creation."""
        from dailydriver.models.keyboard import Key

        key = Key(x=0.0, y=0.0, width=1.0, height=1.0, label="A")

        assert key.x == 0.0
        assert key.y == 0.0
        assert key.width == 1.0
        assert key.height == 1.0
        assert key.label == "A"

    def test_center_position(self) -> None:
        """Test center position calculation."""
        from dailydriver.models.keyboard import Key

        # 1u key at (0,0)
        key = Key(x=0.0, y=0.0, width=1.0, height=1.0)
        assert key.center_x == 0.5
        assert key.center_y == 0.5

        # 2u key at (1,0)
        wide_key = Key(x=1.0, y=0.0, width=2.0, height=1.0)
        assert wide_key.center_x == 2.0
        assert wide_key.center_y == 0.5

        # 1.25u modifier at (2,1)
        modifier = Key(x=2.0, y=1.0, width=1.25, height=1.0)
        assert modifier.center_x == 2.625
        assert modifier.center_y == 1.5

    def test_key_with_labels(self) -> None:
        """Test key with primary and secondary labels."""
        from dailydriver.models.keyboard import Key

        key = Key(
            x=0.0,
            y=0.0,
            label="1",
            secondary_label="!",
        )

        assert key.label == "1"
        assert key.secondary_label == "!"

    def test_modifier_key(self) -> None:
        """Test modifier key properties."""
        from dailydriver.models.keyboard import Key

        shift = Key(x=0.0, y=0.0, label="Shift", is_modifier=True)
        regular = Key(x=1.0, y=0.0, label="A")

        assert shift.is_modifier
        assert not regular.is_modifier


class TestKeyboardLayout:
    """Tests for KeyboardLayout dataclass."""

    def test_layout_from_json(self, tmp_path: Path) -> None:
        """Test loading layout from JSON file."""
        from dailydriver.models.keyboard import KeyboardLayout, KeyboardType

        layout_data = {
            "id": "test-layout",
            "name": "Test Layout",
            "type": "ansi-104",
            "width": 23.0,
            "height": 6.5,
            "keys": [
                {"x": 0.0, "y": 0.0, "label": "Esc", "keycode": 1},
                {"x": 2.0, "y": 0.0, "label": "F1", "keycode": 59},
            ],
        }

        json_path = tmp_path / "layout.json"
        with open(json_path, "w") as f:
            json.dump(layout_data, f)

        layout = KeyboardLayout.from_json(json_path)

        assert layout.id == "test-layout"
        assert layout.name == "Test Layout"
        assert layout.type == KeyboardType.ANSI_104
        assert layout.width == 23.0
        assert layout.height == 6.5
        assert len(layout.keys) == 2

    def test_get_key_at(self, tmp_path: Path) -> None:
        """Test finding key at position."""
        from dailydriver.models.keyboard import KeyboardLayout

        layout_data = {
            "id": "test",
            "name": "Test",
            "type": "ansi-104",
            "keys": [
                {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0, "label": "A"},
                {"x": 1.0, "y": 0.0, "width": 2.0, "height": 1.0, "label": "Tab"},
            ],
        }

        json_path = tmp_path / "layout.json"
        with open(json_path, "w") as f:
            json.dump(layout_data, f)

        layout = KeyboardLayout.from_json(json_path)

        # Find key A
        key_a = layout.get_key_at(0.5, 0.5)
        assert key_a is not None
        assert key_a.label == "A"

        # Find Tab (2u wide)
        key_tab = layout.get_key_at(2.0, 0.5)
        assert key_tab is not None
        assert key_tab.label == "Tab"

        # No key at position
        no_key = layout.get_key_at(10.0, 10.0)
        assert no_key is None

    def test_get_key_by_keycode(self, tmp_path: Path) -> None:
        """Test finding key by keycode."""
        from dailydriver.models.keyboard import KeyboardLayout

        layout_data = {
            "id": "test",
            "name": "Test",
            "type": "ansi-104",
            "keys": [
                {"x": 0.0, "y": 0.0, "keycode": 30, "label": "A"},
                {"x": 1.0, "y": 0.0, "keycode": 48, "label": "B"},
            ],
        }

        json_path = tmp_path / "layout.json"
        with open(json_path, "w") as f:
            json.dump(layout_data, f)

        layout = KeyboardLayout.from_json(json_path)

        key_a = layout.get_key_by_keycode(30)
        assert key_a is not None
        assert key_a.label == "A"

        key_b = layout.get_key_by_keycode(48)
        assert key_b is not None
        assert key_b.label == "B"

        no_key = layout.get_key_by_keycode(999)
        assert no_key is None


class TestDetectedKeyboard:
    """Tests for DetectedKeyboard dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic DetectedKeyboard creation."""
        from dailydriver.models.keyboard import DetectedKeyboard

        kb = DetectedKeyboard(
            name="Test Keyboard",
            path="/dev/input/event0",
            vendor_id=0x1234,
            product_id=0x5678,
        )

        assert kb.name == "Test Keyboard"
        assert kb.vendor_id == 0x1234
        assert kb.product_id == 0x5678

    def test_usb_id(self) -> None:
        """Test USB ID formatting."""
        from dailydriver.models.keyboard import DetectedKeyboard

        kb = DetectedKeyboard(
            name="Test",
            path="/dev/input/event0",
            vendor_id=0x05AC,
            product_id=0x0267,
        )

        assert kb.usb_id == "05ac:0267"

    def test_display_name_with_brand(self) -> None:
        """Test display name generation."""
        from dailydriver.models.keyboard import DetectedKeyboard

        # Keyboard with model name
        kb_with_model = DetectedKeyboard(
            name="Internal Keyboard",
            path="/dev/input/event0",
            vendor_id=0x05AC,
            product_id=0x0267,
            brand_name="Apple",
            model_name="Magic Keyboard",
        )
        assert kb_with_model.display_name == "Magic Keyboard"

        # Keyboard without model name
        kb_no_model = DetectedKeyboard(
            name="USB Keyboard",
            path="/dev/input/event0",
            vendor_id=0x046D,
            product_id=0x1234,
            brand_name="Logitech",
        )
        assert "Logitech" in kb_no_model.display_name

        # Bluetooth keyboard
        kb_bluetooth = DetectedKeyboard(
            name="BT Keyboard",
            path="/dev/input/event0",
            vendor_id=0x1234,
            product_id=0x5678,
            is_bluetooth=True,
        )
        assert "(Bluetooth)" in kb_bluetooth.display_name

    def test_form_factor(self) -> None:
        """Test form factor detection."""
        from dailydriver.models.keyboard import DetectedKeyboard

        # Full-size with numpad
        full = DetectedKeyboard(
            name="Full",
            path="/dev/input/event0",
            vendor_id=0x1234,
            product_id=0x5678,
            has_numpad=True,
        )
        assert "Full-size" in full.form_factor

        # Laptop keyboard
        laptop = DetectedKeyboard(
            name="Laptop",
            path="/dev/input/event0",
            vendor_id=0x1234,
            product_id=0x5678,
            is_internal=True,
        )
        assert "Laptop" in laptop.form_factor

        # TKL
        tkl = DetectedKeyboard(
            name="TKL",
            path="/dev/input/event0",
            vendor_id=0x1234,
            product_id=0x5678,
        )
        assert "TKL" in tkl.form_factor

    def test_suggested_layout(self) -> None:
        """Test layout suggestion."""
        from dailydriver.models.keyboard import DetectedKeyboard, KeyboardType

        # Mac keyboard
        mac = DetectedKeyboard(
            name="Mac",
            path="/dev/input/event0",
            vendor_id=0x05AC,
            product_id=0x0267,
            is_mac=True,
        )
        assert mac.suggested_layout() == KeyboardType.MAC_ANSI

        # Full-size
        full = DetectedKeyboard(
            name="Full",
            path="/dev/input/event0",
            vendor_id=0x1234,
            product_id=0x5678,
            has_numpad=True,
        )
        assert full.suggested_layout() == KeyboardType.ANSI_104

        # TKL
        tkl = DetectedKeyboard(
            name="TKL",
            path="/dev/input/event0",
            vendor_id=0x1234,
            product_id=0x5678,
        )
        assert tkl.suggested_layout() == KeyboardType.ANSI_87


class TestFnMode:
    """Tests for FnMode enum."""

    def test_fn_mode_values(self) -> None:
        """Test FnMode enum values."""
        from dailydriver.models.profile import FnMode

        assert FnMode.DISABLED.value == 0
        assert FnMode.FKEYS.value == 1
        assert FnMode.MEDIA.value == 2


class TestMacKeyboardConfig:
    """Tests for MacKeyboardConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default Mac keyboard configuration."""
        from dailydriver.models.profile import FnMode, MacKeyboardConfig

        config = MacKeyboardConfig()

        assert config.fn_mode == FnMode.MEDIA
        assert not config.swap_opt_cmd
        assert not config.swap_fn_leftctrl
        assert not config.iso_layout

    def test_to_modprobe_options(self) -> None:
        """Test conversion to modprobe options."""
        from dailydriver.models.profile import FnMode, MacKeyboardConfig

        config = MacKeyboardConfig(
            fn_mode=FnMode.FKEYS,
            swap_opt_cmd=True,
            swap_fn_leftctrl=False,
            iso_layout=True,
        )

        options = config.to_modprobe_options()

        assert options["fnmode"] == 1
        assert options["swap_opt_cmd"] == 1
        assert options["swap_fn_leftctrl"] == 0
        assert options["iso_layout"] == 1


class TestXKBOptions:
    """Tests for XKBOptions dataclass."""

    def test_default_options(self) -> None:
        """Test default XKB options."""
        from dailydriver.models.profile import XKBOptions

        options = XKBOptions()

        assert options.caps_lock_behavior == ""
        assert options.alt_win_behavior == ""
        assert options.to_xkb_options() == []

    def test_to_xkb_options(self) -> None:
        """Test conversion to XKB options list."""
        from dailydriver.models.profile import XKBOptions

        options = XKBOptions(
            caps_lock_behavior="caps:escape",
            alt_win_behavior="altwin:swap_alt_win",
            compose_key="compose:ralt",
        )

        xkb_list = options.to_xkb_options()

        assert "caps:escape" in xkb_list
        assert "altwin:swap_alt_win" in xkb_list
        assert "compose:ralt" in xkb_list
        assert len(xkb_list) == 3

    def test_partial_options(self) -> None:
        """Test with only some options set."""
        from dailydriver.models.profile import XKBOptions

        options = XKBOptions(caps_lock_behavior="caps:ctrl_modifier")

        xkb_list = options.to_xkb_options()

        assert xkb_list == ["caps:ctrl_modifier"]


class TestProfile:
    """Tests for Profile dataclass."""

    def test_profile_creation(self) -> None:
        """Test basic profile creation."""
        from dailydriver.models.profile import Profile

        profile = Profile(
            name="test-profile",
            description="Test description",
        )

        assert profile.name == "test-profile"
        assert profile.description == "Test description"
        assert isinstance(profile.created, datetime)
        assert isinstance(profile.modified, datetime)

    def test_profile_from_toml(self, sample_profile_toml: Path) -> None:
        """Test loading profile from TOML file."""
        from dailydriver.models.profile import Profile

        profile = Profile.from_toml(sample_profile_toml)

        assert profile.name == "test-profile"
        assert profile.description == "Test profile for unit tests"
        assert "org.gnome.desktop.wm.keybindings.close" in profile.shortcuts
        assert profile.xkb_options.caps_lock_behavior == "caps:escape"

    def test_profile_to_toml(self, tmp_path: Path) -> None:
        """Test saving profile to TOML file."""
        from dailydriver.models.profile import Profile, XKBOptions

        profile = Profile(
            name="save-test",
            description="Test saving",
            xkb_options=XKBOptions(caps_lock_behavior="caps:escape"),
        )
        profile.set_shortcut("org.gnome.desktop.wm.keybindings", "close", ["<Alt>F4"])

        save_path = tmp_path / "save-test.toml"
        profile.to_toml(save_path)

        # Load and verify
        loaded = Profile.from_toml(save_path)

        assert loaded.name == "save-test"
        assert loaded.description == "Test saving"
        assert loaded.get_shortcut("org.gnome.desktop.wm.keybindings", "close") == ["<Alt>F4"]
        assert loaded.xkb_options.caps_lock_behavior == "caps:escape"

    def test_profile_round_trip(self, tmp_path: Path) -> None:
        """Test that profile survives TOML round-trip."""
        from dailydriver.models.profile import (
            FnMode,
            MacKeyboardConfig,
            Profile,
            XKBOptions,
        )

        original = Profile(
            name="round-trip-test",
            description="Testing round trip",
            author="Test Author",
            version="2.0",
            xkb_options=XKBOptions(
                caps_lock_behavior="caps:escape",
                compose_key="compose:ralt",
            ),
            mac_keyboard=MacKeyboardConfig(
                fn_mode=FnMode.FKEYS,
                swap_opt_cmd=True,
            ),
            metadata={"custom_key": "custom_value"},
        )
        original.set_shortcut("org.gnome.desktop.wm.keybindings", "close", ["<Alt>F4"])
        original.set_shortcut("org.gnome.mutter.keybindings", "toggle-tiled-left", ["<Super>Left"])

        # Save and reload
        save_path = tmp_path / "round-trip.toml"
        original.to_toml(save_path)
        loaded = Profile.from_toml(save_path)

        # Verify all fields
        assert loaded.name == original.name
        assert loaded.description == original.description
        assert loaded.author == original.author
        assert loaded.version == original.version
        assert loaded.shortcuts == original.shortcuts
        assert loaded.xkb_options.caps_lock_behavior == original.xkb_options.caps_lock_behavior
        assert loaded.xkb_options.compose_key == original.xkb_options.compose_key
        assert loaded.mac_keyboard is not None
        assert loaded.mac_keyboard.fn_mode == FnMode.FKEYS
        assert loaded.mac_keyboard.swap_opt_cmd is True
        assert loaded.metadata.get("custom_key") == "custom_value"

    def test_shortcut_key_generation(self) -> None:
        """Test shortcut storage key generation."""
        from dailydriver.models.profile import Profile

        profile = Profile(name="test")

        key = profile.get_shortcut_key("org.gnome.desktop.wm.keybindings", "close")
        assert key == "org.gnome.desktop.wm.keybindings.close"

    def test_set_and_get_shortcut(self) -> None:
        """Test setting and getting shortcuts."""
        from dailydriver.models.profile import Profile

        profile = Profile(name="test")

        # Initially empty
        assert profile.get_shortcut("org.gnome.desktop.wm.keybindings", "close") is None

        # Set shortcut
        profile.set_shortcut("org.gnome.desktop.wm.keybindings", "close", ["<Alt>F4"])
        assert profile.get_shortcut("org.gnome.desktop.wm.keybindings", "close") == ["<Alt>F4"]

        # Update shortcut
        profile.set_shortcut("org.gnome.desktop.wm.keybindings", "close", ["<Super>q"])
        assert profile.get_shortcut("org.gnome.desktop.wm.keybindings", "close") == ["<Super>q"]


class TestPresetValidity:
    """Tests to ensure all preset files are valid."""

    def test_all_presets_load(self, presets_dir: Path) -> None:
        """Test that all preset files can be loaded."""
        from dailydriver.models.profile import Profile

        preset_files = list(presets_dir.glob("*.toml"))
        assert len(preset_files) >= 3, "Expected at least 3 preset files"

        for preset_path in preset_files:
            profile = Profile.from_toml(preset_path)

            assert profile.name, f"Preset {preset_path.name} has no name"
            assert profile.shortcuts, f"Preset {preset_path.name} has no shortcuts"

    def test_preset_has_required_fields(self, presets_dir: Path) -> None:
        """Test that presets have required metadata."""
        from dailydriver.models.profile import Profile

        for preset_path in presets_dir.glob("*.toml"):
            profile = Profile.from_toml(preset_path)

            assert profile.name, f"Missing name in {preset_path.name}"
            assert profile.description, f"Missing description in {preset_path.name}"

    def test_vanilla_gnome_preset(self, presets_dir: Path) -> None:
        """Test specific vanilla-gnome preset content."""
        from dailydriver.models.profile import Profile

        profile = Profile.from_toml(presets_dir / "vanilla-gnome.toml")

        assert profile.name == "vanilla-gnome"

        # Check expected shortcuts exist
        assert "org.gnome.desktop.wm.keybindings.close" in profile.shortcuts
        assert "org.gnome.desktop.wm.keybindings.maximize" in profile.shortcuts
        assert "org.gnome.mutter.keybindings.toggle-tiled-left" in profile.shortcuts
