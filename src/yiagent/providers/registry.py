"""Model and provider catalog."""

from __future__ import annotations

from typing import Any

PROVIDERS: dict[str, dict[str, Any]] = {
    "kimi-coding": {
        "label": "Kimi Coding Plan",
        "base_url": "https://api.kimi.com/coding/v1",
        "protocol": "openai",
        "key_hint": "Kimi Coding Plan Key",
        "env_keys": ("KIMI_API_KEY", "KIMI_CODING_API_KEY"),
    },
    "moonshot": {
        "label": "Moonshot",
        "base_url": "https://api.moonshot.cn/v1",
        "protocol": "openai",
        "key_hint": "Moonshot API Key",
        "env_keys": ("MOONSHOT_API_KEY",),
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "protocol": "openai",
        "key_hint": "OpenAI API Key (sk-…)",
        "env_keys": ("OPENAI_API_KEY",),
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "protocol": "openai",
        "key_hint": "DeepSeek API Key",
        "env_keys": ("DEEPSEEK_API_KEY",),
    },
    "dashscope": {
        "label": "通义 / DashScope",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "protocol": "openai",
        "key_hint": "DashScope API Key (sk-…)",
        "env_keys": ("DASHSCOPE_API_KEY",),
    },
    "zhipu": {
        "label": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "protocol": "openai",
        "key_hint": "智谱 API Key",
        "env_keys": ("ZHIPU_API_KEY", "GLM_API_KEY"),
    },
    "anthropic": {
        "label": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "protocol": "anthropic",
        "key_hint": "Anthropic API Key (sk-ant-…)",
        "env_keys": ("ANTHROPIC_API_KEY",),
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "protocol": "openai",
        "key_hint": "OpenRouter Key (sk-or-…)",
        "env_keys": ("OPENROUTER_API_KEY",),
    },
}

MODELS: list[dict[str, Any]] = [
    {"id": "k3", "label": "Kimi 3", "provider": "kimi-coding", "supported": True},
    {"id": "kimi-k2.6", "label": "Kimi 2.6", "provider": "kimi-coding", "supported": True},
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
    {"id": "qwen-plus", "label": "Qwen Plus", "provider": "dashscope", "supported": True},
    {"id": "qwen-max", "label": "Qwen Max", "provider": "dashscope", "supported": True},
    {"id": "qwen-turbo", "label": "Qwen Turbo", "provider": "dashscope", "supported": True},
    {"id": "glm-4-plus", "label": "GLM-4 Plus", "provider": "zhipu", "supported": True},
    {"id": "glm-4-flash", "label": "GLM-4 Flash", "provider": "zhipu", "supported": True},
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


def provider_of(model_id: str) -> dict[str, Any]:
    meta = model_entry(model_id) or {"id": model_id, "provider": "openai", "supported": True}
    provider_id = meta.get("provider") or "openai"
    return PROVIDERS.get(provider_id) or PROVIDERS["openai"]
