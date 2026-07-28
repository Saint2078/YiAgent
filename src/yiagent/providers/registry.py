"""Model and provider catalog."""

from __future__ import annotations

from typing import Any

PROVIDERS: dict[str, dict[str, Any]] = {
    # Official pay-as-you-go Open Platform (CN). Intl twin: api.moonshot.ai/v1
    "kimi": {
        "label": "Kimi 开放平台",
        "base_url": "https://api.moonshot.cn/v1",
        "protocol": "openai",
        "key_hint": "Kimi 开放平台 Key (platform.kimi.com)",
        "env_keys": ("MOONSHOT_API_KEY", "KIMI_API_KEY"),
    },
    # Subscription Plan endpoint (separate keys; not interchangeable with 开放平台)
    "kimi-plan": {
        "label": "Kimi Plan",
        "base_url": "https://api.kimi.com/coding/v1",
        "protocol": "openai",
        "key_hint": "Kimi Plan Key",
        "env_keys": ("KIMI_PLAN_API_KEY", "KIMI_CODING_API_KEY"),
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

# Backward-compatible aliases (old ids → same endpoint as kimi / kimi-plan)
PROVIDERS["moonshot"] = {
    **PROVIDERS["kimi"],
    "label": "Kimi 开放平台 (moonshot)",
}
PROVIDERS["kimi-coding"] = {
    **PROVIDERS["kimi-plan"],
    "label": "Kimi Plan (legacy id)",
}

MODELS: list[dict[str, Any]] = [
    # —— Kimi 开放平台（官方按量）——
    {
        "id": "kimi-k2.5",
        "label": "Kimi K2.5",
        "provider": "kimi",
        "supported": True,
    },
    {
        "id": "kimi-k2.6",
        "label": "Kimi K2.6",
        "provider": "kimi",
        "supported": True,
    },
    {
        "id": "kimi-latest",
        "label": "Kimi Latest",
        "provider": "kimi",
        "supported": True,
    },
    {
        "id": "moonshot-v1-auto",
        "label": "Moonshot Auto",
        "provider": "kimi",
        "supported": True,
    },
    {
        "id": "moonshot-v1-128k",
        "label": "Moonshot 128k",
        "provider": "kimi",
        "supported": True,
    },
    {
        "id": "moonshot-v1-32k",
        "label": "Moonshot 32k",
        "provider": "kimi",
        "supported": True,
    },
    {
        "id": "moonshot-v1-8k",
        "label": "Moonshot 8k",
        "provider": "kimi",
        "supported": True,
    },
    # —— Kimi Plan（订阅端点；Key/URL 与开放平台不互通）——
    {
        "id": "plan/kimi-k2.6",
        "label": "Kimi K2.6",
        "provider": "kimi-plan",
        "wire_model": "kimi-k2.6",
        "supported": True,
    },
    {
        "id": "plan/k3",
        "label": "Kimi 3",
        "provider": "kimi-plan",
        "wire_model": "k3",
        "supported": True,
        "reasoning_effort": True,
    },
    # Legacy catalog ids (still resolve; prefer plan/* or 开放平台 models above)
    {
        "id": "k3",
        "label": "Kimi 3 (Plan)",
        "provider": "kimi-plan",
        "supported": True,
        "reasoning_effort": True,
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
    # Hide raw legacy id `k3` in UI (still accepted by model_ok / chat); use plan/k3.
    hide_ids = {"k3"}
    out = []
    for m in MODELS:
        if m["id"] in hide_ids:
            continue
        provider_id = m["provider"]
        p = PROVIDERS.get(provider_id, {})
        label = p.get("label") or provider_id
        # Don't surface legacy alias provider names in UI
        if provider_id == "kimi-coding":
            label = PROVIDERS["kimi-plan"]["label"]
        if provider_id == "moonshot":
            label = PROVIDERS["kimi"]["label"]
        out.append(
            {
                "id": m["id"],
                "label": m["label"],
                "provider": "kimi-plan" if provider_id == "kimi-coding" else (
                    "kimi" if provider_id == "moonshot" else provider_id
                ),
                "provider_label": label,
                "key_hint": p.get("key_hint") or "API Key",
                "supported": bool(m.get("supported")),
            }
        )
    return out


def provider_of(model_id: str) -> dict[str, Any]:
    meta = model_entry(model_id) or {"id": model_id, "provider": "kimi", "supported": True}
    provider_id = meta.get("provider") or "kimi"
    return PROVIDERS.get(provider_id) or PROVIDERS["kimi"]
