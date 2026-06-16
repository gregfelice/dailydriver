# SPDX-License-Identifier: GPL-3.0-or-later
"""TmuxAdapter — overlay write + source-file flip + status-style probe.

The adapter applies by writing a palette overlay to
``~/.config/nightpanel/themes/tmux-nightpanel.conf`` and sourcing it into the
running server; it reverts by re-sourcing the user's base ``~/.tmux.conf``.
verify() probes ``status-style`` for the overlay's pure-black background.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nightpanel.adapters import tmux as tmux_mod
from nightpanel.adapters.tmux import TmuxAdapter
from nightpanel.palette import NIGHTPANEL


class FakeRun:
    """Stand-in for the module-level ``_run`` — records argv, returns canned."""

    def __init__(self, stdout: str = "", returncode: int = 0):
        self.calls: list[list[str]] = []
        self.stdout = stdout
        self.returncode = returncode

    def __call__(self, cmd):
        self.calls.append(cmd)
        return SimpleNamespace(returncode=self.returncode, stdout=self.stdout)


@pytest.fixture
def env(tmp_path, monkeypatch):
    overlay = tmp_path / "themes" / "tmux-nightpanel.conf"
    base = tmp_path / ".tmux.conf"
    base.write_text("# user base conf\n")
    monkeypatch.setattr(tmux_mod, "_NP_OVERLAY", overlay)
    monkeypatch.setattr(tmux_mod, "_BASE_CONF", base)
    fake = FakeRun()
    monkeypatch.setattr(tmux_mod, "_run", fake)
    return SimpleNamespace(overlay=overlay, base=base, run=fake)


def test_installed_follows_which(monkeypatch):
    monkeypatch.setattr(tmux_mod.shutil, "which", lambda _: "/usr/bin/tmux")
    assert TmuxAdapter().installed() is True
    monkeypatch.setattr(tmux_mod.shutil, "which", lambda _: None)
    assert TmuxAdapter().installed() is False


def test_apply_writes_overlay_and_sources_it(env):
    TmuxAdapter().apply(NIGHTPANEL)

    assert env.overlay.exists()
    body = env.overlay.read_text()
    # Pure-black status bar is the overlay's signature (bg_header == #000000).
    assert "status-style" in body
    assert "bg=#000000" in body
    # The running server was told to source the overlay we just wrote.
    assert ["tmux", "source-file", str(env.overlay)] in env.run.calls


def test_revert_sources_base_conf(env):
    TmuxAdapter().revert({})
    assert ["tmux", "source-file", str(env.base)] in env.run.calls


def test_verify_on_when_status_style_is_black(env):
    env.run.stdout = "fg=#7DB890,bg=#000000"
    adapter = TmuxAdapter()
    assert adapter.verify("on") is True
    assert adapter.verify("off") is False


def test_verify_off_when_status_style_is_not_black(env):
    env.run.stdout = "fg=colour250,bg=colour236"
    adapter = TmuxAdapter()
    assert adapter.verify("off") is True
    assert adapter.verify("on") is False


def test_verify_off_on_nonzero_returncode(env):
    env.run.returncode = 1
    env.run.stdout = "bg=#000000"  # ignored because returncode != 0
    assert TmuxAdapter().verify("on") is False


def test_apply_survives_overlay_write_failure(env, monkeypatch):
    """A write failure is logged, not raised — apply must not crash the run."""

    def boom(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(tmux_mod.Path, "write_text", boom)
    TmuxAdapter().apply(NIGHTPANEL)  # no exception


def test_snapshot_is_empty_contract(env):
    # Documented (and flagged) behavior: tmux relies on re-sourcing the base
    # conf, so snapshot captures nothing. Locking it so a future real-snapshot
    # change is a deliberate, test-visible decision.
    assert TmuxAdapter().snapshot() == {}
