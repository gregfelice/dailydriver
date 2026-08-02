# SPDX-License-Identifier: GPL-3.0-or-later
"""EmacsAdapter — sentinel + emacsclient round-trip.

apply() drops a sentinel (the only signal that survives across daemon
restarts) and tells any live daemon to load the installed nightpanel theme.
It no longer writes ``nightpanel-theme.el``: that ships as its own package.
revert() removes the sentinel and disables the theme. verify() keys purely
off the sentinel.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nightpanel.adapters import emacs as emacs_mod
from nightpanel.adapters.emacs import EmacsAdapter
from nightpanel.palette import NIGHTPANEL


@pytest.fixture
def env(tmp_path, monkeypatch):
    sentinel = tmp_path / "config" / "emacs-active"
    monkeypatch.setattr(emacs_mod, "_SENTINEL", sentinel)

    forms: list[str] = []

    def fake_client(form: str):
        forms.append(form)
        if form == "custom-enabled-themes":
            return "(doom-one)"
        # The load form is wrapped in condition-case and yields t on success —
        # i.e. this daemon has nightpanel-theme installed.
        return "t" if "load-theme" in form else ""

    monkeypatch.setattr(emacs_mod, "_emacsclient", fake_client)
    return SimpleNamespace(sentinel=sentinel, forms=forms)


def test_installed_follows_which(monkeypatch):
    monkeypatch.setattr(emacs_mod.shutil, "which", lambda _: "/usr/bin/emacs")
    assert EmacsAdapter().installed() is True
    monkeypatch.setattr(emacs_mod.shutil, "which", lambda _: None)
    assert EmacsAdapter().installed() is False


def test_apply_writes_sentinel_and_loads(env):
    EmacsAdapter().apply(NIGHTPANEL)

    assert env.sentinel.exists()
    # A daemon was asked to load the theme.
    assert any("load-theme (quote nightpanel)" in f for f in env.forms)


def test_apply_does_not_write_a_theme_file(env, monkeypatch):
    # The theme is an installed package; rendering it here is what caused the
    # two copies to drift, so apply() must not put any .el on disk.
    written: list[str] = []
    monkeypatch.setattr(
        emacs_mod.Path, "write_text", lambda self, *a, **k: written.append(str(self))
    )
    EmacsAdapter().apply(NIGHTPANEL)
    assert not [p for p in written if p.endswith(".el")]


def test_apply_warns_when_theme_is_not_installed(env, monkeypatch, caplog):
    # condition-case swallowed a load failure -> nil, not t.
    monkeypatch.setattr(emacs_mod, "_emacsclient", lambda form: "nil")
    EmacsAdapter().apply(NIGHTPANEL)
    assert "not loaded" in caplog.text


def test_apply_is_quiet_when_no_daemon_is_running(env, monkeypatch, caplog):
    # _emacsclient returns None with no daemon — the common case, not an error.
    monkeypatch.setattr(emacs_mod, "_emacsclient", lambda form: None)
    EmacsAdapter().apply(NIGHTPANEL)
    assert "not loaded" not in caplog.text


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


def test_apply_survives_sentinel_write_failure(env, monkeypatch):
    def boom(*_a, **_k):
        raise OSError("read-only fs")

    monkeypatch.setattr(emacs_mod.Path, "touch", boom)
    EmacsAdapter().apply(NIGHTPANEL)  # logged, not raised


def test_revert_is_safe_with_empty_snapshot(env):
    EmacsAdapter().revert({})  # missing 'enabled_themes' key must not crash
