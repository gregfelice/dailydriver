# DailyDriver Status - 2026-02-02

## Current State
**Application is SOLID and RUNNING WELL on GNOME/Wayland**

Tested on Ubuntu with GNOME 49/Wayland - keyboard configuration, cheat sheet overlay, preset switching all functional.

## Last Work Session

### What We Did
1. Migrated DailyDriver from deeper monorepo to standalone repo at `/home/gregf/development/dailydriver-standalone`
2. Archived detailed backlog from deeper to `dailydriver-standalone/BACKLOG.md`
3. Ran full test suite to establish baseline
4. Committed and pushed to GitHub

### Test Results
- **220 tests passed** ✅
- **6 tests failed** (mock setup issues in custom keybinding tests - not functional)
- **29% code coverage** (core services well tested; UI views untested)
- **CI/CD working** - GitHub Actions test workflow operational

## What's Ready to Ship
- ✅ Preset system (Hyprland-style, GNOME+Tiling, Vanilla GNOME)
- ✅ Keyboard visualization with shortcuts
- ✅ Cheat sheet overlay (Alt+Super+/)
- ✅ Conflict detection
- ✅ Mac keyboard support (hid-apple integration)
- ✅ Tiling Assistant integration
- ✅ 10 workspace support
- ✅ Flatpak packaging (0.1.0-alpha available)

## Critical Technical Finding

**GNOME does NOT support xdg-desktop-portal GlobalShortcuts**
- Only KDE Plasma and Hyprland support it
- GNOME Shell's GrabAccelerator API restricted to extensions only
- This is a platform limitation, not a DailyDriver bug
- App gracefully falls back to gnome-settings-daemon keybindings
- Reference: https://gitlab.gnome.org/GNOME/xdg-desktop-portal-gnome/-/issues/47

## Next Priority (P0) When Resuming

1. **Fix 6 failing custom keybinding tests** - mock setup refinement needed
2. **Screenshots for Flathub submission** - metainfo finalized, need AppStream screenshots
3. **Fix `<D-/>` shortcut bug** - slash key with Super modifier not rendering
4. **Hyprland/Apple preset screenshots** - should show equivalent of apple keys

See `BACKLOG.md` for full P0/P1/P2 breakdown.

## Key Files
- `BACKLOG.md` - Prioritized issues and research
- `pyproject.toml` - Dependencies, test config
- `src/dailydriver/` - Core application code
- `tests/unit/` - 226 unit tests
- `.github/workflows/test.yml` - CI pipeline

## How to Resume
```bash
cd /home/gregf/development/dailydriver-standalone
source venv/bin/activate
PYTHONPATH=src pytest tests/unit/ -v
```

## Git History
- Commit d27dddb: "Add BACKLOG.md with prioritized issues and research findings"
- Main branch is up-to-date with GitHub
