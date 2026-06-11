#!/usr/bin/env bash
# selftest.sh — runs INSIDE a test guest (pushed + executed via the qemu guest agent).
# Exercises install -> extension version-gate -> toggle round-trip -> errors, and emits
# JSON to $OUT with a DE-aware verdict (pass/fail/incomplete) the host aggregates.
#
# Invoked as root by the guest agent. Session-affecting + user-owned work runs as the live
# graphical-session user via sess(). Critical checks that skip/need-manual make the verdict
# 'incomplete' (NOT pass) — an all-skipped guest must never read green.
#
# Env: HTTP_BASE (default http://10.0.2.2:8099)  APP_ID  EXT_UUID  OUT
set -uo pipefail   # NOT -e: every check is independent and must not abort the run

HTTP_BASE="${HTTP_BASE:-http://10.0.2.2:8099}"
APP_ID="${APP_ID:-io.github.gregfelice.DailyDriver}"
EXT_UUID="${EXT_UUID:-nightpanel@nightpanel}"
OUT="${OUT:-/tmp/np-selftest.json}"
WORK="$(mktemp -d)"; RES="$WORK/results"; : >"$RES"

# rec <check> <pass|fail|skip|manual|info> <detail> [crit:0|1]
rec() { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "${3//$'\t'/ }" "${4:-0}" >>"$RES"
        printf '  [%-6s]%s %-26s %s\n' "$2" "$([[ "${4:-0}" == 1 ]] && echo '*' || echo ' ')" "$1" "${3:-}"; }

# --- locate the live graphical session user --------------------------------
SU="" UIDN="" RT="" STYPE=""
resolve_session() {
  SU=""; for s in $(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $1}'); do
    local t st; t="$(loginctl show-session "$s" -p Type --value 2>/dev/null)"
    st="$(loginctl show-session "$s" -p State --value 2>/dev/null)"
    if [[ "$t" =~ ^(wayland|x11)$ && "$st" == active ]]; then
      SU="$(loginctl show-session "$s" -p Name --value)"; STYPE="$t"; break
    fi
  done
  [[ -n "$SU" ]] && { UIDN="$(id -u "$SU")"; RT="/run/user/$UIDN"; }
}
resolve_session
SUHOME="$(getent passwd "$SU" 2>/dev/null | cut -d: -f6)"
sess() { sudo -u "$SU" env XDG_RUNTIME_DIR="$RT" DBUS_SESSION_BUS_ADDRESS="unix:path=$RT/bus" HOME="$SUHOME" "$@"; }
[[ -n "$SU" ]] && rec session.user pass "$SU (uid=$UIDN, $STYPE)" || rec session.user fail "no active graphical session — autologin not set?" 1

# --- DE detection -----------------------------------------------------------
IS_GNOME=0; IS_KDE=0
if command -v gnome-shell >/dev/null; then IS_GNOME=1; rec env.de info "GNOME $(gnome-shell --version | grep -oE '[0-9.]+')"
elif command -v plasmashell >/dev/null; then IS_KDE=1; rec env.de info "KDE Plasma $(plasmashell --version | grep -oE '[0-9.]+' | head -1)"
else rec env.de info "unknown"; fi

# --- 1. install: flatpak bundle (critical) ---------------------------------
BUNDLE="$(curl -fsSL "$HTTP_BASE/" 2>/dev/null | grep -oE '[^"]+\.flatpak' | head -1)"
if [[ -n "$SU" && -n "$BUNDLE" ]] && curl -fsSL -o "$WORK/app.flatpak" "$HTTP_BASE/$BUNDLE"; then
  if sess flatpak install --user --noninteractive --assumeyes "$WORK/app.flatpak" >/dev/null 2>"$WORK/e"; then
    rec install.flatpak pass "$(sess flatpak info "$APP_ID" 2>/dev/null | awk -F': ' '/Version/{print $2}' | head -1)" 1
  else rec install.flatpak fail "$(tail -1 "$WORK/e")" 1; fi
else rec install.flatpak fail "no *.flatpak served / no session" 1; fi

# --- 2. install the TOGGLE path (NOT packaged: needs repo checkout + venv) --
# Reproduces the real deployment: ~/.local/bin/nightpanel-toggle -> repo bin/, with a
# .venv-dev (system-site PyGObject + pip deps). This is itself a shippability finding.
SRC="$SUHOME/nightpanel-src"
if [[ -n "$SU" ]] && curl -fsSL -o "$WORK/src.tgz" "$HTTP_BASE/nightpanel-src.tar.gz" 2>/dev/null; then
  sess bash -c "
    set -e
    rm -rf '$SRC' && mkdir -p '$SRC' && tar xzf '$WORK/src.tgz' -C '$SRC'
    python3 -m venv --system-site-packages '$SRC/.venv-dev'
    '$SRC/.venv-dev/bin/pip' install -q pydantic 'tomli-w' >/dev/null 2>&1
    mkdir -p '$SUHOME/.local/bin'
    ln -sf '$SRC/bin/nightpanel-toggle' '$SUHOME/.local/bin/nightpanel-toggle'
  " 2>"$WORK/te" && rec install.toggle pass "deployed to ~/.local/bin (repo+venv)" 1 \
                 || rec install.toggle fail "$(tail -1 "$WORK/te")" 1
else rec install.toggle fail "no src tarball / no session" 1; fi
TOGGLE="$SUHOME/.local/bin/nightpanel-toggle"

# --- 3. extension shell-version gate (GNOME only; critical on GNOME) --------
if [[ "$IS_GNOME" == 1 && -n "$SU" ]]; then
  EXTZIP="$(curl -fsSL "$HTTP_BASE/" 2>/dev/null | grep -oE '[^"]+\.shell-extension\.zip' | head -1)"
  if [[ -n "$EXTZIP" ]] && curl -fsSL -o "$WORK/ext.zip" "$HTTP_BASE/$EXTZIP"; then
    sess gnome-extensions install --force "$WORK/ext.zip" >/dev/null 2>&1
    systemctl restart gdm 2>/dev/null || true; sleep 20; resolve_session
    sess gnome-extensions enable "$EXT_UUID" >/dev/null 2>&1
    STATE="$(sess gnome-extensions info "$EXT_UUID" 2>/dev/null | awk -F': ' '/State/{print $2}')"
    case "$STATE" in
      ENABLED|ACTIVE)    rec extension.gate pass "loads + enables: $STATE" 1 ;;
      *OUT*)             rec extension.gate fail "OUT_OF_DATE — shell-version cap excludes this GNOME (ship-blocker)" 1 ;;
      *)                 rec extension.gate fail "did not load: ${STATE:-absent}" 1 ;;
    esac
  else rec extension.gate fail "no extension zip served" 1; fi
else rec extension.gate skip "GNOME-only check" 0; fi

# --- 4. toggle round-trip (GNOME: assert gsettings + adapter files) --------
if [[ "$IS_GNOME" == 1 && -n "$SU" ]] && sess test -x "$TOGGLE"; then
  before="$(sess gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null)"
  sess "$TOGGLE" >/dev/null 2>&1; sleep 2
  after="$(sess gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null)"
  [[ "$before" != "$after" ]] && rec toggle.colorscheme pass "$before -> $after" 1 || rec toggle.colorscheme fail "unchanged ($before)" 1
  sess test -s "$SUHOME/.config/gtk-4.0/gtk.css" && rec toggle.gtkcss pass "gtk-4.0/gtk.css written" 0 || rec toggle.gtkcss fail "no gtk.css" 0
  sess test -s "$SUHOME/.config/nightpanel/nightpanel-state.json" && rec toggle.state pass "state.json present" 0 || rec toggle.state fail "no state.json" 0
  sess "$TOGGLE" >/dev/null 2>&1; sleep 2
  rev="$(sess gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null)"
  [[ "$rev" == "$before" ]] && rec toggle.revert pass "restored to $before" 1 || rec toggle.revert fail "stuck at $rev (expected $before)" 1
elif [[ "$IS_GNOME" == 1 ]]; then rec toggle.colorscheme fail "toggle not installed" 1; fi

# --- 5. KDE: no auto-green — backend assertions are not implemented --------
if [[ "$IS_KDE" == 1 ]]; then
  rec kde.backend manual "verify MANUALLY: does it detect KDE or silently fall back to GNOME (factory.py)? kglobalshortcutsrc + qdbus writes?" 1
fi

# --- 6. runtime errors in the journal --------------------------------------
ERRS="$(journalctl --user -b 2>/dev/null | grep -iE "$EXT_UUID|nightpanel|DailyDriver" | grep -ciE "error|traceback|critical|fail")"
[[ "${ERRS:-0}" -eq 0 ]] && rec runtime.journal pass "no app/extension errors" 0 || rec runtime.journal fail "$ERRS error line(s)" 0

# --- emit JSON + verdict ----------------------------------------------------
python3 - "$RES" >"$OUT" <<'PY'
import sys, json
rows=[]
for ln in open(sys.argv[1]):
    p=ln.rstrip("\n").split("\t")
    if len(p)>=2: rows.append({"check":p[0],"status":p[1],"detail":p[2] if len(p)>2 else "","crit":(len(p)>3 and p[3]=="1")})
fail=[r for r in rows if r["status"]=="fail"]
crit_incomplete=[r for r in rows if r["crit"] and r["status"] in ("skip","manual")]
manual=[r for r in rows if r["status"]=="manual"]
if fail: verdict="fail"
elif crit_incomplete or manual: verdict="incomplete"
else: verdict="pass"
print(json.dumps({"verdict":verdict,"results":rows,
  "summary":{"total":len(rows),"pass":sum(r["status"]=="pass" for r in rows),
    "fail":len(fail),"skip":sum(r["status"]=="skip" for r in rows),
    "manual":len(manual)},
  "failed":[r["check"] for r in fail]+["%s(%s)"%(r["check"],r["status"]) for r in crit_incomplete if r["status"]!="fail"]},indent=2))
PY
echo "--- verdict: $(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["verdict"])' "$OUT") (wrote $OUT) ---"
rm -rf "$WORK"
