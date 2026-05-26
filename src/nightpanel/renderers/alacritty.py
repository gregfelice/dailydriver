# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the alacritty nightpanel theme TOML from a Palette."""

from __future__ import annotations

from ..palette import Palette


def render(p: Palette) -> str:
    return f"""# nightpanel — saab instrument cluster theme for alacritty
# generated from nightpanel.palette — edit there, not here

[colors.primary]
background = "{p.bg}"
foreground = "{p.fg}"   # instrument scale green — unified default across Nautilus / Firefox / Claude Code

[colors.cursor]
text    = "{p.bg}"
cursor  = "{p.fg_amber}"

[colors.vi_mode_cursor]
text   = "{p.bg}"
cursor = "{p.fg_bright}"

[colors.selection]
text       = "{p.bg}"
background = "{p.bg_select}"

[colors.search.matches]
foreground = "{p.bg}"
background = "{p.fg_amber}"

[colors.search.focused_match]
foreground = "{p.bg}"
background = "{p.amber_warm}"

[colors.footer_bar]
background = "{p.bg_header}"
foreground = "{p.fg}"

[colors.hints.start]
foreground = "{p.bg}"
background = "{p.fg_amber}"

[colors.hints.end]
foreground = "{p.bg}"
background = "{p.fg_dim}"

[colors.line_indicator]
foreground = "None"
background = "None"

# SAAB instrument cluster — green / amber / red discipline.
# Default narrative text and code share the same green family so the dialog
# (CC chat, status output, etc.) stays the "lovely green" baseline. Diff
# signal comes via line-state slots (slot 77 for added → bright green,
# ANSI red for removed). Syntax token slots that would otherwise scream
# (purple booleans, wheat numbers) are remapped further down to palette
# colors via [[colors.indexed_colors]].
[colors.normal]
black   = "{p.bg}"
red     = "{p.red}"
green   = "{p.fg}"         # instrument scale — matches default fg
yellow  = "{p.fg_amber}"
blue    = "{p.fg_dim}"
magenta = "{p.fg}"
cyan    = "{p.fg_bright}"
white   = "{p.fg_light}"

[colors.bright]
black   = "{p.fg_dim}"
red     = "{p.red}"
green   = "{p.fg_bright}"
yellow  = "{p.amber_warm}"
blue    = "{p.fg_mid}"
magenta = "{p.fg_light}"
cyan    = "{p.fg_bright}"
white   = "{p.fg_light}"

# 256-color extended palette overrides — some apps (Claude Code) draw UI
# chrome with specific slots in the 6x6x6 cube + grayscale ramp. Remap them
# so the instrument cluster discipline survives beyond the ANSI 16 block.

# Claude Code chrome
[[colors.indexed_colors]]
index = 137   # light tan — activity word ("Meandering…", "Contemplating…")
color = "{p.fg_amber}"

[[colors.indexed_colors]]
index = 147   # lavender — mode indicator ("accept edits on")
color = "{p.fg_amber}"

# Diff backgrounds — kill them so diffs sit on the NP canvas, not in a box
[[colors.indexed_colors]]
index = 22    # dark green — added-line bg (whole line)
color = "{p.bg}"

[[colors.indexed_colors]]
index = 52    # dark red — removed-line bg (whole line)
color = "{p.bg}"

[[colors.indexed_colors]]
index = 28    # brighter green — inline added-character highlight bg (JSON diffs etc.)
color = "{p.bg}"

[[colors.indexed_colors]]
index = 88    # brighter red — inline removed-character highlight bg
color = "{p.bg}"

[[colors.indexed_colors]]
index = 237   # dark grey — context-line bg / user-echo bg
color = "{p.bg}"

# Added-line text — carries the green diff signal
[[colors.indexed_colors]]
index = 77    # bright lime — added-line text → palette bright-green
color = "{p.fg_bright}"

# Pull stray Claude Code syntax slots into the green/amber palette so
# they don't leak purple or cyan into the dialog. They share the dialog
# greens — the diff still distinguishes via line-state (slot 77 / ANSI red).
[[colors.indexed_colors]]
index = 81    # bright cyan — function / class names
color = "{p.fg_bright}"

[[colors.indexed_colors]]
index = 141   # bright purple — booleans / None constants
color = "{p.fg_bright}"

[[colors.indexed_colors]]
index = 153   # pale blue — file paths / accents
color = "{p.fg_bright}"

[[colors.indexed_colors]]
index = 186   # wheat / pale yellow — number / keyword highlight
color = "{p.fg_amber}"

[[colors.indexed_colors]]
index = 231   # pure white — explicit white text
color = "{p.fg}"

[window]
decorations               = "None"   # hide the title bar entirely in NP mode
decorations_theme_variant = "Dark"   # keep dark style if compositor ignores `decorations`

[font]
size = 13.0

[font.normal]
family = "JetBrains Mono"
style  = "Light"

[font.bold]
family = "JetBrains Mono"
style  = "Regular"   # one weight up from Light for emphasis without going to actual bold

[font.italic]
family = "JetBrains Mono"
style  = "Italic"

[font.bold_italic]
family = "JetBrains Mono"
style  = "Italic"
"""
