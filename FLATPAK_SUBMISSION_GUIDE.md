# Flatpak/Flathub Submission Guide

A complete step-by-step guide for submitting an application to Flathub.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Prepare Your Application](#2-prepare-your-application)
3. [Create the Flatpak Manifest](#3-create-the-flatpak-manifest)
4. [Test Your Flatpak Locally](#4-test-your-flatpak-locally)
5. [Prepare Flathub Submission](#5-prepare-flathub-submission)
6. [Submit to Flathub](#6-submit-to-flathub)
7. [Review Process](#7-review-process)
8. [Post-Acceptance Maintenance](#8-post-acceptance-maintenance)
9. [Common Issues & Solutions](#9-common-issues--solutions)

---

## 1. Prerequisites

### 1.1 Install Required Tools

```bash
# Install flatpak and flatpak-builder
sudo apt install flatpak flatpak-builder  # Debian/Ubuntu
sudo dnf install flatpak flatpak-builder  # Fedora

# Add Flathub repository
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install the SDK (match your runtime version)
flatpak install flathub org.gnome.Platform//48 org.gnome.Sdk//48
# Or for KDE:
# flatpak install flathub org.kde.Platform//6.8 org.kde.Sdk//6.8
```

### 1.2 Application Requirements

Your application must have:

- [ ] **Valid App ID** - Reverse DNS format (e.g., `io.github.username.AppName`)
- [ ] **Open source license** - GPL, MIT, Apache, etc. (proprietary apps go to Flathub-beta)
- [ ] **Stable release** - Tagged version in your Git repository
- [ ] **Desktop file** - Valid `.desktop` file with correct app ID
- [ ] **AppStream metadata** - `.metainfo.xml` or `.appdata.xml` file
- [ ] **Application icon** - At least 128x128, preferably scalable SVG

---

## 2. Prepare Your Application

### 2.1 App ID Naming Convention

Your app ID must follow reverse DNS format:

```
io.github.username.AppName      # GitHub hosted
org.example.AppName             # Your domain
com.company.AppName             # Company domain
```

**Rules:**
- Only lowercase letters, numbers, and periods
- At least 3 components (e.g., `org.example.app`)
- No hyphens in components (use CamelCase)

### 2.2 Desktop File

Create `data/your.app.id.desktop`:

```ini
[Desktop Entry]
Name=Your App Name
Comment=Brief description of your app
Exec=your-executable
Icon=your.app.id
Terminal=false
Type=Application
Categories=Utility;GTK;
Keywords=keyword1;keyword2;
StartupNotify=true
```

**Important:** The `Icon=` value must match your app ID exactly.

### 2.3 AppStream Metadata

Create `data/your.app.id.metainfo.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>your.app.id</id>
  <name>Your App Name</name>
  <summary>One-line description</summary>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>

  <description>
    <p>Longer description of your application.</p>
    <p>Can have multiple paragraphs.</p>
  </description>

  <launchable type="desktop-id">your.app.id.desktop</launchable>

  <screenshots>
    <screenshot type="default">
      <image>https://raw.githubusercontent.com/user/repo/main/data/screenshots/main.png</image>
      <caption>Main window showing feature X</caption>
    </screenshot>
  </screenshots>

  <url type="homepage">https://github.com/user/repo</url>
  <url type="bugtracker">https://github.com/user/repo/issues</url>

  <content_rating type="oars-1.1" />

  <releases>
    <release version="1.0.0" date="2024-01-15">
      <description>
        <p>Initial release with features:</p>
        <ul>
          <li>Feature one</li>
          <li>Feature two</li>
        </ul>
      </description>
    </release>
  </releases>

  <developer id="your.developer.id">
    <name>Your Name</name>
  </developer>

  <branding>
    <color type="primary" scheme_preference="light">#ffffff</color>
    <color type="primary" scheme_preference="dark">#000000</color>
  </branding>
</component>
```

### 2.4 Validate Metadata

```bash
# Validate desktop file
desktop-file-validate data/your.app.id.desktop

# Validate AppStream metadata
appstreamcli validate data/your.app.id.metainfo.xml

# Check for NEWS/releases (Flathub requires release info)
appstreamcli validate --pedantic data/your.app.id.metainfo.xml
```

### 2.5 Screenshots

**Requirements:**
- PNG format, 16:9 or similar aspect ratio
- Minimum 620x350, recommended 1600x900 or 1920x1080
- Show actual application UI (not mockups)
- Host on a stable URL (GitHub raw URLs work)
- At least one screenshot required, 3-5 recommended

---

## 3. Create the Flatpak Manifest

### 3.1 Basic Manifest Structure

Create `your.app.id.yml`:

```yaml
app-id: your.app.id
runtime: org.gnome.Platform
runtime-version: '48'
sdk: org.gnome.Sdk
command: your-executable

finish-args:
  # Basic GUI access (almost always needed)
  - --share=ipc
  - --socket=fallback-x11
  - --socket=wayland
  - --device=dri

  # Network access (if needed)
  # - --share=network

  # Filesystem access (minimize this)
  # - --filesystem=home
  # - --filesystem=xdg-documents

modules:
  # Dependencies first
  - name: dependency-name
    buildsystem: meson  # or cmake, simple, autotools
    sources:
      - type: archive
        url: https://example.com/dependency.tar.gz
        sha256: abc123...

  # Your application last
  - name: your-app
    buildsystem: meson
    sources:
      - type: git
        url: https://github.com/user/repo.git
        tag: v1.0.0
```

### 3.2 Common Build Systems

**Meson:**
```yaml
- name: app
  buildsystem: meson
  config-opts:
    - -Doption=value
  sources:
    - type: git
      url: https://github.com/user/repo.git
      tag: v1.0.0
```

**CMake:**
```yaml
- name: app
  buildsystem: cmake-ninja
  config-opts:
    - -DCMAKE_BUILD_TYPE=Release
  sources:
    - type: git
      url: https://github.com/user/repo.git
      tag: v1.0.0
```

**Python (pip):**
```yaml
- name: python3-package
  buildsystem: simple
  build-commands:
    - pip3 install --prefix=/app --no-deps .
  sources:
    - type: git
      url: https://github.com/user/repo.git
      tag: v1.0.0
```

**Python (wheel):**
```yaml
- name: python3-dependency
  buildsystem: simple
  build-commands:
    - unzip -o *.whl -d /app/lib/python3.12/site-packages
  sources:
    - type: file
      url: https://files.pythonhosted.org/packages/.../package-1.0.0-py3-none-any.whl
      sha256: abc123...
```

### 3.3 Permission Reference

| Permission | Use Case |
|-----------|----------|
| `--share=ipc` | X11 shared memory (almost always needed) |
| `--socket=wayland` | Wayland display |
| `--socket=fallback-x11` | X11 fallback |
| `--device=dri` | GPU acceleration |
| `--share=network` | Network access |
| `--socket=pulseaudio` | Audio playback |
| `--filesystem=home` | Full home directory (avoid if possible) |
| `--filesystem=xdg-documents` | Documents folder only |
| `--filesystem=xdg-config/app` | App-specific config |
| `--talk-name=org.freedesktop.Notifications` | Desktop notifications |
| `--talk-name=org.freedesktop.secrets` | Keyring access |

**Flathub prefers minimal permissions.** You'll need to justify any unusual permissions in your PR.

---

## 4. Test Your Flatpak Locally

### 4.1 Build and Install

```bash
# Build the flatpak
flatpak-builder --user --install --force-clean build-dir your.app.id.yml

# Run it
flatpak run your.app.id

# Check for sandbox issues
flatpak run --command=sh your.app.id
# Then run your app manually to see errors
```

### 4.2 Export and Test Bundle

```bash
# Create a repo and export
flatpak-builder --repo=repo --force-clean build-dir your.app.id.yml

# Create a bundle file for testing
flatpak build-bundle repo your-app.flatpak your.app.id

# Install bundle on another machine
flatpak install your-app.flatpak
```

### 4.3 Verify Metadata in Built App

```bash
# Check installed metadata
flatpak info your.app.id
flatpak info --show-metadata your.app.id

# Verify icons installed
ls ~/.local/share/flatpak/app/your.app.id/current/active/files/share/icons/

# Verify desktop file
cat ~/.local/share/flatpak/app/your.app.id/current/active/files/share/applications/your.app.id.desktop
```

---

## 5. Prepare Flathub Submission

### 5.1 Create a GitHub Release

```bash
# Tag your release
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
```

Then create a GitHub Release from the tag with release notes.

### 5.2 Update Manifest for Flathub

Your Flathub manifest should:

1. **Use git source with tag** (not local directory):
```yaml
sources:
  - type: git
    url: https://github.com/user/repo.git
    tag: v1.0.0
    # Optionally pin commit for reproducibility:
    # commit: abc123def456...
```

2. **Remove development-only options**

3. **Use stable dependency versions with checksums**

### 5.3 Create Flathub Manifest Directory

Prepare a directory with:
```
flathub/
├── your.app.id.yml          # The manifest
└── FLATHUB_PR.md             # PR description (optional but helpful)
```

---

## 6. Submit to Flathub

### 6.1 Fork the Flathub Repository

1. Go to https://github.com/flathub/flathub
2. Click "Fork" to create your copy

### 6.2 Create Your App Branch

```bash
# Clone your fork
git clone git@github.com:YOUR_USERNAME/flathub.git
cd flathub

# Create a branch for your app (use the app ID as branch name)
git checkout -b your.app.id

# Copy your manifest
cp /path/to/your.app.id.yml .

# Commit and push
git add your.app.id.yml
git commit -m "Add your.app.id"
git push origin your.app.id
```

### 6.3 Open a Pull Request

1. Go to https://github.com/flathub/flathub
2. Click "Pull requests" → "New pull request"
3. Click "compare across forks"
4. Select your fork and branch
5. Fill in the PR template

### 6.4 PR Template Content

Your PR should include:

```markdown
## App Summary

**App Name** - Brief description

**Homepage:** https://github.com/user/repo
**License:** GPL-3.0-or-later

## Features

- Feature 1
- Feature 2

## Permission Justifications

### [Permission Name]
```
--permission-flag
```
**Justification:** Why this permission is needed.

## Checklist

- [ ] App builds successfully
- [ ] AppStream metadata validates
- [ ] Desktop file validates
- [ ] Icon included (128x128+ or SVG)
- [ ] Screenshots included
- [ ] Release version tagged
- [ ] Content rating present

## Testing

Tested on:
- Distro 1 (Desktop Environment)
- Distro 2 (Desktop Environment)
```

---

## 7. Review Process

### 7.1 Automated Checks

Flathub's CI will:
1. Build your app
2. Validate AppStream metadata
3. Check for common issues
4. Generate a test Flatpak

### 7.2 Manual Review

Reviewers will check:
- **Permissions** - Are they justified and minimal?
- **Metadata** - Is it complete and accurate?
- **Quality** - Does the app work correctly?
- **Guidelines** - Does it follow Flathub guidelines?

### 7.3 Common Review Feedback

| Issue | Solution |
|-------|----------|
| "Too broad filesystem access" | Use specific paths like `xdg-documents` instead of `home` |
| "Missing permission justification" | Add comments explaining why each permission is needed |
| "AppStream validation failed" | Fix metadata issues shown in CI logs |
| "Screenshots not loading" | Use stable URLs (GitHub raw URLs recommended) |
| "No release information" | Add `<releases>` section to metainfo.xml |

### 7.4 Responding to Review

```bash
# Make requested changes
git add .
git commit -m "Address review feedback"
git push origin your.app.id
```

The PR will automatically update.

---

## 8. Post-Acceptance Maintenance

### 8.1 After Merge

Once merged, Flathub will:
1. Create a dedicated repo: `https://github.com/flathub/your.app.id`
2. Build and publish your app
3. Make it available at `https://flathub.org/apps/your.app.id`

### 8.2 Publishing Updates

```bash
# Clone your Flathub repo (you'll have write access)
git clone git@github.com:flathub/your.app.id.git
cd your.app.id

# Update the manifest with new version
# Edit your.app.id.yml:
#   - Update tag: v1.1.0
#   - Optionally update commit hash

git add your.app.id.yml
git commit -m "Update to v1.1.0"
git push
```

The build will start automatically. Check status at:
`https://buildbot.flathub.org/#/apps/your.app.id`

### 8.3 Update Best Practices

1. **Tag releases in your main repo first**
2. **Update AppStream with release notes**
3. **Test locally before pushing to Flathub**
4. **Update dependency versions if needed**

---

## 9. Common Issues & Solutions

### 9.1 Build Failures

**"Module X failed to build"**
```bash
# Check build logs for the specific error
# Common causes:
# - Missing build dependency (add to SDK extensions or modules)
# - Wrong source URL or checksum
# - Incompatible build options
```

**"Cannot find file X"**
- Check that all files are committed to your repo
- Verify paths in meson.build/CMakeLists.txt

### 9.2 Runtime Issues

**"App crashes on launch"**
```bash
# Run with debugging
flatpak run --command=sh your.app.id
# Then: G_MESSAGES_DEBUG=all your-executable
```

**"Cannot access files"**
- Check filesystem permissions in manifest
- Use portals for file access when possible

**"Cannot connect to D-Bus service"**
- Add appropriate `--talk-name=` or `--own-name=` permissions

### 9.3 Metadata Issues

**"AppStream validation failed"**
```bash
# Run local validation with verbose output
appstreamcli validate --pedantic --verbose your.app.id.metainfo.xml
```

**"Screenshots not showing"**
- Ensure URLs are HTTPS
- Use raw GitHub URLs: `https://raw.githubusercontent.com/...`
- Check image dimensions (min 620x350)

### 9.4 Permission Issues

**"Flathub rejected due to permissions"**

Consider alternatives:
| Instead of... | Use... |
|--------------|--------|
| `--filesystem=home` | `--filesystem=xdg-documents` or portals |
| `--socket=system-bus` | Specific `--system-talk-name=` |
| `--device=all` | Specific `--device=dri` |

---

## Quick Reference Commands

```bash
# Build locally
flatpak-builder --user --install --force-clean build-dir app.yml

# Run app
flatpak run your.app.id

# Run with shell access
flatpak run --command=sh your.app.id

# Check permissions
flatpak info --show-permissions your.app.id

# Validate metadata
desktop-file-validate your.app.id.desktop
appstreamcli validate your.app.id.metainfo.xml

# Uninstall
flatpak uninstall your.app.id

# Clean build directory
rm -rf build-dir .flatpak-builder
```

---

## Resources

- [Flathub Documentation](https://docs.flathub.org/)
- [Flatpak Documentation](https://docs.flatpak.org/)
- [AppStream Documentation](https://www.freedesktop.org/software/appstream/docs/)
- [Flathub App Requirements](https://docs.flathub.org/docs/for-app-authors/requirements)
- [Flatpak Manifest Reference](https://docs.flatpak.org/en/latest/manifests.html)
- [Flathub GitHub](https://github.com/flathub/flathub)
