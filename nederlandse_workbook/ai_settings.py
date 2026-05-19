"""
AI/OpenCode configuration settings for Dutch Workbook.
"""

import shutil

OPENCODE_ENABLED = bool(shutil.which("opencode"))

DEFAULT_WORD_LEVEL = "A2"
DEFAULT_WORD_COUNT = 10
DEFAULT_TIMEOUT = 120  # seconds
