"""
AI/OpenRouter configuration settings for Dutch Workbook.
"""

import os

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Feature flags
OPENROUTER_ENABLED = bool(OPENROUTER_API_KEY)

# Default generation settings
DEFAULT_WORD_LEVEL = "A2"
DEFAULT_WORD_COUNT = 10
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 60  # seconds
