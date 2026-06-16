# SPDX-License-Identifier: GPL-3.0-or-later
"""Render gate for the 'sliders don't show on first render' report.

Builds the *real* ``SetupView`` (with stub services) inside the same
``ToastOverlay → ToolbarView → Gtk.Stack`` structure the main window uses,
presents it, and asserts both brightness scales are mapped, visible, and
allocated a non-zero size on the first frame — and that ``_load_state`` (which
runs via ``GLib.idle_add`` after first paint) has populated their values.

Observation that motivated this test: the sliders render correctly first-frame
in isolation, so any "missing slider" symptom lives in the live window/CSS
path, not the view. This locks the view-layer behavior so a real regression
there can't hide behind that ambiguity.

Display-gated: skipped in headless CI (no DISPLAY/WAYLAND_DISPLAY); runs on a
dev box with a live session.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.skipif(
    not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")),
    reason="needs a live display to map widgets",
)

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402


class _StubSettings:
    """Minimal Gio.Settings stand-in returning real (typed) values."""

    def __init__(self):
        self._d = {
            "current-preset": "hyprland-style",
            "theme-brightness": 1.2,
            "video-brightness": 0.6,
            "accent-color": "green",
            "tiling-enabled": True,
        }

    def get_string(self, k):
        return self._d.get(k, "")

    def get_double(self, k):
        return self._d.get(k, 1.0)

    def get_boolean(self, k):
        return bool(self._d.get(k, True))

    def set_string(self, k, v):
        self._d[k] = v

    def set_double(self, k, v):
        self._d[k] = v

    def set_boolean(self, k, v):
        self._d[k] = v


def _build_setup():
    from nightpanel.views.setup_view import SetupView

    tiling = MagicMock()
    tiling.get_ta_settings.return_value = {}
    return SetupView(
        gsettings_service=MagicMock(),
        profile_service=MagicMock(),
        kbd_config=MagicMock(),
        tiling_service=tiling,
        app_settings=_StubSettings(),
        on_toast=lambda *a, **k: None,
        on_shortcuts_reload=lambda *a, **k: None,
        theme_service=MagicMock(),
        on_brightness_update=lambda *a, **k: None,
        on_video_brightness_update=lambda *a, **k: None,
    )


def test_setup_sliders_render_on_first_frame():
    Adw.init()
    setup = _build_setup()

    win = Adw.ApplicationWindow()
    win.set_default_size(900, 650)
    overlay = Adw.ToastOverlay()
    win.set_content(overlay)
    toolbar = Adw.ToolbarView()
    overlay.set_child(toolbar)
    toolbar.add_top_bar(Adw.HeaderBar())
    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.NONE)
    toolbar.set_content(stack)
    stack.add_named(setup, "setup")
    stack.add_named(Gtk.Box(), "other")
    stack.set_visible_child_name("setup")
    win.present()

    loop = GLib.MainLoop()
    seen: dict[str, tuple] = {}

    def capture():
        for key, scale in (
            ("brightness", setup._brightness_scale),
            ("video", setup._video_brightness_scale),
        ):
            alloc = scale.get_allocation()
            seen[key] = (
                scale.get_mapped(),
                scale.get_visible(),
                alloc.width,
                alloc.height,
                scale.get_value(),
            )
        win.close()
        loop.quit()
        return False

    GLib.timeout_add(120, capture)
    GLib.timeout_add(5000, lambda: (loop.quit(), False)[1])  # safety: never hang
    loop.run()

    assert seen, "capture tick never ran — window failed to map"
    for key in ("brightness", "video"):
        mapped, visible, width, height, value = seen[key]
        assert mapped, f"{key} slider not mapped on first frame"
        assert visible, f"{key} slider not visible on first frame"
        assert width > 0 and height > 0, f"{key} slider has zero allocation: {width}x{height}"

    # _load_state ran and populated the values from settings (1.2 / 0.6).
    assert seen["brightness"][4] == pytest.approx(1.2, abs=0.05)
    assert seen["video"][4] == pytest.approx(0.6, abs=0.05)
