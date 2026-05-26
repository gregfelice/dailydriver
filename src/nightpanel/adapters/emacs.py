# SPDX-License-Identifier: GPL-3.0-or-later
"""Emacs adapter — renders nightpanel-theme.el and toggles it via emacsclient.

The theme file lives in ~/.emacs.d/themes/ (default `custom-theme-load-path`).
Apply writes a sentinel + tells any running daemons to load the theme; revert
removes the sentinel + tells daemons to disable it. `verify()` keys off the
sentinel (the only signal that survives across daemon restarts).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from ..palette import Palette
from ..renderers import emacs as _renderer
from .base import Adapter

_LOG = logging.getLogger(__name__)

_THEME_DIR  = Path.home() / ".emacs.d" / "themes"
_THEME_FILE = _THEME_DIR / "nightpanel-theme.el"
_SENTINEL   = Path.home() / ".config" / "nightpanel" / "emacs-active"
_NP_THEME   = "nightpanel"


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=5)


def _emacsclient(form: str) -> str | None:
    """Eval an elisp form in the running daemon; return stdout or None.
    Quiet failure if no daemon is running (the common case)."""
    try:
        r = _run(["emacsclient", "-e", form])
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


class EmacsAdapter(Adapter):
    name = "emacs"

    def installed(self) -> bool:
        return bool(shutil.which("emacs"))

    def snapshot(self) -> dict:
        # Capture the daemon's currently-enabled themes so revert can restore
        # them. If no daemon is running, snapshot is empty — revert will just
        # disable nightpanel and leave the rest alone.
        themes = _emacsclient("custom-enabled-themes")
        return {"enabled_themes": themes}

    def apply(self, palette: Palette) -> None:
        # 1. Write the theme file from the palette.
        try:
            _THEME_DIR.mkdir(parents=True, exist_ok=True)
            _THEME_FILE.write_text(_renderer.render(palette))
        except OSError as e:
            _LOG.warning("nightpanel: emacs theme write failed: %s", e)

        # 2. Drop the sentinel so verify() can answer even when no daemon runs.
        try:
            _SENTINEL.parent.mkdir(parents=True, exist_ok=True)
            _SENTINEL.touch()
        except OSError as e:
            _LOG.warning("nightpanel: emacs sentinel write failed: %s", e)

        # 3. Tell any live daemon to load the theme. The theme dir path is
        #    absolute (no tilde) so add-to-list works in every daemon context.
        theme_dir = str(_THEME_DIR).rstrip("/") + "/"
        _emacsclient(
            f'(progn (add-to-list (quote custom-theme-load-path) "{theme_dir}") '
            f'(load-theme (quote {_NP_THEME}) t))'
        )

    def revert(self, snapshot: dict) -> None:
        # 1. Remove sentinel first so verify("off") returns True immediately.
        try:
            _SENTINEL.unlink(missing_ok=True)
        except OSError as e:
            _LOG.warning("nightpanel: emacs sentinel remove failed: %s", e)

        # 2. Tell any live daemon to disable nightpanel. The user's other
        #    themes (captured in snapshot["enabled_themes"]) remain enabled
        #    since we never disabled them.
        _emacsclient(f"(disable-theme (quote {_NP_THEME}))")

    def verify(self, expected: Literal["on", "off"]) -> bool:
        on = _SENTINEL.exists()
        return on if expected == "on" else not on
