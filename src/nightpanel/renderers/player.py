# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the music player's CSS overlays from a Palette.

Two CSS blocks: PLAYER_CSS (always loaded, always green title/controls)
and NP_CSS (loaded only when nightpanel is active — green title + amber artist).
"""

from __future__ import annotations

from ..palette import Palette


def render_player_css(p: Palette) -> str:
    return f""".np-header-title {{
    font-family: 'Inter', sans-serif;
    font-weight: 300;
    letter-spacing: 3px;
    font-size: 11pt;
    color: {p.fg_bright};
}}
.np-control {{ color: {p.fg_bright}; }}
"""


def render_np_css(p: Palette) -> str:
    return f""".np-title  {{ color: {p.fg_bright}; }}
.np-artist {{ color: {p.fg_amber}; }}
"""
