# SPDX-License-Identifier: GPL-3.0-or-later
"""Emacs adapter — toggles the nightpanel theme via emacsclient.

The theme itself is no longer generated here. `nightpanel-theme.el` is a
standalone package (https://github.com/gregfelice/nightpanel-theme) and is
installed like any other theme, so package.el or the user's init owns
`custom-theme-load-path`. Rendering it from the palette as well produced two
copies that drifted apart, which is why that path was dropped.

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
from .base import Adapter

_LOG = logging.getLogger(__name__)

_SENTINEL = Path.home() / ".config" / "nightpanel" / "emacs-active"
_NP_THEME = "nightpanel"


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
        # `palette` is unused: the Adapter protocol passes it, but the theme is
        # an installed package now rather than something rendered from it.

        # 1. Drop the sentinel so verify() can answer even when no daemon runs.
        try:
            _SENTINEL.parent.mkdir(parents=True, exist_ok=True)
            _SENTINEL.touch()
        except OSError as e:
            _LOG.warning("nightpanel: emacs sentinel write failed: %s", e)

        # 2. Tell any live daemon to load the installed theme. Wrapped in
        #    condition-case so a machine without nightpanel-theme installed
        #    still toggles every other adapter instead of erroring out here.
        #    No daemon at all -> _emacsclient returns None -> stay quiet.
        loaded = _emacsclient(
            f"(condition-case nil (progn (load-theme (quote {_NP_THEME}) t) t) (error nil))"
        )
        if loaded is not None and loaded != "t":
            _LOG.warning(
                "nightpanel: theme not loaded — install nightpanel-theme "
                "(M-x package-install RET nightpanel-theme) or put it on "
                "custom-theme-load-path"
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
