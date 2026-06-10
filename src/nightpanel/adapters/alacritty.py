# SPDX-License-Identifier: GPL-3.0-or-later
"""Alacritty adapter — flips the ``[general].import`` list in alacritty.toml.

Edits are done structurally with tomlkit (format/comment preserving) rather
than by regex. The regex approach only understood single-line
``import = ["…"]`` and silently corrupted the multi-line array form
(``import = [\\n  "…"\\n]``): the strip matched just the ``import = [`` line and
orphaned the array body, leaving invalid TOML that alacritty refused to load.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Literal

import tomlkit
from tomlkit.exceptions import TOMLKitError

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
        # list[str] | None — plain strings so it serializes into the JSON state.
        return {"import": self._read_import()}

    def apply(self, palette: Palette) -> None:
        # Regenerate the theme file from the palette on every apply so palette
        # changes propagate. Then point alacritty.toml's import at only it.
        try:
            _NP_THEME.parent.mkdir(parents=True, exist_ok=True)
            _NP_THEME.write_text(_renderer.render(palette))
        except OSError as e:
            _LOG.warning("nightpanel: alacritty theme write failed: %s", e)

        self._set_import([str(_NP_THEME)])

    def revert(self, snapshot: dict) -> None:
        prev = snapshot.get("import")
        # Legacy/unexpected shapes (e.g. a bare string from the old regex
        # adapter) can't be trusted as an import list — drop the import rather
        # than write it back malformed; the next apply re-snapshots cleanly.
        if prev is not None and not (
            isinstance(prev, list) and all(isinstance(p, str) for p in prev)
        ):
            prev = None
        self._set_import(prev)

    def verify(self, expected: Literal["on", "off"]) -> bool:
        imp = self._read_import() or []
        on = any("nightpanel" in p for p in imp)
        return on if expected == "on" else not on

    # ── helpers ──
    def _read_import(self) -> list[str] | None:
        doc = self._load()
        if doc is None:
            return None
        imp = doc.get("general", {}).get("import")
        if imp is None:
            return None
        return [str(x) for x in imp]

    def _load(self) -> tomlkit.TOMLDocument | None:
        if not _CFG.exists():
            return None
        try:
            return tomlkit.parse(_CFG.read_text())
        except (OSError, TOMLKitError) as e:
            _LOG.warning("nightpanel: alacritty.toml unreadable: %s", e)
            return None

    def _set_import(self, value: list[str] | None) -> None:
        """Set ``[general].import`` to ``value``, or remove it when ``None``."""
        try:
            doc = self._load()
            if doc is None:
                if value is None:
                    return
                doc = tomlkit.document()
            general = doc.get("general")
            if general is None:
                if value is None:
                    return
                general = tomlkit.table()
                doc["general"] = general
            if value is None:
                general.pop("import", None)
            else:
                general["import"] = value
            _CFG.write_text(tomlkit.dumps(doc))
        except (OSError, TOMLKitError) as e:
            _LOG.warning("nightpanel: alacritty apply failed: %s", e)
