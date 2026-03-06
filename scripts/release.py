#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""
DailyDriver Release Tool
Automates version bumping and metadata updates.
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

def update_file(path: Path, pattern: str, replacement: str):
    """Update a file using regex."""
    if not path.exists():
        print(f"Warning: {path} not found.")
        return False
    
    content = path.read_text()
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        path.write_text(new_content)
        print(f"Updated {path}")
        return True
    return False

def bump_version(new_version: str):
    """Update all version occurrences in the codebase."""
    # 1. meson.build
    update_file(
        Path("meson.build"),
        r"version: '0\.[0-9]+\.[0-9]+'",
        f"version: '{new_version}'"
    )
    
    # 2. pyproject.toml
    update_file(
        Path("pyproject.toml"),
        r'version = "0\.[0-9]+\.[0-9]+"',
        f'version = "{new_version}"'
    )
    
    # 3. PKGBUILD
    update_file(
        Path("aur/PKGBUILD"),
        r"pkgver=0\.[0-9]+\.[0-9]+",
        f"pkgver={new_version}"
    )
    
    # 4. snapcraft.yaml
    update_file(
        Path("snap/snapcraft.yaml"),
        r"version: '0\.[0-9]+\.[0-9]+'",
        f"version: '{new_version}'"
    )

def add_changelog_entry(new_version: str, description: str):
    """Add a release entry to AppStream metainfo."""
    path = Path("data/io.github.gregfelice.DailyDriver.metainfo.xml.in")
    if not path.exists():
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    new_release = f"""    <release version="{new_version}" date="{date_str}">
      <description>
        <p>{description}</p>
      </description>
    </release>"""
    
    content = path.read_text()
    if "<releases>" in content:
        # Insert after <releases>
        new_content = content.replace("<releases>", f"<releases>\n{new_release}")
        path.write_text(new_content)
        print(f"Added changelog entry to {path}")

def main():
    parser = argparse.ArgumentParser(description="Prepare a new release")
    parser.add_argument("version", help="New version (e.g., 0.2.0)")
    parser.add_argument("--desc", help="Release description", default="New release")
    
    args = parser.parse_args()
    
    if not re.match(r"^0\.[0-9]+\.[0-9]+$", args.version):
        print("Error: Version must follow 0.X.Y format")
        sys.exit(1)
        
    print(f"Preparing release {args.version}...")
    bump_version(args.version)
    add_changelog_entry(args.version, args.desc)
    
    print("\nNext steps:")
    print(f"1. git add .")
    print(f'2. git commit -m "Release {args.version}"')
    print(f'3. git tag -a v{args.version} -m "Version {args.version}"')
    print(f"4. git push origin main --tags")

if __name__ == "__main__":
    main()
