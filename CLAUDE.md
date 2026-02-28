# DailyDriver

Visual keyboard shortcut configuration tool for GNOME/Wayland with presets, cheat sheet overlay, and conflict detection.

## Quick Reference

```bash
# Dev environment
cd /home/gregf/development/dailydriver-standalone
source venv/bin/activate
PYTHONPATH=src pytest tests/unit/ -v

# Lint
ruff check src/ tests/
ruff format src/ tests/

# Build Flatpak locally
flatpak-builder --force-clean --user --install build-dir io.github.gregfelice.DailyDriver.yml

# Run dev mode
./run-dev.sh
```

## Architecture

GTK4/Libadwaita app using Python with Meson build system. Packaged as Flatpak.

```
src/dailydriver/
  application.py          # App entry point, GtkApplication subclass
  window.py               # Main window (42k - largest file, handles all views)
  models/
    shortcut.py           # Shortcut data model
    keyboard.py           # Keyboard layout model
    profile.py            # Profile/preset model
  services/
    gsettings_service.py  # Reads/writes GNOME keyboard shortcuts via dconf
    keyboard_config_service.py  # Orchestrates shortcut configuration
    profile_service.py    # Loads/saves preset profiles (TOML)
    hardware_service.py   # Keyboard hardware detection
    hid_apple_service.py  # Mac keyboard hid-apple module config
    backends/             # Desktop-specific backends (GNOME, future KDE/Hyprland)
  views/
    keyboard_view.py      # Visual keyboard display
    cheatsheet.py         # Cheat sheet overlay (Alt+Super+/)
    preset_selector.py    # Preset selection UI
    shortcut_editor.py    # Individual shortcut editing
    shortcut_list.py      # Shortcuts list by category
```

Key patterns:
- GTK requires `gi.require_version()` before imports; ruff E402 is suppressed for these files
- Services are injected into views, not imported directly
- Presets are TOML files defining complete shortcut sets ("clean slate" approach)
- GNOME does NOT support xdg-desktop-portal GlobalShortcuts; app falls back to gnome-settings-daemon keybindings

## Conventions

- **Python**: 3.11+, ruff for linting/formatting, line length 100
- **Testing**: pytest with pytest-cov, pytest-mock; tests in `tests/unit/`; 220+ tests
- **Packaging**: Use `uv pip` for installs, Meson build system, Flatpak for distribution
- **Git**: Conventional commit messages
- **Branching**: main branch, push to GitHub
- **App ID**: `io.github.gregfelice.DailyDriver` (reverse DNS for Flatpak/Flathub)

## Key Documentation

- `docs/BACKLOG.md` - Prioritized backlog (P0-P3)
- `docs/STATUS.md` - Project status and last session notes
- `docs/RELEASING.md` - Version numbering and release process
- `docs/FLATPAK_SUBMISSION_GUIDE.md` - Flathub submission reference
- `docs/adr/` - Architecture decision records
- `docs/research/` - Research notes
- `flathub/FLATHUB_PR.md` - Flathub PR description and permission justifications

## Status

**v0.1.0-alpha** - Application is solid and running well on GNOME/Wayland.

- 220 tests passing, 6 failing (mock setup issues in custom keybinding tests)
- 29% code coverage (core services well tested; UI views untested)
- CI/CD operational via GitHub Actions
- Flathub submission pending review
- AUR package published
- Known platform limitation: GNOME does not implement xdg-desktop-portal GlobalShortcuts

See `docs/BACKLOG.md` for current priorities.
