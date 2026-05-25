# SPDX-License-Identifier: GPL-3.0-or-later
"""Services for Daily Driver."""

from nightpanel.services.backends import (
    DesktopEnvironment,
    GnomeShortcutsBackend,
    KDEShortcutsBackend,
    ShortcutsBackend,
    detect_desktop,
    get_shortcuts_backend,
)
from nightpanel.services.gsettings_service import GSettingsService
from nightpanel.services.keyboard_config_service import (
    CapsLockBehavior,
    KeyboardConfigService,
    ModifierConfig,
)
from nightpanel.services.profile_service import ProfileService

__all__ = [
    # Backends (new cross-desktop API)
    "ShortcutsBackend",
    "GnomeShortcutsBackend",
    "KDEShortcutsBackend",
    "DesktopEnvironment",
    "detect_desktop",
    "get_shortcuts_backend",
    # Legacy (backwards compatibility)
    "GSettingsService",
    # Other services
    "ProfileService",
    "KeyboardConfigService",
    "CapsLockBehavior",
    "ModifierConfig",
]
