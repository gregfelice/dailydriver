# DailyDriver

**Visual keyboard shortcut configuration for GNOME/Wayland**

[![Tests](https://github.com/gregfelice/dailydriver/actions/workflows/test.yml/badge.svg)](https://github.com/gregfelice/dailydriver/actions/workflows/test.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![AUR](https://img.shields.io/aur/version/dailydriver)](https://aur.archlinux.org/packages/dailydriver)

DailyDriver lets you configure GNOME keyboard shortcuts visually, apply curated presets, and see all your shortcuts at a glance with a keyboard cheat sheet. There's presets to instantly give you HYPR-style keymaps too.

![DailyDriver - Keyboard Visualization](data/screenshots/keyboard-view.png)

<details>
<summary>More screenshots</summary>

### Shortcuts List
Browse and edit shortcuts by category

![Shortcuts View](data/screenshots/main-window.png)

### Cheat Sheet
Quick reference overlay showing all active shortcuts (Alt+Super+/)

![Cheat Sheet](data/screenshots/cheat-sheet.png)

### Preset Selection
Choose from curated shortcut profiles

![Presets](data/screenshots/presets.png)

</details>

## Features

- **Preset Profiles** - One-click configuration with curated shortcut sets
- **Clean Slate Mode** - Presets disable ALL shortcuts first, then apply only what's defined (no mystery keymaps)
- **Keyboard Cheat Sheet** - Quick reference overlay showing all active shortcuts (Alt+Super+/)
- **10 Workspace Support** - Navigate workspaces with Super+1-9, Super+0
- **Visual Keyboard** - See shortcuts on an interactive keyboard layout
- **Conflict Detection** - Warns when shortcuts conflict with existing bindings
- **Tiling Assistant Integration** - Built-in support for tiling shortcuts

## Installation

### Arch Linux (AUR)

```bash
yay -S dailydriver
# or
paru -S dailydriver
```

### Flathub (Coming Soon)

Flathub submission is [pending review](https://github.com/flathub/flathub/pull/7735). Once approved:

```bash
flatpak install flathub io.github.gregfelice.DailyDriver
```

### Flatpak Bundle (Manual)

Download the Flatpak bundle from [Releases](https://github.com/gregfelice/dailydriver/releases):

```bash
flatpak install dailydriver-0.1.0.flatpak
flatpak run io.github.gregfelice.DailyDriver
```

### From Source

```bash
git clone https://github.com/gregfelice/dailydriver.git
cd dailydriver
meson setup build
meson compile -C build
meson install -C build
```

## Platform Support

| Platform | Version | Status |
|----------|---------|--------|
| GNOME on Wayland | 45, 46, 47 | Tested in CI |
| GNOME on X11 | 45+ | Should work (untested) |
| KDE Plasma | - | Planned |
| Hyprland | - | Planned |

### Requirements

- GNOME 45+
- Wayland session (recommended)
- Flatpak runtime: `org.gnome.Platform//47`

## Built-in Presets

| Preset | Description |
|--------|-------------|
| **Hyprland Style** | Keyboard-centric workflow with vim-like navigation. Super+Q close, Super+hjkl tiling, Super+1-0 workspaces. |
| **GNOME + Tiling** | Standard GNOME with Tiling Assistant snap zones. Alt+F4 close, Super+arrows for tiling. |
| **Vanilla GNOME** | Pure GNOME Shell defaults without tiling extensions. |

## How It Works

When you apply a preset, DailyDriver:

1. **Disables ALL shortcuts** - Clears every GNOME keybinding to start fresh
2. **Applies only what's defined** - Sets exactly the shortcuts in your preset file
3. **Preserves custom launchers** - Your Terminal/Browser/Files shortcuts stay intact

This "clean slate" approach means your cheat sheet shows exactly what's in your config - no inherited GNOME defaults cluttering things up.

## Development

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
ruff format src/ tests/

# Build Flatpak locally
flatpak-builder --force-clean --user --install build-dir io.github.gregfelice.DailyDriver.yml
```

## CI/CD

Tests run on every push:
- **Lint** - ruff check and format
- **Unit Tests** - pytest with coverage
- **Integration Tests** - Real GNOME Shell on Fedora 39/40/41 (GNOME 45/46/47)
- **Preset Validation** - Ensures all preset TOML files are valid
- **Flatpak Build** - Verifies the app builds as a Flatpak

## Roadmap

- [x] Screenshots for README
- [x] AUR package
- [ ] Flathub ([pending review](https://github.com/flathub/flathub/pull/7735))
- [ ] COPR (Fedora)
- [ ] KDE Plasma backend
- [ ] Hyprland backend
- [ ] Custom shortcut editor (create new shortcuts)
- [ ] Import/export profiles

## Feedback & Contributing

Your feedback helps make DailyDriver better!

- **Bug reports**: [Open an issue](https://github.com/gregfelice/dailydriver/issues/new?labels=bug&title=Bug:%20)
- **Feature requests**: [Open an issue](https://github.com/gregfelice/dailydriver/issues/new?labels=enhancement&title=Feature:%20)
- **Questions**: [Open an issue](https://github.com/gregfelice/dailydriver/issues/new?labels=question&title=Question:%20)

## License

GPL-3.0-or-later
