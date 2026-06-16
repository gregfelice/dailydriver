# SPDX-License-Identifier: GPL-3.0-or-later
"""GwsAdapter — theme line flip in gws's todo.state, preserving other lines.

gws persists its theme as a ``theme:<Name>`` line in ``~/.gws/todo.state``,
alongside collapse markers (cat:/proj:/task:). The adapter must flip only the
theme line on apply, restore the prior theme on revert, and clean up the file
entirely if it created it.
"""

from __future__ import annotations

import pytest

from nightpanel.adapters import gws as gws_mod
from nightpanel.adapters.gws import GwsAdapter, _parse, _serialize
from nightpanel.palette import NIGHTPANEL


@pytest.fixture
def state(tmp_path, monkeypatch):
    path = tmp_path / ".gws" / "todo.state"
    monkeypatch.setattr(gws_mod, "_STATE", path)
    return path


# ── pure parse/serialize ────────────────────────────────────────────────


def test_parse_splits_theme_from_other_lines():
    theme, others = _parse("theme:Dracula\ncat:work:1\nproj:home:0\n")
    assert theme == "Dracula"
    assert others == ["cat:work:1", "proj:home:0"]


def test_parse_no_theme_line():
    theme, others = _parse("cat:work:1\n")
    assert theme is None
    assert others == ["cat:work:1"]


def test_serialize_round_trip_preserves_order():
    text = _serialize("Nightpanel", ["cat:work:1", "proj:home:0"])
    assert text == "theme:Nightpanel\ncat:work:1\nproj:home:0\n"


def test_serialize_empty_is_empty_string():
    assert _serialize(None, []) == ""


# ── adapter behavior ────────────────────────────────────────────────────


def test_installed_when_state_dir_exists(state):
    state.parent.mkdir(parents=True)
    assert GwsAdapter().installed() is True


def test_apply_sets_theme_and_preserves_other_lines(state):
    state.parent.mkdir(parents=True)
    state.write_text("theme:Dracula\ncat:work:1\n")

    GwsAdapter().apply(NIGHTPANEL)

    theme, others = _parse(state.read_text())
    assert theme == "Nightpanel"
    assert others == ["cat:work:1"]


def test_verify_tracks_theme(state):
    state.parent.mkdir(parents=True)
    adapter = GwsAdapter()
    assert adapter.verify("off") is True  # no file
    adapter.apply(NIGHTPANEL)
    assert adapter.verify("on") is True
    assert adapter.verify("off") is False


def test_snapshot_records_prior_theme_and_existence(state):
    state.parent.mkdir(parents=True)
    state.write_text("theme:Dracula\ncat:work:1\n")
    assert GwsAdapter().snapshot() == {"theme": "Dracula", "existed": True}


def test_snapshot_when_no_state_file(state):
    assert GwsAdapter().snapshot() == {"theme": None, "existed": False}


def test_revert_restores_prior_theme(state):
    state.parent.mkdir(parents=True)
    state.write_text("theme:Dracula\ncat:work:1\n")
    adapter = GwsAdapter()
    snap = adapter.snapshot()

    adapter.apply(NIGHTPANEL)
    adapter.revert(snap)

    theme, others = _parse(state.read_text())
    assert theme == "Dracula"
    assert others == ["cat:work:1"]


def test_revert_drops_file_it_created_when_only_theme_line(state):
    """If gws had no state file and we created one holding only our theme
    line, revert removes the whole file rather than leaving an orphan."""
    state.parent.mkdir(parents=True)
    adapter = GwsAdapter()
    snap = adapter.snapshot()  # existed=False
    adapter.apply(NIGHTPANEL)
    assert state.exists()

    adapter.revert(snap)
    assert not state.exists()


def test_revert_strips_only_our_line_when_other_content_appeared(state):
    """File didn't exist before us, but other lines showed up alongside our
    theme; revert must strip only the theme line and keep the rest."""
    state.parent.mkdir(parents=True)
    adapter = GwsAdapter()
    snap = adapter.snapshot()  # existed=False
    adapter.apply(NIGHTPANEL)
    # Simulate gws adding its own markers while nightpanel was active.
    state.write_text("theme:Nightpanel\ncat:work:1\n")

    adapter.revert(snap)
    assert state.exists()
    theme, others = _parse(state.read_text())
    assert theme is None
    assert others == ["cat:work:1"]
