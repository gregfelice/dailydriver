# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the GTK 4 CSS overlay from a Palette."""

from __future__ import annotations

from ..palette import Palette


def render(p: Palette) -> str:
    return f"""\
/* nightpanel — uniform NP black canvas across every Adwaita surface.
   Headerbar, sidebar (Nautilus places/bookmarks), cards, popovers,
   dialogs — everything resolves to the same {p.bg}. Without these
   explicit overrides Adwaita computes lighter shades for some
   surfaces, producing the visible black-saturation mismatch the
   user reported between alacritty, Firefox, and Nautilus. */
@define-color window_bg_color {p.bg};
@define-color view_bg_color {p.bg};
@define-color headerbar_bg_color {p.bg};
@define-color headerbar_backdrop_color {p.bg};
@define-color card_bg_color {p.bg};
@define-color sidebar_bg_color {p.bg};
@define-color sidebar_backdrop_color {p.bg};
@define-color secondary_sidebar_bg_color {p.bg};
@define-color secondary_sidebar_backdrop_color {p.bg};
@define-color popover_bg_color {p.bg};
@define-color dialog_bg_color {p.bg};
@define-color thumbnail_bg_color {p.bg};

/* nightpanel — foreground / accent.
   Default text uses fg (#7DB890 instrument scale) for unified saturation
   across Nautilus / Firefox / Claude Code. Bright (#26DE81 fg_bright) is
   reserved for the accent_color (active items, focused state, links). */
@define-color window_fg_color {p.fg};
@define-color headerbar_fg_color {p.fg};
@define-color view_fg_color {p.fg};
@define-color card_fg_color {p.fg};
@define-color sidebar_fg_color {p.fg};
@define-color secondary_sidebar_fg_color {p.fg};
@define-color popover_fg_color {p.fg};
@define-color dialog_fg_color {p.fg};
@define-color accent_color {p.fg_bright};
@define-color accent_bg_color {p.bg_select};
@define-color accent_fg_color {p.fg_bright};

/* nightpanel — direct selector overrides catch surfaces some apps
   (Nautilus, file-chooser) style with class names instead of the
   Adwaita variable system. */
.navigation-sidebar,
.places-sidebar,
placessidebar,
filechooser sidebar,
sidebar list,
sidebar listview {{
    background-color: {p.bg};
}}

/* nightpanel — sharp corners + thin NP border everywhere.
   Industrial SAAB aesthetic: square windows, no Adwaita rounding.
   The 1px border_q grey separates the window from the canvas. */
window,
window.background,
.csd,
.csd > decoration,
.csd > decoration-overlay,
dialog,
popover > arrow,
popover > contents,
menu,
.menu {{
    border-radius: 0 !important;
    border: 1px solid {p.border_q};
}}

window > headerbar,
window > .titlebar,
headerbar {{
    border-radius: 0 !important;
    border-bottom: 1px solid {p.border_q};
}}

/* nightpanel — neutralize Adwaita's window drop-shadow ring so the
   thin border isn't doubled by a phantom highlight. */
window.csd {{
    box-shadow: none;
}}

/* nightpanel — desaturate file/folder icons in content areas only */
scrolledwindow image,
scrolledwindow picture {{
    -gtk-icon-filter: saturate(0) brightness(0.15);
    opacity: 0.35;
}}
"""
