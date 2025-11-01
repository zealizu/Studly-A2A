"""
Configuration settings for history management and summarization.

These settings control how conversation history is trimmed and summarized
to reduce prompt size and preprocessing overhead while maintaining context.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# History trimming settings
HISTORY_CAP_TURNS = int(os.getenv("HISTORY_CAP_TURNS", "4"))
HISTORY_CAP_MESSAGES = HISTORY_CAP_TURNS * 2  # Each turn = user + agent message

# Summarization settings
ENABLE_SUMMARIZATION = os.getenv("ENABLE_SUMMARIZATION", "true").lower() == "true"
SUMMARY_THRESHOLD = int(os.getenv("SUMMARY_THRESHOLD", "8"))  # Trigger summary after this many messages

# Cache settings
ENABLE_HISTORY_CACHE = os.getenv("ENABLE_HISTORY_CACHE", "true").lower() == "true"
