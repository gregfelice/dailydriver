# Nightpanel Backlog

Prioritized bugs, features, and improvements.

Two halves:
- **Theming / orchestrator layer** (post-rename) — palette, adapters, GNOME shell extension, Firefox bridge.
- **Keyboard / preset layer** (pre-rename, formerly DailyDriver) — visual keyboard config, presets, cheat sheet.

Scope of latest audit (2026-05-25, extended through 2026-05-26 by testing): orchestrator + adapter layer. `window.py` (1236 lines), `services/theme_service.py` (416 lines), `player_app.py`, and most renderer files **still not audited**.

---

## Theming layer — P0 (shipping blockers)

**Completed in v0.2.1 → v0.2.5 (private on Forgejo; see [[project-release-state]] for public-push status):**

- [x] **Hardcoded Firefox profile** — replaced with `profiles.ini` discovery in `adapters/firefox.py:find_default_profile()`. (31a86c7)
- [x] **Silent `xpinstall.signatures.required=false` flip** — `install_bridge()` now raises `ConsentRequired` unless `confirmed=True`. (31a86c7)
- [x] **`apply()` lying about state** — only touches `ACTIVE_FILE` if ≥1 adapter succeeded; returns `{adapter: success}` dict. (31a86c7)
- [x] **`_strip_np_block` brittle end-marker** — replaced with paired `/* nightpanel:start */ … /* nightpanel:end */` sentinels. (31a86c7)
- [x] **Dead DailyDriver shell extension at `/extension/`** — deleted. (146ec1f)
- [x] **CLAUDE.md describes DailyDriver** — rewritten for nightpanel post-rename. (146ec1f)
- [x] **CI workflows reference `dailydriver` paths** — swept to `nightpanel`; Snap/Flathub jobs removed. (110ee85, 903ce02)
- [x] **Desktop launcher missing / wrong name** — `Nightpanel.desktop` installed in user prefix + `~/.local/bin/nightpanel` wrapper. (110ee85)
- [x] **Firefox flash on brightness drag** — extension does `insertCSS(new)` before `removeCSS(old)` so the user-origin override never goes empty. (df74eae)
- [x] **`revert()` race window** — `ACTIVE_FILE` unlinked before adapter reverts run so brightness updates mid-revert can't re-engage FF. (a3da2bd)
- [x] **Brightness slider scroll spam** — capture-phase EventControllerScroll consumes wheel events on the slider; 100ms write debounce. (8cb7b96)
- [x] **Multi-instance race** — dropped `NON_UNIQUE` flag; second launches activate existing window. (844aa1a)
- [x] **`GLib.idle_add(orchestrator.apply)` re-firing forever** — apply returns a truthy dict and idle_add interprets that as "stay live." Wrapped in one-shot inner function. (9b6021a) — also captured as [[feedback-glib-idle-add-truthy-return]].
- [x] **Panel button chip background when NP active** — transparent so only NIGHT PANEL text floats on the black panel. (f7df0d5)
- [x] **gws adapter** — new tier-1 adapter writing `theme:Nightpanel` to `~/.gws/todo.state`; matching `Nightpanel` theme added to gws Rust source (`gtd/gws@34c4386`). (fdfe760)

**Still open:**

- [ ] **`docs/STATUS.md` describes DailyDriver** — CLAUDE.md was rewritten but STATUS.md is still stale.

## Theming layer — P0.5 (UX surfacing)

- [ ] **Add gws status row to the Setup tab.** Analogous to the existing Tiling Assistant status row in `views/setup_view.py`. Should show: binary present (`shutil.which("gws")`), state file present (`~/.gws/todo.state`), current theme name from snapshot, and whether NP is currently driving it (`adapter.verify("on")`). Makes the new gws adapter discoverable in the UI rather than buried in the orchestrator's adapter list.

## Theming layer — P1 (correctness / UX)

**Completed:**

- [x] **`pkill nautilus` on every gtk.css apply/revert** — removed. Nautilus colors update on next launch rather than immediately; tradeoff is no destroyed tab state. (31a86c7)
- [x] **Dead `extension/` dir + Firefox XPI rebuild** — dead dir gone; XPI rebuild is a tracked Python one-liner in commit history; live source at `src/nightpanel/shell-extension/`. (5ccb1f7, df74eae)
- [x] **Orchestrator state-machine tests** — 5 happy-path tests covering snapshot guard + apply outcomes + revert. (903ce02)

**Still open:**

- [ ] **Singleton dbus race** — dropping `NON_UNIQUE` mostly fixes duplicates, but TWO instances can still spawn if launched fast enough that neither has registered the dbus name yet. Observed during the Alt+Super+/ binding test on 2026-05-26: two `--cheat-sheet` instances, the second ended up owning the dbus name. Use a startup lock file (or accept the rare race).
- [ ] **No lock on concurrent `apply()`/`revert()`** — singleton mitigates most cases but rapid panel-button + in-app-toggle races still possible. `fcntl.flock` on `nightpanel-state.json` would close it.
- [ ] **No surfacing of adapter failures to the UI** — `apply()` now returns outcomes but nothing renders them. Need `np-status.json` + extension JS to display per-adapter state in the panel button.
- [ ] **`TmuxAdapter.snapshot()` / `FirefoxAdapter.snapshot()` return `{}`** — violate the adapter contract; revert is a hardcoded recovery rather than real restoration. Capture a real pre-state.
- [ ] **Per-adapter happy-path tests** — orchestrator covered now (5 tests); each adapter still needs at least one apply→verify("on")→revert→verify("off") smoke test.

## Theming layer — P2 (DX / code quality)

- [ ] **Extract shared helpers** — `_run`, `_gsettings_get/set`, `~/.config/nightpanel` path construction duplicated across 5+ files. Single `_util.py` + `_paths.py`.
- [ ] **Inject paths into adapters** — module-level constants make testing require monkey-patching globals; a `Paths` dataclass via constructor is cleaner.
- [ ] **`Adapter.name` class-attr without default + no ABC enforcement** — forgetting to set `name` is a runtime `AttributeError`. Default + check or `__init_subclass__`.
- [ ] **`_load_state()` swallows JSON decode errors** — corrupt state file = silent no-op revert. Should warn loudly.
- [ ] **`np-host.py` 500ms busy-poll** — replace with `Gio.FileMonitor` / `inotify` for true event-driven forwarding.
- [ ] **`np-host.py` filename hyphen + copied-to-config detachment** — rename to `np_host.py`; consider not copying (run from src tree via wrapper).
- [ ] **`nvim` adapter socket discovery** — patterns may miss modern nvim's `$XDG_RUNTIME_DIR/nvim.<pid>.0`. Validate.
- [ ] **`install_gnome_extension()` always enables** — coercive if user explicitly disabled. Check disabled-list first.
- [ ] **`bin/release` private/public mode** — currently the private flow (Forgejo-only) is manual; add a `--private` flag that skips the `git push github`.

---

## Keyboard layer — P0 (legacy DailyDriver)

- [ ] Screenshots for hypr / apple presets don't work — should show equivalent of apple keys
- [ ] `<D-/>` shortcut bug (slash key with Super modifier)
- [ ] Fix ~34 failing `test_gsettings.py` tests — mock-setup mismatches surfaced by the dailydriver→nightpanel rename (was 6 pre-rename; the rename surfaced more)

**Completed:**
- [x] Test compositor shortcut grabs on a live GNOME Wayland session (tested, doesn't work — GNOME limitation)
- [x] Update `ShortcutGrabberService` to detect GNOME and skip portal attempt
- [x] AppStream metainfo (`data/io.github.gregfelice.Nightpanel.metainfo.xml.in`) finalized
- [x] Alt+Super+/ keybinding repointed at `nightpanel --cheat-sheet` (was pointing at a stale `dailydriver-standalone` path)

## Keyboard layer — P1

- [ ] **AppStream metainfo screenshots fail validation** — `release.yml` workflow's `validate-appstream` job fails with: `<release>` version duplicated, screenshot heights >900px (max), images have padding. Cosmetic; release publishing succeeds independently.
- [ ] Research GNOME Shell extension approach for global shortcuts (extension exposes GrabAccelerator via custom D-Bus interface)
- [ ] Background daemon mode (`nightpanel --daemon`) for persistent shortcut grabs
- [ ] Make detection methods on `GSettingsService` public (`_detect_terminal` etc.)
- [ ] Add "Shortcut Status" indicator in UI showing compositor grab state + GNOME limitation warning
- [ ] Integration test for `ShortcutGrabberService` with `python-dbusmock`
- [ ] GNOME schema version validation in preset tests
- [ ] Add CI status badge once test_gsettings is green

## Keyboard layer — P2

- [ ] KDE Plasma backend
- [ ] Hyprland backend
- [ ] GNOME Circle application
- [ ] Auto-update checker
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

## Distribution (queued, see [[project-release-state]])

- [ ] **Forgejo repo rename** `dailydriver-standalone` → `nightpanel` (Greg does in web UI; no API token available)
- [ ] **GitHub public push** of v0.2.2 → v0.2.5 tags (`git push github main v0.2.5`; GH Actions auto-publishes Releases)
- [ ] **AUR migration** — orphan `dailydriver`, push fresh `nightpanel` package. PKGBUILD + .SRCINFO ready in `aur/`; instructions in `aur/MIGRATION.md`.
- [ ] **extensions.gnome.org submission** — ZIP + compliance checklist ready in `packaging/extensions-gnome-org/`. User clicks submit (per [[feedback-submission-carefulness]]).
- [ ] **Flathub** — deprioritized after the prior moderator interaction; the manifest `io.github.gregfelice.DailyDriver.yml` at repo root is stale.

---

## Lessons learned (incidents → memories)

- **GLib.idle_add truthy-return trap** — see [[feedback-glib-idle-add-truthy-return]]. Burned ~90 minutes on 2026-05-26 because I'd changed `orchestrator.apply()` to return a dict (state-machine fix) and the idle_add callback at `window.py:58` had no return-False wrapper. Lock this in next time you change any method's return type that's bound to a GLib source.
- **Submission carefulness** — see [[feedback-submission-carefulness]]. Flathub PR went bad after a missed guideline + hostile moderator; prep + checklist, never auto-submit.

---

## Out of scope of latest audit (worth a follow-up pass)

- `src/nightpanel/window.py` (1236 lines) — handles all views; almost certainly wants splitting.
- `src/nightpanel/services/theme_service.py` (416 lines) — relationship to the new palette/renderer layer unclear; possible duplication.
- `src/nightpanel/player_app.py` (304 lines) — Spotify player UI; not audited.
- `src/nightpanel/renderers/{alacritty,emacs,firefox_chrome,player,tmux}.py` — only `gtk.py` was read.
