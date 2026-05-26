# SPDX-License-Identifier: GPL-3.0-or-later
"""nvim adapter — sets g:colors_name via an after/plugin override.

Lives in ~/.config/nvim/after/plugin/nightpanel_active.lua. Created on apply,
removed on revert. Live nvim sessions (those exposing --server sockets) are
notified directly so they switch colorschemes immediately.
"""

from __future__ import annotations

import glob
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from ..palette import Palette
from .base import Adapter

_LOG = logging.getLogger(__name__)

_AFTER_PLUGIN = Path.home() / ".config" / "nvim" / "after" / "plugin" / "nightpanel_active.lua"
_DEFAULT_CS   = "tokyonight"
_NP_CS        = "nightpanel"


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=5)


class NvimAdapter(Adapter):
    name = "nvim"

    def installed(self) -> bool:
        return bool(shutil.which("nvim"))

    def snapshot(self) -> dict:
        return {"colorscheme": self._query_live_colorscheme() or _DEFAULT_CS}

    def apply(self, palette: Palette) -> None:
        try:
            _AFTER_PLUGIN.parent.mkdir(parents=True, exist_ok=True)
            _AFTER_PLUGIN.write_text(f"vim.cmd('colorscheme {_NP_CS}')\n")
        except OSError as e:
            _LOG.warning("nightpanel: nvim after/plugin write failed: %s", e)
        self._send_cmd(f"colorscheme {_NP_CS}")

    def revert(self, snapshot: dict) -> None:
        try:
            _AFTER_PLUGIN.unlink(missing_ok=True)
        except OSError as e:
            _LOG.warning("nightpanel: nvim after/plugin remove failed: %s", e)
        prev = snapshot.get("colorscheme", _DEFAULT_CS)
        self._send_cmd(f"colorscheme {prev}")

    def verify(self, expected: Literal["on", "off"]) -> bool:
        on = _AFTER_PLUGIN.exists()
        return on if expected == "on" else not on

    # ── helpers ──
    def _sockets(self) -> list[str]:
        patterns = [
            "/tmp/nvim*/0",
            "/run/user/*/nvim.*",
            str(Path.home() / ".local" / "state" / "nvim" / "*.sock"),
        ]
        out: list[str] = []
        for p in patterns:
            out.extend(glob.glob(p))
        return out

    def _query_live_colorscheme(self) -> str | None:
        for sock in self._sockets():
            try:
                r = _run(["nvim", "--server", sock, "--remote-expr", "g:colors_name"])
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip()
            except Exception:
                continue
        return None

    def _send_cmd(self, cmd: str) -> None:
        for sock in self._sockets():
            try:
                _run(["nvim", "--server", sock, "--remote-send",
                      f"<Esc>:silent! {cmd}<CR>"])
            except Exception:
                continue
