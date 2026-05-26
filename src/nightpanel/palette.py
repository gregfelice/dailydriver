# SPDX-License-Identifier: GPL-3.0-or-later
"""Palette — the single source of truth for nightpanel colors.

Every adapter (alacritty, tmux, nvim, GTK, firefox extension, music player)
renders its config from a Palette instance instead of hardcoding hexes.
Changing a hue is a one-line edit here; the next apply() repaints every tool.

The default palette is the "saab instrument cluster" aesthetic — pure black
canvas, instrument-scale green text, amber needle accents, redline error.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    """A nightpanel color scheme. Every adapter consumes these slots."""

    name: str = "nightpanel"

    # ── Backgrounds (darkest → lightest) ─────────────────────────────
    bg: str         = "#0A0A0A"   # main canvas
    bg_card: str    = "#111111"   # cards, headerbars, message bg
    bg_header: str  = "#000000"   # tmux/nvim status bars — pure black
    bg_select: str  = "#1A3020"   # selection — dark green
    bg_accent: str  = "#0A5C35"   # deeper accent green

    # ── Greens (instrument cluster scale) ────────────────────────────
    fg: str         = "#7DB890"   # default text — instrument scale
    fg_bright: str  = "#26DE81"   # active / live reading / accent
    fg_dim: str     = "#2E5040"   # ghost ticks / disabled
    fg_mid: str     = "#5A8A6A"   # secondary text
    fg_light: str   = "#9EC8A8"   # type names / params

    # ── Ambers (the amber needle) ────────────────────────────────────
    fg_amber: str   = "#B08030"   # standard amber / odometer
    amber_warm: str = "#E8930A"   # warm needle — focused match

    # ── Status ───────────────────────────────────────────────────────
    red: str        = "#EF4444"   # turbo redline — error

    # ── Borders (quiet → strong) ─────────────────────────────────────
    border_q: str   = "#2A2A2A"   # quiet
    border_d: str   = "#383838"   # default
    border_s: str   = "#5A5A5A"   # strong


# The canonical nightpanel palette. Importers should use this unless they
# want to test a variant.
NIGHTPANEL = Palette()
