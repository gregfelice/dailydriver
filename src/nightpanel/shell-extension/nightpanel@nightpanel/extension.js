// nightpanel GNOME Shell extension — GNOME 45+ ES module
//
// Adds a night-light button to the right side of the panel.
// State is read from ~/.config/nightpanel/nightpanel-active (presence = on).
// Toggle runs `nightpanel-toggle`, resolved from PATH (system package →
// /usr/bin) with a ~/.local/bin fallback for dev-stow / pipx checkouts.
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

// System install lands the toggle in /usr/bin; resolve via PATH so the panel
// button works for distro users. Fall back to ~/.local/bin (dev-stow / pipx).
const TOGGLE_SCRIPT = GLib.find_program_in_path('nightpanel-toggle')
    || (GLib.get_home_dir() + '/.local/bin/nightpanel-toggle');
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
        // Every press fires _toggle(). Filtering re-dispatched clicks here
        // proved fragile (source actor identity unreliable across GNOME 48);
        // the debounce lives in nightpanel-toggle. Event metadata is forwarded
        // as argv purely as evidence — toggle.log records it so we can later
        // distinguish a real second click from a stale-grab re-dispatch by
        // comparing event-times across invocations.
        this._btn.connect('button-press-event', (_actor, event) => {
            this._toggle(event);
            return Clutter.EVENT_STOP;
        });

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

    _toggle(event) {
        // Forward event metadata as argv purely for post-hoc analysis (see
        // bin/analyze-toggle-log). The toggle script ignores these flags.
        //
        // The primary discriminator between a real click and a stale-grab
        // re-dispatch is COORDS: a real panel-button click lands inside the
        // top panel (y < ~40), a re-dispatched click carries the cursor's
        // actual screen position (typically y >> 40). evt-on-btn is recorded
        // too but is expected to be unreliable — Clutter delivers grabbed
        // events to the grab holder regardless of cursor position, so the
        // source actor often points at the panel button in BOTH cases.
        //
        // Metadata gathering is isolated in its own try so a Clutter API
        // shift (e.g. get_coords / is_pointer_emulated renamed in a future
        // GNOME) degrades to evidence-less invocation rather than breaking
        // the toggle entirely.
        const argv = [TOGGLE_SCRIPT];
        if (event) {
            try {
                argv.push('--evt-time', String(event.get_time()));
                argv.push('--evt-button', String(event.get_button()));
                argv.push('--evt-emulated', event.is_pointer_emulated() ? '1' : '0');
                const [x, y] = event.get_coords();
                argv.push('--evt-coords', `${Math.round(x)},${Math.round(y)}`);
                const src = event.get_source();
                const srcName = src
                    ? (src.get_name() || src.toString()).replace(/\s+/g, '_')
                    : 'null';
                argv.push('--evt-source', srcName);
                argv.push(
                    '--evt-on-btn',
                    src && (src === this._btn || this._btn.contains(src)) ? '1' : '0',
                );
            } catch (e) {
                logError(e, 'nightpanel: event metadata capture failed (toggle still fires)');
            }
        }
        try {
            Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE);
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
