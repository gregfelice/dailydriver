# SPDX-License-Identifier: GPL-3.0-or-later
"""FirefoxAdapter — profiles.ini discovery, command-file flip, userChrome.css.

Two surfaces:
  - ``find_default_profile()``: mirror Firefox's own profile-selection order
    (Install Default → Profile Default=1 → first Profile).
  - apply()/revert()/verify(): write the command JSON the native host polls,
    and (re)materialize userChrome.css + the legacy-stylesheets pref.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from nightpanel.adapters import firefox as ff_mod
from nightpanel.adapters.firefox import FirefoxAdapter, find_default_profile
from nightpanel.palette import NIGHTPANEL

# ── find_default_profile ────────────────────────────────────────────────


def _write_ini(root, body: str):
    root.mkdir(parents=True, exist_ok=True)
    (root / "profiles.ini").write_text(body)


def test_find_profile_missing_ini_returns_none(tmp_path):
    assert find_default_profile(tmp_path) is None


def test_find_profile_prefers_install_default(tmp_path):
    _write_ini(
        tmp_path,
        "[Install123]\nDefault=abc.default-release\n\n[Profile0]\nPath=zzz.other\nDefault=1\n",
    )
    assert find_default_profile(tmp_path) == tmp_path / "abc.default-release"


def test_find_profile_falls_back_to_default_flag(tmp_path):
    _write_ini(
        tmp_path,
        "[Profile0]\nPath=aaa.first\n\n[Profile1]\nPath=bbb.default\nDefault=1\n",
    )
    assert find_default_profile(tmp_path) == tmp_path / "bbb.default"


def test_find_profile_falls_back_to_first_profile(tmp_path):
    _write_ini(tmp_path, "[Profile0]\nPath=aaa.first\n\n[Profile1]\nPath=bbb.second\n")
    assert find_default_profile(tmp_path) == tmp_path / "aaa.first"


def test_find_profile_absolute_path_respected(tmp_path):
    abs_dir = tmp_path / "elsewhere" / "prof"
    _write_ini(tmp_path, f"[Profile0]\nPath={abs_dir}\nDefault=1\n")
    assert find_default_profile(tmp_path) == abs_dir


# ── apply / revert / verify ─────────────────────────────────────────────


@pytest.fixture
def env(tmp_path, monkeypatch):
    command_file = tmp_path / "config" / "np-command.json"
    ff_root = tmp_path / "mozilla" / "firefox"
    profile = ff_root / "abc.default"
    profile.mkdir(parents=True)
    _write_ini(ff_root, "[Profile0]\nPath=abc.default\nDefault=1\n")

    monkeypatch.setattr(ff_mod, "_COMMAND_FILE", command_file)
    monkeypatch.setattr(ff_mod, "_FF_ROOT", ff_root)
    # _install_user_chrome calls find_default_profile() with no arg, so its
    # default (_FF_ROOT bound at def time) wins over the attr patch above —
    # patch the function itself to point at our tmp profile.
    monkeypatch.setattr(ff_mod, "find_default_profile", lambda *a, **k: profile)
    # Keep gsettings out of the test — pin deterministic brightness values.
    monkeypatch.setattr(ff_mod, "_read_brightness", lambda: 0.7)
    monkeypatch.setattr(ff_mod, "_read_video_brightness", lambda: 0.4)
    return SimpleNamespace(command_file=command_file, ff_root=ff_root, profile=profile)


def test_apply_writes_command_with_both_brightnesses(env):
    FirefoxAdapter().apply(NIGHTPANEL)
    cmd = json.loads(env.command_file.read_text())
    assert cmd["action"] == "apply"
    assert cmd["brightness"] == 0.7
    assert cmd["videoBrightness"] == 0.4


def test_apply_materializes_userchrome_and_pref(env):
    FirefoxAdapter().apply(NIGHTPANEL)
    user_chrome = env.profile / "chrome" / "userChrome.css"
    user_js = env.profile / "user.js"
    assert user_chrome.exists()
    assert "nightpanel" in user_chrome.read_text().lower()
    assert "toolkit.legacyUserProfileCustomizations.stylesheets" in user_js.read_text()


def test_apply_does_not_duplicate_pref(env):
    adapter = FirefoxAdapter()
    adapter.apply(NIGHTPANEL)
    adapter.apply(NIGHTPANEL)
    pref_line = 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets"'
    assert (env.profile / "user.js").read_text().count(pref_line) == 1


def test_verify_tracks_command_action(env):
    adapter = FirefoxAdapter()
    assert adapter.verify("off") is True  # no command file yet
    adapter.apply(NIGHTPANEL)
    assert adapter.verify("on") is True
    adapter.revert({})
    assert adapter.verify("off") is True
    assert adapter.verify("on") is False


def test_verify_off_on_corrupt_command_file(env):
    env.command_file.parent.mkdir(parents=True, exist_ok=True)
    env.command_file.write_text("{not valid json")
    assert FirefoxAdapter().verify("off") is True


def test_revert_writes_revert_action(env):
    FirefoxAdapter().revert({})
    cmd = json.loads(env.command_file.read_text())
    assert cmd["action"] == "revert"


def test_install_always_true(env):
    assert FirefoxAdapter().installed() is True
