#!/bin/bash
# Test if GTK4/libadwaita work on this system

echo "=== Environment ==="
echo "DISPLAY=$DISPLAY"
echo "WAYLAND_DISPLAY=$WAYLAND_DISPLAY"
echo "XDG_SESSION_TYPE=$XDG_SESSION_TYPE"
echo ""

echo "=== GTK4 Test ==="
/usr/bin/python3 << 'EOF'
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

class TestApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.test.Gtk4Test')
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        win = Adw.ApplicationWindow(application=app)
        win.set_title("GTK4 Test - Close Me")
        win.set_default_size(400, 200)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)

        label = Gtk.Label(label="GTK4 + libadwaita working!")
        label.add_css_class("title-1")
        box.append(label)

        btn = Gtk.Button(label="Close")
        btn.connect('clicked', lambda _: app.quit())
        btn.add_css_class("suggested-action")
        box.append(btn)

        win.set_content(box)
        win.present()

print("Starting GTK4 test window...")
app = TestApp()
app.run([])
print("GTK4 test complete.")
EOF
