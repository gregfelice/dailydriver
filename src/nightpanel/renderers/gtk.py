# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the GTK 4 CSS overlay from a Palette.

The output is wrapped in paired sentinel comments
(``/* nightpanel:start */`` / ``/* nightpanel:end */``) so revert can
locate and strip the block deterministically even if the rules between
them change. Anything outside the sentinels is user content and must
survive both apply and revert untouched.
"""

from __future__ import annotations

from ..palette import Palette

START_SENTINEL = "/* nightpanel:start — do not edit between sentinels; this block is regenerated on every apply() */"
END_SENTINEL = "/* nightpanel:end */"


def render(p: Palette) -> str:
    return f"""\
{START_SENTINEL}
/* Uniform NP black canvas across every Adwaita surface.
   Headerbar, sidebar, cards, popovers, dialogs — everything resolves
   to {p.bg}. Without these explicit overrides Adwaita computes lighter
   shades for some surfaces, producing visible saturation mismatch
   between alacritty, Firefox, and Nautilus. */
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

/* Foreground / accent. Default text uses fg ({p.fg}) for unified
   saturation across Nautilus / Firefox / Claude Code. Bright
   ({p.fg_bright}) is reserved for accent_color (active items, focus, links). */
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

/* Direct selector overrides for apps (Nautilus, file-chooser) that
   style sidebar surfaces via class names instead of Adwaita variables. */
.navigation-sidebar,
.places-sidebar,
placessidebar,
filechooser sidebar,
sidebar list,
sidebar listview {{
    background-color: {p.bg};
}}

/* Sharp corners + thin NP border everywhere. Industrial SAAB
   aesthetic: square windows, no Adwaita rounding. 1px border_q grey
   separates window from canvas. Length unit explicit (0px not 0) so
   Firefox's CSS parser doesn't emit "junk at end of value" warnings
   when it loads gtk.css for legacy system theming. */
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
    border-radius: 0;
    border: 1px solid {p.border_q};
}}

window > headerbar,
window > .titlebar,
headerbar {{
    border-radius: 0;
    border-bottom: 1px solid {p.border_q};
}}

/* Neutralize Adwaita's window drop-shadow ring so the thin border
   isn't doubled by a phantom highlight. */
window.csd {{
    box-shadow: none;
}}

/* Desaturate file/folder icons in content areas only. Standard CSS
   `filter:` rather than the GTK3-only `-gtk-icon-filter:` so Firefox
   stops emitting "not a valid property name" warnings. */
scrolledwindow image,
scrolledwindow picture {{
    filter: saturate(0) brightness(0.15);
    opacity: 0.35;
}}
{END_SENTINEL}
"""
