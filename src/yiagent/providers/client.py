"""Multi-provider chat client (OpenAI-compatible + Anthropic Messages)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Iterator

from .auth import AuthError, normalize_key
from .registry import PROVIDERS, model_entry
from .usage import record_from_response

USER_AGENT = "yiagent-providers/0.1"


class LLMAPIError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


# Back-compat alias
KimiAPIError = LLMAPIError


def _read_http_error(err: urllib.error.HTTPError) -> tuple[int, str]:
    try:
        raw = err.read().decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        raw = ""
    return err.code, raw[:800]


def _split_system(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    rest: list[dict[str, Any]] = []
    for m in messages:
        role = (m.get("role") or "").strip()
        content = m.get("content") or ""
        if role == "system":
            if content:
                system_parts.append(str(content))
        else:
            # Anthropic text path: only user/assistant with string content
            if role not in ("user", "assistant"):
                role = "user"
            rest.append({"role": role, "content": str(content)})
    return "\n\n".join(system_parts).strip(), rest


def _openai_body(
    model: str,
    messages: list[dict[str, Any]],
    *,
    max_tokens: int,
    meta: dict[str, Any],
    reasoning_effort: str,
    stream: bool = False,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    wire = meta.get("wire_model") or model
    # Strip None content for cleaner payloads
    clean_msgs: list[dict[str, Any]] = []
    for m in messages:
        item = dict(m)
        if item.get("content") is None and item.get("tool_calls"):
            item.pop("content", None)
        clean_msgs.append(item)
    body: dict[str, Any] = {"model": wire, "messages": clean_msgs}
    if meta.get("max_completion_tokens"):
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens
    if meta.get("reasoning_effort") or model in ("k3", "plan/k3") or (
        model.startswith("k3") and meta.get("provider") in ("kimi-plan", "kimi-coding")
    ):
        body["reasoning_effort"] = reasoning_effort
    if stream:
        body["stream"] = True
    if tools:
        body["tools"] = tools
    return body


def _route(model: str, base_url: str | None) -> dict[str, Any]:
    meta = model_entry(model) or {"id": model, "provider": "openai", "supported": True}
    provider_id = str(meta.get("provider") or "openai")
    provider = PROVIDERS.get(provider_id) or PROVIDERS["openai"]
    return {
        "meta": meta,
        "provider_id": provider_id,
        "provider": provider,
        "protocol": provider.get("protocol") or "openai",
        "base": (base_url or provider.get("base_url") or "").rstrip("/"),
        "err_prefix": provider.get("label") or provider_id,
    }


def _headers_openai(provider_id: str, key: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    if provider_id == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/Saint2078/YiAgent"
        headers["X-Title"] = "YiAgent"
    return headers


def _headers_anthropic(key: str) -> dict[str, str]:
    return {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }


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


def _normalize_anthropic(raw: dict[str, Any], model: str, provider_id: str) -> dict[str, Any]:
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


def chat_completions(
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    *,
    max_tokens: int = 2200,
    base_url: str | None = None,
    reasoning_effort: str = "low",
    timeout: int = 300,
    retries: int = 4,
    purpose: str = "llm",
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Provider-aware chat call.
    OpenAI-compatible → POST {base}/chat/completions
    Anthropic → POST {base}/v1/messages (normalized to OpenAI-like response)
    When a TokenMeter is active, records usage under ``purpose``.
    ``tools`` is OpenAI function-calling format (openai protocol only for now).
    """
    try:
        key = normalize_key(api_key)
    except AuthError as e:
        raise LLMAPIError(str(e), status=e.status) from e

    route = _route(model, base_url)
    meta = route["meta"]
    provider_id = route["provider_id"]
    protocol = route["protocol"]
    resolved_base = route["base"]
    err_prefix = route["err_prefix"]

    if protocol == "anthropic":
        # Tool calling via Anthropic format not wired yet; text-only path.
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
            _headers_anthropic(key),
            timeout=timeout,
            retries=retries,
            err_prefix=err_prefix,
        )
        resp = _normalize_anthropic(raw, model, provider_id)
        record_from_response(resp, purpose=purpose, model=model)
        return resp

    body = _openai_body(
        model,
        messages,
        max_tokens=max_tokens,
        meta=meta,
        reasoning_effort=reasoning_effort,
        tools=tools,
    )
    resp = _post_json(
        f"{resolved_base}/chat/completions",
        body,
        _headers_openai(provider_id, key),
        timeout=timeout,
        retries=retries,
        err_prefix=err_prefix,
    )
    if isinstance(resp, dict):
        resp.setdefault("_provider", provider_id)
        record_from_response(resp, purpose=purpose, model=model)
    return resp


def extract_content(resp: dict[str, Any]) -> str:
    msg = ((resp.get("choices") or [{}])[0].get("message")) or {}
    return (msg.get("content") or "").strip() or (msg.get("reasoning_content") or "").strip()


def _iter_sse_lines(resp: Any) -> Iterator[str]:
    while True:
        line = resp.readline()
        if not line:
            break
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        yield line.rstrip("\r\n")


def stream_chat(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 2200,
    base_url: str | None = None,
    reasoning_effort: str = "low",
    timeout: int = 300,
    purpose: str = "llm",
) -> Iterator[str]:
    """
    Yield assistant text deltas. Records usage on the active TokenMeter when the
    stream ends (if the provider includes usage).
    """
    try:
        key = normalize_key(api_key)
    except AuthError as e:
        raise LLMAPIError(str(e), status=e.status) from e

    route = _route(model, base_url)
    meta = route["meta"]
    provider_id = route["provider_id"]
    protocol = route["protocol"]
    resolved_base = route["base"]
    err_prefix = route["err_prefix"]
    usage: dict[str, Any] | None = None
    parts: list[str] = []

    if protocol == "anthropic":
        system, rest = _split_system(messages)
        if not rest:
            rest = [{"role": "user", "content": "(empty)"}]
        body: dict[str, Any] = {
            "model": meta.get("wire_model") or model,
            "max_tokens": max_tokens,
            "messages": rest,
            "stream": True,
        }
        if system:
            body["system"] = system
        url = f"{resolved_base}/v1/messages"
        headers = _headers_anthropic(key)
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for line in _iter_sse_lines(resp):
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload or payload == "[DONE]":
                        continue
                    try:
                        evt = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    et = evt.get("type")
                    if et == "content_block_delta":
                        delta = evt.get("delta") or {}
                        if delta.get("type") == "text_delta":
                            text = delta.get("text") or ""
                            if text:
                                parts.append(text)
                                yield text
                    elif et == "message_delta":
                        usage = evt.get("usage") or usage
                    elif et == "message_start":
                        msg = evt.get("message") or {}
                        if msg.get("usage"):
                            usage = msg.get("usage")
        except urllib.error.HTTPError as e:
            code, raw = _read_http_error(e)
            raise LLMAPIError(
                f"{err_prefix} HTTP {code}: {raw or e.reason}",
                status=code,
                body=raw,
            ) from e
    else:
        body = _openai_body(
            model,
            messages,
            max_tokens=max_tokens,
            meta=meta,
            reasoning_effort=reasoning_effort,
            stream=True,
        )
        url = f"{resolved_base}/chat/completions"
        headers = _headers_openai(provider_id, key)
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for line in _iter_sse_lines(resp):
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload:
                        continue
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("usage"):
                        usage = chunk["usage"]
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    text = delta.get("content") or delta.get("reasoning_content") or ""
                    if text:
                        parts.append(text)
                        yield text
        except urllib.error.HTTPError as e:
            code, raw = _read_http_error(e)
            raise LLMAPIError(
                f"{err_prefix} HTTP {code}: {raw or e.reason}",
                status=code,
                body=raw,
            ) from e

    # Record usage if present; otherwise estimate nothing (0) still counts a call.
    fake = {
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": "".join(parts)}}],
        "usage": usage or {},
        "_provider": provider_id,
    }
    record_from_response(fake, purpose=purpose, model=model)
