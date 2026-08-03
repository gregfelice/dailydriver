# SPDX-License-Identifier: GPL-3.0-or-later
"""Policy tests for nightpanel-toggle's debounce window.

test_toggle_debounce.py verifies the *mechanism* (the debounce works as
implemented). These tests verify the *policy* (the implementation matches
what a user clicking on the panel button actually wants).

The distinction matters: a debounce window that swallows every deliberate
"on, look, off" retap is mechanically correct but policy-wrong. Reported
symptom: "i have to click on np twice to toggle".

Evidence from a live ~/.config/nightpanel/toggle.log session at 3.0 s
production window:
    22:11:21.858  apply
    22:11:24.041  debounce-revert    <- user's deliberate off-click, eaten
    22:11:24.975  revert              <- user's *second* deliberate off-click

These tests pin the policy: a deliberate retap (>= ~200 ms apart, which is
already slower than the fastest possible accidental double-click) must
toggle. Anything stricter is a UX bug.

Each test asserts user-visible state after a realistic click pattern.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

# Resolve the installed toggle from PATH (system pkg → /usr/bin), falling back to
# the dev-stow location. The autouse script_exists fixture skips when neither is
# present (e.g. CI without install).
SCRIPT = Path(
    shutil.which("nightpanel-toggle") or Path.home() / ".local" / "bin" / "nightpanel-toggle"
)

# Production window is 3.0 s; we run tests at 0.5 s for speed. The 60 %
# retap-ratio below mirrors the real-world 1.5 s-after-3 s-window pattern
# captured in toggle.log — so a fix that passes here will fix production too.
DEBOUNCE_S = 0.5
DELIBERATE_RETAP_S = 0.3  # 60 % of window — well past any accidental double-tap


@pytest.fixture
def env(tmp_path):
    base = {**os.environ}
    for k in ("NP_CONFIG_DIR", "NP_DEBOUNCE_S", "NP_TOGGLE_MOCK"):
        base.pop(k, None)
    return {
        **base,
        "NP_CONFIG_DIR": str(tmp_path),
        "NP_DEBOUNCE_S": str(DEBOUNCE_S),
        "NP_TOGGLE_MOCK": "1",
    }


@pytest.fixture(autouse=True)
def script_exists():
    if not SCRIPT.exists():
        pytest.skip(f"toggle launcher missing at {SCRIPT}")


def _invoke(env, *args):
    r = subprocess.run([str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, f"toggle script failed: {r.stderr}"
    return r


def _active(tmp_path) -> bool:
    return (tmp_path / "nightpanel-active").exists()


def _decisions(tmp_path) -> list[str]:
    text = (tmp_path / "toggle.log").read_text()
    return [
        line.split("decision:", 1)[1].strip() for line in text.splitlines() if "decision:" in line
    ]


def test_deliberate_retap_must_toggle_off(env, tmp_path):
    """User taps ON, looks at the result for 300 ms, taps OFF.

    This is the workflow that the live bug report ("click twice to toggle")
    points at. The second tap is deliberate — it MUST flip the state.
    Currently fails because the 0.5 s debounce window eats the 300 ms retap.
    Fix is to shorten the window to ~150 ms (covers accidental double-clicks
    only) or remove the debounce entirely if the stale-grab re-dispatch it
    was added for never empirically reproduces (see bin/analyze-toggle-log).
    """
    _invoke(env)
    time.sleep(DELIBERATE_RETAP_S)
    _invoke(env)
    assert not _active(tmp_path), (
        f"second deliberate tap {DELIBERATE_RETAP_S}s after first must toggle off; "
        f"decisions={_decisions(tmp_path)}"
    )


def test_accidental_double_click_is_still_debounced(env, tmp_path):
    """Two presses within 50 ms (faster than humanly deliberate) — accidental
    double-click, stuck button, or stale-grab re-dispatch. SHOULD be debounced.

    This documents the *legitimate* job of the debounce so a future fix
    doesn't throw out the safety net along with the bug.
    """
    _invoke(env)
    time.sleep(0.05)
    _invoke(env)
    assert _active(tmp_path), (
        f"50ms double-tap should be treated as accidental; decisions={_decisions(tmp_path)}"
    )


def test_evt_metadata_args_are_logged(env, tmp_path):
    """Extension forwards event metadata as argv; the script must capture
    it into toggle.log so the post-hoc analyzer can correlate invocations.

    Without this signal in the log there's no way to tell a stale-grab
    re-dispatch from a deliberate second click — exactly the question
    the user asked us to investigate.
    """
    _invoke(env, "--evt-time", "12345", "--evt-source", "btn", "--evt-button", "1")
    log = (tmp_path / "toggle.log").read_text()
    assert "--evt-time" in log and "12345" in log, (
        f"event metadata must appear in toggle.log argv line; got:\n{log}"
    )
