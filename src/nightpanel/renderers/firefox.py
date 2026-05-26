# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the Firefox extension's selection CSS from a Palette.

The page-inversion filter logic lives in background.js; only the brand colors
(selection bg + fg) are rendered here. Splice into the extension at build time
or pass via the native messaging payload.
"""

from __future__ import annotations

from ..palette import Palette


def render_selection_css(p: Palette) -> str:
    return f"""::selection {{
    background-color: {p.bg_select} !important;
    color: {p.fg_bright} !important;
}}"""
