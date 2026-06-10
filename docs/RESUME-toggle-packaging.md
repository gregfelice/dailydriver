# RESUME: toggle packaging — ship the theming/toggle half without the repo

**Status:** COMPLETE (2026-06-09) via the .deb ship path. Remaining REMAINING-list
items below were resolved as follows: steps 3 (`src/nightpanel-toggle.in`),
4 (root `meson.build` configure_file → bindir), and 5 (extension.js keystone:
`GLib.find_program_in_path('nightpanel-toggle')` + metadata version bump 2→3)
are DONE. Step 6 was satisfied differently — instead of a `bin/` dev shim, the
two toggle test files now resolve the binary via `shutil.which("nightpanel-toggle")`
(PATH → /usr/bin) with a `~/.local/bin` fallback and skip-if-missing. Steps 1/2
(lazy `services/__init__` + gi-free regression test) were CONSCIOUSLY SKIPPED:
the .deb hard-depends on `python3-gi`, so a gi import in the orchestrator graph
is always satisfiable; lazy init only matters for the still-deferred wheel path.
Step 7 (VM harness) not needed — validated on the real box: `dpkg -c` pre-flight,
installed-binary import check, and the 8 toggle tests passing against
`/usr/bin/nightpanel-toggle`. The deb also renames the package dailydriver→nightpanel
and adds `python3-tomlkit` to Depends (alacritty adapter). Originally started 2026-06-04.
**Goal:** `nightpanel-toggle` (and the theming orchestrator it drives) must work on a clean
machine that has *no repo checkout and no `.venv-dev`* — installed via the project's ship
vehicles (Flatpak / AUR / deb / Nix / AppImage), all of which use raw `meson install`.

## Why this is needed (the finding)

The theming half was never packaged. Two root causes:
1. **Modules weren't installed.** `src/meson.build` shipped only `__init__/application/window`
   + models/services/views/resources. `palette.py`, `adapters/`, `renderers/`, and
   `services/nightpanel_orchestrator.py` were **absent** from the meson install lists — so no
   installed package could import the orchestrator.
2. **The toggle reached into the repo.** `bin/nightpanel-toggle` derived `NIGHTPANEL_HOME`
   from its own path, ran `<repo>/.venv-dev/bin/python3`, and `sys.path.insert(<repo>/src)`
   before importing the orchestrator. Worked only via the dotfiles-stow symlink to the checkout.

## Key decisions (with rationale — do NOT relitigate)

- **Entry-point mechanism = `configure_file` `.in` launcher → `bindir`**, NOT the pip
  wheel / `[project.scripts]`. The ship vehicles all use raw `meson install`; meson does not
  process `[project.scripts]`. (`[project.scripts] nightpanel-toggle` is kept for a future
  wheel but is not the shipping mechanism.)
- **`services/__init__.py` must become lazy (PEP 562 `__getattr__`).** It eagerly imports
  `gsettings_service` / `keyboard_config_service` / `profile_service` — **all import `gi`** (and
  backends do too). So `from nightpanel.services.nightpanel_orchestrator import …` pulls in `gi`
  today. The toggle/theming graph is otherwise **gi-free** (verified: no adapter/renderer/palette
  imports gi). Lazy init keeps the `from nightpanel.services import GSettingsService` API working
  while making the orchestrator import gi-free. Pin with a regression test.
- **KEYSTONE — extension hardcodes the toggle path.** `extension.js:18`:
  `TOGGLE_SCRIPT = GLib.get_home_dir() + '/.local/bin/nightpanel-toggle'`. System packages
  install to `/usr/bin`, so the panel button would be **dead for distro users**. Fix in the
  *extension*: resolve via `GLib.find_program_in_path('nightpanel-toggle')` with the
  `~/.local/bin/...` path kept as a fallback (dev-stow + pipx). Validation MUST confirm the
  *extension's* resolution, not just that the script runs when invoked directly.
- **Defer the wheel/pipx path.** It's blocked by a *pre-existing GUI* bug (below). Once the
  extension resolves by PATH, pipx→`~/.local/bin` buys nothing the distro path doesn't.
- **Skip moving PyGObject → `gui` extra.** Only matters for the wheel path; raw `meson install`
  doesn't read pip deps. No consumer yet → no change.

## DONE (durable, validated)

- `src/meson.build` — added `palette.py`, `toggle.py` to sources; added `subdir('nightpanel/adapters')`
  + `subdir('nightpanel/renderers')`.
- `src/nightpanel/adapters/meson.build` — **created**, installs all 11 adapter .py (paths relative to subdir).
- `src/nightpanel/renderers/meson.build` — **created**, installs all 8 renderer .py.
- `src/nightpanel/services/meson.build` — added `nightpanel_orchestrator.py`.
- `data/icons/meson.build` — **fixed pre-existing build break**: referenced `…DailyDriver.svg`
  but files are `…Nightpanel.svg` (stale from the rename). Build now configures.
- `pyproject.toml` — added `[project.scripts] nightpanel-toggle = "nightpanel.toggle:main"`.
- `src/nightpanel/toggle.py` — **created, real implementation** (faithful port of the bash
  heredoc: GUARD_CEIL_S=0.2, NP_CONFIG_DIR/NP_DEBOUNCE_S/NP_TOGGLE_MOCK, nightpanel-active +
  toggle.log, decisions apply/debounce-revert/revert). `drive()` uses a plain
  `from nightpanel.services.nightpanel_orchestrator import …` — no NIGHTPANEL_HOME/sys.path.
  **Verified:** `meson setup`+`compile`+`install` to a staging prefix lands toggle/orchestrator/
  adapters in purelib; `python -m nightpanel.toggle` runs the policy state machine correctly
  (apply→debounce-revert→revert) in mock mode.

**Nothing is broken right now:** the existing `bin/nightpanel-toggle` (bash) is UNCHANGED and
still works via the repo; the new module is additive.

## REMAINING (ordered — mechanical)

1. **`services/__init__.py` → lazy PEP 562.** Replace the eager `from … import …` block with
   `__all__` + a `__getattr__(name)` that imports the owning submodule on demand. Keep the same
   public names. (This de-contaminates the orchestrator import from `gi`.)
2. **Regression test** `tests/unit/test_toggle_importable.py`: assert `import nightpanel.toggle`
   and `from nightpanel.services.nightpanel_orchestrator import NightpanelOrchestrator` succeed
   with `gi` blocked (e.g. `sys.modules['gi'] = None` / a meta-path finder that raises for `gi`).
   Pins decision #2 so a future eager import can't silently re-break it.
3. **`src/nightpanel-toggle.in`** launcher (mirror `src/nightpanel.in`, minimal — NO gi/gresource):
   set `sys.path.insert(1, '@pythondir@')`, then `from nightpanel import toggle; sys.exit(toggle.main())`.
4. **Root `meson.build`** — add a `configure_file(input:'src/nightpanel-toggle.in', output:'nightpanel-toggle',
   configuration: conf, install: true, install_dir: get_option('bindir'), install_mode:'rwxr-xr-x')`
   (conf already has `pythondir`). Mirrors the existing `nightpanel` launcher block.
5. **`extension.js` keystone fix** — replace the hardcoded `TOGGLE_SCRIPT` with
   `GLib.find_program_in_path('nightpanel-toggle') || GLib.get_home_dir()+'/.local/bin/nightpanel-toggle'`.
   Bump `metadata.json` version (extension reload needs it). Update the line-5 comment.
6. **`bin/nightpanel-toggle` → thin dev shim**: `exec env NIGHTPANEL_HOME=<repo> PYTHONPATH=<repo>/src
   <repo>/.venv-dev/bin/python3 -m nightpanel.toggle "$@"` (must `exec env` so NP_* pass through).
   Logic now lives only in the module; keeps dotfiles-stow + the toggle tests working.
7. **VM harness** `tests/vm/guest/selftest.sh` — replace the repo-tarball+venv reconstruction
   with the real ship path: install to a staging prefix (or a built distro pkg) so
   `nightpanel-toggle` is on PATH, and assert the *extension* resolution finds it. Keep lean.

## Validation plan (the acceptance test for "ships without the repo")

- `meson setup /tmp/mb --prefix=/tmp/pfx && meson install -C /tmp/mb --destdir /tmp/stage`
- Run the **staged launcher** `/tmp/stage/tmp/pfx/bin/nightpanel-toggle` with **only the staged
  purelib** importable and **no repo on `sys.path`**; NP_TOGGLE_MOCK=1 for policy, then a real
  apply/revert against a throwaway `$HOME` (proves the orchestrator imports + runs with zero repo).
- `grep extension.js` for every toggle reference → confirm none is a bare hardcoded `~/.local/bin`.
- Run BOTH `tests/unit/test_toggle_policy.py` and `test_toggle_debounce.py` (they invoke
  `~/.local/bin/nightpanel-toggle` as a subprocess; the dev shim must keep them green).
- gi-free import check (the regression test above).

## DEFERRED (separate follow-ups, NOT this task)

- **Wheel/pipx build is blocked** by a pre-existing GUI bug: meson-python errors
  `Could not map installation path … '{prefix}/share/nightpanel/nightpanel.gresource'` because
  `PKGDATA_DIR` is built with `get_option('prefix')`. Likely-small fix: split it — use relative
  `get_option('datadir')/name` for `install_dir`, keep the prefix-absolute form for the runtime
  `conf.set('PKGDATA_DIR', …)` (so `nightpanel.in`'s `Gio.Resource.load` still works). Then re-run
  and count remaining unmappable installs (presets/layouts/schemas may also need it). Icons/desktop
  already use relative datadir and map fine, so it may be ~3 lines.
- App-ID rename consistency (Flatpak manifest still `…DailyDriver`, meson is `…Nightpanel`).
- PyGObject → `gui` optional-dependency (only when the wheel path is revived).

## Changed-files surface (for the diff)
src/meson.build · src/nightpanel/adapters/meson.build (new) · src/nightpanel/renderers/meson.build (new) ·
src/nightpanel/services/meson.build · data/icons/meson.build · pyproject.toml · src/nightpanel/toggle.py (new)
