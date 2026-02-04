# SPDX-License-Identifier: GPL-3.0-or-later
"""Service for configuring hid-apple kernel module for Mac keyboards."""

import subprocess
from pathlib import Path

from dailydriver.models import FnMode, MacKeyboardConfig


class HidAppleService:
    """Service for managing hid-apple kernel module configuration."""

    MODULE_NAME = "hid_apple"
    MODULE_PARAMS_PATH = Path("/sys/module/hid_apple/parameters")
    MODPROBE_CONF_PATH = Path("/etc/modprobe.d/hid_apple.conf")

    def __init__(self) -> None:
        self._cached_config: MacKeyboardConfig | None = None

    def is_module_loaded(self) -> bool:
        """Check if hid-apple module is currently loaded."""
        return self.MODULE_PARAMS_PATH.exists()

    def get_current_config(self) -> MacKeyboardConfig | None:
        """Read current hid-apple configuration from sysfs."""
        if not self.is_module_loaded():
            return None

        try:
            config = MacKeyboardConfig()

            # Read fnmode
            fnmode_file = self.MODULE_PARAMS_PATH / "fnmode"
            if fnmode_file.exists():
                fnmode_value = int(fnmode_file.read_text().strip())
                config.fn_mode = {
                    0: FnMode.DISABLED,
                    1: FnMode.FKEYS,
                    2: FnMode.MEDIA,
                }.get(fnmode_value, FnMode.MEDIA)

            # Read swap_opt_cmd
            swap_file = self.MODULE_PARAMS_PATH / "swap_opt_cmd"
            if swap_file.exists():
                config.swap_opt_cmd = swap_file.read_text().strip() == "Y"

            # Read swap_fn_leftctrl
            fn_ctrl_file = self.MODULE_PARAMS_PATH / "swap_fn_leftctrl"
            if fn_ctrl_file.exists():
                config.swap_fn_leftctrl = fn_ctrl_file.read_text().strip() == "Y"

            # Read iso_layout
            iso_file = self.MODULE_PARAMS_PATH / "iso_layout"
            if iso_file.exists():
                config.iso_layout = iso_file.read_text().strip() == "Y"

            self._cached_config = config
            return config

        except (OSError, ValueError):
            return None

    def apply_config(self, config: MacKeyboardConfig, persistent: bool = True) -> bool:
        """
        Apply hid-apple configuration.

        Args:
            config: The configuration to apply
            persistent: If True, also write to modprobe.d for persistence

        Returns:
            True if successful, False otherwise

        Note:
            This requires root privileges. Uses a single pkexec call to avoid
            multiple password prompts.
        """
        if not self.is_module_loaded():
            return False

        params = config.to_modprobe_options()

        # Build a shell script that does all writes in one go
        # This way we only prompt for sudo ONCE
        script_lines = ["#!/bin/sh", "set -e"]

        # Add sysfs writes
        for param, value in params.items():
            param_file = self.MODULE_PARAMS_PATH / param
            if param_file.exists():
                script_lines.append(f'echo {value} > "{param_file}"')

        # Add modprobe.d write for persistence
        if persistent:
            options_line = " ".join(f"{k}={v}" for k, v in params.items())
            content = f"options {self.MODULE_NAME} {options_line}"
            script_lines.append(f'echo "{content}" > "{self.MODPROBE_CONF_PATH}"')

        script = "\n".join(script_lines)

        # Execute with single pkexec call
        success = self._run_as_root(script)

        if success:
            self._cached_config = config

        return success

    def _run_as_root(self, script: str) -> bool:
        """Run a shell script as root with a single pkexec prompt."""
        try:
            result = subprocess.run(
                ["pkexec", "sh", "-c", script],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
