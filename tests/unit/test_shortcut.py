# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for Shortcut and KeyBinding models.

These tests require GTK mocking since the shortcut module uses GTK
accelerator parsing functions.
"""

from __future__ import annotations

import pytest


class TestModifier:
    """Tests for Modifier flag enum."""

    def test_modifier_none(self, mock_gi: dict) -> None:
        """Test NONE modifier."""
        from dailydriver.models.shortcut import Modifier

        assert Modifier.NONE.value == 0

    def test_modifier_flags(self, mock_gi: dict) -> None:
        """Test individual modifier flags."""
        from dailydriver.models.shortcut import Modifier

        assert Modifier.SHIFT.value > 0
        assert Modifier.CTRL.value > 0
        assert Modifier.ALT.value > 0
        assert Modifier.SUPER.value > 0

    def test_modifier_combinations(self, mock_gi: dict) -> None:
        """Test combining modifier flags."""
        from dailydriver.models.shortcut import Modifier

        combined = Modifier.CTRL | Modifier.SHIFT
        assert Modifier.CTRL in combined
        assert Modifier.SHIFT in combined
        assert Modifier.ALT not in combined

    def test_from_gtk(self, mock_gi: dict) -> None:
        """Test conversion from GTK modifier state."""
        from dailydriver.models.shortcut import Modifier
        from tests.conftest import MockGdkModifierType

        # Single modifier
        result = Modifier.from_gtk(MockGdkModifierType.CONTROL_MASK)
        assert Modifier.CTRL in result

        # Combined modifiers
        combined_mask = MockGdkModifierType.CONTROL_MASK | MockGdkModifierType.SHIFT_MASK
        result = Modifier.from_gtk(combined_mask)
        assert Modifier.CTRL in result
        assert Modifier.SHIFT in result

    def test_to_gtk(self, mock_gi: dict) -> None:
        """Test conversion to GTK modifier state."""
        from dailydriver.models.shortcut import Modifier
        from tests.conftest import MockGdkModifierType

        mods = Modifier.CTRL | Modifier.SHIFT
        gtk_state = mods.to_gtk()

        assert gtk_state & MockGdkModifierType.CONTROL_MASK
        assert gtk_state & MockGdkModifierType.SHIFT_MASK


class TestKeyBinding:
    """Tests for KeyBinding dataclass."""

    def test_keybinding_creation(self, mock_gi: dict) -> None:
        """Test basic KeyBinding creation."""
        from dailydriver.models.shortcut import KeyBinding, Modifier

        binding = KeyBinding(keyval=0x61, modifiers=Modifier.CTRL)

        assert binding.keyval == 0x61
        assert Modifier.CTRL in binding.modifiers

    def test_from_accelerator_simple(self, mock_gi: dict) -> None:
        """Test parsing simple accelerator strings."""
        from dailydriver.models.shortcut import KeyBinding, Modifier

        # Super+a
        binding = KeyBinding.from_accelerator("<Super>a")
        assert binding is not None
        assert binding.keyval == 0x61  # 'a'
        assert Modifier.SUPER in binding.modifiers

    def test_from_accelerator_combined_modifiers(self, mock_gi: dict) -> None:
        """Test parsing accelerator with multiple modifiers."""
        from dailydriver.models.shortcut import KeyBinding, Modifier

        # Ctrl+Shift+Tab
        binding = KeyBinding.from_accelerator("<Control><Shift>Tab")
        assert binding is not None
        assert Modifier.CTRL in binding.modifiers
        assert Modifier.SHIFT in binding.modifiers

    def test_from_accelerator_empty(self, mock_gi: dict) -> None:
        """Test parsing empty accelerator."""
        from dailydriver.models.shortcut import KeyBinding

        assert KeyBinding.from_accelerator("") is None
        assert KeyBinding.from_accelerator("disabled") is None

    def test_from_accelerator_invalid(self, mock_gi: dict) -> None:
        """Test parsing invalid accelerator."""
        from dailydriver.models.shortcut import KeyBinding

        assert KeyBinding.from_accelerator("<InvalidKey>xyz") is None

    def test_to_accelerator(self, mock_gi: dict) -> None:
        """Test converting KeyBinding back to accelerator string."""
        from dailydriver.models.shortcut import KeyBinding, Modifier

        binding = KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)
        accel = binding.to_accelerator()

        assert "<Super>" in accel
        assert "a" in accel

    def test_to_label(self, mock_gi: dict) -> None:
        """Test converting KeyBinding to human-readable label."""
        from dailydriver.models.shortcut import KeyBinding, Modifier

        binding = KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)
        label = binding.to_label()

        assert "Super" in label

    def test_key_name(self, mock_gi: dict) -> None:
        """Test getting key name without modifiers."""
        from dailydriver.models.shortcut import KeyBinding, Modifier

        binding = KeyBinding(keyval=0xFF09, modifiers=Modifier.ALT)  # Tab
        assert binding.key_name == "Tab"

    def test_round_trip(self, mock_gi: dict) -> None:
        """Test accelerator parsing round-trip."""
        from dailydriver.models.shortcut import KeyBinding

        original = "<Super>Left"
        binding = KeyBinding.from_accelerator(original)
        assert binding is not None

        result = binding.to_accelerator()
        # Parse again and compare
        binding2 = KeyBinding.from_accelerator(result)
        assert binding2 is not None
        assert binding.keyval == binding2.keyval
        assert binding.modifiers == binding2.modifiers

    def test_frozen_dataclass(self, mock_gi: dict) -> None:
        """Test that KeyBinding is frozen (immutable)."""
        from dailydriver.models.shortcut import KeyBinding, Modifier

        binding = KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)

        with pytest.raises(AttributeError):
            binding.keyval = 0x62  # type: ignore


class TestShortcutCategory:
    """Tests for ShortcutCategory dataclass."""

    def test_category_creation(self, mock_gi: dict) -> None:
        """Test basic category creation."""
        from dailydriver.models.shortcut import ShortcutCategory

        category = ShortcutCategory(
            id="window-management",
            name="Window Management",
            icon="preferences-system-windows-symbolic",
            description="Manage windows",
        )

        assert category.id == "window-management"
        assert category.name == "Window Management"
        assert category.description == "Manage windows"


class TestShortcut:
    """Tests for Shortcut dataclass."""

    def test_shortcut_creation(self, mock_gi: dict) -> None:
        """Test basic shortcut creation."""
        from dailydriver.models.shortcut import Shortcut

        shortcut = Shortcut(
            id="org.gnome.desktop.wm.keybindings.close",
            name="Close Window",
            description="Close the active window",
            category="window-management",
            schema="org.gnome.desktop.wm.keybindings",
            key="close",
        )

        assert shortcut.id == "org.gnome.desktop.wm.keybindings.close"
        assert shortcut.name == "Close Window"
        assert shortcut.bindings == []

    def test_accelerator_property(self, mock_gi: dict) -> None:
        """Test accelerator property."""
        from dailydriver.models.shortcut import KeyBinding, Modifier, Shortcut

        shortcut = Shortcut(
            id="test",
            name="Test",
            description="",
            category="test",
            schema="test",
            key="test",
            bindings=[KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)],
        )

        assert shortcut.accelerator
        assert "<Super>" in shortcut.accelerator

        # No bindings
        empty_shortcut = Shortcut(
            id="test2",
            name="Test2",
            description="",
            category="test",
            schema="test",
            key="test2",
        )
        assert empty_shortcut.accelerator == ""

    def test_accelerators_property(self, mock_gi: dict) -> None:
        """Test accelerators property with multiple bindings."""
        from dailydriver.models.shortcut import KeyBinding, Modifier, Shortcut

        shortcut = Shortcut(
            id="test",
            name="Test",
            description="",
            category="test",
            schema="test",
            key="test",
            bindings=[
                KeyBinding(keyval=0x61, modifiers=Modifier.SUPER),
                KeyBinding(keyval=0x62, modifiers=Modifier.CTRL),
            ],
            allow_multiple=True,
        )

        accels = shortcut.accelerators
        assert len(accels) == 2

    def test_label_property(self, mock_gi: dict) -> None:
        """Test label property."""
        from dailydriver.models.shortcut import KeyBinding, Modifier, Shortcut

        shortcut = Shortcut(
            id="test",
            name="Test",
            description="",
            category="test",
            schema="test",
            key="test",
            bindings=[KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)],
        )

        assert shortcut.label
        assert "Disabled" not in shortcut.label

        # No bindings
        empty_shortcut = Shortcut(
            id="test2",
            name="Test2",
            description="",
            category="test",
            schema="test",
            key="test2",
        )
        assert empty_shortcut.label == "Disabled"

    def test_is_modified(self, mock_gi: dict) -> None:
        """Test is_modified property."""
        from dailydriver.models.shortcut import KeyBinding, Modifier, Shortcut

        binding1 = KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)
        binding2 = KeyBinding(keyval=0x62, modifiers=Modifier.SUPER)

        # Not modified (bindings match defaults)
        shortcut = Shortcut(
            id="test",
            name="Test",
            description="",
            category="test",
            schema="test",
            key="test",
            bindings=[binding1],
            default_bindings=[binding1],
        )
        assert not shortcut.is_modified

        # Modified (bindings differ from defaults)
        modified_shortcut = Shortcut(
            id="test2",
            name="Test2",
            description="",
            category="test",
            schema="test",
            key="test2",
            bindings=[binding2],
            default_bindings=[binding1],
        )
        assert modified_shortcut.is_modified

    def test_set_binding(self, mock_gi: dict) -> None:
        """Test set_binding method."""
        from dailydriver.models.shortcut import KeyBinding, Modifier, Shortcut

        shortcut = Shortcut(
            id="test",
            name="Test",
            description="",
            category="test",
            schema="test",
            key="test",
        )

        binding = KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)
        shortcut.set_binding(binding)

        assert len(shortcut.bindings) == 1
        assert shortcut.bindings[0] == binding

        # Set to None (clear)
        shortcut.set_binding(None)
        assert len(shortcut.bindings) == 0

    def test_add_binding_single(self, mock_gi: dict) -> None:
        """Test add_binding when allow_multiple is False."""
        from dailydriver.models.shortcut import KeyBinding, Modifier, Shortcut

        shortcut = Shortcut(
            id="test",
            name="Test",
            description="",
            category="test",
            schema="test",
            key="test",
            allow_multiple=False,
        )

        binding1 = KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)
        binding2 = KeyBinding(keyval=0x62, modifiers=Modifier.SUPER)

        shortcut.add_binding(binding1)
        assert len(shortcut.bindings) == 1

        # Adding second replaces first
        shortcut.add_binding(binding2)
        assert len(shortcut.bindings) == 1
        assert shortcut.bindings[0] == binding2

    def test_add_binding_multiple(self, mock_gi: dict) -> None:
        """Test add_binding when allow_multiple is True."""
        from dailydriver.models.shortcut import KeyBinding, Modifier, Shortcut

        shortcut = Shortcut(
            id="test",
            name="Test",
            description="",
            category="test",
            schema="test",
            key="test",
            allow_multiple=True,
        )

        binding1 = KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)
        binding2 = KeyBinding(keyval=0x62, modifiers=Modifier.SUPER)

        shortcut.add_binding(binding1)
        shortcut.add_binding(binding2)

        assert len(shortcut.bindings) == 2

        # Adding duplicate does nothing
        shortcut.add_binding(binding1)
        assert len(shortcut.bindings) == 2

    def test_remove_binding(self, mock_gi: dict) -> None:
        """Test remove_binding method."""
        from dailydriver.models.shortcut import KeyBinding, Modifier, Shortcut

        binding1 = KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)
        binding2 = KeyBinding(keyval=0x62, modifiers=Modifier.SUPER)

        shortcut = Shortcut(
            id="test",
            name="Test",
            description="",
            category="test",
            schema="test",
            key="test",
            bindings=[binding1, binding2],
            allow_multiple=True,
        )

        shortcut.remove_binding(binding1)
        assert len(shortcut.bindings) == 1
        assert shortcut.bindings[0] == binding2

        # Removing non-existent binding does nothing
        shortcut.remove_binding(binding1)
        assert len(shortcut.bindings) == 1

    def test_reset(self, mock_gi: dict) -> None:
        """Test reset method."""
        from dailydriver.models.shortcut import KeyBinding, Modifier, Shortcut

        default_binding = KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)
        current_binding = KeyBinding(keyval=0x62, modifiers=Modifier.CTRL)

        shortcut = Shortcut(
            id="test",
            name="Test",
            description="",
            category="test",
            schema="test",
            key="test",
            bindings=[current_binding],
            default_bindings=[default_binding],
        )

        assert shortcut.is_modified

        shortcut.reset()

        assert not shortcut.is_modified
        assert shortcut.bindings[0] == default_binding

    def test_conflicts_with(self, mock_gi: dict) -> None:
        """Test conflicts_with method."""
        from dailydriver.models.shortcut import KeyBinding, Modifier, Shortcut

        binding1 = KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)
        binding2 = KeyBinding(keyval=0x62, modifiers=Modifier.SUPER)

        shortcut1 = Shortcut(
            id="test1",
            name="Test1",
            description="",
            category="test",
            schema="test",
            key="test1",
            bindings=[binding1],
        )

        shortcut2_conflict = Shortcut(
            id="test2",
            name="Test2",
            description="",
            category="test",
            schema="test",
            key="test2",
            bindings=[binding1],  # Same binding
        )

        shortcut3_no_conflict = Shortcut(
            id="test3",
            name="Test3",
            description="",
            category="test",
            schema="test",
            key="test3",
            bindings=[binding2],  # Different binding
        )

        assert shortcut1.conflicts_with(shortcut2_conflict)
        assert not shortcut1.conflicts_with(shortcut3_no_conflict)

        # Self never conflicts
        assert not shortcut1.conflicts_with(shortcut1)
