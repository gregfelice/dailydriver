# SPDX-License-Identifier: GPL-3.0-or-later
"""The ``--player`` launch intercept.

Super+P is wired (in the GNOME backend) to a ``... --player`` command. That flag
is honored in one shared place — ``application.main()`` — so every install path
(`nightpanel`, the Flatpak, run-dev.sh) launches nightpanel's standalone
theme-synced mini-player instead of the keyboard-config UI.

The test mocks ``PlayerApp`` so no window is created; it asserts the flag routes
to the player and that the unknown ``--player`` option is stripped before the
player's own ``run()`` (which does not parse it).
"""

from __future__ import annotations

import sys

import pytest

# The intercept lives in application.py, which imports gi/Gtk at module load.
gi = pytest.importorskip("gi", reason="GTK bindings required to import application")


def test_player_flag_launches_player_app(monkeypatch):
    from unittest.mock import MagicMock, patch

    monkeypatch.setattr(sys, "argv", ["nightpanel", "--player"])
    with patch("nightpanel.player_app.PlayerApp") as mock_player:
        inst = MagicMock()
        inst.run.return_value = 0
        mock_player.return_value = inst

        from nightpanel.application import main

        rc = main()

    assert rc == 0
    assert mock_player.called, "--player must construct PlayerApp"
    # --player is stripped: only the program name reaches PlayerApp.run().
    assert inst.run.call_args.args[0] == ["nightpanel"]


def test_no_player_flag_does_not_launch_player(monkeypatch):
    """Without --player, the player app is never constructed (the keyboard UI
    path runs instead — which we stub out at the DailyDriverApplication.run
    boundary so no real window opens)."""
    from unittest.mock import patch

    monkeypatch.setattr(sys, "argv", ["nightpanel"])
    with (
        patch("nightpanel.player_app.PlayerApp") as mock_player,
        patch("nightpanel.application.DailyDriverApplication") as mock_app,
    ):
        mock_app.return_value.run.return_value = 0

        from nightpanel.application import main

        main("9.9.9")

    assert not mock_player.called, "no --player => player app must not launch"
