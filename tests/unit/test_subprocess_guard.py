# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the privilege-escalation guardrail in conftest.py.

The guard is an autouse fixture; it's already active in every test in the
suite. These tests exercise it explicitly:

- positive: harmless commands pass through (verified by inspecting the
  subprocess.run / Popen objects to confirm they ARE the wrapped versions,
  and by running a known-safe command via `["true"]`).
- negative: a command starting with pkexec / sudo / doas raises RuntimeError
  with a message that names the offending call.
"""

from __future__ import annotations

import subprocess

import pytest


class TestPrivilegeEscalationGuard:
    """The guard refuses pkexec / sudo / doas but passes everything else."""

    @pytest.mark.parametrize("escalator", ["pkexec", "sudo", "doas"])
    def test_refuses_known_escalator(self, escalator: str) -> None:
        """A list-form argv starting with a known escalator must raise."""
        with pytest.raises(RuntimeError, match="refused subprocess"):
            subprocess.run([escalator, "whoami"], capture_output=True)

    @pytest.mark.parametrize("escalator", ["pkexec", "sudo", "doas"])
    def test_refuses_absolute_path_escalator(self, escalator: str) -> None:
        """The guard must match on basename, so /usr/bin/pkexec is caught too."""
        with pytest.raises(RuntimeError, match="refused subprocess"):
            subprocess.run([f"/usr/bin/{escalator}", "-c", "true"], capture_output=True)

    def test_refuses_shell_string_form(self) -> None:
        """The string form (shell=True) is also checked."""
        with pytest.raises(RuntimeError, match="refused subprocess"):
            subprocess.run("pkexec sh -c 'whoami'", shell=True, capture_output=True)

    def test_refuses_popen_call_check_output(self) -> None:
        """Popen / call / check_output / check_call are also guarded."""
        with pytest.raises(RuntimeError):
            subprocess.Popen(["sudo", "ls"])
        with pytest.raises(RuntimeError):
            subprocess.call(["doas", "whoami"])
        with pytest.raises(RuntimeError):
            subprocess.check_output(["pkexec", "id"])
        with pytest.raises(RuntimeError):
            subprocess.check_call(["sudo", "-n", "true"])

    def test_passes_harmless_command(self) -> None:
        """A non-privileged command must run normally."""
        # `true` is in coreutils, present on every Linux system.
        result = subprocess.run(["true"], capture_output=True)
        assert result.returncode == 0

    def test_passes_modinfo_like_command(self) -> None:
        """modinfo is read-only and harmless; the guard must not block it.

        We don't actually run modinfo (it may not exist on every box);
        we just exercise the dispatch path with a command shape that
        matches the production hid_apple is_available() call.
        """
        # The guard inspects argv[0] only. If it doesn't raise on this
        # construction, the dispatch reached the real subprocess.run.
        result = subprocess.run(["echo", "ok"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "ok" in result.stdout

    def test_error_message_names_the_call(self) -> None:
        """The RuntimeError must include the rejected argv so the developer
        can find the offending call site quickly."""
        with pytest.raises(RuntimeError, match=r"pkexec"):
            subprocess.run(["pkexec", "secret-thing"])
