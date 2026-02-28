# DailyDriver Backlog

Prioritized bugs, features, and improvements for DailyDriver development.

---

## P0 - Critical

- [ ] Update `ShortcutGrabberService` to detect GNOME and skip portal attempt (cleaner logs, no error spam)
- [ ] Capture screenshots and finalize AppStream metainfo for Flathub submission
- [ ] Screenshots for hypr / apple presets don't work - should show equivalent of apple keys
- [ ] `<D-/>` shortcut bug (slash key with Super modifier)
- [ ] Fix 6 failing custom keybinding tests (mock setup refinement needed)

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

## P2 - Soon

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

## P3 - Future

- [ ] COPR (Fedora) packaging
- [ ] Keyboard layout auto-detection (QWERTY/Dvorak/Colemak)
- [ ] User-contributed preset marketplace / sharing
- [ ] Multi-monitor shortcut awareness
