# SPDX-License-Identifier: GPL-3.0-or-later
"""Visual keyboard display widget using Cairo."""

import math

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gsk", "4.0")
gi.require_version("Graphene", "1.0")
from gi.repository import GObject, Gtk

from dailydriver.models import Key, KeyboardLayout, KeyboardType, Shortcut

# =============================================================================
# PC KEYBOARD LAYOUTS
# =============================================================================

# ANSI-104 Full Size (with numpad)
ANSI_104_DATA = {
    "id": "ansi-104",
    "name": "Full Size (104-key)",
    "type": "ansi-104",
    "width": 22.75,
    "height": 6.5,
    "keys": [
        # === Function row ===
        {"x": 0, "y": 0, "label": "Esc", "keyval": 65307, "row": 0},
        {"x": 2, "y": 0, "label": "F1", "keyval": 65470, "row": 0},
        {"x": 3, "y": 0, "label": "F2", "keyval": 65471, "row": 0},
        {"x": 4, "y": 0, "label": "F3", "keyval": 65472, "row": 0},
        {"x": 5, "y": 0, "label": "F4", "keyval": 65473, "row": 0},
        {"x": 6.5, "y": 0, "label": "F5", "keyval": 65474, "row": 0},
        {"x": 7.5, "y": 0, "label": "F6", "keyval": 65475, "row": 0},
        {"x": 8.5, "y": 0, "label": "F7", "keyval": 65476, "row": 0},
        {"x": 9.5, "y": 0, "label": "F8", "keyval": 65477, "row": 0},
        {"x": 11, "y": 0, "label": "F9", "keyval": 65478, "row": 0},
        {"x": 12, "y": 0, "label": "F10", "keyval": 65479, "row": 0},
        {"x": 13, "y": 0, "label": "F11", "keyval": 65480, "row": 0},
        {"x": 14, "y": 0, "label": "F12", "keyval": 65481, "row": 0},
        # Print/Scroll/Pause
        {"x": 15.25, "y": 0, "label": "Prt", "keyval": 65377, "row": 0},
        {"x": 16.25, "y": 0, "label": "Scr", "keyval": 65300, "row": 0},
        {"x": 17.25, "y": 0, "label": "Pse", "keyval": 65299, "row": 0},
        # === Number row ===
        {"x": 0, "y": 1.5, "label": "`", "secondary": "~", "keyval": 96, "row": 1},
        {"x": 1, "y": 1.5, "label": "1", "secondary": "!", "keyval": 49, "row": 1},
        {"x": 2, "y": 1.5, "label": "2", "secondary": "@", "keyval": 50, "row": 1},
        {"x": 3, "y": 1.5, "label": "3", "secondary": "#", "keyval": 51, "row": 1},
        {"x": 4, "y": 1.5, "label": "4", "secondary": "$", "keyval": 52, "row": 1},
        {"x": 5, "y": 1.5, "label": "5", "secondary": "%", "keyval": 53, "row": 1},
        {"x": 6, "y": 1.5, "label": "6", "secondary": "^", "keyval": 54, "row": 1},
        {"x": 7, "y": 1.5, "label": "7", "secondary": "&", "keyval": 55, "row": 1},
        {"x": 8, "y": 1.5, "label": "8", "secondary": "*", "keyval": 56, "row": 1},
        {"x": 9, "y": 1.5, "label": "9", "secondary": "(", "keyval": 57, "row": 1},
        {"x": 10, "y": 1.5, "label": "0", "secondary": ")", "keyval": 48, "row": 1},
        {"x": 11, "y": 1.5, "label": "-", "secondary": "_", "keyval": 45, "row": 1},
        {"x": 12, "y": 1.5, "label": "=", "secondary": "+", "keyval": 61, "row": 1},
        {
            "x": 13,
            "y": 1.5,
            "width": 2,
            "label": "Bksp",
            "keyval": 65288,
            "row": 1,
            "special": True,
        },
        # Nav cluster
        {"x": 15.25, "y": 1.5, "label": "Ins", "keyval": 65379, "row": 1},
        {"x": 16.25, "y": 1.5, "label": "Hm", "keyval": 65360, "row": 1},
        {"x": 17.25, "y": 1.5, "label": "PU", "keyval": 65365, "row": 1},
        # Numpad top
        {"x": 18.5, "y": 1.5, "label": "Num", "keyval": 65407, "row": 1},
        {"x": 19.5, "y": 1.5, "label": "/", "keyval": 65455, "row": 1},
        {"x": 20.5, "y": 1.5, "label": "*", "keyval": 65450, "row": 1},
        {"x": 21.5, "y": 1.5, "label": "-", "keyval": 65453, "row": 1},
        # === Tab row ===
        {
            "x": 0,
            "y": 2.5,
            "width": 1.5,
            "label": "Tab",
            "keyval": 65289,
            "row": 2,
            "special": True,
        },
        {"x": 1.5, "y": 2.5, "label": "Q", "keyval": 113, "row": 2},
        {"x": 2.5, "y": 2.5, "label": "W", "keyval": 119, "row": 2},
        {"x": 3.5, "y": 2.5, "label": "E", "keyval": 101, "row": 2},
        {"x": 4.5, "y": 2.5, "label": "R", "keyval": 114, "row": 2},
        {"x": 5.5, "y": 2.5, "label": "T", "keyval": 116, "row": 2},
        {"x": 6.5, "y": 2.5, "label": "Y", "keyval": 121, "row": 2},
        {"x": 7.5, "y": 2.5, "label": "U", "keyval": 117, "row": 2},
        {"x": 8.5, "y": 2.5, "label": "I", "keyval": 105, "row": 2},
        {"x": 9.5, "y": 2.5, "label": "O", "keyval": 111, "row": 2},
        {"x": 10.5, "y": 2.5, "label": "P", "keyval": 112, "row": 2},
        {"x": 11.5, "y": 2.5, "label": "[", "secondary": "{", "keyval": 91, "row": 2},
        {"x": 12.5, "y": 2.5, "label": "]", "secondary": "}", "keyval": 93, "row": 2},
        {
            "x": 13.5,
            "y": 2.5,
            "width": 1.5,
            "label": "\\",
            "secondary": "|",
            "keyval": 92,
            "row": 2,
        },
        # Nav
        {"x": 15.25, "y": 2.5, "label": "Del", "keyval": 65535, "row": 2},
        {"x": 16.25, "y": 2.5, "label": "End", "keyval": 65367, "row": 2},
        {"x": 17.25, "y": 2.5, "label": "PD", "keyval": 65366, "row": 2},
        # Numpad
        {"x": 18.5, "y": 2.5, "label": "7", "keyval": 65463, "row": 2},
        {"x": 19.5, "y": 2.5, "label": "8", "keyval": 65464, "row": 2},
        {"x": 20.5, "y": 2.5, "label": "9", "keyval": 65465, "row": 2},
        {"x": 21.5, "y": 2.5, "height": 2, "label": "+", "keyval": 65451, "row": 2},
        # === Caps row ===
        {
            "x": 0,
            "y": 3.5,
            "width": 1.75,
            "label": "Caps",
            "keyval": 65509,
            "row": 3,
            "modifier": True,
        },
        {"x": 1.75, "y": 3.5, "label": "A", "keyval": 97, "row": 3},
        {"x": 2.75, "y": 3.5, "label": "S", "keyval": 115, "row": 3},
        {"x": 3.75, "y": 3.5, "label": "D", "keyval": 100, "row": 3},
        {"x": 4.75, "y": 3.5, "label": "F", "keyval": 102, "row": 3},
        {"x": 5.75, "y": 3.5, "label": "G", "keyval": 103, "row": 3},
        {"x": 6.75, "y": 3.5, "label": "H", "keyval": 104, "row": 3},
        {"x": 7.75, "y": 3.5, "label": "J", "keyval": 106, "row": 3},
        {"x": 8.75, "y": 3.5, "label": "K", "keyval": 107, "row": 3},
        {"x": 9.75, "y": 3.5, "label": "L", "keyval": 108, "row": 3},
        {"x": 10.75, "y": 3.5, "label": ";", "secondary": ":", "keyval": 59, "row": 3},
        {"x": 11.75, "y": 3.5, "label": "'", "secondary": '"', "keyval": 39, "row": 3},
        {
            "x": 12.75,
            "y": 3.5,
            "width": 2.25,
            "label": "Enter",
            "keyval": 65293,
            "row": 3,
            "special": True,
        },
        # Numpad
        {"x": 18.5, "y": 3.5, "label": "4", "keyval": 65460, "row": 3},
        {"x": 19.5, "y": 3.5, "label": "5", "keyval": 65461, "row": 3},
        {"x": 20.5, "y": 3.5, "label": "6", "keyval": 65462, "row": 3},
        # === Shift row ===
        {
            "x": 0,
            "y": 4.5,
            "width": 2.25,
            "label": "Shift",
            "keyval": 65505,
            "row": 4,
            "modifier": True,
        },
        {"x": 2.25, "y": 4.5, "label": "Z", "keyval": 122, "row": 4},
        {"x": 3.25, "y": 4.5, "label": "X", "keyval": 120, "row": 4},
        {"x": 4.25, "y": 4.5, "label": "C", "keyval": 99, "row": 4},
        {"x": 5.25, "y": 4.5, "label": "V", "keyval": 118, "row": 4},
        {"x": 6.25, "y": 4.5, "label": "B", "keyval": 98, "row": 4},
        {"x": 7.25, "y": 4.5, "label": "N", "keyval": 110, "row": 4},
        {"x": 8.25, "y": 4.5, "label": "M", "keyval": 109, "row": 4},
        {"x": 9.25, "y": 4.5, "label": ",", "secondary": "<", "keyval": 44, "row": 4},
        {"x": 10.25, "y": 4.5, "label": ".", "secondary": ">", "keyval": 46, "row": 4},
        {"x": 11.25, "y": 4.5, "label": "/", "secondary": "?", "keyval": 47, "row": 4},
        {
            "x": 12.25,
            "y": 4.5,
            "width": 2.75,
            "label": "Shift",
            "keyval": 65506,
            "row": 4,
            "modifier": True,
        },
        # Arrow up
        {"x": 16.25, "y": 4.5, "label": "^", "keyval": 65362, "row": 4},
        # Numpad
        {"x": 18.5, "y": 4.5, "label": "1", "keyval": 65457, "row": 4},
        {"x": 19.5, "y": 4.5, "label": "2", "keyval": 65458, "row": 4},
        {"x": 20.5, "y": 4.5, "label": "3", "keyval": 65459, "row": 4},
        {"x": 21.5, "y": 4.5, "height": 2, "label": "Ent", "keyval": 65421, "row": 4},
        # === Bottom row ===
        {
            "x": 0,
            "y": 5.5,
            "width": 1.25,
            "label": "Ctrl",
            "keyval": 65507,
            "row": 5,
            "modifier": True,
        },
        {
            "x": 1.25,
            "y": 5.5,
            "width": 1.25,
            "label": "Super",
            "keyval": 65515,
            "row": 5,
            "modifier": True,
        },
        {
            "x": 2.5,
            "y": 5.5,
            "width": 1.25,
            "label": "Alt",
            "keyval": 65513,
            "row": 5,
            "modifier": True,
        },
        {"x": 3.75, "y": 5.5, "width": 6.25, "label": "", "keyval": 32, "row": 5},
        {
            "x": 10,
            "y": 5.5,
            "width": 1.25,
            "label": "Alt",
            "keyval": 65514,
            "row": 5,
            "modifier": True,
        },
        {
            "x": 11.25,
            "y": 5.5,
            "width": 1.25,
            "label": "Super",
            "keyval": 65516,
            "row": 5,
            "modifier": True,
        },
        {"x": 12.5, "y": 5.5, "width": 1.25, "label": "Menu", "keyval": 65383, "row": 5},
        {
            "x": 13.75,
            "y": 5.5,
            "width": 1.25,
            "label": "Ctrl",
            "keyval": 65508,
            "row": 5,
            "modifier": True,
        },
        # Arrows
        {"x": 15.25, "y": 5.5, "label": "<", "keyval": 65361, "row": 5},
        {"x": 16.25, "y": 5.5, "label": "v", "keyval": 65364, "row": 5},
        {"x": 17.25, "y": 5.5, "label": ">", "keyval": 65363, "row": 5},
        # Numpad
        {"x": 18.5, "y": 5.5, "width": 2, "label": "0", "keyval": 65456, "row": 5},
        {"x": 20.5, "y": 5.5, "label": ".", "keyval": 65454, "row": 5},
    ],
}

# ANSI-87 TKL (Tenkeyless - no numpad)
ANSI_87_DATA = {
    "id": "ansi-87",
    "name": "TKL (87-key)",
    "type": "ansi-87",
    "width": 18.25,
    "height": 6.5,
    "keys": [
        # === Function row ===
        {"x": 0, "y": 0, "label": "Esc", "keyval": 65307, "row": 0},
        {"x": 2, "y": 0, "label": "F1", "keyval": 65470, "row": 0},
        {"x": 3, "y": 0, "label": "F2", "keyval": 65471, "row": 0},
        {"x": 4, "y": 0, "label": "F3", "keyval": 65472, "row": 0},
        {"x": 5, "y": 0, "label": "F4", "keyval": 65473, "row": 0},
        {"x": 6.5, "y": 0, "label": "F5", "keyval": 65474, "row": 0},
        {"x": 7.5, "y": 0, "label": "F6", "keyval": 65475, "row": 0},
        {"x": 8.5, "y": 0, "label": "F7", "keyval": 65476, "row": 0},
        {"x": 9.5, "y": 0, "label": "F8", "keyval": 65477, "row": 0},
        {"x": 11, "y": 0, "label": "F9", "keyval": 65478, "row": 0},
        {"x": 12, "y": 0, "label": "F10", "keyval": 65479, "row": 0},
        {"x": 13, "y": 0, "label": "F11", "keyval": 65480, "row": 0},
        {"x": 14, "y": 0, "label": "F12", "keyval": 65481, "row": 0},
        # Print/Scroll/Pause
        {"x": 15.25, "y": 0, "label": "Prt", "keyval": 65377, "row": 0},
        {"x": 16.25, "y": 0, "label": "Scr", "keyval": 65300, "row": 0},
        {"x": 17.25, "y": 0, "label": "Pse", "keyval": 65299, "row": 0},
        # === Number row ===
        {"x": 0, "y": 1.5, "label": "`", "secondary": "~", "keyval": 96, "row": 1},
        {"x": 1, "y": 1.5, "label": "1", "secondary": "!", "keyval": 49, "row": 1},
        {"x": 2, "y": 1.5, "label": "2", "secondary": "@", "keyval": 50, "row": 1},
        {"x": 3, "y": 1.5, "label": "3", "secondary": "#", "keyval": 51, "row": 1},
        {"x": 4, "y": 1.5, "label": "4", "secondary": "$", "keyval": 52, "row": 1},
        {"x": 5, "y": 1.5, "label": "5", "secondary": "%", "keyval": 53, "row": 1},
        {"x": 6, "y": 1.5, "label": "6", "secondary": "^", "keyval": 54, "row": 1},
        {"x": 7, "y": 1.5, "label": "7", "secondary": "&", "keyval": 55, "row": 1},
        {"x": 8, "y": 1.5, "label": "8", "secondary": "*", "keyval": 56, "row": 1},
        {"x": 9, "y": 1.5, "label": "9", "secondary": "(", "keyval": 57, "row": 1},
        {"x": 10, "y": 1.5, "label": "0", "secondary": ")", "keyval": 48, "row": 1},
        {"x": 11, "y": 1.5, "label": "-", "secondary": "_", "keyval": 45, "row": 1},
        {"x": 12, "y": 1.5, "label": "=", "secondary": "+", "keyval": 61, "row": 1},
        {
            "x": 13,
            "y": 1.5,
            "width": 2,
            "label": "Bksp",
            "keyval": 65288,
            "row": 1,
            "special": True,
        },
        # Nav cluster
        {"x": 15.25, "y": 1.5, "label": "Ins", "keyval": 65379, "row": 1},
        {"x": 16.25, "y": 1.5, "label": "Hm", "keyval": 65360, "row": 1},
        {"x": 17.25, "y": 1.5, "label": "PU", "keyval": 65365, "row": 1},
        # === Tab row ===
        {
            "x": 0,
            "y": 2.5,
            "width": 1.5,
            "label": "Tab",
            "keyval": 65289,
            "row": 2,
            "special": True,
        },
        {"x": 1.5, "y": 2.5, "label": "Q", "keyval": 113, "row": 2},
        {"x": 2.5, "y": 2.5, "label": "W", "keyval": 119, "row": 2},
        {"x": 3.5, "y": 2.5, "label": "E", "keyval": 101, "row": 2},
        {"x": 4.5, "y": 2.5, "label": "R", "keyval": 114, "row": 2},
        {"x": 5.5, "y": 2.5, "label": "T", "keyval": 116, "row": 2},
        {"x": 6.5, "y": 2.5, "label": "Y", "keyval": 121, "row": 2},
        {"x": 7.5, "y": 2.5, "label": "U", "keyval": 117, "row": 2},
        {"x": 8.5, "y": 2.5, "label": "I", "keyval": 105, "row": 2},
        {"x": 9.5, "y": 2.5, "label": "O", "keyval": 111, "row": 2},
        {"x": 10.5, "y": 2.5, "label": "P", "keyval": 112, "row": 2},
        {"x": 11.5, "y": 2.5, "label": "[", "secondary": "{", "keyval": 91, "row": 2},
        {"x": 12.5, "y": 2.5, "label": "]", "secondary": "}", "keyval": 93, "row": 2},
        {
            "x": 13.5,
            "y": 2.5,
            "width": 1.5,
            "label": "\\",
            "secondary": "|",
            "keyval": 92,
            "row": 2,
        },
        # Nav
        {"x": 15.25, "y": 2.5, "label": "Del", "keyval": 65535, "row": 2},
        {"x": 16.25, "y": 2.5, "label": "End", "keyval": 65367, "row": 2},
        {"x": 17.25, "y": 2.5, "label": "PD", "keyval": 65366, "row": 2},
        # === Caps row ===
        {
            "x": 0,
            "y": 3.5,
            "width": 1.75,
            "label": "Caps",
            "keyval": 65509,
            "row": 3,
            "modifier": True,
        },
        {"x": 1.75, "y": 3.5, "label": "A", "keyval": 97, "row": 3},
        {"x": 2.75, "y": 3.5, "label": "S", "keyval": 115, "row": 3},
        {"x": 3.75, "y": 3.5, "label": "D", "keyval": 100, "row": 3},
        {"x": 4.75, "y": 3.5, "label": "F", "keyval": 102, "row": 3},
        {"x": 5.75, "y": 3.5, "label": "G", "keyval": 103, "row": 3},
        {"x": 6.75, "y": 3.5, "label": "H", "keyval": 104, "row": 3},
        {"x": 7.75, "y": 3.5, "label": "J", "keyval": 106, "row": 3},
        {"x": 8.75, "y": 3.5, "label": "K", "keyval": 107, "row": 3},
        {"x": 9.75, "y": 3.5, "label": "L", "keyval": 108, "row": 3},
        {"x": 10.75, "y": 3.5, "label": ";", "secondary": ":", "keyval": 59, "row": 3},
        {"x": 11.75, "y": 3.5, "label": "'", "secondary": '"', "keyval": 39, "row": 3},
        {
            "x": 12.75,
            "y": 3.5,
            "width": 2.25,
            "label": "Enter",
            "keyval": 65293,
            "row": 3,
            "special": True,
        },
        # === Shift row ===
        {
            "x": 0,
            "y": 4.5,
            "width": 2.25,
            "label": "Shift",
            "keyval": 65505,
            "row": 4,
            "modifier": True,
        },
        {"x": 2.25, "y": 4.5, "label": "Z", "keyval": 122, "row": 4},
        {"x": 3.25, "y": 4.5, "label": "X", "keyval": 120, "row": 4},
        {"x": 4.25, "y": 4.5, "label": "C", "keyval": 99, "row": 4},
        {"x": 5.25, "y": 4.5, "label": "V", "keyval": 118, "row": 4},
        {"x": 6.25, "y": 4.5, "label": "B", "keyval": 98, "row": 4},
        {"x": 7.25, "y": 4.5, "label": "N", "keyval": 110, "row": 4},
        {"x": 8.25, "y": 4.5, "label": "M", "keyval": 109, "row": 4},
        {"x": 9.25, "y": 4.5, "label": ",", "secondary": "<", "keyval": 44, "row": 4},
        {"x": 10.25, "y": 4.5, "label": ".", "secondary": ">", "keyval": 46, "row": 4},
        {"x": 11.25, "y": 4.5, "label": "/", "secondary": "?", "keyval": 47, "row": 4},
        {
            "x": 12.25,
            "y": 4.5,
            "width": 2.75,
            "label": "Shift",
            "keyval": 65506,
            "row": 4,
            "modifier": True,
        },
        # Arrow up
        {"x": 16.25, "y": 4.5, "label": "^", "keyval": 65362, "row": 4},
        # === Bottom row ===
        {
            "x": 0,
            "y": 5.5,
            "width": 1.25,
            "label": "Ctrl",
            "keyval": 65507,
            "row": 5,
            "modifier": True,
        },
        {
            "x": 1.25,
            "y": 5.5,
            "width": 1.25,
            "label": "Super",
            "keyval": 65515,
            "row": 5,
            "modifier": True,
        },
        {
            "x": 2.5,
            "y": 5.5,
            "width": 1.25,
            "label": "Alt",
            "keyval": 65513,
            "row": 5,
            "modifier": True,
        },
        {"x": 3.75, "y": 5.5, "width": 6.25, "label": "", "keyval": 32, "row": 5},
        {
            "x": 10,
            "y": 5.5,
            "width": 1.25,
            "label": "Alt",
            "keyval": 65514,
            "row": 5,
            "modifier": True,
        },
        {
            "x": 11.25,
            "y": 5.5,
            "width": 1.25,
            "label": "Super",
            "keyval": 65516,
            "row": 5,
            "modifier": True,
        },
        {"x": 12.5, "y": 5.5, "width": 1.25, "label": "Menu", "keyval": 65383, "row": 5},
        {
            "x": 13.75,
            "y": 5.5,
            "width": 1.25,
            "label": "Ctrl",
            "keyval": 65508,
            "row": 5,
            "modifier": True,
        },
        # Arrows
        {"x": 15.25, "y": 5.5, "label": "<", "keyval": 65361, "row": 5},
        {"x": 16.25, "y": 5.5, "label": "v", "keyval": 65364, "row": 5},
        {"x": 17.25, "y": 5.5, "label": ">", "keyval": 65363, "row": 5},
    ],
}

# ANSI-60 Compact (no F-row, no nav cluster)
ANSI_60_DATA = {
    "id": "ansi-60",
    "name": "60% Compact",
    "type": "ansi-60",
    "width": 15,
    "height": 5,
    "keys": [
        # === Number row ===
        {"x": 0, "y": 0, "label": "Esc", "keyval": 65307, "row": 0},
        {"x": 1, "y": 0, "label": "1", "secondary": "!", "keyval": 49, "row": 0},
        {"x": 2, "y": 0, "label": "2", "secondary": "@", "keyval": 50, "row": 0},
        {"x": 3, "y": 0, "label": "3", "secondary": "#", "keyval": 51, "row": 0},
        {"x": 4, "y": 0, "label": "4", "secondary": "$", "keyval": 52, "row": 0},
        {"x": 5, "y": 0, "label": "5", "secondary": "%", "keyval": 53, "row": 0},
        {"x": 6, "y": 0, "label": "6", "secondary": "^", "keyval": 54, "row": 0},
        {"x": 7, "y": 0, "label": "7", "secondary": "&", "keyval": 55, "row": 0},
        {"x": 8, "y": 0, "label": "8", "secondary": "*", "keyval": 56, "row": 0},
        {"x": 9, "y": 0, "label": "9", "secondary": "(", "keyval": 57, "row": 0},
        {"x": 10, "y": 0, "label": "0", "secondary": ")", "keyval": 48, "row": 0},
        {"x": 11, "y": 0, "label": "-", "secondary": "_", "keyval": 45, "row": 0},
        {"x": 12, "y": 0, "label": "=", "secondary": "+", "keyval": 61, "row": 0},
        {"x": 13, "y": 0, "width": 2, "label": "Bksp", "keyval": 65288, "row": 0, "special": True},
        # === Tab row ===
        {"x": 0, "y": 1, "width": 1.5, "label": "Tab", "keyval": 65289, "row": 1, "special": True},
        {"x": 1.5, "y": 1, "label": "Q", "keyval": 113, "row": 1},
        {"x": 2.5, "y": 1, "label": "W", "keyval": 119, "row": 1},
        {"x": 3.5, "y": 1, "label": "E", "keyval": 101, "row": 1},
        {"x": 4.5, "y": 1, "label": "R", "keyval": 114, "row": 1},
        {"x": 5.5, "y": 1, "label": "T", "keyval": 116, "row": 1},
        {"x": 6.5, "y": 1, "label": "Y", "keyval": 121, "row": 1},
        {"x": 7.5, "y": 1, "label": "U", "keyval": 117, "row": 1},
        {"x": 8.5, "y": 1, "label": "I", "keyval": 105, "row": 1},
        {"x": 9.5, "y": 1, "label": "O", "keyval": 111, "row": 1},
        {"x": 10.5, "y": 1, "label": "P", "keyval": 112, "row": 1},
        {"x": 11.5, "y": 1, "label": "[", "secondary": "{", "keyval": 91, "row": 1},
        {"x": 12.5, "y": 1, "label": "]", "secondary": "}", "keyval": 93, "row": 1},
        {"x": 13.5, "y": 1, "width": 1.5, "label": "\\", "secondary": "|", "keyval": 92, "row": 1},
        # === Caps row ===
        {
            "x": 0,
            "y": 2,
            "width": 1.75,
            "label": "Caps",
            "keyval": 65509,
            "row": 2,
            "modifier": True,
        },
        {"x": 1.75, "y": 2, "label": "A", "keyval": 97, "row": 2},
        {"x": 2.75, "y": 2, "label": "S", "keyval": 115, "row": 2},
        {"x": 3.75, "y": 2, "label": "D", "keyval": 100, "row": 2},
        {"x": 4.75, "y": 2, "label": "F", "keyval": 102, "row": 2},
        {"x": 5.75, "y": 2, "label": "G", "keyval": 103, "row": 2},
        {"x": 6.75, "y": 2, "label": "H", "keyval": 104, "row": 2},
        {"x": 7.75, "y": 2, "label": "J", "keyval": 106, "row": 2},
        {"x": 8.75, "y": 2, "label": "K", "keyval": 107, "row": 2},
        {"x": 9.75, "y": 2, "label": "L", "keyval": 108, "row": 2},
        {"x": 10.75, "y": 2, "label": ";", "secondary": ":", "keyval": 59, "row": 2},
        {"x": 11.75, "y": 2, "label": "'", "secondary": '"', "keyval": 39, "row": 2},
        {
            "x": 12.75,
            "y": 2,
            "width": 2.25,
            "label": "Enter",
            "keyval": 65293,
            "row": 2,
            "special": True,
        },
        # === Shift row ===
        {
            "x": 0,
            "y": 3,
            "width": 2.25,
            "label": "Shift",
            "keyval": 65505,
            "row": 3,
            "modifier": True,
        },
        {"x": 2.25, "y": 3, "label": "Z", "keyval": 122, "row": 3},
        {"x": 3.25, "y": 3, "label": "X", "keyval": 120, "row": 3},
        {"x": 4.25, "y": 3, "label": "C", "keyval": 99, "row": 3},
        {"x": 5.25, "y": 3, "label": "V", "keyval": 118, "row": 3},
        {"x": 6.25, "y": 3, "label": "B", "keyval": 98, "row": 3},
        {"x": 7.25, "y": 3, "label": "N", "keyval": 110, "row": 3},
        {"x": 8.25, "y": 3, "label": "M", "keyval": 109, "row": 3},
        {"x": 9.25, "y": 3, "label": ",", "secondary": "<", "keyval": 44, "row": 3},
        {"x": 10.25, "y": 3, "label": ".", "secondary": ">", "keyval": 46, "row": 3},
        {"x": 11.25, "y": 3, "label": "/", "secondary": "?", "keyval": 47, "row": 3},
        {
            "x": 12.25,
            "y": 3,
            "width": 2.75,
            "label": "Shift",
            "keyval": 65506,
            "row": 3,
            "modifier": True,
        },
        # === Bottom row ===
        {
            "x": 0,
            "y": 4,
            "width": 1.25,
            "label": "Ctrl",
            "keyval": 65507,
            "row": 4,
            "modifier": True,
        },
        {
            "x": 1.25,
            "y": 4,
            "width": 1.25,
            "label": "Super",
            "keyval": 65515,
            "row": 4,
            "modifier": True,
        },
        {
            "x": 2.5,
            "y": 4,
            "width": 1.25,
            "label": "Alt",
            "keyval": 65513,
            "row": 4,
            "modifier": True,
        },
        {"x": 3.75, "y": 4, "width": 6.25, "label": "", "keyval": 32, "row": 4},
        {
            "x": 10,
            "y": 4,
            "width": 1.25,
            "label": "Alt",
            "keyval": 65514,
            "row": 4,
            "modifier": True,
        },
        {
            "x": 11.25,
            "y": 4,
            "width": 1.25,
            "label": "Super",
            "keyval": 65516,
            "row": 4,
            "modifier": True,
        },
        {"x": 12.5, "y": 4, "width": 1.25, "label": "Menu", "keyval": 65383, "row": 4},
        {
            "x": 13.75,
            "y": 4,
            "width": 1.25,
            "label": "Ctrl",
            "keyval": 65508,
            "row": 4,
            "modifier": True,
        },
    ],
}

# Default alias for backwards compatibility
DEFAULT_LAYOUT_DATA = ANSI_87_DATA


# Mac ANSI layout data (embedded for reliable loading)
# Compact Magic Keyboard style - all rows align to 14.5 width
MAC_LAYOUT_DATA = {
    "id": "mac-ansi",
    "name": "Apple Magic Keyboard",
    "type": "mac-ansi",
    "width": 14.5,
    "height": 6,
    "keys": [
        # Function row (ends at 14.5)
        {"x": 0, "y": 0, "label": "Esc", "keyval": 65307, "row": 0},
        {"x": 1, "y": 0, "label": "F1", "keyval": 65470, "row": 0},
        {"x": 2, "y": 0, "label": "F2", "keyval": 65471, "row": 0},
        {"x": 3, "y": 0, "label": "F3", "keyval": 65472, "row": 0},
        {"x": 4, "y": 0, "label": "F4", "keyval": 65473, "row": 0},
        {"x": 5, "y": 0, "label": "F5", "keyval": 65474, "row": 0},
        {"x": 6, "y": 0, "label": "F6", "keyval": 65475, "row": 0},
        {"x": 7, "y": 0, "label": "F7", "keyval": 65476, "row": 0},
        {"x": 8, "y": 0, "label": "F8", "keyval": 65477, "row": 0},
        {"x": 9, "y": 0, "label": "F9", "keyval": 65478, "row": 0},
        {"x": 10, "y": 0, "label": "F10", "keyval": 65479, "row": 0},
        {"x": 11, "y": 0, "label": "F11", "keyval": 65480, "row": 0},
        {"x": 12, "y": 0, "label": "F12", "keyval": 65481, "row": 0},
        {"x": 13, "y": 0, "width": 1.5, "label": "pwr", "keyval": 0, "row": 0},
        # Number row (ends at 14.5)
        {"x": 0, "y": 1, "label": "`", "secondary": "~", "keyval": 96, "row": 1},
        {"x": 1, "y": 1, "label": "1", "secondary": "!", "keyval": 49, "row": 1},
        {"x": 2, "y": 1, "label": "2", "secondary": "@", "keyval": 50, "row": 1},
        {"x": 3, "y": 1, "label": "3", "secondary": "#", "keyval": 51, "row": 1},
        {"x": 4, "y": 1, "label": "4", "secondary": "$", "keyval": 52, "row": 1},
        {"x": 5, "y": 1, "label": "5", "secondary": "%", "keyval": 53, "row": 1},
        {"x": 6, "y": 1, "label": "6", "secondary": "^", "keyval": 54, "row": 1},
        {"x": 7, "y": 1, "label": "7", "secondary": "&", "keyval": 55, "row": 1},
        {"x": 8, "y": 1, "label": "8", "secondary": "*", "keyval": 56, "row": 1},
        {"x": 9, "y": 1, "label": "9", "secondary": "(", "keyval": 57, "row": 1},
        {"x": 10, "y": 1, "label": "0", "secondary": ")", "keyval": 48, "row": 1},
        {"x": 11, "y": 1, "label": "-", "secondary": "_", "keyval": 45, "row": 1},
        {"x": 12, "y": 1, "label": "=", "secondary": "+", "keyval": 61, "row": 1},
        {"x": 13, "y": 1, "width": 1.5, "label": "del", "keyval": 65288, "row": 1, "special": True},
        # Tab row (ends at 14.5)
        {"x": 0, "y": 2, "width": 1.5, "label": "Tab", "keyval": 65289, "row": 2, "special": True},
        {"x": 1.5, "y": 2, "label": "Q", "keyval": 113, "row": 2},
        {"x": 2.5, "y": 2, "label": "W", "keyval": 119, "row": 2},
        {"x": 3.5, "y": 2, "label": "E", "keyval": 101, "row": 2},
        {"x": 4.5, "y": 2, "label": "R", "keyval": 114, "row": 2},
        {"x": 5.5, "y": 2, "label": "T", "keyval": 116, "row": 2},
        {"x": 6.5, "y": 2, "label": "Y", "keyval": 121, "row": 2},
        {"x": 7.5, "y": 2, "label": "U", "keyval": 117, "row": 2},
        {"x": 8.5, "y": 2, "label": "I", "keyval": 105, "row": 2},
        {"x": 9.5, "y": 2, "label": "O", "keyval": 111, "row": 2},
        {"x": 10.5, "y": 2, "label": "P", "keyval": 112, "row": 2},
        {"x": 11.5, "y": 2, "label": "[", "secondary": "{", "keyval": 91, "row": 2},
        {"x": 12.5, "y": 2, "label": "]", "secondary": "}", "keyval": 93, "row": 2},
        {"x": 13.5, "y": 2, "label": "\\", "secondary": "|", "keyval": 92, "row": 2},
        # Caps row (ends at 14.5)
        {
            "x": 0,
            "y": 3,
            "width": 1.75,
            "label": "Caps",
            "keyval": 65509,
            "row": 3,
            "modifier": True,
        },
        {"x": 1.75, "y": 3, "label": "A", "keyval": 97, "row": 3},
        {"x": 2.75, "y": 3, "label": "S", "keyval": 115, "row": 3},
        {"x": 3.75, "y": 3, "label": "D", "keyval": 100, "row": 3},
        {"x": 4.75, "y": 3, "label": "F", "keyval": 102, "row": 3},
        {"x": 5.75, "y": 3, "label": "G", "keyval": 103, "row": 3},
        {"x": 6.75, "y": 3, "label": "H", "keyval": 104, "row": 3},
        {"x": 7.75, "y": 3, "label": "J", "keyval": 106, "row": 3},
        {"x": 8.75, "y": 3, "label": "K", "keyval": 107, "row": 3},
        {"x": 9.75, "y": 3, "label": "L", "keyval": 108, "row": 3},
        {"x": 10.75, "y": 3, "label": ";", "secondary": ":", "keyval": 59, "row": 3},
        {"x": 11.75, "y": 3, "label": "'", "secondary": '"', "keyval": 39, "row": 3},
        {
            "x": 12.75,
            "y": 3,
            "width": 1.75,
            "label": "return",
            "keyval": 65293,
            "row": 3,
            "special": True,
        },
        # Shift row (ends at 14.5)
        {
            "x": 0,
            "y": 4,
            "width": 2.25,
            "label": "Shift",
            "keyval": 65505,
            "row": 4,
            "modifier": True,
        },
        {"x": 2.25, "y": 4, "label": "Z", "keyval": 122, "row": 4},
        {"x": 3.25, "y": 4, "label": "X", "keyval": 120, "row": 4},
        {"x": 4.25, "y": 4, "label": "C", "keyval": 99, "row": 4},
        {"x": 5.25, "y": 4, "label": "V", "keyval": 118, "row": 4},
        {"x": 6.25, "y": 4, "label": "B", "keyval": 98, "row": 4},
        {"x": 7.25, "y": 4, "label": "N", "keyval": 110, "row": 4},
        {"x": 8.25, "y": 4, "label": "M", "keyval": 109, "row": 4},
        {"x": 9.25, "y": 4, "label": ",", "secondary": "<", "keyval": 44, "row": 4},
        {"x": 10.25, "y": 4, "label": ".", "secondary": ">", "keyval": 46, "row": 4},
        {"x": 11.25, "y": 4, "label": "/", "secondary": "?", "keyval": 47, "row": 4},
        {
            "x": 12.25,
            "y": 4,
            "width": 2.25,
            "label": "Shift",
            "keyval": 65506,
            "row": 4,
            "modifier": True,
        },
        # Bottom row - Mac style with arrow keys fitting within 14.5 width
        {"x": 0, "y": 5, "width": 1.25, "label": "fn", "keyval": 0, "row": 5, "modifier": True},
        {
            "x": 1.25,
            "y": 5,
            "width": 1.25,
            "label": "ctrl",
            "keyval": 65507,
            "row": 5,
            "modifier": True,
        },
        {
            "x": 2.5,
            "y": 5,
            "width": 1.25,
            "label": "opt",
            "keyval": 65513,
            "row": 5,
            "modifier": True,
        },
        {
            "x": 3.75,
            "y": 5,
            "width": 1.25,
            "label": "cmd",
            "keyval": 65515,
            "row": 5,
            "modifier": True,
        },
        {"x": 5, "y": 5, "width": 4, "label": "", "keyval": 32, "row": 5},
        {
            "x": 9,
            "y": 5,
            "width": 1.25,
            "label": "cmd",
            "keyval": 65516,
            "row": 5,
            "modifier": True,
        },
        {
            "x": 10.25,
            "y": 5,
            "width": 1.25,
            "label": "opt",
            "keyval": 65514,
            "row": 5,
            "modifier": True,
        },
        # Arrow keys in inverted T (11.5 to 14.5)
        # Left/right are full height, up/down are half-height stacked
        {"x": 11.5, "y": 5, "width": 1, "height": 1, "label": "<", "keyval": 65361, "row": 5},
        {"x": 12.5, "y": 5, "width": 1, "height": 0.5, "label": "^", "keyval": 65362, "row": 5},
        {"x": 12.5, "y": 5.5, "width": 1, "height": 0.5, "label": "v", "keyval": 65364, "row": 5},
        {"x": 13.5, "y": 5, "width": 1, "height": 1, "label": ">", "keyval": 65363, "row": 5},
    ],
}


class KeyboardView(Gtk.DrawingArea):
    """Visual keyboard display with Cairo rendering."""

    __gtype_name__ = "KeyboardView"

    __gsignals__ = {
        "key-clicked": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (object,),  # Key
        ),
    }

    def __init__(self, keyboard_type: KeyboardType | None = None) -> None:
        super().__init__()

        self._keyboard_type = keyboard_type

        # Layout
        self._layout = self._load_layout(keyboard_type)

        # State
        self._hover_key: Key | None = None
        self._active_keys: set[int] = set()  # keyvals of active keys
        self._shortcut_keys: dict[int, Shortcut] = {}  # keyval -> shortcut

        # Colors - style based on keyboard type
        self._is_mac_style = keyboard_type and keyboard_type.is_apple
        self._setup_colors()

        # Drawing setup
        self.set_draw_func(self._on_draw)
        self.set_content_width(int(self._layout.width * 40))
        self.set_content_height(int(self._layout.height * 40))

        # Event handling
        self.set_can_focus(True)

        # Motion events for hover
        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("motion", self._on_motion)
        motion_controller.connect("leave", self._on_leave)
        self.add_controller(motion_controller)

        # Click events
        click_controller = Gtk.GestureClick()
        click_controller.connect("pressed", self._on_click)
        self.add_controller(click_controller)

        self.add_css_class("keyboard-view")

    def _setup_colors(self) -> None:
        """Set up colors based on keyboard style."""
        if self._is_mac_style:
            # Apple-style: silver/white aluminum look
            self._bg_color = (0.85, 0.85, 0.85, 0)  # Transparent
            self._key_color = (0.95, 0.95, 0.95, 1)  # White keys
            self._key_shadow_color = (0.7, 0.7, 0.7, 0.5)  # Subtle shadow
            self._key_hover_color = (0.88, 0.88, 0.88, 1)
            self._key_active_color = (0.6, 0.75, 0.95, 1)  # Apple blue
            self._text_color = (0.2, 0.2, 0.2, 1)  # Dark text
            self._shortcut_color = (0.6, 0.75, 0.95, 0.4)
        else:
            # PC-style: dark mechanical keyboard look
            self._bg_color = (0.15, 0.15, 0.15, 0)  # Transparent
            self._key_color = (0.25, 0.25, 0.25, 1)  # Dark keys
            self._key_shadow_color = (0.0, 0.0, 0.0, 0.4)  # Shadow
            self._key_hover_color = (0.35, 0.35, 0.35, 1)
            self._key_active_color = (0.3, 0.5, 0.8, 1)
            self._text_color = (0.9, 0.9, 0.9, 1)  # Light text
            self._shortcut_color = (0.3, 0.5, 0.8, 0.3)

    def _load_layout(self, keyboard_type: KeyboardType | None) -> KeyboardLayout:
        """Load layout based on keyboard type."""
        # Choose layout data based on type
        if keyboard_type is None:
            layout_data = ANSI_87_DATA  # Default to TKL
        elif keyboard_type.is_apple:
            layout_data = MAC_LAYOUT_DATA
        elif keyboard_type == KeyboardType.ANSI_104:
            layout_data = ANSI_104_DATA
        elif keyboard_type == KeyboardType.ANSI_87:
            layout_data = ANSI_87_DATA
        elif keyboard_type == KeyboardType.ANSI_60:
            layout_data = ANSI_60_DATA
        else:
            # Default to TKL for unknown types (ISO, etc.)
            layout_data = ANSI_87_DATA

        return self._parse_layout_data(layout_data)

    def _parse_layout_data(self, layout_data: dict) -> KeyboardLayout:
        """Parse layout data dictionary into KeyboardLayout."""
        keys = []
        for key_data in layout_data["keys"]:
            keys.append(
                Key(
                    x=key_data["x"],
                    y=key_data["y"],
                    width=key_data.get("width", 1.0),
                    height=key_data.get("height", 1.0),
                    keyval=key_data.get("keyval", 0),
                    label=key_data.get("label", ""),
                    secondary_label=key_data.get("secondary", ""),
                    row=key_data.get("row", 0),
                    is_modifier=key_data.get("modifier", False),
                    is_special=key_data.get("special", False),
                )
            )

        return KeyboardLayout(
            id=layout_data["id"],
            name=layout_data["name"],
            type=KeyboardType(layout_data["type"]),
            keys=keys,
            width=layout_data["width"],
            height=layout_data["height"],
        )

    def set_keyboard_type(self, keyboard_type: KeyboardType) -> None:
        """Change the keyboard layout type."""
        self._keyboard_type = keyboard_type
        self._is_mac_style = keyboard_type and keyboard_type.is_apple
        self._setup_colors()
        self._layout = self._load_layout(keyboard_type)
        self.set_content_width(int(self._layout.width * 40))
        self.set_content_height(int(self._layout.height * 40))
        self.queue_draw()

    def _on_draw(
        self,
        area: Gtk.DrawingArea,
        cr,
        width: int,
        height: int,
        user_data=None,
    ) -> None:
        """Draw the keyboard."""
        # Calculate scale to fit
        scale_x = width / (self._layout.width * 40)
        scale_y = height / (self._layout.height * 40)
        scale = min(scale_x, scale_y)

        # Center the keyboard
        offset_x = (width - self._layout.width * 40 * scale) / 2
        offset_y = (height - self._layout.height * 40 * scale) / 2

        # No background - transparent

        # Key unit size (40px base)
        unit = 40 * scale
        key_margin = 2 * scale
        key_radius = 5 * scale
        shadow_offset = 2 * scale

        # First pass: draw shadows for 3D effect
        for key in self._layout.keys:
            x = offset_x + key.x * unit + key_margin
            y = offset_y + key.y * unit + key_margin
            w = key.width * unit - 2 * key_margin
            h = key.height * unit - 2 * key_margin

            # Draw shadow
            cr.set_source_rgba(*self._key_shadow_color)
            self._draw_rounded_rect(cr, x + shadow_offset, y + shadow_offset, w, h, key_radius)
            cr.fill()

        # Second pass: draw keys
        for key in self._layout.keys:
            x = offset_x + key.x * unit + key_margin
            y = offset_y + key.y * unit + key_margin
            w = key.width * unit - 2 * key_margin
            h = key.height * unit - 2 * key_margin

            # Determine key color
            if key == self._hover_key:
                color = self._key_hover_color
            elif key.keyval in self._active_keys:
                color = self._key_active_color
            elif key.keyval in self._shortcut_keys:
                color = self._shortcut_color
            else:
                color = self._key_color

            # Draw key background
            cr.set_source_rgba(*color)
            self._draw_rounded_rect(cr, x, y, w, h, key_radius)
            cr.fill()

            # Draw subtle key border (lighter on top for 3D effect)
            if self._is_mac_style:
                cr.set_source_rgba(0.8, 0.8, 0.8, 0.8)
            else:
                cr.set_source_rgba(0.4, 0.4, 0.4, 0.5)
            self._draw_rounded_rect(cr, x, y, w, h, key_radius)
            cr.set_line_width(1)
            cr.stroke()

            # Draw label
            cr.set_source_rgba(*self._text_color)
            self._draw_key_label(cr, key, x, y, w, h, scale)

    def _draw_rounded_rect(self, cr, x: float, y: float, w: float, h: float, r: float) -> None:
        """Draw a rounded rectangle path."""
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def _draw_key_label(
        self,
        cr,
        key: Key,
        x: float,
        y: float,
        w: float,
        h: float,
        scale: float,
    ) -> None:
        """Draw key label text."""
        # Select font size based on label length
        label = key.label
        if len(label) <= 1:
            font_size = 14 * scale
        elif len(label) <= 3:
            font_size = 10 * scale
        else:
            font_size = 8 * scale

        cr.select_font_face("Sans", 0, 0)  # CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL
        cr.set_font_size(font_size)

        # Get text extents for centering
        extents = cr.text_extents(label)
        text_x = x + (w - extents.width) / 2 - extents.x_bearing
        text_y = y + (h - extents.height) / 2 - extents.y_bearing

        # Draw secondary label (smaller, top-left) if present
        if key.secondary_label:
            cr.set_font_size(font_size * 0.7)
            cr.move_to(x + 4 * scale, y + 12 * scale)
            cr.show_text(key.secondary_label)
            cr.set_font_size(font_size)
            text_y = y + h - 8 * scale

        cr.move_to(text_x, text_y)
        cr.show_text(label)

    def _on_motion(self, controller: Gtk.EventControllerMotion, x: float, y: float) -> None:
        """Handle mouse motion for hover effect."""
        key = self._get_key_at_position(x, y)
        if key != self._hover_key:
            self._hover_key = key
            self.queue_draw()

    def _on_leave(self, controller: Gtk.EventControllerMotion) -> None:
        """Handle mouse leaving the widget."""
        if self._hover_key:
            self._hover_key = None
            self.queue_draw()

    def _on_click(
        self,
        gesture: Gtk.GestureClick,
        n_press: int,
        x: float,
        y: float,
    ) -> None:
        """Handle mouse click on a key."""
        key = self._get_key_at_position(x, y)
        if key:
            self.emit("key-clicked", key)

    def _get_key_at_position(self, x: float, y: float) -> Key | None:
        """Find the key at the given pixel position."""
        width = self.get_width()
        height = self.get_height()

        scale_x = width / (self._layout.width * 40)
        scale_y = height / (self._layout.height * 40)
        scale = min(scale_x, scale_y)

        offset_x = (width - self._layout.width * 40 * scale) / 2
        offset_y = (height - self._layout.height * 40 * scale) / 2

        unit = 40 * scale

        # Convert to key units
        key_x = (x - offset_x) / unit
        key_y = (y - offset_y) / unit

        return self._layout.get_key_at(key_x, key_y)

    def highlight_shortcut(self, shortcut: Shortcut) -> None:
        """Highlight keys used by a shortcut."""
        self._shortcut_keys.clear()

        for binding in shortcut.bindings:
            if binding.keyval:
                self._shortcut_keys[binding.keyval] = shortcut

            # Also highlight modifier keys
            from dailydriver.models import Modifier

            if binding.modifiers & Modifier.CTRL:
                self._shortcut_keys[65507] = shortcut  # Left Ctrl
                self._shortcut_keys[65508] = shortcut  # Right Ctrl
            if binding.modifiers & Modifier.ALT:
                self._shortcut_keys[65513] = shortcut  # Left Alt
                self._shortcut_keys[65514] = shortcut  # Right Alt
            if binding.modifiers & Modifier.SUPER:
                self._shortcut_keys[65515] = shortcut  # Left Super
                self._shortcut_keys[65516] = shortcut  # Right Super
            if binding.modifiers & Modifier.SHIFT:
                self._shortcut_keys[65505] = shortcut  # Left Shift
                self._shortcut_keys[65506] = shortcut  # Right Shift

        self.queue_draw()

    def clear_highlights(self) -> None:
        """Clear all shortcut highlights."""
        self._shortcut_keys.clear()
        self.queue_draw()

    def set_active_keys(self, keyvals: set[int]) -> None:
        """Set which keys are currently active/pressed."""
        self._active_keys = keyvals
        self.queue_draw()
