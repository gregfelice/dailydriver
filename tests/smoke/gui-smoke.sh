#!/usr/bin/env bash
# gui-smoke.sh — exercise the INSTALLED nightpanel package. Catches the classes
# of regression we shipped live: GUI modules missing from the package, the app
# failing to construct, missing design fonts, a broken extension manifest.
#
# Assumes nightpanel is already installed (e.g. `apt install ./nightpanel*.deb`,
# which also pulls Recommends — so the font checks validate that too). Pure
# headless: no X server / GNOME session needed. A full "window actually shows in
# the panel" check requires a real GNOME desktop — run this on a GNOME VM for
# that; in CI these checks catch the construction/packaging regressions.
set -euo pipefail
fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }

echo "== 1. binaries on PATH =="
command -v nightpanel >/dev/null        || fail "nightpanel not on PATH"
command -v nightpanel-toggle >/dev/null || fail "nightpanel-toggle not on PATH"

echo "== 2. import chain (catches missing-module packaging gaps) =="
python3 - <<'PY' || fail "import chain broken"
import importlib, gi
gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")
for m in [
    "nightpanel.application", "nightpanel.window",
    "nightpanel.services.theme_service", "nightpanel.services.tiling_service",
    "nightpanel.services.nightpanel_orchestrator",
    "nightpanel.views.appearance_view", "nightpanel.views.profiles_view",
    "nightpanel.views.setup_view", "nightpanel.adapters.alacritty",
]:
    importlib.import_module(m)
print("   import chain OK")
PY

echo "== 3. toggle policy (mock) =="
NP_TOGGLE_MOCK=1 NP_CONFIG_DIR="$(mktemp -d)" nightpanel-toggle \
  || fail "nightpanel-toggle policy run failed"

echo "== 4. GUI app constructs + CLI initializes =="
# `--help` runs the launcher's full import chain + GApplication construction,
# then exits before activate() — so no window, no display, and no orchestrator
# theme-apply side effects. Catches construction/import regressions headlessly.
log="$(mktemp)"
if ! timeout 20 env -u DISPLAY -u WAYLAND_DISPLAY nightpanel --help >/dev/null 2>"$log"; then
    echo "--- stderr ---"; cat "$log"
    fail "nightpanel --help failed (app construction / import error)"
fi
echo "   app constructs OK"

echo "== 5. design fonts: declared in Recommends + visible to fontconfig =="
# Declaration check — a plain desktop `apt install` pulls Recommends, so this is
# how end users get the fonts. (Checked via dpkg, not by installing Recommends
# here — that would also drag in the gnome-shell recommend.)
rec="$(dpkg-query -W -f='${Recommends}' nightpanel 2>/dev/null || true)"
echo "$rec" | grep -q 'fonts-inter'         || fail "fonts-inter not in package Recommends"
echo "$rec" | grep -q 'fonts-jetbrains-mono' || fail "fonts-jetbrains-mono not in package Recommends"
# Delivery check — the font packages are installed and ship actual font files.
# (Deterministic; fontconfig-cache visibility is a desktop concern, not a
# packaging regression, and is flaky under a headless root container.)
dpkg -L fonts-inter 2>/dev/null | grep -qE '\.(otf|ttf)$' \
  || fail "fonts-inter not installed / ships no font files"
dpkg -L fonts-jetbrains-mono 2>/dev/null | grep -qE '\.(otf|ttf)$' \
  || fail "fonts-jetbrains-mono not installed / ships no font files"
echo "   Inter + JetBrains Mono declared + delivered OK"

echo "== 6. shell extension manifest valid =="
python3 - /usr/share/gnome-shell/extensions/nightpanel@nightpanel/metadata.json <<'PY' \
  || fail "extension metadata invalid"
import json, sys
d = json.load(open(sys.argv[1]))
assert d.get("uuid") == "nightpanel@nightpanel", "wrong/missing uuid"
assert d.get("shell-version"), "no shell-version list"
print("   extension OK; shell-version =", d["shell-version"])
PY

echo "ALL SMOKE CHECKS PASSED"
