# nightpanel per-VM test checklist

Run this inside each guest after reverting to the `clean` snapshot. It is organized so
that completing it produces the evidence for **(a) what we support** and **(b) where it
breaks**. Record `PASS / FAIL / N/A` + a note per line. Reset with `revert.yml` between
install methods.

Fetch artifacts from the host: **`http://10.0.2.2:8099/`** (see `serve.yml`).

> **STEP 0 (host, before anything): rebuild the Flatpak bundle.** The repo may carry a
> months-old `*.flatpak`; `serve.yml` stages the newest one it finds and prints its build
> date — confirm it postdates your latest `src/` changes, or rebuild. Testing a stale build
> is the exact failure this harness exists to prevent.

---

## 0. Session facts (record once per VM)

- [ ] `gnome-shell --version` (or `plasmashell --version`) — actual DE version
- [ ] `echo $XDG_SESSION_TYPE` — wayland / x11
- [ ] `echo $XDG_CURRENT_DESKTOP`
- [ ] Flatpak + flathub present? (`flatpak remotes`)

---

## 1. Install surface — all THREE pieces must install (not just the Flatpak)

The Flatpak app alone is inert without the panel button (extension) and the browser
bridge. Test each:

- [ ] **Flatpak app**: `flatpak install --user nightpanel.flatpak` → launches, main window renders
- [ ] **GNOME Shell extension**: `gnome-extensions install nightpanel@nightpanel.shell-extension.zip` then logout/login → `gnome-extensions enable nightpanel@nightpanel` → **panel button appears**
- [ ] **Firefox bridge**: install the `.xpi`; confirm the native-messaging host path resolves under Flatpak sandboxing
- [ ] (secondary, distro-specific) AUR `PKGBUILD` / `debian/` deb — note if attempted

---

## 2. BREAKAGE #1 (headline) — extension `shell-version` cap (45–48)

The extension declares `["45","46","47","48"]`. Current GNOME is 49/50.

- [ ] **As-shipped**: does `gnome-extensions enable` load it on this GNOME? (expect: **NO** on 49/50, **YES** on 46/48)
- [ ] If it refuses: edit `metadata.json` `shell-version` to add this version, reinstall, logout/login
- [ ] **After the bump — does it actually FUNCTION, or merely load?** Click the panel button; confirm it toggles, no errors in `journalctl --user -b /usr/bin/gnome-shell` / Looking Glass (`lg`)
- [ ] Verdict: ☐ one-line metadata bump is enough  ☐ real porting work needed (which APIs broke?)

> `ubuntu-lts` (46) is the control: it should load as-is. `fedora-ws` (49) and
> `ubuntu-edge` (50) are where this breaks.

---

## 3. BREAKAGE #2 — desktop-environment handling (KDE / silent fallback)

Run on **`fedora-kde`**:

- [ ] Does nightpanel detect KDE, or silently fall back to the GNOME backend? (`factory.py`)
- [ ] If KDE backend engages: do shortcut writes to `~/.config/kglobalshortcutsrc` + `qdbus org.kde.KWin reconfigure` work?
- [ ] Theming adapters on KDE: does the GNOME adapter no-op cleanly (no `gsettings`), or error?
- [ ] Verdict on KDE: ☐ usable ☐ partial ☐ broken/needs gating

---

## 4. BREAKAGE #3 — adapter robustness on a clean machine

The theming layer assumes tools/paths that may differ per distro:

- [ ] **Firefox adapter has no `installed()` guard** — on a VM with Firefox as Snap (Ubuntu) or absent: does it no-op, or write to a wrong/missing profile? Check `~/.mozilla/firefox/profiles.ini` resolution (Snap Firefox uses `~/snap/firefox/common/.mozilla/...`)
- [ ] **`gemini_cli` hardcodes `/usr/local/bin/gemini`** — confirm it doesn't false-detect / crash when gemini is elsewhere or absent
- [ ] **GTK4 CSS reload**: after toggle, does the theme actually apply, or only after the Nautilus bounce? Any visible flicker/breakage?
- [ ] **nvim adapter** socket discovery: start `nvim --listen` in a non-default location; does the adapter find it?
- [ ] Each adapter present on this VM: `installed()` correct? `apply()` then `revert()` round-trips cleanly (diff `~/.config/nightpanel/nightpanel-state.json`)?

---

## 5. Core function — install → toggle → revert

- [ ] `nightpanel-toggle` (or panel button) flips dark mode across every installed adapter
- [ ] Toggle back: every adapter reverts to its pre-toggle state (no leftover config, no corrupted snapshots)
- [ ] Keyboard half: a preset applies; cheat-sheet overlay opens; conflict detection runs
- [ ] No errors in `journalctl --user -b` from the app or extension

---

## 6. X11 (only where it still exists)

Only on **`ubuntu-lts`** (GNOME 46) — pick "Ubuntu on Xorg" at the login screen:

- [ ] App launches and toggles under X11 (`fallback-x11` Flatpak socket)
- [ ] Extension + gsettings behave the same as Wayland

---

## Results summary (fill in per VM)

| VM | GNOME/DE | extension loads | toggle works | adapters clean | verdict |
|---|---|---|---|---|---|
| ubuntu-lts  | 46 |  |  |  |  |
| fedora-ws   | 49 |  |  |  |  |
| ubuntu-edge | 50 |  |  |  |  |
| fedora-kde  | Plasma 6 |  |  |  |  |
| HOST        | 48.7 |  |  |  | (bare-metal boundary check) |
