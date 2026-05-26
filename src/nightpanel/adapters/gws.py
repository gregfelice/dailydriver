# SPDX-License-Identifier: GPL-3.0-or-later
"""gws (Getting Work Sorted) adapter — flips the theme in gws's state file.

gws is a Rust TUI GTD app (~/.local/bin/gws). Its theme selection is
persisted as a ``theme:<Name>`` line in the sibling ``.state`` file
(default ``~/.gws/todo.state``). gws ships with a ``Nightpanel`` theme
that mirrors this project's palette — the adapter writes
``theme:Nightpanel`` on apply, restores the previous theme on revert.

Caveats:
- gws reads its state file only on startup and writes it on exit.
  If gws is RUNNING when the adapter toggles, our write is silently
  clobbered by gws's exit-time save. Workaround: close gws before
  toggling, or relaunch gws after toggling.
- The adapter preserves the other lines (cat:/proj:/task: collapse
  markers) in the state file when rewriting.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Literal

from ..palette import Palette
from .base import Adapter

_LOG = logging.getLogger(__name__)

_STATE = Path.home() / ".gws" / "todo.state"
_NP_THEME = "Nightpanel"


def _parse(state_text: str) -> tuple[str | None, list[str]]:
    """Split state file content into (theme_value_or_None, other_lines)."""
    theme: str | None = None
    others: list[str] = []
    for line in state_text.splitlines():
        if line.startswith("theme:"):
            theme = line[len("theme:") :]
        else:
            others.append(line)
    return theme, others


def _serialize(theme: str | None, others: list[str]) -> str:
    lines: list[str] = []
    if theme:
        lines.append(f"theme:{theme}")
    lines.extend(others)
    content = "\n".join(lines)
    return content + "\n" if content else ""


class GwsAdapter(Adapter):
    name = "gws"

    def installed(self) -> bool:
        # Binary on PATH or the state dir exists (gws has been run at least once).
        return bool(shutil.which("gws")) or _STATE.parent.exists()

    def snapshot(self) -> dict:
        if not _STATE.exists():
            return {"theme": None, "existed": False}
        try:
            theme, _ = _parse(_STATE.read_text())
            return {"theme": theme, "existed": True}
        except OSError as e:
            _LOG.debug("nightpanel: gws snapshot read failed: %s", e)
            return {"theme": None, "existed": False}

    def apply(self, palette: Palette) -> None:
        self._set_theme(_NP_THEME)

    def revert(self, snapshot: dict) -> None:
        if not snapshot.get("existed", False):
            # State file didn't exist before us. If our theme line is now
            # the only content, drop the whole file; otherwise just strip
            # our line and leave the rest.
            self._set_theme(None, drop_if_empty=True)
            return
        self._set_theme(snapshot.get("theme"))

    def verify(self, expected: Literal["on", "off"]) -> bool:
        if not _STATE.exists():
            return expected == "off"
        try:
            theme, _ = _parse(_STATE.read_text())
        except OSError:
            return expected == "off"
        on = theme == _NP_THEME
        return on if expected == "on" else not on

    # ── helpers ──
    def _set_theme(self, theme: str | None, *, drop_if_empty: bool = False) -> None:
        try:
            _STATE.parent.mkdir(parents=True, exist_ok=True)
            existing = _STATE.read_text() if _STATE.exists() else ""
            _, others = _parse(existing)
            content = _serialize(theme, others)
            if drop_if_empty and not content.strip():
                _STATE.unlink(missing_ok=True)
                return
            _STATE.write_text(content)
        except OSError as e:
            _LOG.warning("nightpanel: gws state write failed: %s", e)
