"""高并发 LLM 客户端：连接池 + 信号量 + 退避重试 + 磁盘缓存 + 计量/预算护栏。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .config import SETTINGS

_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        async with _client_lock:
            if _client is None or _client.is_closed:
                _client = httpx.AsyncClient(
                    base_url=SETTINGS.base_url,
                    timeout=httpx.Timeout(SETTINGS.timeout, connect=20.0),
                    limits=httpx.Limits(
                        max_connections=SETTINGS.max_connections,
                        max_keepalive_connections=max(8, SETTINGS.max_connections // 2),
                        keepalive_expiry=60.0,
                    ),
                    http2=True,
                )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


class Budget(Exception):
    """预算或中止信号。"""


# 有些模型（如 kimi k3）只接受 temperature=1：命中该错误后全局改为不传温度参数。
_TEMP_UNSUPPORTED = {"flag": False}
_TEMP_ERR = re.compile(r"temperature", re.I)


@dataclass
class Meter:
    calls: int = 0
    cache_hits: int = 0
    retries: int = 0
    errors: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    api_seconds: float = 0.0
    # 排队等闸门的时间不算 API 时间，否则并发利用率会被高估
    queue_seconds: float = 0.0
    inflight_peak: int = 0
    hedges: int = 0
    hedge_wins: int = 0
    by_purpose: dict[str, dict[str, float]] = field(default_factory=dict)
    latencies: list[float] = field(default_factory=list)

    def add(self, purpose: str, usage: dict[str, int], seconds: float, cached: bool) -> None:
        row = self.by_purpose.setdefault(
            purpose, {"calls": 0, "cache_hits": 0, "tokens": 0, "seconds": 0.0}
        )
        row["calls"] += 1
        row["tokens"] += usage.get("total_tokens", 0)
        row["seconds"] += seconds
        self.calls += 1
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)
        self.total_tokens += usage.get("total_tokens", 0)
        if cached:
            self.cache_hits += 1
            row["cache_hits"] += 1
        else:
            self.api_seconds += seconds
            self.latencies.append(seconds)

    def snapshot(self) -> dict[str, Any]:
        lat = sorted(self.latencies)
        def pct(p: float) -> float | None:
            if not lat:
                return None
            idx = min(len(lat) - 1, max(0, int(round(p * (len(lat) - 1)))))
            return round(lat[idx], 2)

        return {
            "calls": self.calls,
            "api_calls": self.calls - self.cache_hits,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": round(self.cache_hits / self.calls, 4) if self.calls else None,
            "retries": self.retries,
            "errors": self.errors,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "api_seconds_sum": round(self.api_seconds, 1),
            "queue_seconds_sum": round(self.queue_seconds, 1),
            "inflight_peak": self.inflight_peak,
            "hedges": self.hedges,
            "hedge_wins": self.hedge_wins,
            "latency_p50": pct(0.50),
            "latency_p90": pct(0.90),
            "latency_p99": pct(0.99),
            "latency_max": round(lat[-1], 2) if lat else None,
            "by_purpose": {
                k: {
                    "calls": int(v["calls"]),
                    "cache_hits": int(v["cache_hits"]),
                    "tokens": int(v["tokens"]),
                    "seconds": round(v["seconds"], 1),
                }
                for k, v in sorted(self.by_purpose.items())
            },
        }


def _cache_key(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class Session:
    """一次 run 内共享：并发闸门、计量、缓存、预算。"""

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        *,
        concurrency: int | None = None,
        budget_tokens: int | None = None,
        budget_seconds: float | None = None,
        cache: bool | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model or SETTINGS.model
        self.concurrency = max(1, int(concurrency or SETTINGS.concurrency))
        self.sem = asyncio.Semaphore(self.concurrency)
        self.meter = Meter()
        self.budget_tokens = int(budget_tokens or SETTINGS.default_budget_tokens)
        self.budget_seconds = float(budget_seconds or SETTINGS.default_budget_seconds)
        self.cache_enabled = SETTINGS.cache_enabled if cache is None else bool(cache)
        # 容器时钟可能被宿主机校正而回跳；一切时长用单调钟，wall/延时才不会出现负数
        self.started = time.monotonic()
        self.aborted = False
        self.abort_reason = ""
        self._lock = asyncio.Lock()
        self.inflight = 0
        self.hedge_enabled = SETTINGS.hedge_enabled

    # ---- 护栏 ----
    def abort(self, reason: str = "manual") -> None:
        self.aborted = True
        self.abort_reason = self.abort_reason or reason

    def check(self) -> None:
        if self.aborted:
            raise Budget(f"aborted:{self.abort_reason}")
        if self.meter.total_tokens >= self.budget_tokens:
            self.abort("budget_tokens")
            raise Budget("budget_tokens")
        if self.wall >= self.budget_seconds:
            self.abort("budget_seconds")
            raise Budget("budget_seconds")

    @property
    def wall(self) -> float:
        return max(0.0, time.monotonic() - self.started)

    # ---- 缓存 ----
    def _cache_path(self, key: str) -> Path:
        d = SETTINGS.cache_dir / key[:2]
        return d / f"{key}.json"

    def _cache_get(self, key: str) -> dict[str, Any] | None:
        if not self.cache_enabled:
            return None
        p = self._cache_path(key)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _cache_put(self, key: str, value: dict[str, Any]) -> None:
        if not self.cache_enabled:
            return
        p = self._cache_path(key)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(".tmp")
            tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, p)
        except Exception:
            pass

    # ---- 单次 HTTP（含闸门与计时）----
    async def _post(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> tuple[httpx.Response | None, float, str]:
        """返回 (响应, 真实 API 秒数, 错误串)。排队时间单独计量，不混进 API 秒数。"""
        client = await get_client()
        t_submit = time.monotonic()
        async with self.sem:
            t_start = time.monotonic()
            async with self._lock:
                self.inflight += 1
                self.meter.queue_seconds += max(0.0, t_start - t_submit)
                if self.inflight > self.meter.inflight_peak:
                    self.meter.inflight_peak = self.inflight
            try:
                resp = await client.post("/chat/completions", json=payload, headers=headers)
                return resp, max(0.0, time.monotonic() - t_start), ""
            except Exception as exc:  # 网络/超时
                return None, max(0.0, time.monotonic() - t_start), f"{type(exc).__name__}: {exc}"
            finally:
                async with self._lock:
                    self.inflight -= 1

    def _hedge_after(self) -> float | None:
        """对冲阈值：2×p50，夹在 [min, cap]；样本不足或额度用尽则不对冲。"""
        if not self.hedge_enabled:
            return None
        lat = self.meter.latencies
        if len(lat) < SETTINGS.hedge_min_samples:
            return None
        if self.meter.hedges >= max(2, int(self.meter.calls * SETTINGS.hedge_max_rate)):
            return None
        ordered = sorted(lat)
        p50 = ordered[len(ordered) // 2]
        return max(
            SETTINGS.hedge_min_seconds,
            min(SETTINGS.hedge_cap_seconds, SETTINGS.hedge_p50_factor * p50),
        )

    @staticmethod
    def _drop(task: asyncio.Task) -> None:
        task.cancel()
        task.add_done_callback(lambda t: t.cancelled() or t.exception())

    async def _post_hedged(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> tuple[httpx.Response | None, float, str]:
        after = self._hedge_after()
        if after is None:
            return await self._post(payload, headers)
        primary = asyncio.create_task(self._post(payload, headers))
        done, _ = await asyncio.wait({primary}, timeout=after)
        if done:
            return primary.result()
        async with self._lock:
            self.meter.hedges += 1
        backup = asyncio.create_task(self._post(payload, headers))
        done, pending = await asyncio.wait({primary, backup}, return_when=asyncio.FIRST_COMPLETED)
        winner = done.pop()
        for t in pending:
            self._drop(t)
        if winner is backup:
            async with self._lock:
                self.meter.hedge_wins += 1
        return winner.result()

    # ---- 调用 ----
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        purpose: str,
        max_tokens: int = 2048,
        temperature: float | None = 0.6,
        cache: bool = True,
        salt: str = "",
    ) -> str:
        """salt 只参与缓存键，不进请求体：同一问题的多次重复采样各自独立，重跑仍可命中缓存。"""
        self.check()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max(SETTINGS.min_max_tokens, int(max_tokens)),
        }
        if temperature is not None and not _TEMP_UNSUPPORTED["flag"] and not SETTINGS.drop_temperature:
            payload["temperature"] = temperature
        key = _cache_key({"payload": payload, "salt": salt})

        if cache:
            hit = self._cache_get(key)
            if hit is not None:
                async with self._lock:
                    self.meter.add(purpose, hit.get("usage", {}), 0.0, True)
                return hit.get("text", "")

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        last_err = ""
        for attempt in range(SETTINGS.max_retries + 1):
            self.check()
            resp, dt, err = await self._post_hedged(payload, headers)
            if resp is None:
                last_err = err
                async with self._lock:
                    self.meter.retries += 1
                await asyncio.sleep(min(30.0, 1.5 * (2**attempt)) * (0.6 + random.random() * 0.8))
                continue

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    text = (data["choices"][0]["message"].get("content") or "").strip()
                    usage = data.get("usage") or {}
                    usage = {
                        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                        "completion_tokens": int(usage.get("completion_tokens") or 0),
                        "total_tokens": int(usage.get("total_tokens") or 0),
                    }
                except Exception as exc:
                    last_err = f"bad_body: {exc}"
                    async with self._lock:
                        self.meter.retries += 1
                    await asyncio.sleep(1.0 + random.random())
                    continue
                async with self._lock:
                    self.meter.add(purpose, usage, dt, False)
                if text:
                    self._cache_put(key, {"text": text, "usage": usage})
                    return text
                last_err = "empty_content"
                payload["max_tokens"] = min(16384, int(payload["max_tokens"] * 2))
                async with self._lock:
                    self.meter.retries += 1
                continue

            body = resp.text[:400]
            last_err = f"HTTP {resp.status_code}: {body}"
            # 401/403 是「今天别想跑了」：Key 无效或额度耗尽。重试与后续调用都注定失败，
            # 继续跑只会把一整轮变成几百条静默失败。直接中止整个 Session，让 run 干净收场。
            if resp.status_code in (401, 403):
                self.abort(f"http_{resp.status_code}")
                raise Budget(f"{purpose} HTTP {resp.status_code}: {body}")
            if resp.status_code == 400 and "temperature" in payload and _TEMP_ERR.search(body):
                _TEMP_UNSUPPORTED["flag"] = True
                payload.pop("temperature", None)
                key = _cache_key({"payload": payload, "salt": salt})
                if cache:
                    hit = self._cache_get(key)
                    if hit is not None:
                        async with self._lock:
                            self.meter.add(purpose, hit.get("usage", {}), 0.0, True)
                        return hit.get("text", "")
                continue
            if resp.status_code in (429, 500, 502, 503, 504, 529):
                async with self._lock:
                    self.meter.retries += 1
                wait = min(45.0, 2.0 * (2**attempt)) * (0.6 + random.random() * 0.8)
                ra = resp.headers.get("retry-after")
                if ra:
                    try:
                        wait = max(wait, float(ra))
                    except ValueError:
                        pass
                await asyncio.sleep(wait)
                continue
            break

        async with self._lock:
            self.meter.errors += 1
        raise RuntimeError(f"llm_failed[{purpose}] {last_err}")

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        purpose: str,
        max_tokens: int = 3072,
        temperature: float | None = 0.4,
        repair: bool = True,
        cache: bool = True,
    ) -> Any:
        text = await self.chat(
            messages,
            purpose=purpose,
            max_tokens=max_tokens,
            temperature=temperature,
            cache=cache,
        )
        obj = extract_json(text)
        if obj is not None:
            return obj
        if not repair:
            raise ValueError(f"json_parse_failed[{purpose}]: {text[:200]}")
        # 截断 JSON 常被缓存；修复通道强制绕过缓存并拉高 token
        fixed = await self.chat(
            [
                {
                    "role": "system",
                    "content": "你是 JSON 修复器。补全被截断的 JSON，只输出合法完整 JSON，不要解释、不要代码块。",
                },
                {"role": "user", "content": text[:16000]},
            ],
            purpose=f"{purpose}:repair",
            max_tokens=max(max_tokens, 8192),
            temperature=0.0,
            cache=False,
            salt=f"repair-{len(text)}",
        )
        obj = extract_json(fixed)
        if obj is None:
            raise ValueError(f"json_parse_failed[{purpose}]: {text[:200]}")
        return obj


_FENCE = re.compile(r"```(?:json)?\s*(.+?)```", re.S)


def extract_json(text: str) -> Any | None:
    if not text:
        return None
    candidates: list[str] = []
    m = _FENCE.search(text)
    if m:
        candidates.append(m.group(1))
    candidates.append(text)
    for raw in candidates:
        raw = raw.strip()
        try:
            return json.loads(raw)
        except Exception:
            pass
        for opener, closer in (("{", "}"), ("[", "]")):
            i, j = raw.find(opener), raw.rfind(closer)
            if i >= 0 and j > i:
                try:
                    return json.loads(raw[i : j + 1])
                except Exception:
                    continue
    return None
