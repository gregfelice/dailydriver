# SPDX-License-Identifier: GPL-3.0-or-later
"""Adapter — the contract every nightpanel-aware tool implements.

The orchestrator iterates a list of Adapters, calling apply()/revert() to
toggle nightpanel on/off and verify() to confirm the state landed. Each
adapter owns its own state shape (returned from snapshot(), consumed by
revert()); the orchestrator just serializes it under the adapter's name.

To add a new tool (emacs, nautilus, eva, …):
    1. Subclass Adapter
    2. Implement snapshot/apply/revert/verify
    3. Append an instance to NightpanelOrchestrator.adapters
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Literal

from ..palette import Palette

_LOG = logging.getLogger(__name__)


class Adapter(ABC):
    """Contract for everything that participates in nightpanel toggling."""

    #: short slug used for state namespacing and logging (e.g. "alacritty")
    name: str

    def installed(self) -> bool:
        """Is the target tool available? Adapters whose tool is missing are
        skipped silently by the orchestrator. Default: always True."""
        return True

    @abstractmethod
    def snapshot(self) -> dict:
        """Capture current state so revert() can restore it later.

        Returns an opaque dict; only this adapter interprets the keys.
        """

    @abstractmethod
    def apply(self, palette: Palette) -> None:
        """Apply the nightpanel scheme using colors from the palette."""

    @abstractmethod
    def revert(self, snapshot: dict) -> None:
        """Restore the state previously captured by snapshot()."""

    @abstractmethod
    def verify(self, expected: Literal["on", "off"]) -> bool:
        """Cheaply check whether the live tool state matches expected."""
