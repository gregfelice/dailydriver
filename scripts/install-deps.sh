#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Dependency installation script for DailyDriver local builds

set -euo pipefail

echo "🛠️ Installing build dependencies for Ubuntu/Debian..."

# Check if running as root, if not, try to use sudo
if [ "$EUID" -ne 0 ]; then
  SUDO="sudo"
else
  SUDO=""
fi

$SUDO apt-get update

# 1. Base build tools
$SUDO apt-get install -y \
    build-essential \
    curl \
    git \
    meson \
    ninja-build \
    pkg-config

# 2. GTK4 and Libadwaita development headers (Required for Snap destructive mode)
$SUDO apt-get install -y \
    libgtk-4-dev \
    libadwaita-1-dev \
    blueprint-compiler \
    gobject-introspection \
    libgirepository1.0-dev

# 3. Python development headers (Required for Snap destructive mode)
$SUDO apt-get install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-gi

# 4. AppImage dependencies (Specifically libfuse2 which is missing on Ubuntu >= 22.04)
# Try installing libfuse2, fallback to libfuse2t64 for newer Ubuntus
$SUDO apt-get install -y libfuse2 || $SUDO apt-get install -y libfuse2t64

echo "✅ Dependencies installed successfully!"
