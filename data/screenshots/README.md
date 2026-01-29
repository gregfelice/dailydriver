# Screenshots for AppStream/Flathub

Screenshots are required for Flathub submission. They should be:

- **Resolution**: At least 1248×702 pixels (16:9 aspect ratio recommended)
- **Format**: PNG
- **Content**: Show actual app functionality
- **Variants**: Include both light and dark mode if supported

## Required Screenshots

1. `main-window.png` - Main window with visual keyboard layout
2. `shortcut-editor.png` - Shortcut editor showing keybinding configuration
3. `presets.png` - Built-in preset profiles

## How to Capture

```bash
# Run the app
flatpak run io.github.gregfelice.DailyDriver

# Use GNOME Screenshot or:
gnome-screenshot -w -f main-window.png
```

## Before Flathub Submission

1. Capture all required screenshots
2. Verify they display correctly at https://www.flathub.org/apps/preview
3. Test with `appstreamcli validate data/io.github.gregfelice.DailyDriver.metainfo.xml`
