# SPDX-License-Identifier: GPL-3.0-or-later
"""Service for keyboard hardware configuration and modifier mappings."""

from dataclasses import dataclass
from enum import Enum
from typing import Self

from gi.repository import Gio

from dailydriver.models.keyboard import KeyboardType


class CapsLockBehavior(Enum):
    """Caps Lock key behavior options."""

    CAPS_LOCK = "default"  # Normal Caps Lock
    CTRL = "caps:ctrl_modifier"  # Act as Ctrl
    ESCAPE = "caps:escape"  # Act as Escape (vim)
    BACKSPACE = "caps:backspace"  # Act as Backspace
    SUPER = "caps:super"  # Act as Super/Windows key
    DISABLED = "caps:none"  # Disable completely

    @property
    def display_name(self) -> str:
        names = {
            CapsLockBehavior.CAPS_LOCK: "Caps Lock (default)",
            CapsLockBehavior.CTRL: "Control",
            CapsLockBehavior.ESCAPE: "Escape (vim)",
            CapsLockBehavior.BACKSPACE: "Backspace",
            CapsLockBehavior.SUPER: "Super",
            CapsLockBehavior.DISABLED: "Disabled",
        }
        return names.get(self, self.value)

    @property
    def xkb_option(self) -> str | None:
        """Return the xkb option string, or None for default."""
        if self == CapsLockBehavior.CAPS_LOCK:
            return None
        return self.value


@dataclass
class ModifierConfig:
    """Modifier key configuration (stored per-profile)."""

    # Apple keyboard modifier swaps
    swap_cmd_opt: bool = False  # Swap Cmd↔Option (makes Cmd=Alt, Opt=Super)
    swap_fn_ctrl: bool = False  # Swap Fn↔Left Ctrl

    # Caps Lock behavior
    caps_lock: CapsLockBehavior = CapsLockBehavior.CAPS_LOCK

    # Function key mode (for Apple keyboards)
    fn_keys_primary: bool = False  # F1-F12 are primary (not media keys)

    def to_dict(self) -> dict:
        """Serialize to dict for storage."""
        return {
            "swap_cmd_opt": self.swap_cmd_opt,
            "swap_fn_ctrl": self.swap_fn_ctrl,
            "caps_lock": self.caps_lock.value,
            "fn_keys_primary": self.fn_keys_primary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Deserialize from dict."""
        caps_value = data.get("caps_lock", "default")
        caps_lock = CapsLockBehavior.CAPS_LOCK
        for behavior in CapsLockBehavior:
            if behavior.value == caps_value:
                caps_lock = behavior
                break

        return cls(
            swap_cmd_opt=data.get("swap_cmd_opt", False),
            swap_fn_ctrl=data.get("swap_fn_ctrl", False),
            caps_lock=caps_lock,
            fn_keys_primary=data.get("fn_keys_primary", False),
        )


class KeyboardConfigService:
    """Service for managing keyboard hardware and modifier configuration."""

    # GSettings schema for input sources (xkb options)
    INPUT_SOURCES_SCHEMA = "org.gnome.desktop.input-sources"

    def __init__(self) -> None:
        self._schema_source = Gio.SettingsSchemaSource.get_default()
        self._app_settings: Gio.Settings | None = None
        self._input_settings: Gio.Settings | None = None
        self._init_settings()

    def _init_settings(self) -> None:
        """Initialize GSettings connections."""
        # App settings for keyboard type (global)
        try:
            self._app_settings = Gio.Settings.new("io.github.gregfelice.DailyDriver")
        except Exception:
            pass

        # System input settings for xkb options
        if self._schema_source.lookup(self.INPUT_SOURCES_SCHEMA, True):
            self._input_settings = Gio.Settings.new(self.INPUT_SOURCES_SCHEMA)

    # --- Global Keyboard Type ---

    def get_keyboard_type(self) -> KeyboardType:
        """Get the globally configured keyboard type."""
        if self._app_settings:
            try:
                value = self._app_settings.get_string("keyboard-type")
                for kt in KeyboardType:
                    if kt.value == value:
                        return kt
            except Exception:
                pass
        return KeyboardType.ANSI_104  # Default

    def set_keyboard_type(self, keyboard_type: KeyboardType) -> bool:
        """Set the global keyboard type."""
        if self._app_settings:
            try:
                self._app_settings.set_string("keyboard-type", keyboard_type.value)
                return True
            except Exception:
                pass
        return False

    # --- XKB Options (Caps Lock, etc.) ---

    def get_xkb_options(self) -> list[str]:
        """Get current xkb options."""
        if self._input_settings:
            try:
                return list(self._input_settings.get_strv("xkb-options"))
            except Exception:
                pass
        return []

    def set_xkb_options(self, options: list[str]) -> bool:
        """Set xkb options."""
        if self._input_settings:
            try:
                self._input_settings.set_strv("xkb-options", options)
                return True
            except Exception:
                pass
        return False

    def get_caps_lock_behavior(self) -> CapsLockBehavior:
        """Get current Caps Lock behavior from xkb options."""
        options = self.get_xkb_options()
        for opt in options:
            if opt.startswith("caps:"):
                for behavior in CapsLockBehavior:
                    if behavior.value == opt:
                        return behavior
        return CapsLockBehavior.CAPS_LOCK

    def set_caps_lock_behavior(self, behavior: CapsLockBehavior) -> bool:
        """Set Caps Lock behavior via xkb options."""
        options = self.get_xkb_options()

        # Remove existing caps: options
        options = [opt for opt in options if not opt.startswith("caps:")]

        # Add new option if not default
        xkb_opt = behavior.xkb_option
        if xkb_opt:
            options.append(xkb_opt)

        return self.set_xkb_options(options)

    # --- Apple Keyboard (hid_apple) ---

    def get_apple_swap_cmd_opt(self) -> bool:
        """Check if Cmd/Option swap is enabled for Apple keyboards."""
        try:
            with open("/sys/module/hid_apple/parameters/swap_opt_cmd") as f:
                return f.read().strip() == "1"
        except (FileNotFoundError, PermissionError):
            return False

    def get_apple_fn_mode(self) -> int:
        """Get Apple keyboard Fn mode (0=disabled, 1=fkeys, 2=media)."""
        try:
            with open("/sys/module/hid_apple/parameters/fnmode") as f:
                return int(f.read().strip())
        except (FileNotFoundError, PermissionError, ValueError):
            return 2  # Default: media keys

    # --- Modifier Config Application ---

    def apply_modifier_config(self, config: ModifierConfig) -> bool:
        """Apply a modifier configuration."""
        success = True

        # Apply Caps Lock behavior
        if not self.set_caps_lock_behavior(config.caps_lock):
            success = False

        # Apple keyboard settings require root/polkit - handled by hid_apple_service
        # We just return whether the xkb part succeeded

        return success

    def get_current_modifier_config(self) -> ModifierConfig:
        """Get the current modifier configuration from system state."""
        return ModifierConfig(
            swap_cmd_opt=self.get_apple_swap_cmd_opt(),
            swap_fn_ctrl=False,  # Would need to read from hid_apple
            caps_lock=self.get_caps_lock_behavior(),
            fn_keys_primary=self.get_apple_fn_mode() == 1,
        )

    # --- Presets ---

    @staticmethod
    def get_preset_configs() -> dict[str, ModifierConfig]:
        """Get preset modifier configurations."""
        return {
            "default": ModifierConfig(),
            "mac-native": ModifierConfig(
                swap_cmd_opt=False,
                caps_lock=CapsLockBehavior.CAPS_LOCK,
                fn_keys_primary=False,
            ),
            "mac-to-pc": ModifierConfig(
                swap_cmd_opt=True,  # Cmd becomes Alt, Opt becomes Super
                caps_lock=CapsLockBehavior.CAPS_LOCK,
                fn_keys_primary=False,
            ),
            "developer": ModifierConfig(
                swap_cmd_opt=False,
                caps_lock=CapsLockBehavior.CTRL,
                fn_keys_primary=True,
            ),
            "vim": ModifierConfig(
                swap_cmd_opt=False,
                caps_lock=CapsLockBehavior.ESCAPE,
                fn_keys_primary=True,
            ),
        }
