# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the tmux palette overlay from a Palette."""

from __future__ import annotations

from ..palette import Palette


def render(p: Palette) -> str:
    return f"""# nightpanel tmux theme — sourced over the base theme to apply NP palette
# reverted by re-sourcing ~/.tmux.conf
# generated from nightpanel.palette — edit there, not here

set -g status-style "bg={p.bg_header},fg={p.fg}"
set -g status-left ""
set -g status-left-length 100
set -g status-right-length 50
set -g status-right " #[fg={p.fg_amber}]#S #[fg={p.fg_dim}]│ #[fg={p.fg}]%H:%M #[fg={p.fg_dim}]%d-%b-%y "

set-window-option -g window-status-format         '#[fg={p.fg_dim}]#I/#W'
set-window-option -g window-status-current-format '#[fg={p.fg_bright}]#I/#W'

set -g pane-border-style        "fg={p.border_q}"
set -g pane-active-border-style "fg={p.border_s}"

set -g message-style         "bg={p.bg_card},fg={p.fg_amber}"
set -g message-command-style "bg={p.bg_card},fg={p.fg}"

set -g mode-style "fg={p.bg},bg={p.fg_amber}"
"""
