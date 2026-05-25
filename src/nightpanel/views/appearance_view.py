# SPDX-License-Identifier: GPL-3.0-or-later
"""Appearance panel — pure-black base with switchable mono accent color."""

from __future__ import annotations

from collections.abc import Callable

from gi.repository import Adw, Gtk

from nightpanel.services.theme_service import ACCENTS, DEFAULT_ACCENT, ThemeService


class AppearanceView(Adw.PreferencesPage):
    """Panel for choosing the accent color."""

    __gtype_name__ = "AppearanceView"

    def __init__(
        self,
        theme_service: ThemeService,
        app_settings,
        on_toast: Callable[[str, str | None, Callable | None], None],
    ) -> None:
        super().__init__()
        self._theme = theme_service
        self._settings = app_settings
        self._on_toast = on_toast
        self._rows: dict[str, Adw.ActionRow] = {}
        self._checks: dict[str, Gtk.Image] = {}
        self._build_ui()

    def _current_accent(self) -> str:
        if self._settings:
            try:
                v = self._settings.get_string("accent-color")
                if v in ACCENTS:
                    return v
            except Exception:
                pass
        return DEFAULT_ACCENT

    def _build_ui(self) -> None:
        accent_group = Adw.PreferencesGroup()
        accent_group.set_title("accent color")
        accent_group.set_description(
            "all-black canvas. one color — everything else fades."
        )
        self.add(accent_group)

        current = self._current_accent()
        for name in ACCENTS:
            row = self._make_row(name, is_active=(name == current))
            self._rows[name] = row
            accent_group.add(row)

    def _make_row(self, name: str, *, is_active: bool) -> Adw.ActionRow:
        color_hex, _, _, tagline = ACCENTS[name]

        row = Adw.ActionRow()
        row.set_title(name)
        row.set_subtitle(tagline)
        row.set_activatable(True)

        # Colored swatch
        swatch = Gtk.Box()
        swatch.add_css_class(f"swatch-{name}")
        swatch.set_valign(Gtk.Align.CENTER)
        row.add_prefix(swatch)

        # Hex label
        hex_label = Gtk.Label(label=color_hex)
        hex_label.add_css_class("monospace")
        hex_label.add_css_class("dim-label")
        hex_label.add_css_class("caption")
        hex_label.set_valign(Gtk.Align.CENTER)
        row.add_suffix(hex_label)

        # Active checkmark
        check = Gtk.Image.new_from_icon_name("object-select-symbolic")
        check.set_valign(Gtk.Align.CENTER)
        check.set_visible(is_active)
        row.add_suffix(check)
        self._checks[name] = check

        row.connect("activated", self._on_activated, name)
        return row

    def _on_activated(self, _row, name: str) -> None:
        for n, check in self._checks.items():
            check.set_visible(n == name)
        self._theme.save_and_apply(name, self._settings)
        _, _, _, tagline = ACCENTS[name]
        self._on_toast(f"accent: {name} — {tagline}", None, None)
