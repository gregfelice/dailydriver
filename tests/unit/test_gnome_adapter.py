# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the GNOME adapter's gsettings side effects.

Contract (configurable, default black — the Saab "pure black" design):

  - apply(): sets dark color-scheme + GTK CSS, and by DEFAULT blacks out the
    desktop (clears picture-uri + picture-uri-dark, paints primary-color the
    palette canvas, picture-options=none).
  - opt-out: a ``<config-dir>/keep-wallpaper`` sentinel makes apply() leave the
    background untouched (for users who don't want their wallpaper nuked).
  - revert(): always restores the background from the snapshot, so toggle-off
    puts the user's wallpaper back regardless of which mode applied.

The GTK-CSS file writes and the Nautilus bounce are out of scope here (covered
by the renderer tests / manual matrix), so they're stubbed.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from nightpanel.adapters.gnome import GnomeAdapter

_BG_SCHEMA = "org.gnome.desktop.background"


@pytest.fixture
def palette():
    from nightpanel.palette import Palette

    return Palette()


@pytest.fixture
def gsettings_calls():
    """Patch the adapter's gsettings + side-effect helpers; capture every
    ``_gsettings_set`` as a (schema, key, value) tuple."""
    calls: list[tuple[str, str, str]] = []
    with (
        patch(
            "nightpanel.adapters.gnome._gsettings_set",
            side_effect=lambda s, k, v: calls.append((s, k, v)),
        ),
        patch("nightpanel.adapters.gnome._bounce_nautilus"),
        patch.object(GnomeAdapter, "_apply_gtk_css"),
        patch.object(GnomeAdapter, "_revert_gtk_css"),
    ):
        yield calls


def test_apply_blacks_out_wallpaper_by_default(palette, gsettings_calls, tmp_path, monkeypatch):
    monkeypatch.setenv("NP_CONFIG_DIR", str(tmp_path))  # no keep-wallpaper sentinel
    GnomeAdapter().apply(palette)
    bg = {(k, v) for (s, k, v) in gsettings_calls if s == _BG_SCHEMA}
    assert ("picture-uri", "") in bg
    assert ("picture-uri-dark", "") in bg
    assert ("primary-color", palette.bg) in bg
    assert ("picture-options", "none") in bg


def test_apply_keeps_wallpaper_when_opted_out(palette, gsettings_calls, tmp_path, monkeypatch):
    monkeypatch.setenv("NP_CONFIG_DIR", str(tmp_path))
    (tmp_path / "keep-wallpaper").touch()
    GnomeAdapter().apply(palette)
    bg_keys = [(s, k, v) for (s, k, v) in gsettings_calls if s == _BG_SCHEMA]
    assert bg_keys == [], f"keep-wallpaper opt-out must leave the background alone, got {bg_keys}"


def test_apply_still_sets_dark_color_scheme(palette, gsettings_calls):
    GnomeAdapter().apply(palette)
    assert (
        "org.gnome.desktop.interface",
        "color-scheme",
        "prefer-dark",
    ) in gsettings_calls


def test_apply_invokes_gtk_css_and_nautilus_bounce(palette):
    with (
        patch("nightpanel.adapters.gnome._gsettings_set"),
        patch("nightpanel.adapters.gnome._bounce_nautilus") as bounce,
        patch.object(GnomeAdapter, "_apply_gtk_css") as gtk,
    ):
        GnomeAdapter().apply(palette)
    assert gtk.called and bounce.called


def test_revert_restores_wallpaper_from_snapshot(gsettings_calls):
    """The rescue path: a user toggled on under the old build has their real
    wallpaper in the snapshot; revert must put it back."""
    snapshot = {
        "color_scheme": "default",
        "bg_uri": "file:///home/u/Pictures/wall.jpg",
        "bg_uri_dark": "file:///home/u/Pictures/wall-dark.jpg",
        "bg_color": "#3465a4",
        "bg_options": "zoom",
    }
    GnomeAdapter().revert(snapshot)
    assert (_BG_SCHEMA, "picture-uri", snapshot["bg_uri"]) in gsettings_calls
    assert (_BG_SCHEMA, "picture-uri-dark", snapshot["bg_uri_dark"]) in gsettings_calls
    assert (_BG_SCHEMA, "primary-color", snapshot["bg_color"]) in gsettings_calls
    assert (_BG_SCHEMA, "picture-options", "zoom") in gsettings_calls
    assert ("org.gnome.desktop.interface", "color-scheme", "default") in gsettings_calls


def test_snapshot_still_captures_background_keys(gsettings_calls):
    """revert can only rescue if snapshot keeps recording the bg — guard that
    the keys weren't dropped along with the apply-time writes."""
    with patch(
        "nightpanel.adapters.gnome._gsettings_get",
        side_effect=lambda s, k: f"{s}/{k}",
    ):
        snap = GnomeAdapter().snapshot()
    for key in ("bg_uri", "bg_uri_dark", "bg_color", "bg_options"):
        assert key in snap
