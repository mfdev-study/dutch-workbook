"""
AI/OpenCode configuration settings for Dutch Workbook.
"""

import shutil

OPENCODE_ENABLED = bool(shutil.which("opencode"))

DEFAULT_WORD_LEVEL = "A2"
DEFAULT_WORD_COUNT = 10
DEFAULT_TIMEOUT = 120  # seconds

# Rate limiting: seconds a user must wait between generation requests.
# Generation spawns an opencode subprocess (CPU + cost), so throttle it.
GENERATION_COOLDOWN_SECONDS = 30
# Maximum pending generations per user (safety cap to prevent queue abuse).
MAX_PENDING_GENERATIONS = 1
