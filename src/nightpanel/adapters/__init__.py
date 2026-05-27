# SPDX-License-Identifier: GPL-3.0-or-later
"""Adapters — one per nightpanel-aware tool."""

from .alacritty import AlacrittyAdapter
from .base import Adapter
from .claude_code import ClaudeCodeAdapter
from .emacs import EmacsAdapter
from .firefox import FirefoxAdapter
from .gemini_cli import GeminiCliAdapter
from .gnome import GnomeAdapter
from .gws import GwsAdapter
from .nvim import NvimAdapter
from .tmux import TmuxAdapter

__all__ = [
    "Adapter",
    "AlacrittyAdapter",
    "ClaudeCodeAdapter",
    "EmacsAdapter",
    "FirefoxAdapter",
    "GeminiCliAdapter",
    "GnomeAdapter",
    "GwsAdapter",
    "NvimAdapter",
    "TmuxAdapter",
]
