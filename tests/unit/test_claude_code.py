# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for ClaudeCodeAdapter — focus on stale-session detection.

The adapter's theme-flip path is exercised end-to-end by orchestrator
tests; these tests target the new ``_find_stale_claude_pids`` helper and
the notify-send invocation introduced to surface the design gap where a
claude session pre-dating nightpanel-active keeps its inherited
COLORTERM and bypasses the NP-tinted ANSI palette.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from nightpanel.adapters.claude_code import ClaudeCodeAdapter


@pytest.fixture
def fake_proc(tmp_path, monkeypatch):
    """Build a fake /proc-style tree under tmp_path.

    Returns a helper that creates one fake pid entry with the given
    cmdline and environ payloads.
    """
    proc = tmp_path / "proc"
    proc.mkdir()

    real_dir = Path.home() / ".local" / "share" / "claude" / "versions"

    def make(pid: int, cmdline: bytes, environ: bytes) -> Path:
        d = proc / str(pid)
        d.mkdir()
        (d / "cmdline").write_bytes(cmdline)
        (d / "environ").write_bytes(environ)
        return d

    return proc, real_dir, make


def test_find_stale_finds_claude_with_colorterm(fake_proc):
    proc, real_dir, make = fake_proc
    make(
        4242,
        f"{real_dir}/2.1.152\x00--dangerously-skip-permissions\x00".encode(),
        b"COLORTERM=truecolor\x00TERM=alacritty\x00PATH=/usr/bin\x00",
    )

    stale = ClaudeCodeAdapter()._find_stale_claude_pids(proc_root=proc)

    assert stale == [4242]


def test_find_stale_skips_claude_without_colorterm(fake_proc):
    """A claude launched after NP was active has COLORTERM stripped —
    it's already the cleanly-themed case, not stale."""
    proc, real_dir, make = fake_proc
    make(
        4243,
        f"{real_dir}/2.1.152\x00".encode(),
        b"TERM=alacritty\x00PATH=/usr/bin\x00",
    )

    stale = ClaudeCodeAdapter()._find_stale_claude_pids(proc_root=proc)

    assert stale == []


def test_find_stale_ignores_non_claude_processes(fake_proc):
    proc, _, make = fake_proc
    make(
        5000,
        b"/usr/bin/python3\x00script.py\x00",
        b"COLORTERM=truecolor\x00TERM=alacritty\x00",
    )
    make(
        5001,
        b"/usr/bin/firefox\x00",
        b"COLORTERM=truecolor\x00",
    )

    stale = ClaudeCodeAdapter()._find_stale_claude_pids(proc_root=proc)

    assert stale == []


def test_find_stale_handles_unreadable_entries(fake_proc):
    """Permission errors on a pid dir (e.g. another user's process)
    must not abort the scan — the loop should continue."""
    proc, real_dir, make = fake_proc

    bad = proc / "9999"
    bad.mkdir()
    # No cmdline/environ files → OSError on read → skipped.

    make(
        4242,
        f"{real_dir}/2.1.152\x00".encode(),
        b"COLORTERM=truecolor\x00",
    )

    stale = ClaudeCodeAdapter()._find_stale_claude_pids(proc_root=proc)

    assert stale == [4242]


def test_find_stale_skips_non_numeric_dirs(fake_proc):
    proc, real_dir, make = fake_proc
    (proc / "self").mkdir()
    (proc / "meminfo").write_text("noise")
    make(
        4242,
        f"{real_dir}/2.1.152\x00".encode(),
        b"COLORTERM=truecolor\x00",
    )

    stale = ClaudeCodeAdapter()._find_stale_claude_pids(proc_root=proc)

    assert stale == [4242]


def test_find_stale_finds_multiple(fake_proc):
    proc, real_dir, make = fake_proc
    for pid in (4242, 4243, 4244):
        make(
            pid,
            f"{real_dir}/2.1.152\x00".encode(),
            b"COLORTERM=truecolor\x00",
        )

    stale = ClaudeCodeAdapter()._find_stale_claude_pids(proc_root=proc)

    assert sorted(stale) == [4242, 4243, 4244]


def test_find_stale_returns_empty_when_proc_unreadable(tmp_path):
    """If /proc itself can't be enumerated, return [] rather than raise."""
    missing = tmp_path / "nope"

    stale = ClaudeCodeAdapter()._find_stale_claude_pids(proc_root=missing)

    assert stale == []


def test_apply_notifies_when_stale_present(tmp_path, monkeypatch):
    """End-to-end: apply() detects stale claudes and fires notify-send."""
    settings = tmp_path / "settings.json"
    wrapper = tmp_path / "claude"
    real_dir = tmp_path / "claude-versions"
    real_dir.mkdir()
    (real_dir / "2.1.152").write_text("#!/bin/sh\n")

    monkeypatch.setattr("nightpanel.adapters.claude_code._SETTINGS", settings)
    monkeypatch.setattr("nightpanel.adapters.claude_code._WRAPPER", wrapper)
    monkeypatch.setattr("nightpanel.adapters.claude_code._REAL_DIR", real_dir)

    adapter = ClaudeCodeAdapter()

    with (
        patch.object(adapter, "_find_stale_claude_pids", return_value=[1234, 5678]),
        patch("nightpanel.adapters.claude_code.subprocess.Popen") as mock_popen,
    ):
        from nightpanel.palette import NIGHTPANEL

        adapter.apply(NIGHTPANEL)

    assert mock_popen.called
    argv = mock_popen.call_args.args[0]
    assert argv[0] == "notify-send"
    # Body mentions the count so the user knows the scope.
    body = argv[-1]
    assert "2 claude session(s)" in body


def test_apply_does_not_notify_when_no_stale(tmp_path, monkeypatch):
    settings = tmp_path / "settings.json"
    wrapper = tmp_path / "claude"
    real_dir = tmp_path / "claude-versions"
    real_dir.mkdir()
    (real_dir / "2.1.152").write_text("#!/bin/sh\n")

    monkeypatch.setattr("nightpanel.adapters.claude_code._SETTINGS", settings)
    monkeypatch.setattr("nightpanel.adapters.claude_code._WRAPPER", wrapper)
    monkeypatch.setattr("nightpanel.adapters.claude_code._REAL_DIR", real_dir)

    adapter = ClaudeCodeAdapter()

    with (
        patch.object(adapter, "_find_stale_claude_pids", return_value=[]),
        patch("nightpanel.adapters.claude_code.subprocess.Popen") as mock_popen,
    ):
        from nightpanel.palette import NIGHTPANEL

        adapter.apply(NIGHTPANEL)

    assert not mock_popen.called


def test_notify_silent_when_notify_send_missing(monkeypatch):
    """Headless / minimal hosts may not have libnotify installed.
    The adapter must swallow FileNotFoundError silently."""

    def explode(*a, **kw):
        raise FileNotFoundError("notify-send")

    monkeypatch.setattr("nightpanel.adapters.claude_code.subprocess.Popen", explode)

    # No exception → pass.
    ClaudeCodeAdapter()._notify_stale(3)
