#!/usr/bin/env bash
# screenshot.sh LABEL  — capture the live desktop to /tmp/np-shot-LABEL.png INSIDE a guest.
# Runs as root via the guest agent; shoots the active graphical session as its user.
# GNOME: org.gnome.Shell.Screenshot D-Bus.  KDE: spectacle.  Saved PNGs are pulled back
# by the host for human review / pixel-diff (visual fidelity is the one non-assertable axis).
set -uo pipefail
LABEL="${1:?usage: screenshot.sh <label>}"
OUT="/tmp/np-shot-${LABEL}.png"

SU="" UIDN="" RT=""
for s in $(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $1}'); do
  [[ "$(loginctl show-session "$s" -p State --value)" == active ]] || continue
  [[ "$(loginctl show-session "$s" -p Type --value)" =~ ^(wayland|x11)$ ]] || continue
  SU="$(loginctl show-session "$s" -p Name --value)"; break
done
[[ -z "$SU" ]] && { echo "no active graphical session"; exit 2; }
UIDN="$(id -u "$SU")"; RT="/run/user/$UIDN"
sess() { sudo -u "$SU" env XDG_RUNTIME_DIR="$RT" DBUS_SESSION_BUS_ADDRESS="unix:path=$RT/bus" "$@"; }

if command -v gnome-shell >/dev/null; then
  sess gdbus call --session \
    --dest org.gnome.Shell.Screenshot \
    --object-path /org/gnome/Shell/Screenshot \
    --method org.gnome.Shell.Screenshot.Screenshot true false "$OUT" >/dev/null 2>&1 \
    && { echo "$OUT"; exit 0; }
  # GNOME 49/50 fallback: portal-free grim if present (wlroots only — usually absent on GNOME)
fi
if command -v spectacle >/dev/null; then
  sess spectacle -b -n -f -o "$OUT" >/dev/null 2>&1 && { echo "$OUT"; exit 0; }
fi
echo "no usable screenshot backend"; exit 3
