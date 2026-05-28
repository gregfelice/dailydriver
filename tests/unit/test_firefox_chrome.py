# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the Firefox userChrome.css surface (the absorbed slimfox layer).

This is the SECOND half of nightpanel's Firefox integration:
  - `services/firefox-extension/background.js` styles page CONTENT  (covered in
    the e2e marionette matrix)
  - `renderers/firefox_chrome.py` + `adapters/firefox.py::_install_user_chrome`
    style Firefox's UI CHROME (this file)

Firefox does not hot-reload userChrome.css — it's read once at app startup.
So unit tests verify the *file produced* is correct; visual verification of
the chrome in a running FF is documented in the test plan but is a separate
manual / xvfb-headed step.
"""
from __future__ import annotations

from pathlib import Path

import pytest


# Helper: build a Palette without depending on the canonical one (so a future
# palette tweak doesn't silently break these tests).
def _palette(**overrides):
    from nightpanel.palette import Palette
    return Palette(**overrides) if overrides else Palette()


class TestChromeRendererDeterminism:
    """The renderer must be a pure function of the Palette."""

    def test_same_palette_same_output(self) -> None:
        from nightpanel.renderers import firefox_chrome
        a = firefox_chrome.render(_palette())
        b = firefox_chrome.render(_palette())
        assert a == b

    def test_palette_value_threads_through(self) -> None:
        """`p.border_q` from the palette should appear in the rendered CSS."""
        from nightpanel.renderers import firefox_chrome
        css = firefox_chrome.render(_palette(border_q="#DEADBE"))
        assert "#DEADBE" in css, "border_q palette value did not reach the rendered CSS"

    def test_includes_slimfox_collapse_rule(self) -> None:
        """The absorbed slimfox layer must collapse #navigator-toolbox.

        Without this rule, the chrome is full-size — the slimfox layer is
        the user's whole reason for the userChrome.css existing.
        """
        from nightpanel.renderers import firefox_chrome
        css = firefox_chrome.render(_palette())
        assert "#navigator-toolbox" in css
        assert "max-height" in css and "0 !important" in css

    def test_includes_sharp_corner_rules(self) -> None:
        """nightpanel design language: 0 border-radius everywhere."""
        from nightpanel.renderers import firefox_chrome
        css = firefox_chrome.render(_palette())
        # Every radius knob FF exposes
        for var in [
            "--tab-border-radius",
            "--toolbarbutton-border-radius",
            "--arrowpanel-border-radius",
            "--button-border-radius",
            "--urlbar-border-radius",
            "--identity-box-border-radius",
        ]:
            assert var in css, f"expected radius var {var} missing from rendered chrome"


class TestFirefoxAdapterInstallsUserChrome:
    """The adapter writes userChrome.css to the profile and sets the FF pref."""

    @pytest.fixture
    def fake_profile(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Build a Firefox-like profile tree under tmp_path. Patch
        find_default_profile to return it directly (patching the module-level
        _FF_ROOT alone doesn't work — find_default_profile has _FF_ROOT bound
        as a default argument at import time, before pytest monkeypatching)."""
        ff_root = tmp_path / ".mozilla" / "firefox"
        profile = ff_root / "abc.default-test"
        profile.mkdir(parents=True)
        from nightpanel.adapters import firefox as ff_mod
        monkeypatch.setattr(ff_mod, "find_default_profile", lambda *a, **kw: profile)
        return profile

    def test_apply_writes_userchrome_with_palette_content(self, fake_profile: Path) -> None:
        """apply() should write userChrome.css with the renderer's output."""
        from nightpanel.adapters.firefox import FirefoxAdapter
        from nightpanel.renderers import firefox_chrome
        adapter = FirefoxAdapter()
        palette = _palette()
        adapter.apply(palette)
        user_chrome = fake_profile / "chrome" / "userChrome.css"
        assert user_chrome.exists(), "userChrome.css was not written"
        assert user_chrome.read_text() == firefox_chrome.render(palette)

    def test_apply_sets_legacy_stylesheets_pref(self, fake_profile: Path) -> None:
        """apply() must ensure user.js sets toolkit.legacyUserProfileCustomizations.stylesheets=true.

        Without this pref, Firefox ignores userChrome.css entirely.
        """
        from nightpanel.adapters.firefox import FirefoxAdapter
        FirefoxAdapter().apply(_palette())
        user_js = (fake_profile / "user.js").read_text()
        assert 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true)' in user_js

    def test_apply_pref_idempotent(self, fake_profile: Path) -> None:
        """Calling apply() twice does not duplicate the pref line."""
        from nightpanel.adapters.firefox import FirefoxAdapter
        adapter = FirefoxAdapter()
        adapter.apply(_palette())
        adapter.apply(_palette())
        user_js = (fake_profile / "user.js").read_text()
        # Count occurrences of the pref key — must be exactly 1
        assert user_js.count('toolkit.legacyUserProfileCustomizations.stylesheets') == 1

    def test_apply_preserves_existing_user_js(self, fake_profile: Path) -> None:
        """An existing user.js line (unrelated to NP) must survive apply()."""
        user_js = fake_profile / "user.js"
        user_js.write_text('user_pref("browser.tabs.tabClipWidth", 200);\n')
        from nightpanel.adapters.firefox import FirefoxAdapter
        FirefoxAdapter().apply(_palette())
        text = user_js.read_text()
        assert 'browser.tabs.tabClipWidth' in text
        assert 'toolkit.legacyUserProfileCustomizations.stylesheets' in text

    def test_apply_writes_command_file(self, fake_profile: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """apply() also writes the np-command.json the page-content extension reads.

        This is the OTHER half of the integration — the command file the
        WebExtension's native messaging host polls.
        """
        from nightpanel.adapters import firefox as ff_mod
        cmd_file = tmp_path / "cmd.json"
        monkeypatch.setattr(ff_mod, "_COMMAND_FILE", cmd_file)
        from nightpanel.adapters.firefox import FirefoxAdapter
        # Stub _run so brightness lookup doesn't shell out
        monkeypatch.setattr(ff_mod, "_run", lambda cmd: type("R", (), {"returncode": 1, "stdout": ""})())
        FirefoxAdapter().apply(_palette())
        import json
        cmd = json.loads(cmd_file.read_text())
        assert cmd["action"] == "apply"
        assert isinstance(cmd["brightness"], (int, float))

    def test_revert_writes_command_file_only(self, fake_profile: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """revert() touches np-command.json but DELIBERATELY leaves userChrome.css alone.

        Per the adapter's design note: chrome styling is not per-toggle —
        Firefox needs a full restart to re-read userChrome.css, so we keep
        it as a stable artifact. Revert is just "tell the page-content
        extension to stop applying CSS".
        """
        from nightpanel.adapters import firefox as ff_mod
        cmd_file = tmp_path / "cmd.json"
        monkeypatch.setattr(ff_mod, "_COMMAND_FILE", cmd_file)
        monkeypatch.setattr(ff_mod, "_run", lambda cmd: type("R", (), {"returncode": 1, "stdout": ""})())
        from nightpanel.adapters.firefox import FirefoxAdapter
        adapter = FirefoxAdapter()
        adapter.apply(_palette())                # writes userChrome.css
        before_chrome = (fake_profile / "chrome" / "userChrome.css").read_text()
        adapter.revert({})
        import json
        assert json.loads(cmd_file.read_text())["action"] == "revert"
        # userChrome.css survives revert
        after_chrome = (fake_profile / "chrome" / "userChrome.css").read_text()
        assert before_chrome == after_chrome
