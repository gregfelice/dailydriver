# AUR migration: `dailydriver` → `nightpanel`

The Arch package has been renamed because the project was renamed (the old `dailydriver` was just the keyboard-config half; `nightpanel` adds the system-wide theming orchestrator). AUR doesn't support package renames, so the migration is:

1. **A new package `nightpanel` is submitted to AUR.**
2. **The old `dailydriver` AUR package is orphaned.** (Maintainer remains willing to re-adopt if anyone needs the keyboard-only legacy.)
3. **`nightpanel` PKGBUILD declares** `provides=('dailydriver')`, `conflicts=('dailydriver')`, `replaces=('dailydriver')` — so `pacman -Syu` on a system that already has `dailydriver` will automatically swap it for `nightpanel` without manual intervention.

## For end-users

```bash
# AUR helpers handle the replacement transparently:
yay -Syu
# or
paru -Syu
```

If you prefer to do it explicitly:

```bash
sudo pacman -R dailydriver
yay -S nightpanel
```

## For the maintainer (one-time, on AUR side)

These steps happen against `aur.archlinux.org`, not in this repo:

```bash
# 1. Clone the new package slot
git clone ssh://aur@aur.archlinux.org/nightpanel.git aur-nightpanel
cd aur-nightpanel

# 2. Copy PKGBUILD + .SRCINFO from this repo's aur/ dir
cp /srv/data/development/nightpanel/aur/PKGBUILD .
cp /srv/data/development/nightpanel/aur/.SRCINFO .

# 3. Fill in the real sha256sum (PKGBUILD currently has SKIP)
SHA=$(curl -sL https://github.com/gregfelice/nightpanel/archive/refs/tags/v0.2.1.tar.gz | sha256sum | awk '{print $1}')
sed -i "s/^sha256sums=.*/sha256sums=('$SHA')/" PKGBUILD
# Re-generate .SRCINFO from the updated PKGBUILD
makepkg --printsrcinfo > .SRCINFO

# 4. Local sanity check (requires a working makepkg env)
makepkg -si

# 5. Push to AUR
git add PKGBUILD .SRCINFO
git commit -m "Initial release of nightpanel 0.2.1 (formerly dailydriver)"
git push

# 6. Orphan the old dailydriver package via AUR web UI:
#    https://aur.archlinux.org/pkgbase/dailydriver/disown
#    (Leave a comment pointing users at `nightpanel`.)
```

## Why `provides`/`conflicts`/`replaces` instead of just orphaning

Without these directives, existing `dailydriver` users would need to manually `pacman -R dailydriver && yay -S nightpanel`. With them, the pacman/AUR-helper upgrade path handles the swap automatically, and there's no window where the user has neither package installed.
