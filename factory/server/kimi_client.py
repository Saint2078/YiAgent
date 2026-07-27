"""Back-compat shim — prefer `llm_client` for new code."""

from llm_client import KimiAPIError, LLMAPIError, chat_completions, extract_content  # noqa: F401

# Historical default (Kimi Coding Plan)
DEFAULT_BASE = "https://api.kimi.com/coding/v1"
