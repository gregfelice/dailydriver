# DailyDriver Backlog

Bugs, features, and research findings for DailyDriver development.

---

## Critical Finding: GNOME GlobalShortcuts Portal Limitations

**Tested**: 2026-01-28 on Ubuntu with GNOME 49 / Wayland

### The Problem

GNOME does not support the xdg-desktop-portal GlobalShortcuts interface:

- `ShortcutGrabberService` connects to xdg-desktop-portal successfully
- `CreateSession` works, returns valid session handle
- `BindShortcuts` **fails with response code 2** (Other/Unimplemented)
- Root cause: **xdg-desktop-portal-gnome does NOT implement GlobalShortcuts backend**
- GNOME tracking issue: https://gitlab.gnome.org/GNOME/xdg-desktop-portal-gnome/-/issues/47

### Alternative Approach (Also Failed)

- GNOME Shell `GrabAccelerator` D-Bus API exists (`org.gnome.Shell`)
- Returns `AccessDenied: GrabAccelerator is not allowed` for non-extension apps
- This API is restricted to GNOME Shell extensions only
- Reference: https://github.com/Keruspe/GPaste/issues/383

### Wayland Global Shortcuts Support Matrix

| Desktop | xdg-desktop-portal GlobalShortcuts | Shell D-Bus API |
|---------|-----------------------------------|-----------------|
| GNOME | Not implemented | Extension-only |
| KDE Plasma | Works | N/A |
| Hyprland | Works | N/A |

### Implication for DailyDriver

- `ShortcutGrabberService` (using xdg-desktop-portal) won't work on GNOME
- App gracefully falls back to gnome-settings-daemon custom keybindings (existing behavior)
- Those keybindings CAN be bypassed by apps using Wayland keyboard shortcuts inhibitor protocol
- The original problem (shortcuts not working in terminals) remains unsolved on GNOME

---

## P0 - Do Now

- [ ] Update `ShortcutGrabberService` to detect GNOME and skip portal attempt (cleaner logs, no error spam)
- [ ] Capture screenshots and finalize AppStream metainfo for Flathub submission
- [ ] Screenshots for hypr / apple presets don't work - should show equivalent of apple keys
- [ ] `<D-/>` shortcut bug (slash key with Super modifier)

**Completed:**
- [x] Test compositor shortcut grabs on a live GNOME Wayland session (tested, doesn't work - GNOME limitation)

---

## P1 - Next Sprint

- [ ] Flathub beta channel submission
- [ ] Research GNOME Shell extension approach for global shortcuts (extension exposes GrabAccelerator to DailyDriver via custom D-Bus interface)
- [ ] Background daemon mode (`dailydriver --daemon`) for persistent shortcut grabs (useful when GlobalShortcuts works)
- [ ] Make detection methods on GSettingsService public API (`_detect_terminal` etc.)
- [ ] Add "Shortcut Status" indicator in UI showing compositor grab state (and GNOME limitation warning)
- [ ] Integration test for ShortcutGrabberService with `python-dbusmock`
- [ ] GNOME schema version validation in preset tests
- [ ] Add CI notification (GitHub status badge)

---

## P2 - Later

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

---

## Dev Environment Notes

**Fix applied 2026-01-28:**
- Updated `run-dev.sh` to create venv with `--system-site-packages` for GTK bindings
- Requires `python3.13-venv` package on Ubuntu 24.04+
