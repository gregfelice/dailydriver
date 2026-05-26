# SPDX-License-Identifier: GPL-3.0-or-later
"""Firefox adapter — writes a command JSON the native-messaging host polls."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Literal

from ..palette import Palette
from .base import Adapter

_LOG = logging.getLogger(__name__)

_COMMAND_FILE = Path.home() / ".config" / "nightpanel" / "np-command.json"


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=5)


def _read_brightness() -> float:
    """Read brightness from gsettings; clamp to a sane range."""
    try:
        r = _run(["gsettings", "get", "io.github.gregfelice.Nightpanel", "theme-brightness"])
        if r.returncode == 0:
            return max(0.3, min(1.5, float(r.stdout.strip())))
    except Exception:
        pass
    return 0.9


class FirefoxAdapter(Adapter):
    name = "firefox"

    def installed(self) -> bool:
        # The extension may be installed even when firefox isn't running, and
        # the command file is harmless if nothing reads it. Always engage.
        return True

    def snapshot(self) -> dict:
        # The extension reverts via the next command; nothing to capture here.
        return {}

    def apply(self, palette: Palette) -> None:
        self._write({"action": "apply", "brightness": _read_brightness()})

    def revert(self, snapshot: dict) -> None:
        self._write({"action": "revert", "brightness": 0.9})

    def verify(self, expected: Literal["on", "off"]) -> bool:
        try:
            cmd = json.loads(_COMMAND_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            return expected == "off"
        on = cmd.get("action") == "apply"
        return on if expected == "on" else not on

    # ── helpers ──
    def _write(self, payload: dict) -> None:
        try:
            _COMMAND_FILE.parent.mkdir(parents=True, exist_ok=True)
            _COMMAND_FILE.write_text(json.dumps(payload))
        except OSError as e:
            _LOG.warning("nightpanel: firefox command write failed: %s", e)
