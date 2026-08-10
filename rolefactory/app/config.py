from __future__ import annotations

import os
from pathlib import Path


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


class Settings:
    base_url: str = os.environ.get("RF_BASE_URL", "https://api.kimi.com/coding/v1").rstrip("/")
    model: str = os.environ.get("RF_MODEL", "k3")
    key_file: str = os.environ.get("RF_KEY_FILE", "/run/secrets/kimi.key")
    key_env: str = os.environ.get("RF_API_KEY", "")

    data_dir: Path = Path(os.environ.get("RF_DATA_DIR", "/data"))
    bench_index: Path = Path(os.environ.get("RF_BENCH_INDEX", "/bench/benchmark_index.json"))

    # 并发与鲁棒性
    # 32 是实测甜点：/api/perf/probe 在 32 并发达 2.0 rps、重试 2；到 40 吞吐不再涨而重试跳到 34
    concurrency: int = _int("RF_CONCURRENCY", 32)
    max_connections: int = _int("RF_MAX_CONNECTIONS", 96)
    timeout: float = _float("RF_TIMEOUT", 240.0)
    max_retries: int = _int("RF_MAX_RETRIES", 4)

    # 长尾对冲：每代评测是 barrier，最慢的一条决定这代结束时间。
    # 单条超过 hedge_after 秒仍未回，就并发补发一份，取先到的那份。
    # 默认关：run 20260810-181341-bbaec2 实测补发 6 次、先到 0 次 —— 这里的长尾由生成长度决定，
    # 不是排队或丢包，补发只多花 token。机制与计量保留，可用 RF_HEDGE=1 打开再测别的供应商。
    hedge_enabled: bool = os.environ.get("RF_HEDGE", "0") not in ("0", "false", "False")
    hedge_min_seconds: float = _float("RF_HEDGE_MIN_SECONDS", 60.0)
    hedge_cap_seconds: float = _float("RF_HEDGE_CAP_SECONDS", 180.0)
    hedge_p50_factor: float = _float("RF_HEDGE_P50_FACTOR", 2.0)
    hedge_max_rate: float = _float("RF_HEDGE_MAX_RATE", 0.15)
    hedge_min_samples: int = _int("RF_HEDGE_MIN_SAMPLES", 8)
    cache_enabled: bool = os.environ.get("RF_CACHE", "1") not in ("0", "false", "False")
    # k3 等推理模型的 max_tokens 含推理开销：给太小会返回空 content，触发重试风暴
    min_max_tokens: int = _int("RF_MIN_MAX_TOKENS", 512)
    # k3 等模型只接受 temperature=1：默认不传温度参数，避免 400
    drop_temperature: bool = os.environ.get("RF_DROP_TEMPERATURE", "1") not in ("0", "false", "False")

    # 预算护栏
    default_budget_tokens: int = _int("RF_BUDGET_TOKENS", 1_500_000)
    default_budget_seconds: float = _float("RF_BUDGET_SECONDS", 3600.0)

    allow_origins: list[str] = [
        o.strip()
        for o in os.environ.get(
            "RF_ALLOW_ORIGINS",
            "http://127.0.0.1:8188,http://localhost:8188,http://127.0.0.1:8790,http://localhost:8790",
        ).split(",")
        if o.strip()
    ]

    def api_key(self) -> str:
        if self.key_env.strip():
            return self.key_env.strip()
        p = Path(self.key_file)
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
        return ""

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def runs_dir(self) -> Path:
        return self.data_dir / "runs"


SETTINGS = Settings()
