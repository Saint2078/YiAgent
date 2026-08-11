#!/usr/bin/env python3
"""守护还活着吗：按**心跳新鲜度**判定，不看进程表。

判定口径（必须写清楚，否则"没消息"会被读成"好消息"）：
  · 心跳文件不存在      → 守护**从没跑过**（或跑的是没接心跳的旧版本）
  · 心跳超过 2.5 个探针周期没更新 → **判定为已死**，说明当时在等什么
  · 心跳新鲜            → 活着，并报它已连续活了多久、等了多久

阈值取 2.5 个周期而不是 1 个：探针本身要发一次 HTTP，偶尔慢几十秒是正常的，
1 个周期会误报。2.5 个周期（默认 25 分钟）漏报最多一轮，误报接近 0 ——
这个方向的不对称是故意的：**误报会让人不再信告警**，比晚 15 分钟发现更糟。

用法：python tools/watch_health.py [--every 600] [--quiet]
退出码：0 活着 / 1 已死或从没跑过
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import heartbeat  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="检查守护心跳")
    ap.add_argument("--every", type=int, default=600, help="守护的探针周期（秒）")
    ap.add_argument("--quiet", action="store_true", help="只在异常时输出")
    args = ap.parse_args()

    row = heartbeat.read()
    if not row:
        print(f"✗ 守护**从没写过心跳**：{heartbeat.BEAT_PATH} 不存在。")
        print("  可能是守护没启动，或跑的是没接心跳的旧版本 —— 两种都要当作「没人干活」处理。")
        return 1

    age = heartbeat.age_seconds() or 0.0
    limit = args.every * 2.5
    state = str(row.get("state") or "")
    lived = time.time() - float(row.get("started_ts") or row.get("ts") or time.time())

    # 「跑完了」和「死了」都表现为心跳停止，但处置完全不同 —— 必须靠终态标记分开。
    # 没有这一条的话，队列正常结束之后检查器会喊"已死"，喊两次人就不看告警了。
    TERMINAL = {
        "finished": ("✓", "队列**已正常跑完**（心跳停止属预期）"),
        "aborted_quota": ("!", "队列**因额度中途耗尽而中止** —— 需人工重启"),
        "aborted_error": ("!", "队列**因错误中止** —— 见 note"),
        "pilot_failed": ("!", "门槛试跑**失败** —— 见 note"),
    }
    if state in TERMINAL:
        mark, desc = TERMINAL[state]
        print(f"{mark} {desc}")
        print(f"  最后心跳：{row.get('iso')}（{age / 60:.1f} 分钟前）"
              f"  启动于：{row.get('started_iso')}")
        for k in ("seat", "run_id", "reps", "probes", "waited_min", "note"):
            if row.get(k) is not None:
                print(f"  {k}: {row[k]}")
        return 0 if state == "finished" else 1

    alive = age <= limit
    if alive and args.quiet:
        return 0

    mark = "✓" if alive else "✗"
    print(f"{mark} 守护{'存活' if alive else '**已死**'}"
          f"（心跳 {age / 60:.1f} 分钟前，阈值 {limit / 60:.1f} 分钟）")
    print(f"  状态：{row.get('state')}  PID={row.get('pid')}")
    print(f"  最后心跳：{row.get('iso')}   启动于：{row.get('started_iso')}"
          f"（连续 {lived / 3600:.1f} 小时）")
    for k in ("probes", "waited_min", "seat", "run_id", "reps", "note"):
        if row.get(k) is not None:
            print(f"  {k}: {row[k]}")
    if not alive:
        print("  → 它死在上面这个状态里。额度恢复时**没有人在干活**，需要重启守护：")
        print("     python tools/queue_decisive.py --probe-every 600")
    return 0 if alive else 1


if __name__ == "__main__":
    raise SystemExit(main())
