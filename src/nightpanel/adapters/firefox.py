# SPDX-License-Identifier: GPL-3.0-or-later
"""Firefox adapter — writes the command JSON the native host polls, plus
manages userChrome.css (the chrome styling absorbed from the old slimfox
project)."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Literal

from ..palette import Palette
from ..renderers import firefox_chrome as _chrome_renderer
from .base import Adapter

_LOG = logging.getLogger(__name__)

_COMMAND_FILE   = Path.home() / ".config" / "nightpanel" / "np-command.json"
_FF_PROFILE     = Path.home() / ".mozilla" / "firefox" / "x7sc2l5o.default-esr"
_USER_CHROME    = _FF_PROFILE / "chrome" / "userChrome.css"
_USER_JS        = _FF_PROFILE / "user.js"
_CHROME_PREF    = "toolkit.legacyUserProfileCustomizations.stylesheets"


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
        # Re-sync userChrome.css from the palette on every apply so palette
        # edits propagate. Firefox requires a full restart to pick the change
        # up (it doesn't hot-reload chrome.css), but the file is correct at
        # rest. Idempotent.
        self._install_user_chrome(palette)

    def revert(self, snapshot: dict) -> None:
        self._write({"action": "revert", "brightness": 0.9})
        # Leave userChrome.css in place — it's not a per-toggle concern. To
        # fully revert chrome styling, the user removes the file manually or
        # runs the slimfox uninstall script (which still works for now).

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

    def _install_user_chrome(self, palette: Palette) -> None:
        """Write userChrome.css from the palette and ensure the FF pref that
        lets userChrome load is set. Replaces the old slimfox installer."""
        if not _FF_PROFILE.exists():
            return
        try:
            _USER_CHROME.parent.mkdir(parents=True, exist_ok=True)
            _USER_CHROME.write_text(_chrome_renderer.render(palette))
        except OSError as e:
            _LOG.warning("nightpanel: userChrome.css write failed: %s", e)
            return
        # Ensure the pref that lets userChrome.css be loaded.
        try:
            existing = _USER_JS.read_text() if _USER_JS.exists() else ""
            if f'user_pref("{_CHROME_PREF}"' not in existing:
                with _USER_JS.open("a") as f:
                    f.write(f'\nuser_pref("{_CHROME_PREF}", true);\n')
        except OSError as e:
            _LOG.warning("nightpanel: user.js update failed: %s", e)
