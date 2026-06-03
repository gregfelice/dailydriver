# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the GNOME adapter's gsettings side effects.

Focus: nightpanel must NOT blow away the user's desktop wallpaper. It used to
clear ``picture-uri``/``picture-uri-dark`` and paint ``primary-color`` black on
every apply; that was removed. These tests pin the contract so it can't quietly
come back:

  - apply(): sets dark color-scheme + GTK CSS, but touches NO
    ``org.gnome.desktop.background`` key.
  - revert(): still restores the background from the snapshot, so anyone who
    toggled on under the old (wallpaper-blacking) build gets it back.

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


def test_apply_does_not_touch_the_wallpaper(palette, gsettings_calls):
    GnomeAdapter().apply(palette)
    bg_keys = [(s, k, v) for (s, k, v) in gsettings_calls if s == _BG_SCHEMA]
    assert bg_keys == [], f"apply() must not write any background key, got {bg_keys}"


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
