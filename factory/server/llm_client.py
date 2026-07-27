"""Multi-provider chat client (OpenAI-compatible + Anthropic Messages)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

# ---- Provider registry -------------------------------------------------------

PROVIDERS: dict[str, dict[str, Any]] = {
    "kimi-coding": {
        "label": "Kimi Coding Plan",
        "base_url": "https://api.kimi.com/coding/v1",
        "protocol": "openai",
        "key_hint": "Kimi Coding Plan Key",
    },
    "moonshot": {
        "label": "Moonshot",
        "base_url": "https://api.moonshot.cn/v1",
        "protocol": "openai",
        "key_hint": "Moonshot API Key",
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "protocol": "openai",
        "key_hint": "OpenAI API Key (sk-…)",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "protocol": "openai",
        "key_hint": "DeepSeek API Key",
    },
    "dashscope": {
        "label": "通义 / DashScope",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "protocol": "openai",
        "key_hint": "DashScope API Key (sk-…)",
    },
    "zhipu": {
        "label": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "protocol": "openai",
        "key_hint": "智谱 API Key",
    },
    "anthropic": {
        "label": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "protocol": "anthropic",
        "key_hint": "Anthropic API Key (sk-ant-…)",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "protocol": "openai",
        "key_hint": "OpenRouter Key (sk-or-…)",
    },
}

# id → catalog entry (provider + wire model id + flags)
MODELS: list[dict[str, Any]] = [
    # Kimi Coding Plan
    {"id": "k3", "label": "Kimi 3", "provider": "kimi-coding", "supported": True},
    {"id": "kimi-k2.6", "label": "Kimi 2.6", "provider": "kimi-coding", "supported": True},
    # Moonshot open platform
    {
        "id": "moonshot-v1-auto",
        "label": "Moonshot Auto",
        "provider": "moonshot",
        "supported": True,
    },
    {
        "id": "moonshot-v1-128k",
        "label": "Moonshot 128k",
        "provider": "moonshot",
        "supported": True,
    },
    # OpenAI
    {"id": "gpt-4o", "label": "GPT-4o", "provider": "openai", "supported": True},
    {"id": "gpt-4.1", "label": "GPT-4.1", "provider": "openai", "supported": True},
    {"id": "gpt-4.1-mini", "label": "GPT-4.1 mini", "provider": "openai", "supported": True},
    {
        "id": "o4-mini",
        "label": "o4-mini",
        "provider": "openai",
        "supported": True,
        "max_completion_tokens": True,
    },
    # DeepSeek
    {
        "id": "deepseek-chat",
        "label": "DeepSeek Chat",
        "provider": "deepseek",
        "supported": True,
    },
    {
        "id": "deepseek-reasoner",
        "label": "DeepSeek Reasoner",
        "provider": "deepseek",
        "supported": True,
    },
    # Qwen via DashScope OpenAI-compat
    {"id": "qwen-plus", "label": "Qwen Plus", "provider": "dashscope", "supported": True},
    {"id": "qwen-max", "label": "Qwen Max", "provider": "dashscope", "supported": True},
    {"id": "qwen-turbo", "label": "Qwen Turbo", "provider": "dashscope", "supported": True},
    # Zhipu
    {"id": "glm-4-plus", "label": "GLM-4 Plus", "provider": "zhipu", "supported": True},
    {"id": "glm-4-flash", "label": "GLM-4 Flash", "provider": "zhipu", "supported": True},
    # Anthropic (native Messages API)
    {
        "id": "claude-sonnet-4-5",
        "label": "Claude Sonnet 4.5",
        "provider": "anthropic",
        "supported": True,
    },
    {
        "id": "claude-3-5-haiku-latest",
        "label": "Claude 3.5 Haiku",
        "provider": "anthropic",
        "supported": True,
    },
    # OpenRouter escape hatch
    {
        "id": "anthropic/claude-sonnet-4",
        "label": "OR · Claude Sonnet 4",
        "provider": "openrouter",
        "supported": True,
    },
    {
        "id": "google/gemini-2.5-pro",
        "label": "OR · Gemini 2.5 Pro",
        "provider": "openrouter",
        "supported": True,
    },
]


def model_entry(model_id: str) -> dict[str, Any] | None:
    return next((m for m in MODELS if m["id"] == model_id), None)


def model_ok(model_id: str) -> bool:
    m = model_entry(model_id)
    return bool(m and m.get("supported"))


def models_public() -> list[dict[str, Any]]:
    """Payload for GET /api/models (UI-friendly)."""
    out = []
    for m in MODELS:
        p = PROVIDERS.get(m["provider"], {})
        out.append(
            {
                "id": m["id"],
                "label": m["label"],
                "provider": m["provider"],
                "provider_label": p.get("label") or m["provider"],
                "key_hint": p.get("key_hint") or "API Key",
                "supported": bool(m.get("supported")),
            }
        )
    return out


class LLMAPIError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


# Back-compat alias used by older imports
KimiAPIError = LLMAPIError


def _read_http_error(err: urllib.error.HTTPError) -> tuple[int, str]:
    try:
        raw = err.read().decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        raw = ""
    return err.code, raw[:800]


def _normalize_key(api_key: str) -> str:
    key = (api_key or "").strip()
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    if len(key) < 8:
        raise LLMAPIError("API Key 无效或过短", status=401)
    return key


def _split_system(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    system_parts: list[str] = []
    rest: list[dict[str, str]] = []
    for m in messages:
        role = (m.get("role") or "").strip()
        content = m.get("content") or ""
        if role == "system":
            if content:
                system_parts.append(content)
        else:
            # Anthropic only accepts user/assistant in messages
            if role not in ("user", "assistant"):
                role = "user"
            rest.append({"role": role, "content": content})
    return "\n\n".join(system_parts).strip(), rest


def _openai_body(model: str, messages: list[dict[str, str]], *, max_tokens: int, meta: dict[str, Any], reasoning_effort: str) -> dict[str, Any]:
    wire = meta.get("wire_model") or model
    body: dict[str, Any] = {"model": wire, "messages": messages}
    if meta.get("max_completion_tokens"):
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens
    # Kimi Coding Plan reasoning models
    if model in ("k3", "k3-256k") or (model.startswith("k3") and meta.get("provider") == "kimi-coding"):
        body["reasoning_effort"] = reasoning_effort
    return body


def _post_json(
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    *,
    timeout: int,
    retries: int,
    err_prefix: str,
) -> dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last: Exception | None = None
    for i in range(retries):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            code, raw = _read_http_error(e)
            last = LLMAPIError(
                f"{err_prefix} HTTP {code}: {raw or e.reason}",
                status=code,
                body=raw,
            )
            if code in (400, 401, 403, 404, 422):
                raise last from e
            time.sleep(min(2 * (i + 1), 12))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(min(2 * (i + 1), 12))
    raise LLMAPIError(f"{err_prefix} failed: {last}") from last


def chat_completions(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 2200,
    base_url: str | None = None,
    reasoning_effort: str = "low",
    timeout: int = 300,
    retries: int = 4,
) -> dict[str, Any]:
    """
    Provider-aware chat call.
    OpenAI-compatible providers → POST {base}/chat/completions
    Anthropic → POST {base}/v1/messages (normalized to OpenAI-like response)
    """
    key = _normalize_key(api_key)
    meta = model_entry(model) or {"id": model, "provider": "openai", "supported": True}
    provider_id = meta.get("provider") or "openai"
    provider = PROVIDERS.get(provider_id) or PROVIDERS["openai"]
    protocol = provider.get("protocol") or "openai"
    resolved_base = (base_url or provider.get("base_url") or "").rstrip("/")
    err_prefix = provider.get("label") or provider_id

    if protocol == "anthropic":
        system, rest = _split_system(messages)
        if not rest:
            rest = [{"role": "user", "content": "(empty)"}]
        body = {
            "model": meta.get("wire_model") or model,
            "max_tokens": max_tokens,
            "messages": rest,
        }
        if system:
            body["system"] = system
        raw = _post_json(
            f"{resolved_base}/v1/messages",
            body,
            {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
                "User-Agent": "yiagent-factory/0.5",
            },
            timeout=timeout,
            retries=retries,
            err_prefix=err_prefix,
        )
        # Normalize to OpenAI-shaped response for extract_content()
        text_parts = []
        for block in raw.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text") or "")
        content = "".join(text_parts).strip()
        return {
            "id": raw.get("id"),
            "model": raw.get("model") or model,
            "choices": [{"message": {"role": "assistant", "content": content}}],
            "usage": raw.get("usage") or {},
            "_provider": provider_id,
            "_raw": raw,
        }

    body = _openai_body(
        model, messages, max_tokens=max_tokens, meta=meta, reasoning_effort=reasoning_effort
    )
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "yiagent-factory/0.5",
    }
    if provider_id == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/Saint2078/YiAgent"
        headers["X-Title"] = "YiAgent Factory"

    return _post_json(
        f"{resolved_base}/chat/completions",
        body,
        headers,
        timeout=timeout,
        retries=retries,
        err_prefix=err_prefix,
    )


def extract_content(resp: dict[str, Any]) -> str:
    msg = ((resp.get("choices") or [{}])[0].get("message")) or {}
    return (msg.get("content") or "").strip() or (msg.get("reasoning_content") or "").strip()
