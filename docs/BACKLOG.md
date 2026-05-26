# Nightpanel Backlog

Prioritized bugs, features, and improvements.

Two halves:
- **Theming / orchestrator layer** (post-rename) — palette, adapters, GNOME shell extension, Firefox bridge.
- **Keyboard / preset layer** (pre-rename, formerly DailyDriver) — visual keyboard config, presets, cheat sheet.

Scope of latest audit (2026-05-25): orchestrator + adapter layer only. `window.py` (1236 lines), `services/theme_service.py` (416 lines), `player_app.py`, and all renderer files **not audited** — findings limited to what was read.

---

## Theming layer — P0 (correctness / shipping blockers)

- [ ] **Hardcoded Firefox profile** — `adapters/firefox.py:21` and `services/nightpanel_orchestrator.py:41` both literal `x7sc2l5o.default-esr`. Firefox adapter is a no-op on any other machine. Discover via `~/.mozilla/firefox/profiles.ini` (`[Install*]` → Default key, or first `Default=1` profile).
- [ ] **Silently flips `xpinstall.signatures.required=false`** — `nightpanel_orchestrator.py:268` weakens Firefox security globally as a side effect of installing the bridge extension. Either require user confirmation, sign the extension, or document this in big letters before install.
- [ ] **`apply()` touches `ACTIVE_FILE` even if every adapter raised** — `nightpanel_orchestrator.py:98–99`. State machine reports "on" while nothing changed. Should require ≥1 successful adapter to mark active, or surface partial-failure state.
- [ ] **`_strip_np_block` relies on literal `"opacity: 0.35;\n}"` end-marker** — `adapters/gnome.py:125`. The day someone tweaks the gtk renderer's trailing rule (already happened with the recent `pkill nautilus` work), revert silently strips the wrong byte range and corrupts the user's `gtk.css`. Use a paired comment sentinel `/* nightpanel:start */ … /* nightpanel:end */`.
- [ ] **Dead DailyDriver shell extension at `/extension/`** — `metadata.json` is the old `dailydriver-cheatsheet` UUID; nothing in `src/` references it; the new nightpanel extension is at `~/.local/share/gnome-shell/extensions/nightpanel@nightpanel/` (and presumably `src/nightpanel/shell-extension/...` per the install function). Delete `/extension/`. Confusing cruft for any contributor.
- [ ] **CLAUDE.md / docs/STATUS.md / docs/BACKLOG.md describe DailyDriver, not nightpanel** — the rename committed but docs weren't updated. New contributors will get false-rooted assumptions about scope/architecture.

## Theming layer — P0.5 (UX surfacing)

- [ ] **Add gws status row to the Setup tab.** Analogous to the existing Tiling Assistant status row in `views/setup_view.py`. Should show: binary present (`shutil.which("gws")`), state file present (`~/.gws/todo.state`), current theme name from snapshot, and whether NP is currently driving it (`adapter.verify("on")`). Makes the new gws adapter discoverable in the UI rather than buried in the orchestrator's adapter list.

## Theming layer — P1 (correctness / UX)

- [ ] **No lock on concurrent `apply()`/`revert()`** — extension double-click or rapid CLI toggle races on `nightpanel-state.json`. Last writer wins; snapshot for the loser may be the post-apply state (the exact bug we just patched). `fcntl.flock` on the state file would fix it.
- [ ] **`pkill nautilus` on every gtk.css apply AND revert** — `adapters/gnome.py:107, 147`. User loses every Nautilus tab/window/sidebar state on every theme toggle. Either skip the kill (GTK picks up CSS on its own restart) or signal GTK to reload without killing.
- [ ] **No surfacing of adapter failures to the UI** — adapters fail via `_LOG.warning`; the panel button reads the sentinel file. If 6/7 adapters silently failed, the button still says "active." Add a per-adapter status to the sentinel or a `np-status.json` the extension can render.
- [ ] **`TmuxAdapter.snapshot()` returns `{}`; `FirefoxAdapter.snapshot()` returns `{}`** — both violate the adapter contract ("capture state so revert can restore it"). Tmux revert source-files `~/.tmux.conf` blindly; if the user's tmux config changed since apply, revert applies the *current* config, not the pre-apply config. Capture a real pre-state for each.
- [ ] **Two extension dirs in repo + no rebuild script for the Firefox XPI** — `extension/` (dead) and `src/nightpanel/shell-extension/...` (per the install function). The XPI at `~/.config/nightpanel/nightpanel-bridge.xpi` is hand-zipped from `src/nightpanel/services/firefox-extension/`. Add a `scripts/build-extensions.sh` so the artifact is reproducible.
- [ ] **Zero test coverage on the entire new theming layer** — no tests for orchestrator, any adapter, palette, or any renderer. The existing 220+ tests are all for the legacy keyboard half. Even one happy-path test per adapter (apply→verify("on") → revert→verify("off") on a tmp dir) would catch regressions.

## Theming layer — P2 (DX / code quality)

- [ ] **Extract shared helpers** — `subprocess.run(..., capture_output=True, text=True, timeout=5)` redefined as `_run` in 5+ files; `_gsettings_get`/`_gsettings_set` defined inline in multiple places; `Path.home() / ".config" / "nightpanel"` constructed in 7+ files. Single `_util.py` + `_paths.py`.
- [ ] **Inject paths into adapters instead of module-level constants** — every adapter has `_CFG = Path.home() / ...` at import time. Tests have to monkey-patch globals. A `Paths` dataclass passed via constructor makes everything trivially testable.
- [ ] **`Adapter.name` is class-attr without default + no ABC enforcement** — subclass forgetting to set `name` → runtime `AttributeError` mid-apply. Either default `name = "<unset>"` with a runtime check, or enforce via `__init_subclass__`.
- [ ] **`_load_state()` swallows JSON decode errors and returns `{}`** — corrupt state file = silent no-op revert. Should warn loudly so the user knows their snapshot is gone.
- [ ] **`np-host.py` busy-polls `np-command.json` every 500ms** — one Python process per Firefox session, alive for the whole session, polling on disk. `Gio.FileMonitor` or `inotify` would eliminate the poll.
- [ ] **`np-host.py` lives in `services/` but has a hyphen in its filename** — can't be imported; only runs as a script. Either move to `scripts/` or rename to `np_host.py`. Also: it's copied to `~/.config/nightpanel/` at install time, detaching it from the source version — no upgrade signal when the source changes.
- [ ] **`nvim` adapter socket discovery patterns are approximate** — `/tmp/nvim*/0`, `/run/user/*/nvim.*`, `~/.local/state/nvim/*.sock`. Modern nvim uses `$XDG_RUNTIME_DIR/nvim.<pid>.0`. Validate against actual installs.
- [ ] **`install_gnome_extension()` always runs `gnome-extensions enable`** — coercive if the user explicitly disabled it. Check the explicit-disable list first.

---

## Keyboard layer — P0 (legacy DailyDriver)

- [ ] Screenshots for hypr / apple presets don't work — should show equivalent of apple keys
- [ ] `<D-/>` shortcut bug (slash key with Super modifier)
- [ ] Fix 6 failing custom keybinding tests (mock setup refinement needed)

**Completed:**
- [x] Test compositor shortcut grabs on a live GNOME Wayland session (tested, doesn't work — GNOME limitation)
- [x] Update `ShortcutGrabberService` to detect GNOME and skip portal attempt (`services/backends/detection.py`)
- [x] Capture screenshots and finalize AppStream metainfo for Flathub submission (`data/io.github.gregfelice.DailyDriver.metainfo.xml.in`)

## Keyboard layer — P1

- [ ] Flathub beta channel submission (PR #7735 pending review)
- [ ] Research GNOME Shell extension approach for global shortcuts (extension exposes GrabAccelerator to DailyDriver via custom D-Bus interface)
- [ ] Background daemon mode (`dailydriver --daemon`) for persistent shortcut grabs (useful when GlobalShortcuts works)
- [ ] Make detection methods on `GSettingsService` public API (`_detect_terminal` etc.)
- [ ] Add "Shortcut Status" indicator in UI showing compositor grab state (and GNOME limitation warning)
- [ ] Integration test for `ShortcutGrabberService` with `python-dbusmock`
- [ ] GNOME schema version validation in preset tests
- [ ] Add CI notification (GitHub status badge)

## Keyboard layer — P2

- [ ] KDE Plasma backend
- [ ] Hyprland backend
- [ ] AUR PKGBUILD
- [ ] Snap Store packaging
- [ ] GNOME Circle application
- [ ] Auto-update checker for new versions
- [ ] Per-shortcut compositor grab toggle in UI
- [ ] Monitor GNOME GlobalShortcuts portal implementation progress
- [ ] Custom shortcut editor (create new shortcuts)
- [ ] Import/export profiles

## Keyboard layer — P3

- [ ] COPR (Fedora) packaging
- [ ] Keyboard layout auto-detection (QWERTY/Dvorak/Colemak)
- [ ] User-contributed preset marketplace / sharing
- [ ] Multi-monitor shortcut awareness

---

## Out of scope of latest audit (worth a follow-up pass)

- `src/nightpanel/window.py` (1236 lines) — flagged in CLAUDE.md as "handles all views"; almost certainly wants splitting.
- `src/nightpanel/services/theme_service.py` (416 lines) — relationship to the new palette/renderer layer unclear; possible duplication.
- `src/nightpanel/player_app.py` (304 lines) — Spotify player UI; touched recently.
- `src/nightpanel/renderers/{alacritty,emacs,firefox_chrome,player,tmux}.py` — only `gtk.py` was read this pass.
