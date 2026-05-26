# SPDX-License-Identifier: GPL-3.0-or-later
"""NightpanelOrchestrator — drives the registered Adapters on apply / revert.

Each Adapter (alacritty, tmux, nvim, gnome, firefox …) owns its own state
shape. The orchestrator just iterates the list, namespacing snapshots under
the adapter's name in a single JSON file. Adding a new tool means writing
one Adapter subclass and appending it to ``self.adapters``.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from ..adapters import (
    Adapter,
    AlacrittyAdapter,
    ClaudeCodeAdapter,
    EmacsAdapter,
    FirefoxAdapter,
    GnomeAdapter,
    GwsAdapter,
    NvimAdapter,
    TmuxAdapter,
)
from ..adapters.firefox import find_default_profile as _find_ff_profile
from ..palette import NIGHTPANEL, Palette

_LOG = logging.getLogger(__name__)

_STATE_PATH = Path.home() / ".config" / "nightpanel" / "nightpanel-state.json"
_ACTIVE_FILE = Path.home() / ".config" / "nightpanel" / "nightpanel-active"
_NP_COMMAND = Path.home() / ".config" / "nightpanel" / "np-command.json"

# Firefox bridge install paths
_NP_HOST_SRC = Path(__file__).parent / "np-host.py"
_NP_HOST_DEST = Path.home() / ".config" / "nightpanel" / "np-host.py"
_NM_MANIFEST = Path.home() / ".mozilla" / "native-messaging-hosts" / "nightpanel.json"
_EXT_SRC = Path(__file__).parent / "firefox-extension"
_EXT_ID = "nightpanel-bridge@nightpanel"

# Security implication shown when the user requests Firefox bridge install.
_FF_CONSENT_TEXT = """\
Installing the nightpanel Firefox bridge requires lowering Firefox's
extension-signature requirement (xpinstall.signatures.required=false).

This is a global Firefox security setting. It applies to ALL extensions
in your profile — not just nightpanel's bridge. While it's set to false,
Firefox will install unsigned extensions, which weakens its security posture.

The bridge extension itself is unsigned because it isn't published on
Mozilla AMO yet. Until it's signed, this pref must stay flipped for the
bridge to load.

To opt in, pass confirmed=True to install_bridge(), e.g.:
    NightpanelOrchestrator().install_bridge(confirmed=True)

Default install does NOT touch Firefox."""


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=5)


class NightpanelOrchestrator:
    """Toggles nightpanel by driving a list of Adapters.

    Call ``apply()`` to engage, ``revert()`` to disengage, ``verify(expected)``
    to confirm each adapter is in the expected state. Pass a custom Palette
    to ``apply()`` to test alternate color schemes.
    """

    def __init__(self, palette: Palette = NIGHTPANEL, adapters: list[Adapter] | None = None):
        self.palette = palette
        self.adapters: list[Adapter] = (
            adapters
            if adapters is not None
            else [
                AlacrittyAdapter(),
                TmuxAdapter(),
                NvimAdapter(),
                EmacsAdapter(),
                ClaudeCodeAdapter(),
                GnomeAdapter(),
                FirefoxAdapter(),
                GwsAdapter(),
            ]
        )

    # ── Public API ────────────────────────────────────────────────

    def apply(self) -> dict[str, bool]:
        """Snapshot current state then apply nightpanel via every adapter.

        Returns a ``{adapter_name: success}`` dict. ACTIVE_FILE is only
        touched if at least one adapter succeeded — otherwise the state
        machine would lie about being on while nothing changed.
        """
        # Only snapshot if not already engaged — protects against double-apply
        # corrupting the saved baseline. Defense in depth: if ACTIVE_FILE went
        # missing while the world is still in nightpanel state (interrupted
        # revert, manual cleanup), trust the existing snapshot over the live
        # world, otherwise we'd capture the applied palette as the baseline.
        if not _ACTIVE_FILE.exists():
            verdict = {a.name: a.verify("on") for a in self._active_adapters()}
            already_on = {k: v for k, v in verdict.items() if v}
            if already_on:
                _LOG.warning(
                    "nightpanel: apply() with no ACTIVE_FILE but adapters look "
                    "already-on (%s) — keeping existing snapshot",
                    already_on,
                )
            else:
                state = {a.name: a.snapshot() for a in self._active_adapters()}
                self._save_state(state)

        outcomes: dict[str, bool] = {}
        for a in self._active_adapters():
            try:
                a.apply(self.palette)
                outcomes[a.name] = True
            except Exception as e:
                _LOG.warning("nightpanel: %s apply failed: %s", a.name, e)
                outcomes[a.name] = False

        if any(outcomes.values()):
            _ACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
            _ACTIVE_FILE.touch()
        else:
            _LOG.error(
                "nightpanel: every adapter failed during apply() — not marking "
                "ACTIVE_FILE so state machine doesn't lie. Outcomes: %s",
                outcomes,
            )
        return outcomes

    def revert(self) -> None:
        """Restore every adapter to its pre-apply state.

        ACTIVE_FILE is unlinked BEFORE the adapter reverts run, not after.
        Reason: adapter reverts take real time (gsettings round-trips, file
        writes, daemon round-trips), and during that window any incoming
        ``update_brightness`` call would see ACTIVE_FILE still present and
        write ``{"action":"apply", ...}`` to np-command.json — re-engaging
        Firefox while the rest of the world is mid-revert. The visible
        symptom was a "goes bright for a sec, then snaps back to dark"
        cycle when toggling off via the panel button while the config app
        was open emitting brightness-slider events on GTK re-layout.
        Unlinking first closes the race.
        """
        _ACTIVE_FILE.unlink(missing_ok=True)
        state = self._load_state()
        for a in self._active_adapters():
            try:
                a.revert(state.get(a.name, {}))
            except Exception as e:
                _LOG.warning("nightpanel: %s revert failed: %s", a.name, e)

    def verify(self, expected: Literal["on", "off"]) -> dict[str, bool]:
        """Return ``{adapter_name: matches_expected}`` for every active adapter."""
        return {a.name: a.verify(expected) for a in self._active_adapters()}

    _BRIGHTNESS_MIN_INTERVAL = 0.1  # seconds; rate-limit FF command writes to 10/s

    def update_brightness(self, brightness: float) -> None:
        """Push a brightness update to the Firefox extension.

        Rate-limited via _BRIGHTNESS_MIN_INTERVAL — without this, every
        Gtk.Scale value-changed signal (which can arrive 30+ times per
        second during drag, or from spurious scroll-wheel events
        passing through the parent ActionRow) writes np-command.json,
        which the native messaging host then forwards to Firefox at
        500ms cadence. The result is observable as a visible
        "cycling" of page brightness when the slider gets even a hint
        of wheel input from anywhere on its surrounding row.
        """
        if not _ACTIVE_FILE.exists():
            return
        import time

        now = time.monotonic()
        if now - getattr(self, "_last_brightness_write", 0.0) < self._BRIGHTNESS_MIN_INTERVAL:
            return
        self._last_brightness_write = now
        try:
            _NP_COMMAND.parent.mkdir(parents=True, exist_ok=True)
            _NP_COMMAND.write_text(json.dumps({"action": "apply", "brightness": brightness}))
        except OSError as e:
            _LOG.warning("nightpanel: brightness update failed: %s", e)

    # ── Install (one-time setup, not part of apply/revert cycle) ──

    def install_gnome_extension(self) -> bool:
        """Install + enable the GNOME Shell panel extension. Also prunes
        ghost entries from the enabled-extensions gsettings list.

        Ghost entries (enabled UUIDs whose dirs are missing) accumulate
        after renames or uninstalls and can prevent newer extensions from
        loading. The prune is cheap (one gsettings read + a few stats) and
        defensive — runs on every install_gnome_extension() call.

        Returns True if anything changed (shell refresh needed).
        """
        changed = False
        ext_src = Path(__file__).parent.parent / "shell-extension" / "nightpanel@nightpanel"
        ext_dest = (
            Path.home()
            / ".local"
            / "share"
            / "gnome-shell"
            / "extensions"
            / "nightpanel@nightpanel"
        )
        try:
            if ext_src.exists() and ext_src != ext_dest:
                ext_dest.mkdir(parents=True, exist_ok=True)
                for f in ext_src.iterdir():
                    dst = ext_dest / f.name
                    if not dst.exists() or dst.read_bytes() != f.read_bytes():
                        shutil.copy2(f, dst)
                        changed = True
            r = _run(["gnome-extensions", "enable", "nightpanel@nightpanel"])
            if r.returncode != 0:
                _LOG.warning("nightpanel: gnome-extensions enable: %s", r.stderr.strip())
            else:
                changed = True
        except Exception as e:
            _LOG.warning("nightpanel: GNOME extension install failed: %s", e)
        if self._prune_ghost_extensions() > 0:
            changed = True
        return changed

    def _prune_ghost_extensions(self) -> int:
        """Remove enabled-extensions entries that point at missing dirs.

        Walks the gsettings ``org.gnome.shell enabled-extensions`` list,
        drops any UUID whose extension dir exists in neither the user
        prefix nor the system prefix, and writes the cleaned list back.
        Returns the number of ghosts removed.
        """
        try:
            r = _run(["gsettings", "get", "org.gnome.shell", "enabled-extensions"])
            if r.returncode != 0:
                return 0
            raw = r.stdout.strip().strip("[]")
            exts = [e.strip().strip("'") for e in raw.split(",") if e.strip()]
        except Exception as e:
            _LOG.debug("nightpanel: prune read failed: %s", e)
            return 0

        home_ext = Path.home() / ".local" / "share" / "gnome-shell" / "extensions"
        sys_ext = Path("/usr/share/gnome-shell/extensions")

        keep, ghosts = [], []
        for ext in exts:
            if not ext:
                continue
            if (home_ext / ext).is_dir() or (sys_ext / ext).is_dir():
                keep.append(ext)
            else:
                ghosts.append(ext)

        if not ghosts:
            return 0

        new_list = "[" + ", ".join(f"'{e}'" for e in keep) + "]"
        try:
            _run(["gsettings", "set", "org.gnome.shell", "enabled-extensions", new_list])
            _LOG.info(
                "nightpanel: pruned %d ghost extension(s): %s", len(ghosts), ", ".join(ghosts)
            )
        except Exception as e:
            _LOG.warning("nightpanel: prune write failed: %s", e)
            return 0
        return len(ghosts)

    def install_bridge(self, *, confirmed: bool = False) -> bool:
        """Install Firefox native-messaging host + companion extension.

        Requires explicit ``confirmed=True`` because the bridge install lowers
        Firefox's global ``xpinstall.signatures.required`` pref. The caller
        (CLI handler, Setup-panel button) is responsible for presenting the
        security implication and obtaining user consent before passing True.

        Idempotent. Returns True if anything changed (Firefox restart needed).
        Raises ConsentRequired if ``confirmed`` is not True.
        """
        if not confirmed:
            raise ConsentRequired(_FF_CONSENT_TEXT)
        if _find_ff_profile() is None:
            _LOG.warning("nightpanel: no Firefox profile found; bridge not installed")
            return False
        return self._install_native_host() | self._install_extension()

    # ── State persistence ────────────────────────────────────────

    def _save_state(self, state: dict) -> None:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            _STATE_PATH.write_text(json.dumps(state, indent=2))
        except OSError as e:
            _LOG.warning("nightpanel: could not save state: %s", e)

    def _load_state(self) -> dict:
        try:
            return json.loads(_STATE_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def _active_adapters(self):
        return [a for a in self.adapters if a.installed()]

    # ── Firefox install helpers ──

    def _install_native_host(self) -> bool:
        try:
            _NP_HOST_DEST.parent.mkdir(parents=True, exist_ok=True)
            changed = (
                not _NP_HOST_DEST.exists()
                or _NP_HOST_DEST.read_bytes() != _NP_HOST_SRC.read_bytes()
            )
            if changed:
                shutil.copy2(_NP_HOST_SRC, _NP_HOST_DEST)
                _NP_HOST_DEST.chmod(0o755)
            manifest = {
                "name": "nightpanel",
                "description": "nightpanel bridge — connects nightpanel to Firefox",
                "path": str(_NP_HOST_DEST),
                "type": "stdio",
                "allowed_extensions": [_EXT_ID],
            }
            manifest_json = json.dumps(manifest, indent=2)
            _NM_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
            if not _NM_MANIFEST.exists() or _NM_MANIFEST.read_text() != manifest_json:
                _NM_MANIFEST.write_text(manifest_json)
                changed = True
            return changed
        except Exception as e:
            _LOG.warning("nightpanel: native host install failed: %s", e)
            return False

    def _install_extension(self) -> bool:
        profile = _find_ff_profile()
        if profile is None:
            _LOG.warning("nightpanel: no Firefox profile discovered, skipping extension")
            return False
        try:
            ext_dest = profile / "extensions" / _EXT_ID
            if not _EXT_SRC.exists():
                _LOG.warning("nightpanel: extension source not found at %s", _EXT_SRC)
                return False
            changed = not ext_dest.exists()
            ext_dest.mkdir(parents=True, exist_ok=True)
            for src_file in _EXT_SRC.iterdir():
                dst = ext_dest / src_file.name
                if not dst.exists() or dst.read_bytes() != src_file.read_bytes():
                    shutil.copy2(src_file, dst)
                    changed = True
            changed |= self._ensure_user_js_pref(profile, "xpinstall.signatures.required", "false")
            return changed
        except Exception as e:
            _LOG.warning("nightpanel: extension install failed: %s", e)
            return False

    def _ensure_user_js_pref(self, profile: Path, key: str, value: str) -> bool:
        user_js = profile / "user.js"
        try:
            existing = user_js.read_text() if user_js.exists() else ""
            if f'user_pref("{key}"' in existing:
                return False
            with user_js.open("a") as f:
                f.write(f'\nuser_pref("{key}", {value});\n')
            return True
        except OSError as e:
            _LOG.warning("nightpanel: user.js update failed: %s", e)
            return False


class ConsentRequired(Exception):
    """Raised when an action requires explicit user consent and didn't get it.

    Carries a human-readable message describing the security/privacy
    implication and how to opt in.
    """
