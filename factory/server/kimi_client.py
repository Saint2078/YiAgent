"""Deprecated shim — use ``yiagent.providers`` or ``llm_client``."""

from llm_client import KimiAPIError, LLMAPIError, chat_completions, extract_content  # noqa: F401
