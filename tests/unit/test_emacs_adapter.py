# SPDX-License-Identifier: GPL-3.0-or-later
"""EmacsAdapter — theme file + sentinel + emacsclient round-trip.

apply() writes ``nightpanel-theme.el``, drops a sentinel (the only signal
that survives across daemon restarts), and tells any live daemon to load the
theme. revert() removes the sentinel and disables the theme. verify() keys
purely off the sentinel.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nightpanel.adapters import emacs as emacs_mod
from nightpanel.adapters.emacs import EmacsAdapter
from nightpanel.palette import NIGHTPANEL


@pytest.fixture
def env(tmp_path, monkeypatch):
    theme_dir = tmp_path / "emacs.d" / "themes"
    theme_file = theme_dir / "nightpanel-theme.el"
    sentinel = tmp_path / "config" / "emacs-active"
    monkeypatch.setattr(emacs_mod, "_THEME_DIR", theme_dir)
    monkeypatch.setattr(emacs_mod, "_THEME_FILE", theme_file)
    monkeypatch.setattr(emacs_mod, "_SENTINEL", sentinel)

    forms: list[str] = []

    def fake_client(form: str):
        forms.append(form)
        return "(doom-one)" if form == "custom-enabled-themes" else ""

    monkeypatch.setattr(emacs_mod, "_emacsclient", fake_client)
    return SimpleNamespace(theme_file=theme_file, sentinel=sentinel, forms=forms)


def test_installed_follows_which(monkeypatch):
    monkeypatch.setattr(emacs_mod.shutil, "which", lambda _: "/usr/bin/emacs")
    assert EmacsAdapter().installed() is True
    monkeypatch.setattr(emacs_mod.shutil, "which", lambda _: None)
    assert EmacsAdapter().installed() is False


def test_apply_writes_theme_sentinel_and_loads(env):
    EmacsAdapter().apply(NIGHTPANEL)

    assert env.theme_file.exists()
    assert "deftheme nightpanel" in env.theme_file.read_text()
    assert env.sentinel.exists()
    # A daemon was asked to load the theme.
    assert any("load-theme (quote nightpanel)" in f for f in env.forms)


def test_verify_tracks_sentinel(env):
    adapter = EmacsAdapter()
    assert adapter.verify("off") is True  # no sentinel yet
    adapter.apply(NIGHTPANEL)
    assert adapter.verify("on") is True
    assert adapter.verify("off") is False


def test_snapshot_captures_enabled_themes(env):
    snap = EmacsAdapter().snapshot()
    assert snap == {"enabled_themes": "(doom-one)"}


def test_revert_removes_sentinel_and_disables(env):
    adapter = EmacsAdapter()
    adapter.apply(NIGHTPANEL)
    assert env.sentinel.exists()

    adapter.revert({"enabled_themes": "(doom-one)"})
    assert not env.sentinel.exists()
    assert adapter.verify("off") is True
    assert any("disable-theme (quote nightpanel)" in f for f in env.forms)


def test_apply_survives_theme_write_failure(env, monkeypatch):
    def boom(*_a, **_k):
        raise OSError("read-only fs")

    monkeypatch.setattr(emacs_mod.Path, "write_text", boom)
    EmacsAdapter().apply(NIGHTPANEL)  # logged, not raised


def test_revert_is_safe_with_empty_snapshot(env):
    EmacsAdapter().revert({})  # missing 'enabled_themes' key must not crash
