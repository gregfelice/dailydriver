# DailyDriver Cheat Sheet Extension

GNOME Shell extension that shows a keyboard shortcut overlay popup.

## Installation

### From Source

```bash
# Compile schemas
glib-compile-schemas extension/schemas/

# Install to user extensions
mkdir -p ~/.local/share/gnome-shell/extensions/dailydriver-cheatsheet@gregfelice.github.io
cp -r extension/* ~/.local/share/gnome-shell/extensions/dailydriver-cheatsheet@gregfelice.github.io/

# Restart GNOME Shell (X11) or log out/in (Wayland)
# Then enable the extension
gnome-extensions enable dailydriver-cheatsheet@gregfelice.github.io
```

### One-liner Install

```bash
./extension/install.sh
```

## Usage

Press **Alt+Super+/** to toggle the cheat sheet overlay.

Press **Escape** or click outside to close.

## Compatibility

- GNOME Shell 45, 46, 47

## Related

- [DailyDriver App](https://github.com/gregfelice/dailydriver) - Full keyboard shortcut configuration app
