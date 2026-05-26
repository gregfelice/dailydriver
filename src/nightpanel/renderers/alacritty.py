# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the alacritty nightpanel theme TOML from a Palette."""

from __future__ import annotations

from ..palette import Palette


def render(p: Palette) -> str:
    return f"""# nightpanel — saab instrument cluster theme for alacritty
# generated from nightpanel.palette — edit there, not here

[colors.primary]
background = "{p.bg}"
foreground = "{p.border_s}"   # grey default — diff state (slot 77 green / ANSI red) is the only color signal in code

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

# Saab instrument cluster — minimal three-state coloring.
# Code is GREY by default. Diff line-state carries all the signal:
#   green = added (slot 77)
#   red   = removed (ANSI red, kept)
#   grey  = unchanged / context (everything else)
# Every syntax-token slot (keywords, strings, booleans, numbers, function
# names) is folded into grey so token highlighting doesn't compete with
# the diff signal. Status indicators stay amber via slot remaps below.
[colors.normal]
black   = "{p.bg}"
red     = "{p.red}"
green   = "{p.border_s}"   # was syntax green — folded to grey
yellow  = "{p.border_s}"   # was strings amber — folded to grey
blue    = "{p.border_s}"
magenta = "{p.border_s}"
cyan    = "{p.border_s}"
white   = "{p.border_s}"

[colors.bright]
black   = "{p.border_d}"
red     = "{p.red}"
green   = "{p.border_s}"   # was keyword red — folded to grey
yellow  = "{p.border_s}"   # was warm amber — folded to grey
blue    = "{p.border_s}"
magenta = "{p.border_s}"
cyan    = "{p.border_s}"
white   = "{p.border_s}"

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

# Added-line text (carries the green signal)
[[colors.indexed_colors]]
index = 77    # bright lime — added-line text → palette bright-green
color = "{p.fg_bright}"

# Fold every other Claude Code syntax-token slot into grey. None of these
# carry signal under the three-state rule (grey / red / green).
[[colors.indexed_colors]]
index = 81    # bright cyan — function / class names
color = "{p.border_s}"

[[colors.indexed_colors]]
index = 141   # bright purple — booleans / None constants
color = "{p.border_s}"

[[colors.indexed_colors]]
index = 153   # pale blue — file paths / accents
color = "{p.border_s}"

[[colors.indexed_colors]]
index = 186   # wheat / pale yellow — number / keyword highlight
color = "{p.border_s}"

[[colors.indexed_colors]]
index = 231   # pure white — explicit white text
color = "{p.border_s}"

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
