# SPDX-License-Identifier: GPL-3.0-or-later
import json

import pytest

from nightpanel.adapters.gemini_cli import GeminiCliAdapter
from nightpanel.palette import NIGHTPANEL


@pytest.fixture
def mock_gemini_env(tmp_path, monkeypatch):
    settings = tmp_path / "settings.json"
    wrapper = tmp_path / "gemini"

    monkeypatch.setattr("nightpanel.adapters.gemini_cli._SETTINGS", settings)
    monkeypatch.setattr("nightpanel.adapters.gemini_cli._WRAPPER", wrapper)

    return settings


def test_gemini_cli_apply_writes_custom_theme(mock_gemini_env):
    """apply() flips ui.theme to 'nightpanel' and writes the customTheme block.

    Mixed-form check: text/status slots use ANSI color names (which
    alacritty's repainted 16-color palette renders exactly under the
    COLORTERM strip) while backgrounds use the palette hex so gemini's
    interpolation math produces predictable derivatives.
    """
    settings_path = mock_gemini_env
    GeminiCliAdapter().apply(NIGHTPANEL)

    assert settings_path.exists()
    data = json.loads(settings_path.read_text())
    assert data["ui"]["theme"] == "nightpanel"

    theme = data["ui"]["customThemes"]["nightpanel"]
    # Backgrounds clamp to alacritty canvas.
    assert theme["background"]["primary"] == NIGHTPANEL.bg
    assert theme["background"]["diff"]["added"] == NIGHTPANEL.bg
    assert theme["background"]["diff"]["removed"] == NIGHTPANEL.bg
    # Text slots are ANSI names — exact palette match via alacritty.
    assert theme["text"]["primary"] == "green"
    assert theme["text"]["link"] == "greenbright"
    assert theme["text"]["accent"] == "yellow"
    # Hex on text.secondary drives the bg interpolation toward canvas
    # without forcing secondary text to disappear.
    assert theme["text"]["secondary"] == NIGHTPANEL.fg_mid
    assert theme["status"]["error"] == "red"
    assert theme["ui"]["comment"] == "blue"
    assert theme["ui"]["symbol"] == "yellow"
    # DarkGray bypasses interpolation and sets borders directly.
    assert theme["DarkGray"] == NIGHTPANEL.border_d


def test_gemini_cli_apply_preserves_other_custom_themes(mock_gemini_env):
    """User-defined customThemes (other than 'nightpanel') survive apply."""
    settings_path = mock_gemini_env
    settings_path.write_text(
        json.dumps(
            {
                "ui": {
                    "theme": "user-custom",
                    "customThemes": {
                        "user-custom": {"name": "user-custom"},
                    },
                }
            }
        )
    )
    GeminiCliAdapter().apply(NIGHTPANEL)

    data = json.loads(settings_path.read_text())
    assert data["ui"]["theme"] == "nightpanel"
    assert "user-custom" in data["ui"]["customThemes"]
    assert "nightpanel" in data["ui"]["customThemes"]


def test_gemini_cli_revert_restores_previous_theme(mock_gemini_env):
    settings_path = mock_gemini_env
    adapter = GeminiCliAdapter()

    settings_path.write_text(json.dumps({"ui": {"theme": "Dracula"}}))
    snapshot = adapter.snapshot()

    adapter.apply(NIGHTPANEL)
    assert json.loads(settings_path.read_text())["ui"]["theme"] == "nightpanel"

    adapter.revert(snapshot)
    assert json.loads(settings_path.read_text())["ui"]["theme"] == "Dracula"


def test_gemini_cli_snapshot_ignores_own_applied_value(mock_gemini_env):
    """If the live theme is already our applied 'nightpanel', revert
    should fall back to 'Default' rather than reapplying our own value
    after the customTheme block is gone."""
    settings_path = mock_gemini_env
    adapter = GeminiCliAdapter()

    settings_path.write_text(json.dumps({"ui": {"theme": "nightpanel"}}))
    snapshot = adapter.snapshot()
    assert snapshot["theme"] is None

    adapter.apply(NIGHTPANEL)
    adapter.revert(snapshot)
    assert json.loads(settings_path.read_text())["ui"]["theme"] == "Default"


def test_gemini_cli_verify(mock_gemini_env):
    from nightpanel.adapters.gemini_cli import _WRAPPER, _WRAPPER_MARKER

    adapter = GeminiCliAdapter()

    # Pre-write the bare marker; full content equality check will fail
    # until apply() rewrites it with the real wrapper script.
    _WRAPPER.parent.mkdir(parents=True, exist_ok=True)
    _WRAPPER.write_text(_WRAPPER_MARKER)

    assert adapter.verify("on") is False

    adapter.apply(NIGHTPANEL)
    assert adapter.verify("on") is True
    assert adapter.verify("off") is False

    adapter.revert({"theme": "Default"})
    assert adapter.verify("on") is False
    assert adapter.verify("off") is True


def test_gemini_cli_wrapper_strips_colorterm_when_active(mock_gemini_env):
    """The installed wrapper script must strip COLORTERM behind the
    nightpanel-active sentinel — same trick as claude_code."""
    from nightpanel.adapters.gemini_cli import _WRAPPER

    GeminiCliAdapter().apply(NIGHTPANEL)
    script = _WRAPPER.read_text()
    assert "env -u COLORTERM" in script
    assert "nightpanel-active" in script
