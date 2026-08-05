"""名人堂（Hall of Fame）基因组拉取 —— `yiagent hof pull {gene_hash}`。

数据流：GET {base_url}/api/hof/genome/{gene_hash} → 校验（返回 gene_hash
与请求一致、含完整 bank）→ 落盘 ~/.yiagent/hof/genome_{gene_hash}.json
→ `yiagent improve --apply <path>` 装回本地（payload 自带 bank，可直接消费）。

服务地址解析顺序：--url 参数 > YIAGENT_HOF_URL 环境变量 > config.yaml
的 hof.url；都未配置时明确报错（拉取是显式动作，不像上报有 localhost 默认）。
HTTP 风格对齐 factory/server/hof_ship.py：urllib 单次请求、可控超时、
不重试（失败直接报错由用户重发，避免重试风暴）。
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from yiagent.home import ensure_home, get_home

DEFAULT_TIMEOUT = 10


class HofPullError(Exception):
    """拉取失败（网络 / 404 / 校验不通过），message 面向用户可读。"""


def resolve_base_url(explicit: str | None = None, cfg: dict[str, Any] | None = None) -> str:
    """解析 hof 服务地址：参数 > YIAGENT_HOF_URL > config hof.url；未配置抛错。"""
    raw = (explicit or "").strip() or (os.environ.get("YIAGENT_HOF_URL") or "").strip()
    if not raw and isinstance(cfg, dict):
        hof = cfg.get("hof")
        if isinstance(hof, dict):
            raw = str(hof.get("url") or "").strip()
    if not raw:
        raise HofPullError(
            "未配置名人堂服务地址：请设 YIAGENT_HOF_URL 环境变量，"
            "或 `yiagent config set hof.url <url>`，或加 --url 参数"
        )
    return raw.rstrip("/")


def _get_json(url: str, timeout: float) -> dict[str, Any]:
    """GET JSON，单次请求不重试；HTTP 错误映射为可读 HofPullError。"""
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise HofPullError(f"基因组不存在（404）: {url}") from e
        raise HofPullError(f"hof 服务返回 HTTP {e.code}: {url}") from e
    except urllib.error.URLError as e:
        raise HofPullError(f"无法连接 hof 服务: {e.reason}") from e
    except TimeoutError as e:
        raise HofPullError(f"hof 服务响应超时（>{timeout}s）") from e
    try:
        data = json.loads(raw)
    except ValueError as e:
        raise HofPullError("hof 服务返回了非 JSON 响应") from e
    if not isinstance(data, dict):
        raise HofPullError("hof 服务返回的 JSON 不是对象")
    return data


def validate_genome(payload: dict[str, Any], gene_hash: str) -> None:
    """完整性校验：gene_hash 一致 + bank 含 alleles/variants（--apply 可消费）。"""
    got = str(payload.get("gene_hash") or "").strip()
    if not got:
        raise HofPullError("响应缺少 gene_hash 字段，数据不完整")
    if got != gene_hash:
        raise HofPullError(f"gene_hash 不匹配：请求 {gene_hash}，收到 {got}")
    bank = payload.get("bank")
    if not isinstance(bank, dict) or not bank.get("alleles") or not bank.get("variants"):
        raise HofPullError("响应缺少完整 bank（alleles/variants），数据不完整")


def _safe_name(gene_hash: str) -> str:
    """gene_hash 转文件名安全串（服务端上限 128 字符，可能含非常规字符）。"""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", gene_hash)[:128] or "unknown"


def save_genome(payload: dict[str, Any], home: Path | None = None) -> Path:
    """落盘到 ~/.yiagent/hof/genome_{gene_hash}.json（已存在则覆盖，幂等）。"""
    root = ensure_home(home) / "hof"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"genome_{_safe_name(str(payload['gene_hash']))}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def pull_genome(
    gene_hash: str,
    *,
    base_url: str | None = None,
    cfg: dict[str, Any] | None = None,
    home: Path | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Path:
    """下载 → 校验 → 落盘，返回落盘路径。失败抛 HofPullError。"""
    gene_hash = (gene_hash or "").strip()
    if not gene_hash:
        raise HofPullError("缺少 gene_hash 参数")
    url = resolve_base_url(base_url, cfg)
    payload = _get_json(f"{url}/api/hof/genome/{gene_hash}", timeout)
    validate_genome(payload, gene_hash)
    return save_genome(payload, home or get_home())
