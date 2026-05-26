// nightpanel GNOME Shell extension — GNOME 45+ ES module
//
// Adds a night-light button to the right side of the panel.
// State is read from ~/.config/nightpanel/nightpanel-active (presence = on).
// Toggle runs ~/.local/bin/nightpanel-toggle (the standalone orchestrator script).
// File monitor on the config dir keeps the icon in sync when toggled from
// the nightpanel app or CLI without needing a poll loop.
// When active, all other panel elements are hidden — only this button remains.

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import Clutter from 'gi://Clutter';
import St from 'gi://St';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const TOGGLE_SCRIPT = GLib.get_home_dir() + '/.local/bin/nightpanel-toggle';
const STATE_FILE    = GLib.get_home_dir() + '/.config/nightpanel/nightpanel-active';
const WATCH_DIR     = GLib.get_home_dir() + '/.config/nightpanel';

export default class NightpanelExtension extends Extension {

    enable() {
        this._active       = Gio.File.new_for_path(STATE_FILE).query_exists(null);
        this._monitor      = null;
        this._hiddenActors = [];
        this._panelHidden  = false;

        // PanelMenu.Button is required by addToStatusArea
        this._btn = new PanelMenu.Button(0.0, this.metadata.name, true);
        this._btn.add_style_class_name('nightpanel-btn');

        this._label = new St.Label({
            text:    'NIGHT PANEL',
            y_align: Clutter.ActorAlign.CENTER,
            x_align: Clutter.ActorAlign.CENTER,
            style_class: 'nightpanel-label',
        });

        this._btn.add_child(this._label);
        this._btn.connect('button-press-event', () => this._toggle());

        // Position: right side of panel, after system indicators
        Main.panel.addToStatusArea(this.uuid, this._btn, 1, 'right');

        this._updateVisual();

        // Watch config dir so icon updates when toggled from nightpanel app
        this._watchDir();
    }

    disable() {
        this._showPanel();
        this._panelHidden  = false;
        this._monitor?.cancel();
        this._monitor = null;
        this._btn?.destroy();
        this._btn          = null;
        this._label        = null;
        this._hiddenActors = [];
    }

    // ── Toggle ──────────────────────────────────────────────────────

    _toggle() {
        try {
            Gio.Subprocess.new([TOGGLE_SCRIPT], Gio.SubprocessFlags.NONE);
            // Visual updates via the file monitor once the script finishes
        } catch (e) {
            logError(e, 'nightpanel: toggle script failed');
        }
    }

    // ── Panel hide / restore ────────────────────────────────────────

    _hidePanel() {
        this._hiddenActors = [];
        const boxes = [
            Main.panel._leftBox,
            Main.panel._centerBox,
            Main.panel._rightBox,
        ];
        for (const box of boxes) {
            for (const child of box.get_children()) {
                if (child === this._btn || child.contains(this._btn))
                    continue;
                if (child.visible) {
                    child.hide();
                    this._hiddenActors.push(child);
                }
            }
        }
    }

    _showPanel() {
        for (const actor of this._hiddenActors)
            actor.show();
        this._hiddenActors = [];
    }

    // ── State file monitor ──────────────────────────────────────────

    _watchDir() {
        try {
            const dir = Gio.File.new_for_path(WATCH_DIR);
            this._monitor = dir.monitor_directory(Gio.FileMonitorFlags.NONE, null);
            this._monitor.connect('changed', (_mon, file, _other, _eventType) => {
                if (file.get_basename() === 'nightpanel-active') {
                    this._active = Gio.File.new_for_path(STATE_FILE).query_exists(null);
                    this._updateVisual();
                }
            });
        } catch (e) {
            logError(e, 'nightpanel: file monitor failed');
        }
    }

    // ── Visual state ────────────────────────────────────────────────

    _updateVisual() {
        if (!this._btn) return;
        if (this._active) {
            this._btn.remove_style_class_name('nightpanel-btn-inactive');
            this._btn.add_style_class_name('nightpanel-btn-active');
            if (!this._panelHidden) {
                this._hidePanel();
                this._panelHidden = true;
            }
        } else {
            this._btn.remove_style_class_name('nightpanel-btn-active');
            this._btn.add_style_class_name('nightpanel-btn-inactive');
            if (this._panelHidden) {
                this._showPanel();
                this._panelHidden = false;
            }
        }
    }
}
