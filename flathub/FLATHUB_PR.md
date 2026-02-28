# New App: Daily Driver

## App Summary

**Daily Driver** is a visual keyboard shortcut configuration tool for GNOME. It provides a videogame-like options UI for customizing keyboard shortcuts, with a visual keyboard overlay showing which keys are bound to which actions.

**Homepage:** https://github.com/gregfelice/dailydriver
**License:** GPL-3.0-or-later

## Features

- Visual keyboard display with real-time shortcut overlay
- Built-in presets (Vanilla GNOME, GNOME + Tiling, Hyprland-style)
- Profile system for saving and sharing configurations
- Mac keyboard support (hid-apple fn key configuration)
- Tiling Assistant extension integration
- Conflict detection and resolution

## Screenshots

Screenshots are included in the AppStream metadata and visible at:
https://github.com/gregfelice/dailydriver/tree/main/data/screenshots

## Permission Justifications

### dconf/GSettings Access
```
--talk-name=ca.desrt.dconf
--filesystem=xdg-run/dconf
--filesystem=~/.config/dconf:rw
--own-name=ca.desrt.dconf.Writer
--env=GSETTINGS_SCHEMA_DIR=/run/host/usr/share/glib-2.0/schemas
```
**Justification:** The app's core functionality is reading and writing GNOME keyboard shortcuts, which are stored in GSettings/dconf. This includes:
- `org.gnome.desktop.wm.keybindings` (window manager shortcuts)
- `org.gnome.shell.keybindings` (shell shortcuts)
- `org.gnome.settings-daemon.plugins.media-keys` (media keys and custom shortcuts)
- `org.gnome.mutter.keybindings` (compositor shortcuts)
- `org.gnome.shell.extensions.*` (extension shortcuts like Tiling Assistant)

The `--own-name=ca.desrt.dconf.Writer` is needed to write changes back to dconf from within the Flatpak sandbox.

### Host Filesystem (Read-Only)
```
--filesystem=host-os:ro
```
**Justification:** Required to detect installed GNOME Shell extensions (located in `/usr/share/gnome-shell/extensions/` and `~/.local/share/gnome-shell/extensions/`). The app shows shortcuts for extensions like Tiling Assistant when detected.

### Hardware Access
```
--filesystem=/sys/class/input:ro
--filesystem=/sys/module/hid_apple:ro
--system-talk-name=org.freedesktop.PolicyKit1
```
**Justification:** The app detects connected keyboards to identify Mac keyboards and configure the `hid-apple` kernel module (fn key behavior, Option/Command swap). PolicyKit is required to write to `/sys/module/hid_apple/parameters/` with proper authorization.

### GNOME Shell DBus
```
--talk-name=org.gnome.Shell
```
**Justification:** Used for the keyboard shortcut grabber functionality, allowing users to press a key combination to set a shortcut (similar to GNOME Settings).

### Portal Access
```
--talk-name=org.freedesktop.portal.Settings
--talk-name=org.freedesktop.portal.Desktop
```
**Justification:** Standard portal access for system settings and desktop integration.

## Checklist

- [x] App builds and runs correctly
- [x] AppStream metadata validates
- [x] Desktop file present
- [x] Icon present (scalable SVG + symbolic)
- [x] Screenshots included
- [x] Release notes for v0.1.0
- [x] Content rating (OARS-1.1) present
- [x] Appropriate categories (Settings, HardwareSettings)

## Testing

The app has been tested on:
- Fedora 39/40/41 (GNOME 45/46/47)
- Ubuntu 24.04 (GNOME 46)

## Notes

This is the initial submission. The app is fully functional for its core use case (configuring GNOME keyboard shortcuts visually). Future releases will add KDE Plasma support.
