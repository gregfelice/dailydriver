# SPDX-License-Identifier: GPL-3.0-or-later
"""Alacritty adapter — import-flip round-trip, incl. the multi-line array form.

Regression: the old regex adapter only understood single-line
``import = ["…"]`` and corrupted the multi-line array form on apply/revert,
leaving invalid TOML that alacritty refused to load.
"""

import tomllib

import pytest

from nightpanel.adapters.alacritty import AlacrittyAdapter
from nightpanel.palette import NIGHTPANEL

_MULTILINE = """\
[general]
import = [
    "~/.config/alacritty/themes/themes/ayu_dark.toml"
]

[window]
padding = { x = 12, y = 12 }
"""

_SINGLE_LINE = """\
[general]
import = ["~/.config/alacritty/themes/themes/ayu_dark.toml"]

[font]
size = 12.0
"""


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    path = tmp_path / "alacritty.toml"
    theme = tmp_path / "themes" / "themes" / "nightpanel.toml"
    monkeypatch.setattr("nightpanel.adapters.alacritty._CFG", path)
    monkeypatch.setattr("nightpanel.adapters.alacritty._NP_THEME", theme)
    return path, theme


def _parses(path):
    """Raises if the file is not valid TOML; returns the parsed dict."""
    return tomllib.load(open(path, "rb"))


@pytest.mark.parametrize("original", [_MULTILINE, _SINGLE_LINE], ids=["multiline", "single"])
def test_apply_revert_round_trip_preserves_import(cfg, original):
    path, theme = cfg
    path.write_text(original)
    adapter = AlacrittyAdapter()

    # Orchestrator snapshots BEFORE apply, then reverts with that snapshot.
    snap = adapter.snapshot()
    assert snap["import"] == ["~/.config/alacritty/themes/themes/ayu_dark.toml"]

    adapter.apply(NIGHTPANEL)
    applied = _parses(path)  # must stay valid TOML — the old bug failed here
    assert applied["general"]["import"] == [str(theme)]
    assert adapter.verify("on")

    adapter.revert(snap)
    reverted = _parses(path)
    assert reverted["general"]["import"] == ["~/.config/alacritty/themes/themes/ayu_dark.toml"]
    assert adapter.verify("off")


def test_revert_with_no_prior_import_removes_key(cfg):
    path, _ = cfg
    path.write_text("[general]\n\n[window]\npadding = { x = 12, y = 12 }\n")
    adapter = AlacrittyAdapter()

    snap = adapter.snapshot()
    assert snap["import"] is None

    adapter.apply(NIGHTPANEL)
    assert adapter.verify("on")

    adapter.revert(snap)
    data = _parses(path)
    assert "import" not in data.get("general", {})
    assert adapter.verify("off")


def test_corrupt_config_snapshot_is_safe(cfg):
    """A pre-existing broken file must not crash snapshot()/verify()."""
    path, _ = cfg
    path.write_text('[general]\n    "orphaned.toml"\n]\n')
    adapter = AlacrittyAdapter()

    assert adapter.snapshot() == {"import": None}
    assert adapter.verify("off") is True
