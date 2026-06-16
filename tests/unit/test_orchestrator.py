# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for NightpanelOrchestrator state machine.

Locks in the snapshot-guard + ≥1-success-required-to-mark-active behavior
patched on 2026-05-25 after observing that ACTIVE_FILE drift could cause
the next apply() to capture the already-applied palette as the baseline,
and that a fully-failed apply() still touched ACTIVE_FILE.
"""

from __future__ import annotations

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
        self.last_revert_snapshot: dict | None = None
        self._installed = True

    def installed(self) -> bool:
        return self._installed

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
        self.last_revert_snapshot = snapshot
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
    assert not tmp_state["active"].exists(), (
        "ACTIVE_FILE must not be marked when every adapter failed"
    )


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


# ── revert restores per-adapter snapshots ────────────────────────────────


def test_revert_passes_saved_snapshot_to_each_adapter(tmp_state):
    a = FakeAdapter("a")
    b = FakeAdapter("b")
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [a, b])

    o.apply()
    o.revert()

    # Each adapter's saved snapshot (namespaced by name) is handed back to it.
    assert a.last_revert_snapshot == {"name": "a", "captured": True}
    assert b.last_revert_snapshot == {"name": "b", "captured": True}
    assert a.reverts == 1 and b.reverts == 1
    assert not tmp_state["active"].exists(), "revert must clear ACTIVE_FILE"


def test_revert_with_missing_state_passes_empty_dict(tmp_state):
    """No state file (or unknown adapter) → adapter gets {} rather than KeyError."""
    a = FakeAdapter("a")
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [a])
    o.revert()  # never applied → no state file
    assert a.last_revert_snapshot == {}


def test_revert_continues_after_one_adapter_raises(tmp_state, monkeypatch):
    a = FakeAdapter("a")
    b = FakeAdapter("b")

    def boom(_snap):
        raise RuntimeError("a revert boom")

    monkeypatch.setattr(a, "revert", boom)
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [a, b])
    o.apply()
    o.revert()  # must not propagate
    assert b.reverts == 1, "b should still revert even though a raised"


# ── verify() aggregates per-adapter state ────────────────────────────────


def test_verify_returns_dict_for_active_adapters(tmp_state):
    a = FakeAdapter("a", verify_on=True)
    b = FakeAdapter("b", verify_on=False)
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [a, b])
    assert o.verify("on") == {"a": True, "b": False}
    assert o.verify("off") == {"a": False, "b": True}


def test_uninstalled_adapters_are_skipped(tmp_state):
    a = FakeAdapter("a")
    b = FakeAdapter("b")
    b._installed = False
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [a, b])

    outcomes = o.apply()
    assert outcomes == {"a": True}, "uninstalled adapter must not appear in outcomes"
    assert b.applies == 0 and b.snapshots_taken == 0


# ── brightness updates: gated on ACTIVE_FILE + rate-limited ──────────────


@pytest.fixture
def tmp_command(tmp_path, monkeypatch):
    cmd = tmp_path / "np-command.json"
    monkeypatch.setattr(orch, "_NP_COMMAND", cmd)
    return cmd


def test_update_brightness_noops_when_inactive(tmp_state, tmp_command):
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [FakeAdapter("a")])
    # ACTIVE_FILE absent → no command written (nothing is listening).
    o.update_brightness(0.8)
    assert not tmp_command.exists()


def test_update_brightness_writes_when_active(tmp_state, tmp_command):
    import json as _json

    tmp_state["active"].parent.mkdir(parents=True, exist_ok=True)
    tmp_state["active"].touch()
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [FakeAdapter("a")])

    o.update_brightness(0.8)
    payload = _json.loads(tmp_command.read_text())
    assert payload == {"action": "apply", "brightness": 0.8}


def test_update_brightness_rate_limited(tmp_state, tmp_command):
    import json as _json

    tmp_state["active"].parent.mkdir(parents=True, exist_ok=True)
    tmp_state["active"].touch()
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [FakeAdapter("a")])

    o.update_brightness(0.8)
    o.update_brightness(0.2)  # within the 0.1s window → suppressed
    assert _json.loads(tmp_command.read_text())["brightness"] == 0.8


def test_video_brightness_uses_independent_rate_limit(tmp_state, tmp_command):
    """A drag on the page-brightness slider must not suppress the video
    slider — they keep separate timestamps."""
    import json as _json

    tmp_state["active"].parent.mkdir(parents=True, exist_ok=True)
    tmp_state["active"].touch()
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [FakeAdapter("a")])

    o.update_brightness(0.8)
    o.update_video_brightness(0.3)  # different timestamp → not suppressed
    assert _json.loads(tmp_command.read_text()) == {
        "action": "apply",
        "videoBrightness": 0.3,
    }


# ── install_bridge consent gate ──────────────────────────────────────────


def test_install_bridge_requires_consent():
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [FakeAdapter("a")])
    with pytest.raises(orch.ConsentRequired):
        o.install_bridge()  # confirmed defaults to False


def test_is_active_tracks_active_file(tmp_state):
    """is_active() is the single source of truth for 'should we resume the
    system theme' — gates launch-time apply so opening the config window
    doesn't flip the session when nightpanel is off."""
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [FakeAdapter("a")])
    assert o.is_active() is False
    o.apply()
    assert o.is_active() is True
    o.revert()
    assert o.is_active() is False


def test_load_state_returns_empty_on_corrupt_file(tmp_state):
    tmp_state["state"].parent.mkdir(parents=True, exist_ok=True)
    tmp_state["state"].write_text("{ broken json")
    o = orch.NightpanelOrchestrator(NIGHTPANEL, [FakeAdapter("a")])
    assert o._load_state() == {}
