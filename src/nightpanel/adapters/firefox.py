# SPDX-License-Identifier: GPL-3.0-or-later
"""Firefox adapter — writes the command JSON the native host polls, plus
manages userChrome.css (the chrome styling absorbed from the old slimfox
project)."""

from __future__ import annotations

import configparser
import json
import logging
import subprocess
from pathlib import Path
from typing import Literal

from ..palette import Palette
from ..renderers import firefox_chrome as _chrome_renderer
from .base import Adapter

_LOG = logging.getLogger(__name__)

_COMMAND_FILE = Path.home() / ".config" / "nightpanel" / "np-command.json"
_FF_ROOT = Path.home() / ".mozilla" / "firefox"
_CHROME_PREF = "toolkit.legacyUserProfileCustomizations.stylesheets"

_MARK_BEGIN = "/* >>> nightpanel managed — do not edit between markers <<< */"
_MARK_END = "/* <<< nightpanel managed end >>> */"

# Prefs the chrome CSS depends on. The userChrome rules keep the vertical-tabs
# rail visible, which only exists when the sidebar revamp is on — so nightpanel
# owns these rather than inheriting them from slimfox's user.js block.
_MANAGED_PREFS = f"""\
{_MARK_BEGIN}
user_pref("{_CHROME_PREF}", true);
// tab management: native vertical-tabs rail, expanded via Ctrl+Alt+Z.
// expandOnHover is OFF on purpose: it is mutually exclusive with the
// manual/keyboard expand toggle, and enabling it makes Ctrl+Alt+Z a no-op.
user_pref("sidebar.revamp", true);
user_pref("sidebar.verticalTabs", true);
user_pref("sidebar.visibility", "always-show");
user_pref("sidebar.expandOnHover", false);
{_MARK_END}
"""


def _strip_managed_block(text: str) -> str:
    """Drop every prior nightpanel block, keeping the rest of user.js intact."""
    out, skip = [], False
    for line in text.splitlines(keepends=True):
        if _MARK_BEGIN in line:
            skip = True
        if not skip:
            out.append(line)
        if _MARK_END in line:
            skip = False
    return "".join(out)


def find_default_profile(ff_root: Path = _FF_ROOT) -> Path | None:
    """Locate the default Firefox profile dir from ``profiles.ini``.

    Priority (matches what Firefox itself picks):
      1. ``[Install*]`` section's ``Default=`` value (the active install's profile)
      2. First ``[Profile*]`` section with ``Default=1``
      3. First ``[Profile*]`` section in file order

    Returns the absolute Path, or None if no profile is discoverable.
    """
    ini = ff_root / "profiles.ini"
    if not ini.exists():
        return None
    cp = configparser.ConfigParser()
    try:
        cp.read(ini)
    except configparser.Error as e:
        _LOG.debug("nightpanel: profiles.ini parse failed: %s", e)
        return None

    def _resolve(rel_or_abs: str) -> Path:
        p = Path(rel_or_abs)
        return p if p.is_absolute() else ff_root / p

    for section in cp.sections():
        if section.startswith("Install") and cp[section].get("Default"):
            return _resolve(cp[section]["Default"])

    profiles = [s for s in cp.sections() if s.startswith("Profile")]
    for section in profiles:
        if cp[section].get("Default") == "1" and cp[section].get("Path"):
            return _resolve(cp[section]["Path"])
    for section in profiles:
        if cp[section].get("Path"):
            return _resolve(cp[section]["Path"])
    return None


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=5)


def _read_brightness() -> float:
    """Read brightness from gsettings; clamp to a sane range."""
    try:
        r = _run(["gsettings", "get", "io.github.gregfelice.Nightpanel", "theme-brightness"])
        if r.returncode == 0:
            return max(0.3, min(1.5, float(r.stdout.strip())))
    except Exception:
        pass
    return 0.9


def _read_video_brightness() -> float:
    """Read the dedicated <video> brightness from gsettings; clamp to range.

    Crash-safe via subprocess (unlike in-process Gio.Settings.get_double, which
    aborts the process on a missing key): if the schema predates this key,
    `gsettings get` returns non-zero and we fall back to 1.0 (untouched)."""
    try:
        r = _run(["gsettings", "get", "io.github.gregfelice.Nightpanel", "video-brightness"])
        if r.returncode == 0:
            return max(0.1, min(1.0, float(r.stdout.strip())))
    except Exception:
        pass
    return 1.0


class FirefoxAdapter(Adapter):
    name = "firefox"

    def installed(self) -> bool:
        # The extension may be installed even when firefox isn't running, and
        # the command file is harmless if nothing reads it. Always engage.
        return True

    def snapshot(self) -> dict:
        # The extension reverts via the next command; nothing to capture here.
        return {}

    def apply(self, palette: Palette) -> None:
        self._write(
            {
                "action": "apply",
                "brightness": _read_brightness(),
                "videoBrightness": _read_video_brightness(),
            }
        )
        # Re-sync userChrome.css from the palette on every apply so palette
        # edits propagate. Firefox requires a full restart to pick the change
        # up (it doesn't hot-reload chrome.css), but the file is correct at
        # rest. Idempotent.
        self._install_user_chrome(palette)

    def revert(self, snapshot: dict) -> None:
        self._write({"action": "revert", "brightness": 0.9})
        # Leave userChrome.css in place — it's not a per-toggle concern. To
        # fully revert chrome styling, the user removes the file manually or
        # runs the slimfox uninstall script (which still works for now).

    def verify(self, expected: Literal["on", "off"]) -> bool:
        try:
            cmd = json.loads(_COMMAND_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            return expected == "off"
        on = cmd.get("action") == "apply"
        return on if expected == "on" else not on

    # ── helpers ──
    def _write(self, payload: dict) -> None:
        try:
            _COMMAND_FILE.parent.mkdir(parents=True, exist_ok=True)
            _COMMAND_FILE.write_text(json.dumps(payload))
        except OSError as e:
            _LOG.warning("nightpanel: firefox command write failed: %s", e)

    def _install_user_chrome(self, palette: Palette) -> None:
        """Write userChrome.css from the palette and ensure the FF pref that
        lets userChrome load is set. Replaces the old slimfox installer."""
        profile = find_default_profile()
        if profile is None or not profile.exists():
            _LOG.debug("nightpanel: no Firefox profile found, skipping userChrome")
            return
        user_chrome = profile / "chrome" / "userChrome.css"
        user_js = profile / "user.js"
        try:
            user_chrome.parent.mkdir(parents=True, exist_ok=True)
            user_chrome.write_text(_chrome_renderer.render(palette))
        except OSError as e:
            _LOG.warning("nightpanel: userChrome.css write failed: %s", e)
            return
        try:
            existing = user_js.read_text() if user_js.exists() else ""
            desired = _strip_managed_block(existing).rstrip("\n") + "\n" + _MANAGED_PREFS
            if desired != existing:
                user_js.write_text(desired)
        except OSError as e:
            _LOG.warning("nightpanel: user.js update failed: %s", e)
