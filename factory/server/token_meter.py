"""Per-session LLM token meter (prompt / completion / total)."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

_active: ContextVar["TokenMeter | None"] = ContextVar("yiagent_token_meter", default=None)


def normalize_usage(usage: dict[str, Any] | None) -> dict[str, int]:
    """Normalize OpenAI- and Anthropic-shaped usage dicts."""
    u = usage if isinstance(usage, dict) else {}
    prompt = int(u.get("prompt_tokens") or u.get("input_tokens") or 0)
    completion = int(u.get("completion_tokens") or u.get("output_tokens") or 0)
    cached = 0
    details = u.get("prompt_tokens_details")
    if isinstance(details, dict):
        cached = int(details.get("cached_tokens") or 0)
    cached = int(
        u.get("cache_read_input_tokens")
        or u.get("cached_tokens")
        or cached
        or 0
    )
    total = int(u.get("total_tokens") or (prompt + completion))
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "cached_tokens": cached,
        "total_tokens": total,
    }


class TokenMeter:
    """Thread-safe accumulator for one factory session."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls: list[dict[str, Any]] = []
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cached_tokens = 0
        self.total_tokens = 0
        self.by_purpose: dict[str, dict[str, int]] = {}

    def add(
        self,
        *,
        purpose: str,
        model: str,
        usage: dict[str, Any] | None,
        provider: str = "",
    ) -> dict[str, int]:
        norm = normalize_usage(usage)
        purpose = purpose or "llm"
        with self._lock:
            self.calls.append(
                {
                    "purpose": purpose,
                    "model": model,
                    "provider": provider,
                    **norm,
                }
            )
            self.prompt_tokens += norm["prompt_tokens"]
            self.completion_tokens += norm["completion_tokens"]
            self.cached_tokens += norm["cached_tokens"]
            self.total_tokens += norm["total_tokens"]
            bucket = self.by_purpose.setdefault(
                purpose,
                {
                    "calls": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cached_tokens": 0,
                    "total_tokens": 0,
                },
            )
            bucket["calls"] += 1
            bucket["prompt_tokens"] += norm["prompt_tokens"]
            bucket["completion_tokens"] += norm["completion_tokens"]
            bucket["cached_tokens"] += norm["cached_tokens"]
            bucket["total_tokens"] += norm["total_tokens"]
        return norm

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "calls": len(self.calls),
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "cached_tokens": self.cached_tokens,
                "total_tokens": self.total_tokens,
                "by_purpose": {k: dict(v) for k, v in self.by_purpose.items()},
            }

    @contextmanager
    def activate(self) -> Iterator["TokenMeter"]:
        token = _active.set(self)
        try:
            yield self
        finally:
            _active.reset(token)


def current_meter() -> TokenMeter | None:
    return _active.get()


def record_from_response(
    resp: dict[str, Any] | None,
    *,
    purpose: str,
    model: str,
) -> dict[str, int] | None:
    meter = current_meter()
    if meter is None or not isinstance(resp, dict):
        return None
    return meter.add(
        purpose=purpose,
        model=model or str(resp.get("model") or ""),
        usage=resp.get("usage"),
        provider=str(resp.get("_provider") or ""),
    )
