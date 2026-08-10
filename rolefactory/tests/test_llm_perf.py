"""并发/计量/长尾对冲自测。全程离线：假 HTTP 客户端，不发请求、不读密钥。

跑法：python -m tests.test_llm_perf（在 /srv 或 rolefactory 目录下）
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import llm  # noqa: E402
from app.config import SETTINGS  # noqa: E402

FAILS: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        FAILS.append(f"{name}: got={got!r} want={want!r}")


def ok(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        FAILS.append(f"{name}: {detail or 'false'}")


class FakeResponse:
    def __init__(self, text: str = "ok", status_code: int = 200) -> None:
        self.status_code = status_code
        self._text = text
        self.headers: dict[str, str] = {}

    @property
    def text(self) -> str:
        return self._text

    def json(self) -> dict:
        return {
            "choices": [{"message": {"content": self._text}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }


class FakeClient:
    """按调用序号决定耗时；记录并发峰值，供断言。"""

    def __init__(self, delays: list[float], *, default_delay: float = 0.01) -> None:
        self.delays = delays
        self.default_delay = default_delay
        self.calls = 0
        self.inflight = 0
        self.peak = 0
        self.is_closed = False

    async def post(self, _path: str, **_kw) -> FakeResponse:
        idx = self.calls
        self.calls += 1
        self.inflight += 1
        self.peak = max(self.peak, self.inflight)
        try:
            delay = self.delays[idx] if idx < len(self.delays) else self.default_delay
            await asyncio.sleep(delay)
            return FakeResponse(f"reply-{idx}")
        finally:
            self.inflight -= 1


def install(client: FakeClient) -> None:
    async def _get_client():
        return client

    llm.get_client = _get_client  # type: ignore[assignment]


# ---- 1) 排队时间不计入 API 时间；闸门不被突破 ----


def test_queue_vs_api() -> None:
    client = FakeClient([], default_delay=0.05)
    install(client)
    session = llm.Session("k", "m", concurrency=2, cache=False)

    async def run() -> None:
        await asyncio.gather(
            *(
                session.chat([{"role": "user", "content": f"q{i}"}], purpose="t", salt=str(i))
                for i in range(6)
            )
        )

    asyncio.run(run())
    snap = session.meter.snapshot()
    check("6 次调用", snap["calls"], 6)
    ok("闸门未被突破", client.peak <= 2, f"peak={client.peak}")
    ok("计量并发峰值一致", snap["inflight_peak"] <= 2, f"inflight_peak={snap['inflight_peak']}")
    # 每条 0.05s，闸门 2 → 3 波；排队秒数必须为正且 API 秒数≈6×0.05
    ok("排队秒数为正", snap["queue_seconds_sum"] > 0, f"queue={snap['queue_seconds_sum']}")
    ok(
        "API 秒数不含排队",
        0.2 <= snap["api_seconds_sum"] <= 0.45,
        f"api={snap['api_seconds_sum']}",
    )


# ---- 2) 长尾对冲：慢条被补发，且补发先到时计一次 win ----


def test_hedge_fires() -> None:
    # 前 8 条建立 p50 样本（快），第 9 条极慢 → 触发对冲，补发很快返回
    delays = [0.02] * 8 + [5.0] + [0.02] * 4
    client = FakeClient(delays, default_delay=0.02)
    install(client)

    old = (
        SETTINGS.hedge_enabled,
        SETTINGS.hedge_min_samples,
        SETTINGS.hedge_min_seconds,
        SETTINGS.hedge_cap_seconds,
        SETTINGS.hedge_p50_factor,
        SETTINGS.hedge_max_rate,
    )
    SETTINGS.hedge_enabled = True
    SETTINGS.hedge_min_samples = 8
    SETTINGS.hedge_min_seconds = 0.1
    SETTINGS.hedge_cap_seconds = 0.3
    SETTINGS.hedge_p50_factor = 2.0
    SETTINGS.hedge_max_rate = 0.5
    try:
        session = llm.Session("k", "m", concurrency=8, cache=False)

        async def run() -> str:
            for i in range(8):
                await session.chat(
                    [{"role": "user", "content": f"warm{i}"}], purpose="warm", salt=f"w{i}"
                )
            return await session.chat(
                [{"role": "user", "content": "slow"}], purpose="slow", salt="s"
            )

        got = asyncio.run(run())
        snap = session.meter.snapshot()
        ok("触发了对冲", snap["hedges"] >= 1, f"hedges={snap['hedges']}")
        ok("对冲先到并被采用", snap["hedge_wins"] >= 1, f"wins={snap['hedge_wins']}")
        ok("拿到的是补发结果", got == "reply-9", f"got={got}")
    finally:
        (
            SETTINGS.hedge_enabled,
            SETTINGS.hedge_min_samples,
            SETTINGS.hedge_min_seconds,
            SETTINGS.hedge_cap_seconds,
            SETTINGS.hedge_p50_factor,
            SETTINGS.hedge_max_rate,
        ) = old


# ---- 3) 对冲有额度上限：样本不足时不对冲 ----


def test_hedge_needs_samples() -> None:
    client = FakeClient([2.0], default_delay=0.02)
    install(client)
    old = (SETTINGS.hedge_enabled, SETTINGS.hedge_min_samples, SETTINGS.hedge_min_seconds)
    SETTINGS.hedge_enabled = True
    SETTINGS.hedge_min_samples = 8
    SETTINGS.hedge_min_seconds = 0.05
    try:
        session = llm.Session("k", "m", concurrency=4, cache=False)
        asyncio.run(session.chat([{"role": "user", "content": "x"}], purpose="t", salt="x"))
        check("样本不足不对冲", session.meter.snapshot()["hedges"], 0)
    finally:
        (SETTINGS.hedge_enabled, SETTINGS.hedge_min_samples, SETTINGS.hedge_min_seconds) = old


# ---- 4) 缓存命中不计 API 时间 ----


def test_cache_hit_is_free() -> None:
    client = FakeClient([], default_delay=0.02)
    install(client)
    with tempfile.TemporaryDirectory() as tmp:
        old_dir = SETTINGS.data_dir
        SETTINGS.data_dir = Path(tmp)
        try:
            session = llm.Session("k", "m", concurrency=2, cache=True)
            msgs = [{"role": "user", "content": "same"}]
            a = asyncio.run(session.chat(msgs, purpose="t", salt="k"))
            b = asyncio.run(session.chat(msgs, purpose="t", salt="k"))
            check("两次同答", a, b)
            snap = session.meter.snapshot()
            check("只发一次 API", snap["api_calls"], 1)
            check("命中一次缓存", snap["cache_hits"], 1)
            check("HTTP 只被调一次", client.calls, 1)
        finally:
            SETTINGS.data_dir = old_dir


def main() -> int:
    test_queue_vs_api()
    test_hedge_fires()
    test_hedge_needs_samples()
    test_cache_hit_is_free()
    if FAILS:
        print("FAIL", len(FAILS))
        for f in FAILS:
            print(" -", f)
        return 1
    print("OK llm perf/hedge/metering")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
