"""
OpenCode client for AI integration with Django using python-opencode-cli.
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class OpenCodeClient:
    """Client for interacting with opencode CLI."""

    def __init__(self, opencode_path: Path | None = None):
        self.opencode_path = opencode_path or self._find_opencode_path()

    def _find_opencode_path(self) -> Path:
        """Find opencode executable."""
        if path := shutil.which("opencode"):
            return Path(path)
        return Path.home() / ".local" / "bin" / "opencode"

    def _find_opencode_auto_path(self) -> Path:
        """Find opencode-auto executable."""
        if path := shutil.which("opencode-auto"):
            return Path(path)
        return Path.home() / ".local" / "bin" / "opencode-auto"

    def chat(
        self, prompt: str, model: str | None = None, timeout: int = 120
    ) -> tuple[str | None, str]:
        """Send a chat prompt using opencode-auto and return model used and response content."""
        opencode_auto_path = self._find_opencode_auto_path()

        if not opencode_auto_path.exists():
            return None, f"opencode-auto not found at {opencode_auto_path}"

        cmd = [str(opencode_auto_path), "run"]
        if model:
            cmd.extend(["-m", model])
        cmd.append(prompt)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return None, "Timeout"
        except FileNotFoundError:
            return None, "Executable not found"

        if result.returncode != 0:
            return None, f"Error: {result.stderr}"

        try:
            data = json.loads(result.stdout)
            if data.get("success"):
                output = data.get("output", "")
                used_model = data.get("model", model or "unknown")
                return used_model, output
            else:
                errors = data.get("errors", [])
                error_msg = "; ".join(e.get("error", "Unknown error") for e in errors)
                return None, error_msg
        except json.JSONDecodeError:
            return None, result.stdout


def chat(prompt: str, model: str | None = None) -> tuple[str | None, str]:
    """Convenience function for one-off chat requests."""
    client = OpenCodeClient()
    return client.chat(prompt, model)
