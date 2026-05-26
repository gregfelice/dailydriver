# SPDX-License-Identifier: GPL-3.0-or-later
"""GNOME adapter — gsettings color-scheme + background + GTK CSS overlay."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from ..palette import Palette
from ..renderers import gtk as _renderer
from ..renderers.gtk import END_SENTINEL, START_SENTINEL
from .base import Adapter

_LOG = logging.getLogger(__name__)

_GTK4_CSS = Path.home() / ".config" / "gtk-4.0" / "gtk.css"
_GTK3_CSS = Path.home() / ".config" / "gtk-3.0" / "gtk.css"


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=5)


def _gsettings_get(schema: str, key: str) -> str | None:
    try:
        r = _run(["gsettings", "get", schema, key])
        return r.stdout.strip().strip("'") if r.returncode == 0 else None
    except Exception:
        return None


def _gsettings_set(schema: str, key: str, value: str) -> None:
    try:
        _run(["gsettings", "set", schema, key, value])
    except Exception as e:
        _LOG.debug("nightpanel: gsettings %s %s failed: %s", schema, key, e)


class GnomeAdapter(Adapter):
    name = "gnome"

    def installed(self) -> bool:
        return bool(shutil.which("gsettings"))

    def snapshot(self) -> dict:
        return {
            "color_scheme": _gsettings_get("org.gnome.desktop.interface", "color-scheme"),
            "bg_uri": _gsettings_get("org.gnome.desktop.background", "picture-uri"),
            "bg_uri_dark": _gsettings_get("org.gnome.desktop.background", "picture-uri-dark"),
            "bg_color": _gsettings_get("org.gnome.desktop.background", "primary-color"),
            "bg_options": _gsettings_get("org.gnome.desktop.background", "picture-options"),
            "gtk4_css": _GTK4_CSS.read_text() if _GTK4_CSS.exists() else None,
            "gtk3_css": _GTK3_CSS.read_text() if _GTK3_CSS.exists() else None,
        }

    def apply(self, palette: Palette) -> None:
        _gsettings_set("org.gnome.desktop.interface", "color-scheme", "prefer-dark")
        _gsettings_set("org.gnome.desktop.background", "picture-options", "none")
        _gsettings_set("org.gnome.desktop.background", "primary-color", palette.bg)
        _gsettings_set("org.gnome.desktop.background", "picture-uri", "")
        _gsettings_set("org.gnome.desktop.background", "picture-uri-dark", "")
        self._apply_gtk_css(palette)

    def revert(self, snapshot: dict) -> None:
        # Restore CSS before color-scheme so GTK reloads with the right file in one pass.
        self._revert_gtk_css(snapshot)
        cs = snapshot.get("color_scheme", "default")
        if cs:
            _gsettings_set("org.gnome.desktop.interface", "color-scheme", cs)
        if snapshot.get("bg_uri"):
            _gsettings_set("org.gnome.desktop.background", "picture-uri", snapshot["bg_uri"])
        if snapshot.get("bg_uri_dark"):
            _gsettings_set(
                "org.gnome.desktop.background", "picture-uri-dark", snapshot["bg_uri_dark"]
            )
        if snapshot.get("bg_color"):
            _gsettings_set("org.gnome.desktop.background", "primary-color", snapshot["bg_color"])
        _gsettings_set(
            "org.gnome.desktop.background", "picture-options", snapshot.get("bg_options") or "zoom"
        )

    def verify(self, expected: Literal["on", "off"]) -> bool:
        cs = _gsettings_get("org.gnome.desktop.interface", "color-scheme") or ""
        gtk = _GTK4_CSS.read_text() if _GTK4_CSS.exists() else ""
        on = cs == "prefer-dark" and START_SENTINEL in gtk
        return on if expected == "on" else not on

    # ── helpers ──
    def _apply_gtk_css(self, palette: Palette) -> None:
        """Render the NP CSS from the palette and prepend it to gtk.css.

        Strips any prior NP-sentinel-wrapped block first so palette edits
        propagate on re-apply (without the strip, the file would only ever
        contain the very first apply's CSS).
        """
        css = _renderer.render(palette)
        for path in (_GTK4_CSS, _GTK3_CSS):
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                existing = path.read_text() if path.exists() else ""
                existing = self._strip_np_block(existing)
                path.write_text(css + existing)
            except OSError as e:
                _LOG.warning("nightpanel: gtk css apply (%s) failed: %s", path, e)

    @staticmethod
    def _strip_np_block(text: str) -> str:
        """Remove every NP block between paired sentinels (inclusive).

        Robust to multiple blocks (defensive — shouldn't happen, but if it
        ever did during an interrupted apply, we want re-apply to be idempotent).
        Idempotent: returns ``text`` unchanged when no sentinels are present.
        """
        out = text
        while True:
            start = out.find(START_SENTINEL)
            end = out.find(END_SENTINEL, start)
            if start < 0 or end < 0:
                break
            cut_end = end + len(END_SENTINEL)
            if cut_end < len(out) and out[cut_end] == "\n":
                cut_end += 1
            out = out[:start] + out[cut_end:]
        return out

    def _revert_gtk_css(self, snapshot: dict) -> None:
        for path, key in ((_GTK4_CSS, "gtk4_css"), (_GTK3_CSS, "gtk3_css")):
            prev = snapshot.get(key)
            try:
                if prev is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_text(prev)
            except OSError as e:
                _LOG.warning("nightpanel: gtk css revert (%s) failed: %s", path, e)
