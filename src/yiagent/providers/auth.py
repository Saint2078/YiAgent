"""API key normalization and env resolution."""

from __future__ import annotations

import os

from .registry import PROVIDERS, model_entry


class AuthError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = 401):
        super().__init__(message)
        self.status = status


def normalize_key(api_key: str) -> str:
    key = (api_key or "").strip()
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    if len(key) < 8:
        raise AuthError("API Key 无效或过短", status=401)
    return key


def resolve_api_key(
    *,
    explicit: str | None = None,
    provider_id: str | None = None,
    model: str | None = None,
) -> str:
    """Prefer explicit key; else first non-empty env var for the provider."""
    if explicit and explicit.strip():
        return normalize_key(explicit)
    pid = provider_id
    if not pid and model:
        meta = model_entry(model) or {}
        pid = meta.get("provider") or "openai"
    pid = pid or "openai"
    provider = PROVIDERS.get(pid) or {}
    for name in provider.get("env_keys") or ():
        val = (os.environ.get(name) or "").strip()
        if val:
            return normalize_key(val)
    hint = provider.get("key_hint") or "API Key"
    raise AuthError(f"缺少 API Key（{pid}: {hint}）", status=401)
