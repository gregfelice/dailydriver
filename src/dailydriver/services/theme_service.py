# SPDX-License-Identifier: GPL-3.0-or-later
"""Theme service — pure-black base with switchable mono accent."""

from __future__ import annotations

from gi.repository import Adw, Gdk, Gio, Gtk

# name → (accent_color, accent_bg_color, accent_fg_color, tagline)
# Colors sourced from Saab Night Panel reference photography.
ACCENTS: dict[str, tuple[str, str, str, str]] = {
    "green": ("#26DE81", "#0A5C35", "#000000", "saab instruments"),   # gauge face green
    "amber": ("#E8930A", "#6B3800", "#000000", "night needle"),        # needle / odometer
    "cyan":  ("#00C8D4", "#064E57", "#000000", "ice"),
    "red":   ("#EF4444", "#7F1D1D", "#FFFFFF", "warning"),
    "white": ("#E0E0E0", "#484848", "#000000", "bone"),
}

DEFAULT_ACCENT = "green"

_SWATCH_CSS = "\n".join(
    f".swatch-{name} {{ background-color: {color}; border-radius: 10px; min-width: 20px; min-height: 20px; }}"
    for name, (color, _, _, _) in ACCENTS.items()
)


def _scale_hex(hex_color: str, factor: float) -> str:
    """Scale RGB channels of a hex color by a brightness factor (supports >1.0 for glow)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = min(255, int(r * factor))
    g = min(255, int(g * factor))
    b = min(255, int(b * factor))
    return f"#{r:02X}{g:02X}{b:02X}"


def _build_theme_css(accent_name: str, brightness: float = 1.0) -> str:
    color_raw, bg_raw, fg, _ = ACCENTS.get(accent_name, ACCENTS[DEFAULT_ACCENT])

    # Clamp brightness to valid range
    b = max(0.3, min(1.5, brightness))

    # Scale foreground/accent palette only — backgrounds and borders stay pure black
    fg_primary   = _scale_hex("#7DB890", b)
    fg_secondary = _scale_hex("#B08030", b)
    fg_active    = _scale_hex("#26DE81", b)
    fg_dim       = _scale_hex("#2E5040", b)
    color        = _scale_hex(color_raw, b)
    accent_bg    = _scale_hex(bg_raw, b)

    return f"""
/* nightpanel — pure black base */
@define-color window_bg_color #0A0A0A;
@define-color card_bg_color #111111;
@define-color headerbar_bg_color #000000;
@define-color headerbar_border_color #1A1A1A;
@define-color sidebar_bg_color #050505;
@define-color popover_bg_color #1C1C1C;
@define-color dialog_bg_color #111111;

/* text — muted instrument green (NOT the accent); no white */
@define-color window_fg_color {fg_primary};
@define-color card_fg_color {fg_primary};
@define-color headerbar_fg_color {fg_primary};

/* text semantic roles */
@define-color text_primary {fg_primary};     /* instrument scale green — what things ARE */
@define-color text_secondary {fg_secondary};   /* amber — context, descriptions */
@define-color text_active {fg_active};      /* bright green — ON / confirmed */
@define-color text_dim {fg_dim};         /* very quiet — ghost labels */

/* neutral borders (grey, not accent) */
@define-color border_quiet #2A2A2A;
@define-color border_default #383838;
@define-color border_selected #5A5A5A;  /* selected state — grey, not accent */

/* accent (only for active toggles, checkmarks, confirmed states) */
@define-color accent_color {color};
@define-color accent_bg_color {accent_bg};
@define-color accent_fg_color {fg};

/* fonts — Inter regular throughout; no bold */
* {{ font-family: "Inter", "Cantarell", sans-serif; font-weight: 400; }}
.monospace, label.monospace, .shortcut-keys, code {{
  font-family: "JetBrains Mono", monospace;
  font-weight: 400;
}}

/* suppress all bold */
label.title, label.heading, label.title-1, label.title-2,
label.title-3, label.title-4, headerbar label, button label {{
  font-weight: 400;
}}

/* ── Base label color: instrument green for all unclassed labels ── */
label {{
  color: @text_primary;
}}

/* ── Row text: green primary titles, amber secondary ── */
row label.title {{ color: @text_primary; }}
row label.subtitle {{ color: @text_secondary; }}

/* ── Preferences group headings ── */
preferencesgroup > box > label.title {{
  color: @text_primary;
  letter-spacing: 2px;
  font-size: 0.70em;
}}
preferencesgroup > box > label.subtitle {{
  color: @text_secondary;
}}

/* ── Header bar title ── */
headerbar windowtitle .title,
headerbar .title {{
  color: @text_primary;
  letter-spacing: 3px;
  font-size: 0.78em;
}}

/* ── Controls: dark grey bg, visible against black ── */
switch {{
  background-color: #2E2E2E;
}}
switch:checked {{
  background-color: @accent_bg_color;
}}
switch slider {{
  background-color: #141414;
  border: 1px solid #484848;
}}
switch:checked slider {{
  background-color: #0A0A0A;
}}

/* combo row dropdown arrow area */
comborow button,
comborow > box > button {{
  background-color: #222222;
  border: 1px solid #383838;
  border-radius: 4px;
  color: @text_primary;
}}

/* ── Brightness slider ── */
scale trough {{
  background-color: #2A2A2A;
  border-radius: 4px;
  min-height: 4px;
}}
scale trough highlight {{
  background-color: @accent_color;
  border-radius: 4px;
}}
scale slider {{
  background-color: @text_primary;
  border-radius: 50%;
  min-width: 16px;
  min-height: 16px;
  border: none;
  box-shadow: none;
}}

/* ── Nav sidebar section labels ("categories", "settings") ── */
.sidebar-section-label {{
  color: @text_primary;
  font-size: 0.70em;
  letter-spacing: 2px;
}}

/* ── Nav sidebar listbox ── */
.navigation-sidebar {{
  background: transparent;
}}
.navigation-sidebar listboxrow {{
  background: transparent;
  border-radius: 6px;
  margin: 1px 4px;
  min-height: 32px;
}}
.navigation-sidebar listboxrow:hover {{
  background-color: alpha(@border_default, 0.25);
}}
.navigation-sidebar listboxrow:selected,
.navigation-sidebar listboxrow:selected:hover {{
  background-color: alpha(@border_selected, 0.12);
  border: 1px solid @border_quiet;
}}
.navigation-sidebar listboxrow label {{
  color: @text_primary;
}}
.navigation-sidebar listboxrow:selected label {{
  color: @text_primary;
}}
.navigation-sidebar listboxrow label.dim-label {{
  color: @text_dim;
}}
.navigation-sidebar .category-row label {{
  color: @text_primary;
}}

/* ── Config section (expanders, checkbuttons) ── */
expander-widget title {{
  color: @text_primary;
}}
expander-widget title label {{
  color: @text_primary;
}}
expander-widget title expander {{
  color: @text_primary;
}}
checkbutton label {{
  color: @text_primary;
}}

/* ── Symbolic icons: inherit instrument green ── */
image {{
  color: @text_primary;
}}
headerbar image,
headerbar button image {{
  color: @text_primary;
}}
.navigation-sidebar image,
.category-row image {{
  color: @text_primary;
}}
button.flat image {{
  color: @text_primary;
}}

/* ── Shortcut content rows (boxed-list inside shortcuts view) ── */
.boxed-list row label.title {{
  color: @text_primary;
}}
.boxed-list row label.subtitle {{
  color: @text_secondary;
}}

/* ── Shortcut content group/category headers ── */
label.title-2 {{
  color: @text_primary;
}}
label.title-3 {{
  color: @text_primary;
}}

/* ── Shortcut key badges ── */
shortcutlabel {{
  color: @text_primary;
}}
keycap {{
  background-color: #1A1A1A;
  border: 1px solid @border_default;
  color: @text_primary;
  font-family: "JetBrains Mono", monospace;
}}

/* ── Cheat sheet cards ── */
.card label.heading {{
  color: @text_primary;
}}
.card label.monospace {{
  color: @accent_color;
}}
.card label.dim-label {{
  color: @text_secondary;
}}
.card label.caption {{
  color: @text_dim;
  font-size: 0.72em;
  letter-spacing: 1px;
}}

/* ── General label classes ── */
label.dim-label {{
  color: @text_secondary;
}}
label.caption {{
  color: @text_secondary;
}}
label.heading {{
  color: @text_primary;
  font-weight: 400;
}}

/* ── Nightpanel toggle button ── */
.nightpanel-toggle:checked {{
  color: @accent_color;
}}

/* ── Custom tab bar — ALLCAPS, grey borders, NO accent color ── */
.nightpanel-tab {{
  border-radius: 6px;
  border: 1px solid @border_quiet;
  background: none;
  box-shadow: none;
  margin: 4px 3px;
  padding: 3px 12px;
  min-height: 0;
  font-size: 0.72em;
  font-weight: 400;
  letter-spacing: 2px;
  color: @text_dim;
}}
.nightpanel-tab:checked {{
  border-color: @border_selected;
  background-color: alpha(@border_selected, 0.08);
  color: @text_primary;
}}
.nightpanel-tab:hover:not(:checked) {{
  border-color: @border_default;
  color: alpha(@text_primary, 0.60);
}}

/* ── swatches ── */
{_SWATCH_CSS}
"""


class ThemeService:
    """Manages the app-level dark theme and switchable accent color."""

    def __init__(self) -> None:
        self._provider: Gtk.CssProvider | None = None
        self._accent: str = DEFAULT_ACCENT
        self._brightness: float = 1.0
        self._enabled: bool = True
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def brightness(self) -> float:
        return self._brightness

    def apply(self, accent_name: str, brightness: float = 1.0) -> None:
        """Apply (or re-apply) the nightpanel theme."""
        self._accent = accent_name
        self._brightness = brightness
        if not self._enabled:
            return
        display = Gdk.Display.get_default()
        if not display:
            return
        if self._provider:
            Gtk.StyleContext.remove_provider_for_display(display, self._provider)
        self._provider = Gtk.CssProvider()
        self._provider.load_from_string(_build_theme_css(accent_name, brightness))
        Gtk.StyleContext.add_provider_for_display(
            display,
            self._provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER,
        )

    def apply_from_settings(self, settings: Gio.Settings | None) -> None:
        accent = DEFAULT_ACCENT
        brightness = 1.0
        if settings:
            try:
                stored = settings.get_string("accent-color")
                if stored in ACCENTS:
                    accent = stored
            except Exception:
                pass
            try:
                brightness = settings.get_double("theme-brightness")
                brightness = max(0.3, min(1.5, brightness))
            except Exception:
                pass
            try:
                self._enabled = settings.get_boolean("nightpanel-enabled")
            except Exception:
                pass
        if not self._enabled:
            Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.DEFAULT)
            return
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        self.apply(accent, brightness)

    def save_and_apply(self, accent_name: str, settings: Gio.Settings | None) -> None:
        if settings:
            try:
                settings.set_string("accent-color", accent_name)
            except Exception:
                pass
        self.apply(accent_name, self._brightness)

    def set_brightness(self, brightness: float, settings: Gio.Settings | None = None) -> None:
        """Update the brightness and re-apply the theme."""
        if settings:
            try:
                settings.set_double("theme-brightness", brightness)
            except Exception:
                pass
        self.apply(self._accent, brightness)

    def set_enabled(self, enabled: bool, settings: Gio.Settings | None = None) -> None:
        """Enable or disable the nightpanel theme."""
        self._enabled = enabled
        if settings:
            try:
                settings.set_boolean("nightpanel-enabled", enabled)
            except Exception:
                pass
        if enabled:
            Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            self.apply(self._accent, self._brightness)
        else:
            display = Gdk.Display.get_default()
            if display and self._provider:
                Gtk.StyleContext.remove_provider_for_display(display, self._provider)
                self._provider = None
            Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.DEFAULT)
