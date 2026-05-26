# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the alacritty nightpanel theme TOML from a Palette."""

from __future__ import annotations

from ..palette import Palette


def render(p: Palette) -> str:
    return f"""# nightpanel — saab instrument cluster theme for alacritty
# generated from nightpanel.palette — edit there, not here

[colors.primary]
background = "{p.bg}"
foreground = "{p.fg_mid}"   # dim green for default text — added/emphasized text uses brighter shades via slot remaps

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

# Saab instrument cluster discipline — every ANSI slot is green, amber, or red.
# No grays, no blues, no purples. Apps that render syntax tokens via the 16
# ANSI slots (Claude Code, less, git, vim/nvim, etc.) inherit the discipline.
[colors.normal]
black   = "{p.bg}"
red     = "{p.red}"
green   = "{p.fg_mid}"     # dim green — explicit ANSI 2 matches default fg
yellow  = "{p.fg_amber}"
blue    = "{p.fg_dim}"
magenta = "{p.fg_mid}"
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

# Diff foreground emphasis
[[colors.indexed_colors]]
index = 77    # bright lime — added-line text → palette bright-green
color = "{p.fg_bright}"

# Stray non-palette colors that Claude Code emits via 256-color slots
[[colors.indexed_colors]]
index = 153   # pale blue — file paths / accents → palette bright-green
color = "{p.fg_bright}"

[[colors.indexed_colors]]
index = 186   # wheat / pale yellow — keyword highlight → palette amber
color = "{p.fg_amber}"

[[colors.indexed_colors]]
index = 231   # pure white — explicit white text → palette green
color = "{p.fg}"

[window]
decorations_theme_variant = "Dark"

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
