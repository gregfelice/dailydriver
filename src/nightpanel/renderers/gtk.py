# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the GTK 4 CSS overlay from a Palette."""

from __future__ import annotations

from ..palette import Palette


def render(p: Palette) -> str:
    return f"""\
/* nightpanel — backgrounds (must be explicit or GNOME may compute light from fg) */
@define-color window_bg_color {p.bg};
@define-color headerbar_bg_color {p.bg_card};
@define-color view_bg_color {p.bg};
@define-color card_bg_color {p.bg_card};
@define-color sidebar_bg_color {p.bg};
/* nightpanel — foreground / accent */
@define-color window_fg_color {p.fg_bright};
@define-color headerbar_fg_color {p.fg_bright};
@define-color view_fg_color {p.fg_bright};
@define-color card_fg_color {p.fg_bright};
@define-color sidebar_fg_color {p.fg_bright};
@define-color accent_color {p.fg_bright};
@define-color accent_bg_color {p.bg_select};
@define-color accent_fg_color {p.fg_bright};
/* nightpanel — desaturate file/folder icons in content areas only */
scrolledwindow image,
scrolledwindow picture {{
    -gtk-icon-filter: saturate(0) brightness(0.15);
    opacity: 0.35;
}}
"""
