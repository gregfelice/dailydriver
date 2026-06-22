
06-22-2026

- firefox - css is displaying overlays like dropdowns as transparent
  (fixed: makeCss now repaints non-media backgrounds to solid #0A0A0A instead
   of transparent, so dropdowns/menus/sticky headers are opaque)
- some broken fonts
  (fixed: makeCss font rule now excludes icon-font elements — Font Awesome,
   Material Icons/Symbols, Glyphicons, Bootstrap Icons — so their glyphs survive
   instead of being forced to Inter and rendering as tofu/ligature text)




05-26-2026
- np player not starting with super-p
  (fixed: Super+P now binds to nightpanel's OWN theme-synced mini-player, not an
   external Spotify/rhythmbox. Dedicated nightpanel-player binary added (pip
   console script + meson bindir launcher -> player_app:main); nightpanel
   --player / flatpak / run-dev.sh reach the same standalone PlayerApp via an
   application.main() intercept (mirrors --cheat-sheet). detect_np_player()
   resolves the command (prefers the dedicated binary) and the music keybinding
   prefers it, falling back to an external player. Covered by
   tests/unit/test_player_launch.py + the np_player tests in test_gsettings.py.)
- css flaky on ff - resetting on new tabs
  (fixed: tabs.onUpdated re-injects user-origin CSS on every 'loading'/'complete'
   and resets per-tab bookkeeping on 'loading' so navigation can't strand a
   sheet — commits 2c49124, 49287ee. Now locked by tests/unit/test_firefox_newtab.py,
   which drives the real onUpdated listener through new-tab + navigation.)
- upon np toggle on, screen goes dark, but then reverts to light. a second press works.
  (fixed: commit a560724 — opening the config window was gating the whole-session
   apply on the in-app GTK flag (default on) instead of orchestrator.is_active(),
   so it flipped then reverted. Now routed through is_active() as single source
   of truth. Code-verified; not GUI-proven here.)

- need adapter for nvim
  (DONE: src/nightpanel/adapters/nvim.py exists — after/plugin lua + --remote IPC.)



5-27-2026
- nautilus scheme not working
  (fixed: gnome adapter _bounce_nautilus() quits a running Nautilus so it
   re-reads ~/.config/gtk-4.0/gtk.css — GTK4 only parses it at app startup —
   landed in the 06-03/06-10 gnome adapter commits.)
- new tabs and websites in ff not respecting np scheme
  (fixed: same onUpdated re-inject path as the 05-26 new-tab item above;
   covered by tests/unit/test_firefox_newtab.py.)
