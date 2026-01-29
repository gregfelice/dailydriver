# Releasing Daily Driver

This document describes how to release new versions of Daily Driver.

## Version Numbering

We use semantic versioning with the following conventions:

| Version | Type | Example |
|---------|------|---------|
| `v0.1.0-alpha.1` | Alpha (early testing) | First alpha |
| `v0.1.0-beta.1` | Beta (feature complete) | First beta |
| `v0.1.0-rc.1` | Release candidate | Pre-release |
| `v0.1.0` | Stable release | First stable |
| `v0.1.1` | Patch release | Bug fixes |
| `v0.2.0` | Minor release | New features |

## Release Process

### 1. Update Version Numbers

Update the version in these files:

```bash
# meson.build
project('dailydriver', version: '0.1.0', ...)

# pyproject.toml
version = "0.1.0"

# data/io.github.gregfelice.DailyDriver.metainfo.xml.in
<release version="0.1.0" date="2026-01-28">
```

### 2. Update Changelog in Metainfo

Add a new `<release>` entry in `data/io.github.gregfelice.DailyDriver.metainfo.xml.in`:

```xml
<releases>
  <release version="0.2.0" date="2026-02-15">
    <description>
      <p>New features:</p>
      <ul>
        <li>Added feature X</li>
        <li>Improved Y</li>
      </ul>
    </description>
  </release>
  <!-- Previous releases... -->
</releases>
```

### 3. Create and Push Tag

```bash
# For beta releases
git tag -a dailydriver-v0.1.0-beta.1 -m "Daily Driver v0.1.0-beta.1"

# For stable releases
git tag -a dailydriver-v0.1.0 -m "Daily Driver v0.1.0"

# Push the tag
git push origin dailydriver-v0.1.0
```

### 4. Verify Release

The GitHub Actions workflow will automatically:

1. Build the Flatpak bundle
2. Validate AppStream metadata
3. Create a GitHub Release with the Flatpak attached
4. Mark pre-releases appropriately (alpha, beta, rc)

Check the release at: https://github.com/gregfelice/deeper/releases

## Distribution Channels

### GitHub Releases (Immediate)

Every tagged release creates a GitHub Release with downloadable Flatpak.

### Flathub (Manual Submission)

1. Fork https://github.com/flathub/flathub
2. Create new repo for `io.github.gregfelice.DailyDriver`
3. Copy and adapt our `io.github.gregfelice.DailyDriver.yml`
4. Submit PR to flathub/flathub
5. Maintain the Flathub repo separately

**Beta channel on Flathub:**
- Create a `beta` branch in the Flathub repo
- Users opt-in with `flatpak remote-add flathub-beta`

### Snap Store (Optional)

Create `snapcraft.yaml` and publish to Snap Store.

### AUR (Community)

Create PKGBUILD for Arch Linux users.

## Pre-Release Checklist

- [ ] All tests pass (`pytest tests/`)
- [ ] Flatpak builds successfully
- [ ] AppStream metadata validates
- [ ] Screenshots are up to date
- [ ] Version numbers updated everywhere
- [ ] Changelog entry added
- [ ] README reflects current features

## Post-Release

After a stable release:

1. Announce on relevant channels (if applicable)
2. Update Flathub repo (if published there)
3. Monitor GitHub Issues for bug reports
4. Start planning next release
