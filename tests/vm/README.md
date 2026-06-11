# nightpanel cross-distro VM test harness

Ansible-driven libvirt VMs for installing, configuring, and exercising nightpanel on
clean distro/desktop bases — to answer two questions before shipping:

- **(a) what configs do we actually support / test on?**
- **(b) where does it break?**

## Why VMs (and why this isn't containers)

nightpanel has two layers with different testability:

| Layer | What | How to test |
|---|---|---|
| Headless-safe | Python package, adapter file-writing logic, Flatpak build, unit tests | containers / CI (separate, not this harness) |
| **Live-session** | the **GNOME Shell extension** (panel button), `gsettings`/`dconf`, GTK CSS reload, adapters that poke **running** apps (Firefox native-msg, `nvim --remote`, `emacsclient`, tmux) | **these VMs** |

A GNOME Shell extension cannot be meaningfully tested in a container — it needs a live
`gnome-shell` + Mutter + dbus session **of a specific version**. That's the whole point
of this harness.

## Permission model — no sudo

Everything runs on **`qemu:///session`**, a per-user libvirt instance:
- runs as you; VM disks and ISOs are owned by you
- `/dev/kvm` is already reachable on this host via ACL (`user:gregf:rw-`)
- **no `become`, no system `libvirtd`, no group membership, no polkit prompts**

The one thing not auto-installed is a SPICE console viewer. You have `virt-manager`
(use `virt-manager -c qemu:///session`); `virt-viewer` is a lighter alternative if you
want to `apt/dnf install` it once.

## Disk + RAM reality (this host)

- The repo's filesystem (root, `/dev/nvme1n1p3`) has **~14 GB free — too small for VMs.**
  Images therefore live on the **ZFS pool** at `~/vm/nightpanel-test` (~1.5 TB free).
- Host RAM is tight while og-llama is up (~20 GB free). **Run ONE VM at a time** (4 GB each).
- Override the pool location with `-e vm_base=/some/other/path`.

## Controller setup (one-time)

```bash
cd tests/vm
uv venv .venv-ansible && source .venv-ansible/bin/activate
uv pip install ansible-core
ansible-galaxy collection install -r requirements.yml
ansible-playbook bootstrap.yml          # verifies kvm + qemu:///session, makes pool dirs
```

## The matrix

`ansible-playbook` reads `group_vars/all.yml`. Distro→GNOME mapping verified 2026-06-03.

| key | distro | GNOME / DE | why it's in the matrix |
|---|---|---|---|
| `ubuntu-lts`  | Ubuntu 24.04 | GNOME 46 / Wayland | happy-path baseline; extension **in-band** (45–48); biggest install base |
| `fedora-ws`   | Fedora 43    | GNOME 49 / Wayland | current GNOME; canonical Flatpak distro; **first version the extension is rejected** |
| `ubuntu-edge` | Ubuntu 26.04 | GNOME 50 / Wayland-only | newest LTS; X11 removed; extension 2 majors out of band |
| `fedora-kde`  | Fedora 43    | KDE Plasma 6 | KDE backend + the silent GNOME-fallback bug |

**GNOME 48** (the extension's declared ceiling) needs no VM — **this host runs GNOME
Shell 48.7**, so test that boundary on bare metal.

## Per-VM workflow

```bash
source .venv-ansible/bin/activate

# 1. download ISO, create disk, boot the installer
ansible-playbook create.yml -e vm=ubuntu-lts
virt-manager -c qemu:///session          # double-click np-ubuntu-lts, install the OS

# 2. GOLDEN-IMAGE PREP inside the guest after first boot (bake into the clean snapshot):
#    - spice-vdagent (clipboard/resize)
#    - qemu-guest-agent  ENABLED  -> lets bin/test-vm reach in with NO ssh/network
#        sudo systemctl enable --now qemu-guest-agent
#    - AUTOLOGIN for the test user -> an active graphical session always exists after revert
#        GNOME/gdm:  /etc/gdm3/custom.conf or /etc/gdm/custom.conf -> [daemon] AutomaticLoginEnable=true / AutomaticLogin=<user>
#        KDE/sddm:   /etc/sddm.conf.d/autologin.conf -> [Autologin] User= / Session=
#    - on Fedora add flathub:
#        flatpak remote-add --if-not-exists --user flathub https://flathub.org/repo/flathub.flatpakrepo

# 3. power off the guest, snapshot the clean baseline (agent + autologin now baked in)
ansible-playbook snapshot.yml -e vm=ubuntu-lts      # snapshot name defaults to "clean"

# 4. serve nightpanel's artifacts to the guests
ansible-playbook serve.yml                          # stages flatpak + extension + xpi, prints the serve cmd
( cd stage && python3 -m http.server 8099 --bind 0.0.0.0 )
#   inside the guest, fetch from:  http://10.0.2.2:8099/

# 5. work through CHECKLIST.md in the guest, recording pass/fail per breakage

# 6. reset to clean and move to the next install method / next VM
ansible-playbook revert.yml  -e vm=ubuntu-lts
ansible-playbook destroy.yml -e vm=ubuntu-lts       # full teardown (keeps the ISO)
```

## Scripted testing (the live-session plane)

Once a VM has a `clean` snapshot with **qemu-guest-agent + autologin** baked in, the suite
runs itself — no SSH, no clicking. `bin/test-vm` (in the repo root, estate-compliant per
ADR-030: a portable script + ntfy, **not** a CI engine) is the entry point:

```bash
bin/test-vm                  # all matrix VMs: revert clean -> serve -> in-guest tests -> table
bin/test-vm fedora-ws        # one (or several) VM keys
bin/test-vm --async          # background + ntfy ops-high (pass) / ops-critical (fail)
bin/test-vm --list
```

How it reaches in and what it asserts:

1. **Connection** — `community.libvirt.libvirt_qemu` runs commands + pushes/fetches files
   through the **QEMU guest agent**. SLIRP gives no inbound route, so this (not ssh) is how
   the host drives the guest.
2. **Session** — guest-agent exec runs as root with no session bus; `guest/selftest.sh`
   re-runs session commands as the autologin user (`XDG_RUNTIME_DIR`, `DBUS_SESSION_BUS_ADDRESS`).
   The extension reload uses `systemctl restart gdm` — the Wayland-scriptable "logout/login".
3. **Assertions** (`guest/selftest.sh`, emits JSON) — install exit codes; **the extension
   shell-version gate** (`gnome-extensions info … State` → `ENABLED` vs `OUT_OF_DATE`/`ERROR`,
   the headline ship-blocker, fully automated); toggle round-trip (gsettings flip + `gtk.css`
   palette + `nightpanel-state.json` + revert restoration); journal error scan.
4. **Screenshots** (`guest/screenshot.sh`) — before/after PNGs via `org.gnome.Shell.Screenshot`
   D-Bus (GNOME) / spectacle (KDE), fetched to `tests/vm/results/<vm>/` for human review.
   Visual *fidelity* is the one axis you can't assert; this captures it for the eye.

Results land in `tests/vm/results/<vm>/` (`np-selftest.json` + PNGs); the table + overall
exit code come from the JSON, so `bin/test-vm` is non-zero if any VM has a failing check.

Also run the **headless** suite (`bin/test`, pytest) *inside* each guest to catch
distro-specific adapter/path differences against that distro's real Python.

## What is and isn't validated

This harness is **scaffolding**, validated as far as is possible without a live guest:

- `bootstrap.yml` runs unprivileged; the rendered domain XML (incl. the guest-agent
  channel) passes `virt-xml-validate` **and** libvirt's `define`; the `community.libvirt`
  write path works on `qemu:///session`; all playbooks pass `--syntax-check`.
- `guest/selftest.sh`, `guest/screenshot.sh`, `bin/test-vm` pass `bash -n`; the JSON
  emit/aggregate paths are exercised with sample data; `bin/test-vm --list` parses the matrix.
- ISO URLs HEAD-checked / corrected against directory listings (2026-06-03).

**Not yet run end-to-end against a real OS install** — desktop installs are interactive and
can't be driven headlessly. Confirm these on run one (each is a known soft spot):

- **UEFI empty-disk→cdrom fallthrough** on first boot — OVMF sometimes drops to the UEFI
  shell instead; if so, set explicit boot order or eject/re-add the cdrom.
- **`10.0.2.2` assumes SLIRP.** `<interface type='user'>` may resolve to **passt** on this
  qemu 10 build (different host address) or fail if libslirp is absent. Check after first
  `create`; if passt, the guest-reaches-host address differs — fix `guest_sees_host_at`.
- **Screenshots are GNOME-version-fragile.** `org.gnome.Shell.Screenshot` D-Bus was
  restricted in recent GNOME — it likely works on `ubuntu-lts` (46) but **may write nothing
  on GNOME 49/50** (and grim won't exist on Mutter). Expect empty PNGs on the edge VMs until
  a portal-based capture is wired; the assertions still run, only the visual artifact is at risk.
- **Guest-agent exec path** — `define`/`list` are exercised; `copy`/`command` over the agent are not.

Re-verify ISO URLs before a run; point releases drift.

> **Shippability finding (not a harness bug):** the theming/toggle half is **not packaged**.
> `nightpanel-toggle` resolves `NIGHTPANEL_HOME` from its own path and imports the
> `nightpanel` package from `<repo>/src` via `<repo>/.venv-dev` — so it only works where a
> repo checkout + dev venv exist (your dotfiles-stow symlink). The Flatpak does **not** carry
> it. `selftest.sh` reproduces that (fetches the repo tarball, builds a venv, symlinks the
> toggle) — which is exactly why it's worth fixing before shipping to anyone without the repo.

## Wayland gotchas (bake into every run)

- On Wayland you **cannot restart GNOME Shell in place** (Alt+F2 `r` is X11-only).
  Enabling a freshly-installed extension requires a **logout/login**.
- GNOME 49 disables X11 by default; GNOME 50 removed it — so "GNOME on X11" only exists
  to test on `ubuntu-lts` (GNOME 46), selectable at the login screen.

## Relationship to the known bugs

The harness *validates fixes* for issues already visible in the code (extension
`shell-version` cap, hardcoded `/usr/local/bin/gemini`, Firefox adapter with no
`installed()` guard, `factory.py` silent GNOME fallback). You don't need a VM to *find*
those — see `CHECKLIST.md`, which maps each VM run to confirming the breakage and its fix.
