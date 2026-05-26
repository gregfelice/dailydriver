# SPDX-License-Identifier: GPL-3.0-or-later
"""Alacritty adapter — flips the `import` line in alacritty.toml."""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Literal

from ..palette import Palette
from ..renderers import alacritty as _renderer
from .base import Adapter

_LOG = logging.getLogger(__name__)

_CFG = Path.home() / ".config" / "alacritty" / "alacritty.toml"
_NP_THEME = Path.home() / ".config" / "alacritty" / "themes" / "themes" / "nightpanel.toml"


class AlacrittyAdapter(Adapter):
    name = "alacritty"

    def installed(self) -> bool:
        return bool(shutil.which("alacritty")) or _CFG.exists()

    def snapshot(self) -> dict:
        return {"import": self._read_import()}

    def apply(self, palette: Palette) -> None:
        # Regenerate the theme file from the palette on every apply so palette
        # changes propagate. Then point alacritty.toml at it.
        try:
            _NP_THEME.parent.mkdir(parents=True, exist_ok=True)
            _NP_THEME.write_text(_renderer.render(palette))
        except OSError as e:
            _LOG.warning("nightpanel: alacritty theme write failed: %s", e)

        import_line = f'import = ["{_NP_THEME}"]'
        try:
            text = _CFG.read_text() if _CFG.exists() else ""
            text = re.sub(r"^[ \t]*import\s*=.*\n?", "", text, flags=re.MULTILINE)
            if re.search(r"^\[general\]", text, re.MULTILINE):
                text = re.sub(
                    r"^(\[general\][ \t]*)$", rf"\1\n{import_line}", text, flags=re.MULTILINE
                )
            else:
                text = f"[general]\n{import_line}\n\n" + text.lstrip()
            _CFG.write_text(text)
        except OSError as e:
            _LOG.warning("nightpanel: alacritty apply failed: %s", e)

    def revert(self, snapshot: dict) -> None:
        prev = snapshot.get("import")
        if not _CFG.exists():
            return
        try:
            text = _CFG.read_text()
            if prev and "[" in prev:
                text = re.sub(r"^[ \t]*import\s*=.*$", prev, text, flags=re.MULTILINE)
            else:
                text = re.sub(r"^[ \t]*import\s*=.*\n?", "", text, flags=re.MULTILINE)
            _CFG.write_text(text)
        except OSError as e:
            _LOG.warning("nightpanel: alacritty revert failed: %s", e)

    def verify(self, expected: Literal["on", "off"]) -> bool:
        imp = (self._read_import() or "").lower()
        on = "nightpanel" in imp
        return on if expected == "on" else not on

    # ── helpers ──
    def _read_import(self) -> str | None:
        if not _CFG.exists():
            return None
        text = _CFG.read_text()
        general = re.search(r"^\[general\][^\[]*", text, re.MULTILINE | re.DOTALL)
        if general:
            m = re.search(r"^[ \t]*(import\s*=\s*\[.+\])[ \t]*$", general.group(0), re.MULTILINE)
            if m:
                return m.group(1).strip()
        m = re.search(r"^(import\s*=\s*\[.+\])[ \t]*$", text, re.MULTILINE)
        return m.group(1) if m else None
