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


def console_can_show_chinese() -> bool:
    """这个终端能否如实显示中文 —— 不能就别用中文报状态。

    这条不是排版讲究，是**正确性**问题：实测「心跳 4.5 分钟前」被渲染成
    `心�?4.5 分钟前`，我把糊掉的那个字读成了数字，于是把 4.5 分钟误判成 14.5 分钟，
    凭空怀疑守护漏了一个探针周期。同一个坑之前更贵 —— `Get-Process` 的空输出
    被读成"进程已死"，于是又起了一个守护，后来发现三个旧守护一直活着，
    差点四发同一个复核。**糊掉的输出会被当成关于系统状态的事实**。

    但要如实说清这个自动检测的**局限**（否则它自己就是一个虚假的保证）：
    它只能发现「Python 这一端就编码不了中文」。而真正咬人的那次不是这种 ——
    Python 直接写终端时中文是好的，是**管道下游的 PowerShell**（`| Select-Object`）
    重新编码时弄糊的，那时 `sys.stdout.encoding` 完全正常，本函数返回 True。

    所以操作纪律优先于自动检测：**任何要过 PowerShell 管道的调用都显式加 `--ascii`**。
    自动检测只兜住"控制台本身是 GBK/cp437"那一类。
    """
    enc = getattr(sys.stdout, "encoding", None) or ""
    try:
        "守护心跳".encode(enc)
        return True
    except (LookupError, UnicodeEncodeError, TypeError):
        return False


def report_ascii(row: dict, age: float, limit: float, state: str) -> int:
    """纯 ASCII 状态块：宁可难看，也不能被误读。"""
    alive = age <= limit
    terminal = state in ("finished", "aborted_quota", "aborted_error", "pilot_failed")
    verdict = ("FINISHED-OK" if state == "finished"
               else f"TERMINAL-{state.upper()}" if terminal
               else "ALIVE" if alive else "DEAD")
    print(f"verdict    : {verdict}")
    print(f"state      : {state}   pid: {row.get('pid')}")
    print(f"last_beat  : {row.get('iso')}   age_min: {age / 60:.1f}"
          f"   dead_if_over_min: {limit / 60:.1f}")
    print(f"started    : {row.get('started_iso')}")
    for k in ("probes", "waited_min", "seat", "run_id", "reps", "note"):
        if row.get(k) is not None:
            print(f"{k:<11}: {row[k]}")
    if verdict == "DEAD":
        print("action     : restart -> python tools/queue_decisive.py --probe-every 600")
    return 0 if verdict in ("ALIVE", "FINISHED-OK") else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="检查守护心跳")
    ap.add_argument("--every", type=int, default=600, help="守护的探针周期（秒）")
    ap.add_argument("--quiet", action="store_true", help="只在异常时输出")
    ap.add_argument("--ascii", action="store_true",
                    help="强制纯 ASCII 输出（中文会被终端编码吃掉时用；不给也会自动检测）")
    args = ap.parse_args()

    use_ascii = args.ascii or not console_can_show_chinese()

    row = heartbeat.read()
    if not row and use_ascii:
        print("verdict    : NEVER-RAN")
        print(f"detail     : no heartbeat file at {heartbeat.BEAT_PATH}")
        print("action     : treat as 'nobody is working'; start the watcher")
        return 1
    if row and use_ascii:
        return report_ascii(row, heartbeat.age_seconds() or 0.0,
                            args.every * 2.5, str(row.get("state") or ""))
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
