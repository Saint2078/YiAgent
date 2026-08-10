from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx

_TEMP_DROP = {"flag": False}
_TEMP_ERR = re.compile(r"temperature", re.I)


def api_key() -> str:
    env = os.environ.get("CB_API_KEY", "").strip()
    if env:
        return env
    p = Path(os.environ.get("CB_KEY_FILE", "/run/secrets/kimi.key"))
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return ""


def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    max_tokens: int = 8192,
    timeout: float = 240.0,
) -> dict[str, Any]:
    key = api_key()
    if not key:
        raise RuntimeError("missing_kimi_key")
    base = os.environ.get("CB_BASE_URL", "https://api.kimi.com/coding/v1").rstrip("/")
    model = model or os.environ.get("CB_MODEL", "k3")
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if not _TEMP_DROP["flag"]:
        body["temperature"] = 0

    with httpx.Client(base_url=base, timeout=timeout) as client:
        for attempt in range(3):
            r = client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                content=json.dumps(body),
            )
            if r.status_code == 400 and _TEMP_ERR.search(r.text or "") and "temperature" in body:
                body.pop("temperature", None)
                _TEMP_DROP["flag"] = True
                continue
            if r.status_code >= 500 and attempt < 2:
                continue
            r.raise_for_status()
            data = r.json()
            msg = ((data.get("choices") or [{}])[0].get("message")) or {}
            content = (msg.get("content") or "") or ""
            # k3 偶发只把正文放在 reasoning_content
            if not str(content).strip():
                alt = msg.get("reasoning_content") or msg.get("reasoning") or ""
                if str(alt).strip():
                    content = alt
            usage = data.get("usage") or {}
            return {
                "content": content,
                "usage": usage,
                "model": model,
                "raw": data,
                "finish_reason": ((data.get("choices") or [{}])[0].get("finish_reason")),
            }
    raise RuntimeError("kimi_chat_failed")
