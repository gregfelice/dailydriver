# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for NightpanelOrchestrator state machine.

Locks in the snapshot-guard + ≥1-success-required-to-mark-active behavior
patched on 2026-05-25 after observing that ACTIVE_FILE drift could cause
the next apply() to capture the already-applied palette as the baseline,
and that a fully-failed apply() still touched ACTIVE_FILE.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest

from nightpanel.adapters.base import Adapter
from nightpanel.palette import NIGHTPANEL, Palette
from nightpanel.services import nightpanel_orchestrator as orch


class FakeAdapter(Adapter):
    """Adapter test double — records every call, configurable apply outcome."""

    def __init__(self, name: str, *, raises: bool = False, verify_on: bool = False):
        self.name = name
        self.raises = raises
        self._verify_on = verify_on
        self._applied = False
        self.snapshots_taken = 0
        self.applies = 0
        self.reverts = 0

    def installed(self) -> bool:
        return True

    def snapshot(self) -> dict:
        self.snapshots_taken += 1
        return {"name": self.name, "captured": True}

    def apply(self, palette: Palette) -> None:
        self.applies += 1
        if self.raises:
            raise RuntimeError(f"{self.name} apply boom")
        self._applied = True

    def revert(self, snapshot: dict) -> None:
        self.reverts += 1
        self._applied = False

    def verify(self, expected: Literal["on", "off"]) -> bool:
        on = self._verify_on or self._applied
        return on if expected == "on" else not on


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    """Redirect orchestrator's state + active-file constants to a tmp dir."""
    state = tmp_path / "state.json"
    active = tmp_path / "active"
    monkeypatch.setattr(orch, "_STATE_PATH", state)
    monkeypatch.setattr(orch, "_ACTIVE_FILE", active)
    return {"state": state, "active": active}


def test_apply_happy_path_marks_active(tmp_state):
    a = FakeAdapter("a")
    b = FakeAdapter("b")
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [a, b])

    outcomes = o.apply()

    assert outcomes == {"a": True, "b": True}
    assert tmp_state["active"].exists(), "ACTIVE_FILE should be marked on success"
    assert a.snapshots_taken == 1 and b.snapshots_taken == 1
    assert a.applies == 1 and b.applies == 1


def test_apply_all_fail_does_not_mark_active(tmp_state):
    """If every adapter raises, ACTIVE_FILE must NOT be touched. State
    machine should report 'off' so a follow-up apply isn't misled into
    capturing the failed-attempt world as a baseline."""
    a = FakeAdapter("a", raises=True)
    b = FakeAdapter("b", raises=True)
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [a, b])

    outcomes = o.apply()

    assert outcomes == {"a": False, "b": False}
    assert not tmp_state["active"].exists(), \
        "ACTIVE_FILE must not be marked when every adapter failed"


def test_apply_partial_success_marks_active(tmp_state):
    """≥1 success is sufficient to call ourselves 'on'."""
    a = FakeAdapter("a", raises=True)
    b = FakeAdapter("b")
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [a, b])

    outcomes = o.apply()

    assert outcomes == {"a": False, "b": True}
    assert tmp_state["active"].exists()


def test_snapshot_guard_preserves_baseline_when_world_already_on(tmp_state):
    """ACTIVE_FILE missing but verify('on') returns True for some adapter
    means a prior apply landed partially. Re-applying must NOT overwrite
    the existing snapshot with the post-apply state — that was the
    snapshot-corruption bug from 2026-05-25."""
    # First apply captures a baseline + leaves adapters in 'on' state.
    a = FakeAdapter("a")
    b = FakeAdapter("b")
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [a, b])
    o.apply()
    original_state_text = tmp_state["state"].read_text()
    assert a.snapshots_taken == 1

    # Simulate the failure mode: ACTIVE_FILE goes missing while world stays on.
    tmp_state["active"].unlink()
    assert a.verify("on") is True  # the world is still on

    # Re-apply should detect this and refuse to re-snapshot.
    o.apply()

    # Snapshot file unchanged.
    assert tmp_state["state"].read_text() == original_state_text
    # And only the original snapshot was ever taken.
    assert a.snapshots_taken == 1, "snapshot must not be re-taken when world looks on"
    assert b.snapshots_taken == 1


def test_snapshot_taken_fresh_when_world_off(tmp_state):
    """Negative of the guard: if nothing looks on, we DO snapshot fresh."""
    a = FakeAdapter("a")
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [a])

    o.apply()
    o.revert()
    # State file should still exist (we don't delete it on revert).
    assert tmp_state["state"].exists()
    snapshot_count_after_first_cycle = a.snapshots_taken

    # World is off (revert just ran). Apply again — should re-snapshot.
    o.apply()
    assert a.snapshots_taken == snapshot_count_after_first_cycle + 1
