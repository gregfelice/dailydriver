# SPDX-License-Identifier: GPL-3.0-or-later
"""tmux adapter — sources a palette overlay over the user's base theme."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from ..palette import Palette
from ..renderers import tmux as _renderer
from .base import Adapter

_LOG = logging.getLogger(__name__)

_NP_OVERLAY = Path.home() / ".config" / "nightpanel" / "themes" / "tmux-nightpanel.conf"
_BASE_CONF  = Path.home() / ".tmux.conf"


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=5)


class TmuxAdapter(Adapter):
    name = "tmux"

    def installed(self) -> bool:
        return bool(shutil.which("tmux"))

    def snapshot(self) -> dict:
        # tmux source-file restores from base conf on revert; nothing to capture.
        return {}

    def apply(self, palette: Palette) -> None:
        try:
            _NP_OVERLAY.parent.mkdir(parents=True, exist_ok=True)
            _NP_OVERLAY.write_text(_renderer.render(palette))
        except OSError as e:
            _LOG.warning("nightpanel: tmux overlay write failed: %s", e)
        try:
            _run(["tmux", "source-file", str(_NP_OVERLAY)])
        except Exception as e:
            _LOG.debug("nightpanel: tmux apply skipped: %s", e)

    def revert(self, snapshot: dict) -> None:
        try:
            _run(["tmux", "source-file", str(_BASE_CONF)])
        except Exception as e:
            _LOG.debug("nightpanel: tmux revert skipped: %s", e)

    def verify(self, expected: Literal["on", "off"]) -> bool:
        # Probe a single distinctive style. Our overlay sets status-style with
        # bg=#000000 (pure black); base themes typically use a non-pure-black bg.
        try:
            r = _run(["tmux", "show", "-gv", "status-style"])
            value = r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return False
        on = "bg=#000000" in value.lower()
        return on if expected == "on" else not on
