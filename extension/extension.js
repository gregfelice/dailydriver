/* extension.js
 * DailyDriver Cheat Sheet - GNOME Shell Extension
 * Shows a keyboard shortcut overlay popup
 */

import St from 'gi://St';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Clutter from 'gi://Clutter';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// Shortcut schemas to read from
const SHORTCUT_SCHEMAS = [
    'org.gnome.desktop.wm.keybindings',
    'org.gnome.shell.keybindings',
    'org.gnome.mutter.keybindings',
    'org.gnome.mutter.wayland.keybindings',
    'org.gnome.settings-daemon.plugins.media-keys',
];

// Category mappings
const CATEGORIES = {
    'close': 'Window',
    'minimize': 'Window',
    'maximize': 'Window',
    'toggle-fullscreen': 'Window',
    'toggle-maximized': 'Window',
    'switch-windows': 'Navigation',
    'switch-applications': 'Navigation',
    'cycle-windows': 'Navigation',
    'switch-to-workspace': 'Workspaces',
    'move-to-workspace': 'Workspaces',
    'toggle-overview': 'Shell',
    'toggle-application-view': 'Shell',
    'toggle-message-tray': 'Shell',
    'screenshot': 'Screenshots',
    'screencast': 'Screenshots',
    'volume': 'Media',
    'mic': 'Media',
    'play': 'Media',
    'pause': 'Media',
    'next': 'Media',
    'previous': 'Media',
};

export default class DailyDriverCheatSheet {
    constructor() {
        this._overlay = null;
        this._settings = null;
    }

    enable() {
        // Add keybinding for Alt+Super+/
        Main.wm.addKeybinding(
            'toggle-cheatsheet',
            new Gio.Settings({ schema_id: 'org.gnome.shell.extensions.dailydriver-cheatsheet' }),
            Meta.KeyBindingFlags.NONE,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW,
            () => this._toggleOverlay()
        );
    }

    disable() {
        Main.wm.removeKeybinding('toggle-cheatsheet');
        this._hideOverlay();
    }

    _toggleOverlay() {
        if (this._overlay && this._overlay.visible) {
            this._hideOverlay();
        } else {
            this._showOverlay();
        }
    }

    _showOverlay() {
        if (this._overlay) {
            this._overlay.destroy();
        }

        // Create overlay container
        this._overlay = new St.BoxLayout({
            style_class: 'cheatsheet-overlay',
            vertical: true,
            reactive: true,
        });

        // Add title
        const title = new St.Label({
            text: 'Keyboard Shortcuts',
            style_class: 'cheatsheet-title',
        });
        this._overlay.add_child(title);

        // Create columns container
        const columnsBox = new St.BoxLayout({
            style_class: 'cheatsheet-columns',
            vertical: false,
        });
        this._overlay.add_child(columnsBox);

        // Load shortcuts and organize by category
        const shortcuts = this._loadShortcuts();
        const categories = this._organizeByCategory(shortcuts);

        // Create columns
        const numColumns = 3;
        const columns = [];
        for (let i = 0; i < numColumns; i++) {
            const col = new St.BoxLayout({
                style_class: 'cheatsheet-column',
                vertical: true,
            });
            columns.push(col);
            columnsBox.add_child(col);
        }

        // Distribute categories to columns
        const categoryNames = Object.keys(categories).sort();
        categoryNames.forEach((catName, i) => {
            const col = columns[i % numColumns];
            const catBox = this._createCategoryBox(catName, categories[catName]);
            col.add_child(catBox);
        });

        // Add to stage
        Main.layoutManager.addTopChrome(this._overlay);

        // Center on screen
        const monitor = Main.layoutManager.primaryMonitor;
        this._overlay.set_position(
            monitor.x + (monitor.width - this._overlay.width) / 2,
            monitor.y + (monitor.height - this._overlay.height) / 2
        );

        // Close on click outside or Escape
        this._overlay.connect('button-press-event', () => this._hideOverlay());

        global.stage.connect('key-press-event', (actor, event) => {
            if (event.get_key_symbol() === Clutter.KEY_Escape) {
                this._hideOverlay();
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });
    }

    _hideOverlay() {
        if (this._overlay) {
            Main.layoutManager.removeChrome(this._overlay);
            this._overlay.destroy();
            this._overlay = null;
        }
    }

    _loadShortcuts() {
        const shortcuts = [];
        const schemaSource = Gio.SettingsSchemaSource.get_default();

        for (const schemaId of SHORTCUT_SCHEMAS) {
            const schema = schemaSource.lookup(schemaId, true);
            if (!schema) continue;

            const settings = new Gio.Settings({ schema_id: schemaId });
            const keys = schema.list_keys();

            for (const key of keys) {
                const value = settings.get_value(key);
                const type = value.get_type_string();

                // Only process string arrays (keybindings)
                if (type !== 'as') continue;

                const bindings = value.deep_unpack();
                if (!bindings || bindings.length === 0 || bindings[0] === '') continue;

                // Skip disabled bindings
                if (bindings[0] === 'disabled') continue;

                shortcuts.push({
                    name: this._humanizeName(key),
                    binding: this._humanizeBinding(bindings[0]),
                    key: key,
                    schema: schemaId,
                });
            }
        }

        return shortcuts;
    }

    _humanizeName(key) {
        return key
            .replace(/-/g, ' ')
            .replace(/\b\w/g, c => c.toUpperCase());
    }

    _humanizeBinding(binding) {
        return binding
            .replace('<Super>', 'Super+')
            .replace('<Shift>', 'Shift+')
            .replace('<Control>', 'Ctrl+')
            .replace('<Alt>', 'Alt+')
            .replace('<Primary>', 'Ctrl+')
            .replace('>', '')
            .replace('<', '');
    }

    _organizeByCategory(shortcuts) {
        const categories = {};

        for (const shortcut of shortcuts) {
            let category = 'Other';

            for (const [pattern, cat] of Object.entries(CATEGORIES)) {
                if (shortcut.key.includes(pattern)) {
                    category = cat;
                    break;
                }
            }

            if (!categories[category]) {
                categories[category] = [];
            }
            categories[category].push(shortcut);
        }

        return categories;
    }

    _createCategoryBox(name, shortcuts) {
        const box = new St.BoxLayout({
            style_class: 'cheatsheet-category',
            vertical: true,
        });

        const header = new St.Label({
            text: name,
            style_class: 'cheatsheet-category-header',
        });
        box.add_child(header);

        for (const shortcut of shortcuts.slice(0, 10)) { // Limit per category
            const row = new St.BoxLayout({
                style_class: 'cheatsheet-row',
            });

            const binding = new St.Label({
                text: shortcut.binding,
                style_class: 'cheatsheet-binding',
            });
            row.add_child(binding);

            const label = new St.Label({
                text: shortcut.name,
                style_class: 'cheatsheet-label',
            });
            row.add_child(label);

            box.add_child(row);
        }

        return box;
    }
}
