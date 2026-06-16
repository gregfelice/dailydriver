# SPDX-License-Identifier: GPL-3.0-or-later
"""NvimAdapter — after/plugin override create/remove + colorscheme restore.

apply() drops ``after/plugin/nightpanel_active.lua`` (which forces the
nightpanel colorscheme) and nudges any live ``--server`` sessions; revert()
removes the file and restores the colorscheme captured at snapshot time.
verify() keys off the override file's presence.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nightpanel.adapters import nvim as nvim_mod
from nightpanel.adapters.nvim import NvimAdapter
from nightpanel.palette import NIGHTPANEL


@pytest.fixture
def env(tmp_path, monkeypatch):
    after = tmp_path / "nvim" / "after" / "plugin" / "nightpanel_active.lua"
    monkeypatch.setattr(nvim_mod, "_AFTER_PLUGIN", after)
    sent: list[str] = []
    # Keep hermetic: no real nvim sockets, record any --remote-send commands.
    monkeypatch.setattr(NvimAdapter, "_sockets", lambda self: [])
    monkeypatch.setattr(NvimAdapter, "_send_cmd", lambda self, cmd: sent.append(cmd))
    return SimpleNamespace(after=after, sent=sent)


def test_installed_follows_which(monkeypatch):
    monkeypatch.setattr(nvim_mod.shutil, "which", lambda _: "/usr/bin/nvim")
    assert NvimAdapter().installed() is True
    monkeypatch.setattr(nvim_mod.shutil, "which", lambda _: None)
    assert NvimAdapter().installed() is False


def test_apply_writes_override_and_sends_colorscheme(env):
    NvimAdapter().apply(NIGHTPANEL)

    assert env.after.exists()
    assert "colorscheme nightpanel" in env.after.read_text()
    assert "colorscheme nightpanel" in env.sent


def test_verify_tracks_override_file(env):
    adapter = NvimAdapter()
    assert adapter.verify("off") is True
    adapter.apply(NIGHTPANEL)
    assert adapter.verify("on") is True
    assert adapter.verify("off") is False


def test_snapshot_defaults_when_no_live_session(env, monkeypatch):
    monkeypatch.setattr(NvimAdapter, "_query_live_colorscheme", lambda self: None)
    assert NvimAdapter().snapshot() == {"colorscheme": "tokyonight"}


def test_snapshot_captures_live_colorscheme(env, monkeypatch):
    monkeypatch.setattr(NvimAdapter, "_query_live_colorscheme", lambda self: "gruvbox")
    assert NvimAdapter().snapshot() == {"colorscheme": "gruvbox"}


def test_revert_removes_override_and_restores_previous(env):
    adapter = NvimAdapter()
    adapter.apply(NIGHTPANEL)
    env.sent.clear()

    adapter.revert({"colorscheme": "gruvbox"})
    assert not env.after.exists()
    assert adapter.verify("off") is True
    assert "colorscheme gruvbox" in env.sent


def test_revert_falls_back_to_default_when_snapshot_empty(env):
    adapter = NvimAdapter()
    adapter.apply(NIGHTPANEL)
    env.sent.clear()
    adapter.revert({})
    assert "colorscheme tokyonight" in env.sent
