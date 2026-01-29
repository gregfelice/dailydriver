# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration tests for conflict detection."""

from __future__ import annotations

from pathlib import Path


class TestConflictDetection:
    """Tests for shortcut conflict detection."""

    def test_no_internal_conflicts_in_presets(self, presets_dir: Path, mock_gi: dict) -> None:
        """Test that presets have no internal conflicts."""
        from dailydriver.models.profile import Profile
        from dailydriver.models.shortcut import KeyBinding

        for preset_path in presets_dir.glob("*.toml"):
            profile = Profile.from_toml(preset_path)

            # Collect all bindings and their sources
            binding_sources: dict[str, list[str]] = {}

            for storage_key, accelerators in profile.shortcuts.items():
                for accel in accelerators:
                    if accel:  # Skip empty/disabled
                        # Normalize through parsing
                        binding = KeyBinding.from_accelerator(accel)
                        if binding:
                            normalized = binding.to_accelerator()
                            if normalized not in binding_sources:
                                binding_sources[normalized] = []
                            binding_sources[normalized].append(storage_key)

            # Check for conflicts (same binding used by multiple shortcuts)
            conflicts = {
                binding: sources for binding, sources in binding_sources.items() if len(sources) > 1
            }

            assert len(conflicts) == 0, (
                f"Preset {preset_path.name} has internal conflicts:\n"
                + "\n".join(f"  {b}: {s}" for b, s in conflicts.items())
            )

    def test_shortcut_conflicts_with_method(self, mock_gi: dict) -> None:
        """Test the Shortcut.conflicts_with method."""
        from dailydriver.models.shortcut import KeyBinding, Modifier, Shortcut

        binding = KeyBinding(keyval=0x61, modifiers=Modifier.SUPER)

        shortcut1 = Shortcut(
            id="test1",
            name="Test 1",
            description="",
            category="test",
            schema="test",
            key="test1",
            bindings=[binding],
        )

        shortcut2 = Shortcut(
            id="test2",
            name="Test 2",
            description="",
            category="test",
            schema="test",
            key="test2",
            bindings=[binding],  # Same binding
        )

        shortcut3 = Shortcut(
            id="test3",
            name="Test 3",
            description="",
            category="test",
            schema="test",
            key="test3",
            bindings=[KeyBinding(keyval=0x62, modifiers=Modifier.SUPER)],  # Different
        )

        # Same binding = conflict
        assert shortcut1.conflicts_with(shortcut2)

        # Different binding = no conflict
        assert not shortcut1.conflicts_with(shortcut3)

        # Self = no conflict
        assert not shortcut1.conflicts_with(shortcut1)


class TestCrossPresetConflicts:
    """Tests for detecting conflicts between presets."""

    def test_vanilla_vs_hyprland_differences(self, presets_dir: Path) -> None:
        """Test that vanilla and hyprland presets have meaningful differences."""
        from dailydriver.models.profile import Profile

        vanilla = Profile.from_toml(presets_dir / "vanilla-gnome.toml")
        hyprland = Profile.from_toml(presets_dir / "hyprland-style.toml")

        # Find shortcuts that differ
        different_shortcuts = []

        for key in vanilla.shortcuts:
            if key in hyprland.shortcuts and vanilla.shortcuts[key] != hyprland.shortcuts[key]:
                different_shortcuts.append(key)

        # The presets should have some intentional differences
        # (otherwise why have different presets?)
        assert len(different_shortcuts) > 0, "Presets should have different shortcut bindings"


class TestBindingUniqueness:
    """Tests for binding uniqueness within categories."""

    def test_presets_minimize_super_key_conflicts(self, presets_dir: Path, mock_gi: dict) -> None:
        """Test that presets avoid Super+letter conflicts where possible."""
        from dailydriver.models.profile import Profile
        from dailydriver.models.shortcut import KeyBinding

        for preset_path in presets_dir.glob("*.toml"):
            profile = Profile.from_toml(preset_path)

            # Collect Super+letter bindings
            super_letter_bindings: dict[str, list[str]] = {}

            for storage_key, accelerators in profile.shortcuts.items():
                for accel in accelerators:
                    if accel:
                        binding = KeyBinding.from_accelerator(accel)
                        if binding:
                            accel_str = binding.to_accelerator()
                            # Check if it's Super+single letter
                            if accel_str.startswith("<Super>") and len(accel_str) == 8:
                                letter = accel_str[-1]
                                if letter.isalpha():
                                    if letter not in super_letter_bindings:
                                        super_letter_bindings[letter] = []
                                    super_letter_bindings[letter].append(storage_key)

            # Check for conflicts on Super+letter
            conflicts = {
                letter: sources
                for letter, sources in super_letter_bindings.items()
                if len(sources) > 1
            }

            # Allow some conflicts but report them
            if conflicts:
                # This is informational, not a failure
                print(f"Note: {preset_path.name} has Super+letter reuse: {list(conflicts.keys())}")
