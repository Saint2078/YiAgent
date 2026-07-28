"""YiAgent multi-provider LLM layer."""

from .auth import AuthError, normalize_key, resolve_api_key
from .client import (
    KimiAPIError,
    LLMAPIError,
    chat_completions,
    extract_content,
    stream_chat,
)
from .registry import (
    MODELS,
    PROVIDERS,
    model_entry,
    model_ok,
    models_public,
    provider_of,
)
from .usage import (
    TokenMeter,
    current_meter,
    normalize_usage,
    record_from_response,
)

__all__ = [
    "AuthError",
    "KimiAPIError",
    "LLMAPIError",
    "MODELS",
    "PROVIDERS",
    "TokenMeter",
    "chat_completions",
    "current_meter",
    "extract_content",
    "model_entry",
    "model_ok",
    "models_public",
    "normalize_key",
    "normalize_usage",
    "provider_of",
    "record_from_response",
    "resolve_api_key",
    "stream_chat",
]
