"""Kimi Coding Plan OpenAI-compatible chat client."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE = "https://api.kimi.com/coding/v1"


class KimiAPIError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


def _read_http_error(err: urllib.error.HTTPError) -> tuple[int, str]:
    try:
        raw = err.read().decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        raw = ""
    return err.code, raw[:800]


def chat_completions(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 2200,
    base_url: str = DEFAULT_BASE,
    reasoning_effort: str = "low",
    timeout: int = 300,
    retries: int = 4,
) -> dict[str, Any]:
    key = (api_key or "").strip()
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    if len(key) < 8:
        raise KimiAPIError("API Key 无效或过短", status=401)

    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    # Kimi Coding Plan: k3 / k3-256k use reasoning_effort; k2.6 uses plain chat.
    if model in ("k3", "k3-256k") or model.startswith("k3"):
        body["reasoning_effort"] = reasoning_effort

    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last: Exception | None = None
    for i in range(retries):
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": "yiagent-factory-demo/0.3",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            code, raw = _read_http_error(e)
            last = KimiAPIError(
                f"Kimi HTTP {code}: {raw or e.reason}",
                status=code,
                body=raw,
            )
            # Do not retry auth / client errors
            if code in (400, 401, 403, 404, 422):
                raise last from e
            time.sleep(min(2 * (i + 1), 12))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(min(2 * (i + 1), 12))
    raise KimiAPIError(f"kimi api failed: {last}") from last


def extract_content(resp: dict[str, Any]) -> str:
    msg = ((resp.get("choices") or [{}])[0].get("message")) or {}
    return (msg.get("content") or "").strip() or (msg.get("reasoning_content") or "").strip()
