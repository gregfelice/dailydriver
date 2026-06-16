# SPDX-License-Identifier: GPL-3.0-or-later
"""theme_service — color math + CSS generation (the display-free core).

The ``ThemeService`` class itself drives a live Gdk display (StyleManager /
CssProvider) and so isn't exercised here; these tests lock the pure functions
that decide *what colors come out*: ``_scale_hex``, ``_build_theme_css``, and
the ``ACCENTS`` table. Brightness clamping is the highest-risk bit — it guards
against a slider value blowing past the legible range.
"""

from __future__ import annotations

import re

# theme_service imports Adw/Gtk at module load; in the app an entry point
# (application.py / __main__.py) calls require_version first. Mirror that here
# so importing the module in isolation doesn't emit a PyGIWarning.
import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from nightpanel.services.theme_service import (  # noqa: E402
    ACCENTS,
    DEFAULT_ACCENT,
    _build_theme_css,
    _scale_hex,
)

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


# ── _scale_hex ───────────────────────────────────────────────────────────


def test_scale_hex_identity_at_factor_one():
    assert _scale_hex("#26DE81", 1.0) == "#26DE81"


def test_scale_hex_accepts_hash_optional():
    assert _scale_hex("26DE81", 1.0) == "#26DE81"


def test_scale_hex_halves_channels():
    # 0x80 -> 64, 0x40 -> 32, 0x20 -> 16
    assert _scale_hex("#804020", 0.5) == "#402010"


def test_scale_hex_clamps_at_255():
    # Glow factor > 1.0 must not overflow a channel past 0xFF.
    assert _scale_hex("#FFFFFF", 1.5) == "#FFFFFF"


def test_scale_hex_always_valid_hex():
    for name, (color, *_rest) in ACCENTS.items():
        for factor in (0.3, 1.0, 1.5):
            assert _HEX.match(_scale_hex(color, factor)), (name, factor)


# ── ACCENTS table ────────────────────────────────────────────────────────


def test_default_accent_is_present():
    assert DEFAULT_ACCENT in ACCENTS


def test_every_accent_is_a_four_tuple_of_strings():
    for name, entry in ACCENTS.items():
        assert len(entry) == 4, name
        color, bg, fg, tagline = entry
        assert _HEX.match(color), name
        assert _HEX.match(bg), name
        assert _HEX.match(fg), name
        assert isinstance(tagline, str) and tagline


# ── _build_theme_css ─────────────────────────────────────────────────────


def test_css_has_pure_black_base():
    css = _build_theme_css(DEFAULT_ACCENT, 1.0)
    assert "@define-color headerbar_bg_color #000000;" in css
    assert "@define-color window_bg_color #0A0A0A;" in css


def test_css_uses_selected_accent_color():
    css = _build_theme_css("amber", 1.0)
    amber_hex = ACCENTS["amber"][0]
    assert f"@define-color accent_color {amber_hex};" in css


def test_unknown_accent_falls_back_to_default():
    fallback = _build_theme_css("not-a-real-accent", 1.0)
    default = _build_theme_css(DEFAULT_ACCENT, 1.0)
    assert fallback == default


def test_brightness_clamped_high():
    # 2.0 must behave identically to the 1.5 ceiling.
    assert _build_theme_css("amber", 2.0) == _build_theme_css("amber", 1.5)


def test_brightness_clamped_low():
    # 0.0 must behave identically to the 0.3 floor.
    assert _build_theme_css("amber", 0.0) == _build_theme_css("amber", 0.3)


def test_brightness_changes_foreground_scaling():
    dim = _build_theme_css("green", 0.5)
    bright = _build_theme_css("green", 1.5)
    assert dim != bright


def test_css_carries_tab_bar_styles():
    # The custom tab bar relies on these classes; regressions here silently
    # break the tab highlight that the Ctrl+Tab fix depends on.
    css = _build_theme_css(DEFAULT_ACCENT, 1.0)
    assert ".nightpanel-tab" in css
    assert ".nightpanel-tab:checked" in css
