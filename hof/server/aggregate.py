"""名人堂聚合纯函数：同 gene_hash 多次上报的加权合并 + 贝塔收缩防刷。

对应规划文档第四节"聚合"与第五节"防刷"：
- 加权合并：同一基因组的多次鉴定按样本量 n 加权合并 mean/sdv；
- 贝塔收缩：shrunk = (n*mean + m*prior) / (n + m)，n 小的向 prior 收缩，
  防止单次高方差（运气好的小样本）刷榜。
"""

from __future__ import annotations

import math
from typing import Iterable

# 默认收缩强度与先验分（社区自报分的保守锚点）
DEFAULT_M = 5.0
DEFAULT_PRIOR = 75.0


def merge_weighted_mean_sdv(records: Iterable[tuple[float, float, int]]) -> tuple[float, float, int]:
    """按 n 加权合并多组 (mean, sdv, n)。

    方差合并用并行方差公式：E[x^2] = sdv^2 + mean^2。
    返回 (merged_mean, merged_sdv, total_n)；无有效记录时返回 (0, 0, 0)。
    """
    total_n = 0
    sum_mean = 0.0
    sum_sq = 0.0
    for mean, sdv, n in records:
        if not n or n <= 0:
            continue
        total_n += int(n)
        sum_mean += n * float(mean)
        sum_sq += n * (float(sdv) ** 2 + float(mean) ** 2)
    if total_n <= 0:
        return 0.0, 0.0, 0
    mean = sum_mean / total_n
    var = max(sum_sq / total_n - mean * mean, 0.0)
    return mean, math.sqrt(var), total_n


def beta_shrink(mean: float, n: int, m: float = DEFAULT_M, prior: float = DEFAULT_PRIOR) -> float:
    """贝塔收缩：样本量越小越向 prior 收缩。m 为虚拟先验样本量。"""
    if n < 0:
        n = 0
    return (n * float(mean) + m * float(prior)) / (n + m)


def merge_dim_means(records: Iterable[tuple[dict, int]]) -> dict[str, float]:
    """按 n 加权合并多组 dim_means（各记录的维度集合可不同，按各自权重归一）。"""
    acc: dict[str, float] = {}
    weights: dict[str, float] = {}
    for dims, n in records:
        if not isinstance(dims, dict) or not n or n <= 0:
            continue
        for dim, val in dims.items():
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            acc[dim] = acc.get(dim, 0.0) + v * n
            weights[dim] = weights.get(dim, 0.0) + n
    return {dim: acc[dim] / weights[dim] for dim in acc if weights.get(dim)}
