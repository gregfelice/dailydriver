# SPDX-License-Identifier: GPL-3.0-or-later
"""GNOME adapter — gsettings color-scheme + background + GTK CSS overlay.

GTK4 reads ``~/.config/gtk-4.0/gtk.css`` exactly once per display in
``settings_init_style()`` (gtk/gtksettings.c). The static ``GtkCssProvider``
it allocates is never reloaded — there is no GFileMonitor on the file and
no documented out-of-process hook (DBus, signal, XSettings) to ask a
running GTK4 app to re-parse it.

libadwaita's color-scheme change channel (XDG portal
``org.freedesktop.portal.Settings`` → ``org.freedesktop.appearance``
``color-scheme``) re-renders the *already-parsed* CSS through media
queries, so gsettings dark-mode toggles propagate live — but the on-disk
gtk.css is not re-read. That's why a long-running Nautilus shows
"standard Adwaita dark" after toggling NP on but doesn't pick up the NP
overrides written between its startup and the toggle.

The only reliable recipe is to bounce the running GTK4 app. We do this
for Nautilus specifically (``gapplication action org.gnome.Nautilus
kill`` → ``g_application_quit()``) on both apply and revert. Other
GTK4 apps started before nightpanel applies will keep stale CSS until
the user restarts them — documented caveat.

Refs:
  https://gitlab.gnome.org/GNOME/gtk/-/raw/main/gtk/gtksettings.c
  https://gitlab.gnome.org/GNOME/libadwaita/-/raw/main/src/adw-style-manager.c
  https://gitlab.gnome.org/GNOME/nautilus/-/raw/main/src/nautilus-application.c
"""

from __future__ import annotations

import logging
import os
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


def _keep_wallpaper() -> bool:
    """Opt-out flag: if ``<config-dir>/keep-wallpaper`` exists, apply() leaves
    the desktop background alone instead of blacking it out. Default (no file)
    is to black out, per the design. NP_CONFIG_DIR-aware so it tracks the same
    config dir the toggle uses."""
    cfg = os.environ.get("NP_CONFIG_DIR") or str(Path.home() / ".config" / "nightpanel")
    return (Path(cfg) / "keep-wallpaper").exists()


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


def _bounce_nautilus() -> None:
    """Force a running Nautilus to re-read gtk.css by quitting it.

    GTK4 only re-parses ``~/.config/gtk-4.0/gtk.css`` at app startup; see
    module docstring. ``gapplication action org.gnome.Nautilus kill``
    routes to ``g_application_quit()`` and is the supported clean exit
    (same as ``nautilus --quit``). Non-zero exit is normal when Nautilus
    isn't registered on the bus — no instance to bounce, nothing to do.
    """
    try:
        _run(["gapplication", "action", "org.gnome.Nautilus", "kill"])
    except Exception as e:
        _LOG.debug("nightpanel: nautilus bounce skipped: %s", e)


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
            "bg_color2": _gsettings_get("org.gnome.desktop.background", "secondary-color"),
            "bg_shading": _gsettings_get("org.gnome.desktop.background", "color-shading-type"),
            "bg_options": _gsettings_get("org.gnome.desktop.background", "picture-options"),
            "gtk4_css": _GTK4_CSS.read_text() if _GTK4_CSS.exists() else None,
            "gtk3_css": _GTK3_CSS.read_text() if _GTK3_CSS.exists() else None,
        }

    def apply(self, palette: Palette) -> None:
        _gsettings_set("org.gnome.desktop.interface", "color-scheme", "prefer-dark")
        # Black out the desktop to the palette canvas by DEFAULT — the design is a
        # pure black background (Saab night-panel aesthetic). Opt out by creating
        # <config-dir>/keep-wallpaper (see _keep_wallpaper). Clear BOTH picture-uri
        # and picture-uri-dark (dark mode reads the -dark key, so clearing only
        # picture-uri leaves the wallpaper up) and set picture-options=none so the
        # solid primary-color shows. Also force color-shading-type=solid: if the
        # user's pre-existing shading is horizontal/vertical, GNOME paints a
        # gradient from primary-color to secondary-color (observed as a black→blue
        # gradient), NOT a solid fill — so pin both shading and secondary to the
        # canvas. snapshot()/revert() restore the user's wallpaper + shading on
        # toggle-off regardless.
        if not _keep_wallpaper():
            _gsettings_set("org.gnome.desktop.background", "picture-uri", "")
            _gsettings_set("org.gnome.desktop.background", "picture-uri-dark", "")
            _gsettings_set("org.gnome.desktop.background", "primary-color", palette.bg)
            _gsettings_set("org.gnome.desktop.background", "secondary-color", palette.bg)
            _gsettings_set("org.gnome.desktop.background", "color-shading-type", "solid")
            _gsettings_set("org.gnome.desktop.background", "picture-options", "none")
        self._apply_gtk_css(palette)
        _bounce_nautilus()

    def revert(self, snapshot: dict) -> None:
        # Restore CSS before color-scheme so GTK reloads with the right file in one pass.
        self._revert_gtk_css(snapshot)
        _bounce_nautilus()
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
        if snapshot.get("bg_color2"):
            _gsettings_set("org.gnome.desktop.background", "secondary-color", snapshot["bg_color2"])
        if snapshot.get("bg_shading"):
            _gsettings_set(
                "org.gnome.desktop.background", "color-shading-type", snapshot["bg_shading"]
            )
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
