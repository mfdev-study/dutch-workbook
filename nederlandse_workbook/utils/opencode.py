"""
OpenCode client for AI integration with Django using python-opencode-cli.
"""

import logging
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def _strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from a string."""
    return _ANSI_PATTERN.sub("", text)


class OpenCodeClient:
    """Client for interacting with opencode CLI."""

    def __init__(self, opencode_path: Path | None = None):
        self.opencode_path = opencode_path or self._find_opencode_path()

    def _find_opencode_path(self) -> Path:
        """Find opencode executable."""
        if path := shutil.which("opencode"):
            return Path(path)
        return Path.home() / ".local" / "bin" / "opencode"

    def chat(
        self, prompt: str, model: str | None = None, timeout: int = 120
    ) -> tuple[str | None, str]:
        """Send a chat prompt using opencode and return model used and response content."""
        opencode_path = self.opencode_path

        if not opencode_path.exists():
            return None, f"opencode not found at {opencode_path}"

        cmd = [str(opencode_path), "run"]
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

        output = result.stdout
        output = _strip_ansi(output)
        used_model = "deepseek-v4-flash"

        lines = output.strip().splitlines()
        output_lines = [line for line in lines if not line.startswith(">")]
        clean_output = "\n".join(output_lines).strip()

        return used_model, clean_output


def chat(prompt: str, model: str | None = None) -> tuple[str | None, str]:
    """Convenience function for one-off chat requests."""
    client = OpenCodeClient()
    return client.chat(prompt, model)
