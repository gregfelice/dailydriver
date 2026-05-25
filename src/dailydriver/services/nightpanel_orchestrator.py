# SPDX-License-Identifier: GPL-3.0-or-later
"""NightpanelOrchestrator — applies / reverts the nightpanel scheme across all system tools.

Applies:   alacritty theme import, tmux palette override, nvim colorscheme, GNOME gsettings
Reverts:   snapshots pre-apply state to ~/.config/dailydriver/nightpanel-state.json and restores it

Live sessions are updated where the tool supports it (tmux source-file, nvim --server).
Each tool method fails silently — nightpanel still engages even if one tool isn't installed.
"""

from __future__ import annotations

import glob
import json
import logging
import re
import subprocess
from pathlib import Path

_LOG = logging.getLogger(__name__)

_STATE_PATH         = Path.home() / ".config" / "dailydriver" / "nightpanel-state.json"
_ACTIVE_FILE        = Path.home() / ".config" / "dailydriver" / "nightpanel-active"
_NP_TMUX            = Path.home() / ".config" / "dailydriver" / "themes" / "tmux-nightpanel.conf"
_NP_ALACRITTY_THEME = Path.home() / ".config" / "alacritty" / "themes" / "themes" / "nightpanel.toml"
_ALACRITTY_CFG      = Path.home() / ".config" / "alacritty" / "alacritty.toml"
_TMUX_CONF          = Path.home() / ".tmux.conf"
# Written to make nightpanel the active theme for every new nvim session; deleted on revert.
_NVIM_AFTER         = Path.home() / ".config" / "nvim" / "after" / "plugin" / "nightpanel_active.lua"

# Firefox bridge
_NP_COMMAND         = Path.home() / ".config" / "dailydriver" / "np-command.json"
_NP_HOST_SRC        = Path(__file__).parent / "np-host.py"
_NP_HOST_DEST       = Path.home() / ".config" / "dailydriver" / "np-host.py"
_NM_MANIFEST        = Path.home() / ".mozilla" / "native-messaging-hosts" / "nightpanel.json"
_FF_PROFILE         = Path.home() / ".mozilla" / "firefox" / "x7sc2l5o.default-esr"
_EXT_SRC            = Path(__file__).parent / "firefox-extension"
_EXT_ID             = "nightpanel-bridge@dailydriver"


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=5, **kwargs)


class NightpanelOrchestrator:
    """Applies and reverts nightpanel scheme across system tools."""

    # ── Public API ────────────────────────────────────────────────

    def apply(self) -> None:
        """Snapshot current state then apply nightpanel to all tools."""
        self._save_state()
        self._apply_alacritty()
        self._apply_tmux()
        self._apply_nvim()
        self._apply_gnome()
        self._apply_firefox()
        _ACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ACTIVE_FILE.touch()

    def revert(self) -> None:
        """Restore all tools to the pre-nightpanel state."""
        state = self._load_state()
        self._revert_alacritty(state)
        self._revert_tmux()
        self._revert_nvim(state)
        self._revert_gnome(state)
        self._revert_firefox()
        _ACTIVE_FILE.unlink(missing_ok=True)

    def install_gnome_extension(self) -> bool:
        """Copy the GNOME Shell extension files and enable the extension.

        Returns True if anything changed. On GNOME 45+, enable takes effect
        immediately without a shell restart.
        """
        import shutil
        ext_src  = Path(__file__).parent.parent.parent.parent.parent / \
                   ".local" / "share" / "gnome-shell" / "extensions" / "nightpanel@dailydriver"
        # Prefer the already-installed path; fall back to package-bundled copy
        # (during dev the files are written directly to ~/.local/share/... above)
        ext_dest = Path.home() / ".local" / "share" / "gnome-shell" / \
                   "extensions" / "nightpanel@dailydriver"

        changed = False
        try:
            if ext_src.exists() and ext_src != ext_dest:
                ext_dest.mkdir(parents=True, exist_ok=True)
                for f in ext_src.iterdir():
                    dst = ext_dest / f.name
                    if not dst.exists() or dst.read_bytes() != f.read_bytes():
                        shutil.copy2(f, dst)
                        changed = True

            # Enable via gnome-extensions CLI (no shell restart needed on GNOME 45+)
            r = _run(["gnome-extensions", "enable", "nightpanel@dailydriver"])
            if r.returncode != 0:
                _LOG.warning("nightpanel: gnome-extensions enable: %s", r.stderr.strip())
            else:
                changed = True
        except Exception as e:
            _LOG.warning("nightpanel: GNOME extension install failed: %s", e)
        return changed

    def install_bridge(self) -> bool:
        """Install the Firefox native messaging host and companion extension.

        Safe to call multiple times — idempotent.
        Returns True if anything changed (Firefox restart needed).
        """
        changed = False
        changed |= self._install_native_host()
        changed |= self._install_extension()
        return changed

    # ── State snapshot ────────────────────────────────────────────

    def _save_state(self) -> None:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        state: dict = {}

        # alacritty — record current import block if it exists
        state["alacritty_import"] = self._read_alacritty_import()

        # nvim — record current colorscheme name
        state["nvim_colorscheme"] = "tokyonight"   # default fallback
        cs = self._query_nvim_colorscheme()
        if cs:
            state["nvim_colorscheme"] = cs

        # GNOME
        state["gnome_color_scheme"] = self._gsettings_get(
            "org.gnome.desktop.interface", "color-scheme"
        )
        state["gnome_bg_uri"] = self._gsettings_get(
            "org.gnome.desktop.background", "picture-uri"
        )
        state["gnome_bg_uri_dark"] = self._gsettings_get(
            "org.gnome.desktop.background", "picture-uri-dark"
        )
        state["gnome_bg_color"] = self._gsettings_get(
            "org.gnome.desktop.background", "primary-color"
        )
        state["gnome_bg_options"] = self._gsettings_get(
            "org.gnome.desktop.background", "picture-options"
        )

        try:
            _STATE_PATH.write_text(json.dumps(state, indent=2))
        except OSError as e:
            _LOG.warning("nightpanel: could not save state: %s", e)

    def _load_state(self) -> dict:
        try:
            return json.loads(_STATE_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    # ── Alacritty ─────────────────────────────────────────────────

    def _read_alacritty_import(self) -> str | None:
        """Return the current import line for state snapshot. Returns None if no real value."""
        if not _ALACRITTY_CFG.exists():
            return None
        text = _ALACRITTY_CFG.read_text()
        # New format: import inside [general] section
        general = re.search(r"^\[general\][^\[]*", text, re.MULTILINE | re.DOTALL)
        if general:
            m = re.search(r"^[ \t]*(import\s*=\s*\[.+\])[ \t]*$", general.group(0), re.MULTILINE)
            if m:
                return m.group(1).strip()
        # Old top-level format (alacritty < 0.13)
        m = re.search(r"^(import\s*=\s*\[.+\])[ \t]*$", text, re.MULTILINE)
        return m.group(1) if m else None

    def _apply_alacritty(self) -> None:
        import_line = f'import = ["{_NP_ALACRITTY_THEME}"]'
        try:
            text = _ALACRITTY_CFG.read_text() if _ALACRITTY_CFG.exists() else ""
            # Remove any existing import line (top-level or in [general])
            text = re.sub(r"^[ \t]*import\s*=.*\n?", "", text, flags=re.MULTILINE)
            if re.search(r"^\[general\]", text, re.MULTILINE):
                text = re.sub(r"^(\[general\][ \t]*)$", rf"\1\n{import_line}", text, flags=re.MULTILINE)
            else:
                text = f"[general]\n{import_line}\n\n" + text.lstrip()
            _ALACRITTY_CFG.write_text(text)
        except Exception as e:
            _LOG.warning("nightpanel: alacritty apply failed: %s", e)

    def _revert_alacritty(self, state: dict) -> None:
        try:
            prev_import = state.get("alacritty_import")
            if not _ALACRITTY_CFG.exists():
                return
            text = _ALACRITTY_CFG.read_text()
            # Remove nightpanel import line wherever it lives
            text = re.sub(r"^[ \t]*import\s*=.*\n?", "", text, flags=re.MULTILINE)
            # Only restore if prev_import is a real value (contains an array)
            if prev_import and "[" in prev_import:
                if re.search(r"^\[general\]", text, re.MULTILINE):
                    text = re.sub(r"^(\[general\][ \t]*)$", rf"\1\n{prev_import}", text, flags=re.MULTILINE)
                else:
                    text = f"[general]\n{prev_import}\n\n" + text.lstrip()
            _ALACRITTY_CFG.write_text(text)
        except Exception as e:
            _LOG.warning("nightpanel: alacritty revert failed: %s", e)

    # ── tmux ──────────────────────────────────────────────────────

    def _apply_tmux(self) -> None:
        try:
            _run(["tmux", "source-file", str(_NP_TMUX)])
        except Exception as e:
            _LOG.debug("nightpanel: tmux not running or not found: %s", e)

    def _revert_tmux(self) -> None:
        try:
            _run(["tmux", "source-file", str(_TMUX_CONF)])
        except Exception as e:
            _LOG.debug("nightpanel: tmux revert skipped: %s", e)

    # ── nvim ──────────────────────────────────────────────────────

    def _nvim_sockets(self) -> list[str]:
        patterns = [
            "/tmp/nvim*/0",
            "/run/user/*/nvim.*",
            str(Path.home() / ".local" / "state" / "nvim" / "*.sock"),
        ]
        sockets = []
        for pat in patterns:
            sockets.extend(glob.glob(pat))
        return sockets

    def _query_nvim_colorscheme(self) -> str | None:
        for sock in self._nvim_sockets():
            try:
                r = _run(["nvim", "--server", sock, "--remote-expr", "g:colors_name"])
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip()
            except Exception:
                continue
        return None

    def _send_nvim_cmd(self, cmd: str) -> None:
        for sock in self._nvim_sockets():
            try:
                _run(["nvim", "--server", sock, "--remote-send",
                      f"<Esc>:silent! {cmd}<CR>"])
            except Exception:
                continue

    def _apply_nvim(self) -> None:
        # Persist for new sessions via after/plugin/ override
        try:
            _NVIM_AFTER.parent.mkdir(parents=True, exist_ok=True)
            _NVIM_AFTER.write_text("vim.cmd('colorscheme nightpanel')\n")
        except OSError as e:
            _LOG.warning("nightpanel: nvim after/plugin write failed: %s", e)
        # Apply to live sessions
        self._send_nvim_cmd("colorscheme nightpanel")

    def _revert_nvim(self, state: dict) -> None:
        # Remove the after/plugin override
        try:
            _NVIM_AFTER.unlink(missing_ok=True)
        except OSError as e:
            _LOG.warning("nightpanel: nvim after/plugin remove failed: %s", e)
        # Revert live sessions
        prev = state.get("nvim_colorscheme", "tokyonight")
        self._send_nvim_cmd(f"colorscheme {prev}")

    # ── Firefox bridge ────────────────────────────────────────────

    def update_brightness(self, brightness: float) -> None:
        """Push a brightness update to Firefox (no-op if nightpanel is not active)."""
        active_file = Path.home() / ".config" / "dailydriver" / "nightpanel-active"
        if active_file.exists():
            self._write_command("apply", brightness=brightness)

    def _write_command(self, action: str, brightness: float = 0.9) -> None:
        """Write a command to np-command.json — native host picks it up and
        forwards to the extension within one poll interval (0.5 s)."""
        try:
            _NP_COMMAND.parent.mkdir(parents=True, exist_ok=True)
            _NP_COMMAND.write_text(json.dumps({"action": action, "brightness": brightness}))
        except OSError as e:
            _LOG.warning("nightpanel: command file write failed: %s", e)

    def _apply_firefox(self) -> None:
        brightness = self._read_brightness_setting()
        self._write_command("apply", brightness=brightness)

    def _revert_firefox(self) -> None:
        self._write_command("revert")

    def _read_brightness_setting(self) -> float:
        try:
            r = _run(["gsettings", "get", "com.dailydriver.dailydriver", "theme-brightness"])
            if r.returncode == 0:
                return max(0.3, min(1.5, float(r.stdout.strip())))
        except Exception:
            pass
        return 0.9

    def _install_native_host(self) -> bool:
        """Copy np-host.py to config dir and write the Firefox NM manifest."""
        try:
            import shutil
            _NP_HOST_DEST.parent.mkdir(parents=True, exist_ok=True)

            # Copy host script
            changed = not _NP_HOST_DEST.exists() or \
                      _NP_HOST_DEST.read_bytes() != _NP_HOST_SRC.read_bytes()
            if changed:
                shutil.copy2(_NP_HOST_SRC, _NP_HOST_DEST)
                _NP_HOST_DEST.chmod(0o755)

            # Write manifest
            manifest = {
                "name": "nightpanel",
                "description": "nightpanel bridge — connects dailydriver to Firefox",
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
        """Install the companion extension to the Firefox ESR profile."""
        try:
            import shutil
            ext_dest = _FF_PROFILE / "extensions" / _EXT_ID
            if not _EXT_SRC.exists():
                _LOG.warning("nightpanel: extension source not found at %s", _EXT_SRC)
                return False

            # Copy extension files
            changed = not ext_dest.exists()
            ext_dest.mkdir(parents=True, exist_ok=True)
            for src_file in _EXT_SRC.iterdir():
                dst = ext_dest / src_file.name
                if not dst.exists() or dst.read_bytes() != src_file.read_bytes():
                    shutil.copy2(src_file, dst)
                    changed = True

            # Allow unsigned extensions in user.js
            changed |= self._ensure_user_js_pref(
                "xpinstall.signatures.required", "false"
            )
            return changed
        except Exception as e:
            _LOG.warning("nightpanel: extension install failed: %s", e)
            return False

    def _ensure_user_js_pref(self, key: str, value: str) -> bool:
        """Add a user_pref line to user.js if not already present."""
        user_js = _FF_PROFILE / "user.js"
        line = f'user_pref("{key}", {value});'
        try:
            existing = user_js.read_text() if user_js.exists() else ""
            if f'user_pref("{key}"' in existing:
                return False
            with user_js.open("a") as f:
                f.write(f"\n{line}\n")
            return True
        except OSError as e:
            _LOG.warning("nightpanel: user.js update failed: %s", e)
            return False

    # ── GNOME ─────────────────────────────────────────────────────

    def _gsettings_get(self, schema: str, key: str) -> str | None:
        try:
            r = _run(["gsettings", "get", schema, key])
            return r.stdout.strip().strip("'") if r.returncode == 0 else None
        except Exception:
            return None

    def _gsettings_set(self, schema: str, key: str, value: str) -> None:
        try:
            _run(["gsettings", "set", schema, key, value])
        except Exception as e:
            _LOG.debug("nightpanel: gsettings %s %s failed: %s", schema, key, e)

    def _apply_gnome(self) -> None:
        self._gsettings_set("org.gnome.desktop.interface", "color-scheme", "prefer-dark")
        # Solid near-black background — slightly lighter than pure black
        self._gsettings_set("org.gnome.desktop.background", "picture-options", "none")
        self._gsettings_set("org.gnome.desktop.background", "primary-color", "#0D0D0D")
        self._gsettings_set("org.gnome.desktop.background", "picture-uri", "")
        self._gsettings_set("org.gnome.desktop.background", "picture-uri-dark", "")

    def _revert_gnome(self, state: dict) -> None:
        cs = state.get("gnome_color_scheme", "default")
        if cs:
            self._gsettings_set("org.gnome.desktop.interface", "color-scheme", cs)
        bg_uri = state.get("gnome_bg_uri", "")
        bg_uri_dark = state.get("gnome_bg_uri_dark", "")
        bg_color = state.get("gnome_bg_color", "")
        bg_options = state.get("gnome_bg_options", "zoom")
        if bg_uri:
            self._gsettings_set("org.gnome.desktop.background", "picture-uri", bg_uri)
        if bg_uri_dark:
            self._gsettings_set("org.gnome.desktop.background", "picture-uri-dark", bg_uri_dark)
        if bg_color:
            self._gsettings_set("org.gnome.desktop.background", "primary-color", bg_color)
        self._gsettings_set("org.gnome.desktop.background", "picture-options", bg_options)
