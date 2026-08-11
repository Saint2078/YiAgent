#!/usr/bin/env python3
"""守护进程的心跳：让「它还活着吗」变成一个**可以回答**的问题。

为什么需要这个：08:0x 那次守护静默死了 —— 进程不在了，日志停在"开始等"那一行，
错误文件 0 字节。而"守护挂了"恰好是最不该静默的一件事：无人值守的 8 小时里
额度恢复时没人干活，人回来看到的是"还在等额度"，与"守护早死了"**长得一模一样**。

只靠看进程表不行（实测在这台机器上 `Get-Process` 查受管作业查不到，
容易把活的判成死的）。所以让守护自己每轮写一行时间戳，
「活着」由**文件新鲜度**判定，与进程表无关。

用法（库）：
    from heartbeat import beat
    beat("waiting_quota", probes=n, waited_min=w)

用法（检查）：python tools/watch_health.py
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BEAT_PATH = HERE.parent / "data" / "watch_heartbeat.json"


def beat(state: str, **extra: Any) -> None:
    """写一次心跳。**绝不因为写失败而拖垮守护** —— 它只是仪表，不是任务。"""
    try:
        BEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
        prev: dict[str, Any] = {}
        if BEAT_PATH.is_file():
            try:
                prev = json.loads(BEAT_PATH.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                prev = {}
        row = {
            "ts": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pid": os.getpid(),
            "state": state,
            # 起始时间保留下来，才能回答"它连续活了多久"
            "started_iso": prev.get("started_iso") or time.strftime("%Y-%m-%d %H:%M:%S"),
            "started_ts": prev.get("started_ts") or time.time(),
            **extra,
        }
        tmp = BEAT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(BEAT_PATH)  # 原子替换：别让检查器读到半个文件
        refresh_lock(state)
    except Exception:  # noqa: BLE001
        pass


LOCK_PATH = HERE.parent / "data" / "watch.lock"


def force_utf8_output() -> None:
    """把本进程的 stdout/stderr 钉成 UTF-8，**并且永不因编码抛异常**。

    实测（`sys.executable -c` 走管道）：管道上的 stdout 编码是 **gbk**，
    errors=surrogateescape。这带来两个各自独立的坑：

    1. **崩**：`⚠`（U+26A0）在 gbk 里编不出来 → `UnicodeEncodeError`。
       真崩过一次，而且崩在门槛四条检查都跑完之后 ——
       「这次 run 是中断的、哪些相位没验到」那段话没打出来，
       进程带异常退出，看起来像抢救逻辑自己失败了。**仪表把任务弄死了。**
    2. **糊**：中文能进 gbk，但读的人按 UTF-8 解 → 整段变 `?`。
       这正是我把「心跳 4.5 分钟前」读成 14.5 分钟的那个坑的同源版本。

    只设 errors="replace" 只治第 1 条，第 2 条照旧。所以**连编码一起钉成 UTF-8**：
    符号不再崩，中文按 UTF-8 出去，日志文件与 `chcp 65001` 的终端都能如实读。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def pid_alive(pid: int) -> bool | None:
    """那个 PID 还在吗。**True/False/None(判不了)** —— 判不了必须能表达出来。

    为什么不能只看时间戳：锁被一次**测试运行**刷成了"6 分钟前、waiting_quota"，
    而真实守护早已退出。锁的失效期是 1 小时，于是这把孤儿锁会在
    **下一个额度窗口整段时间里**拦住合法守护 —— 额度回来了却没有人干活，
    正是心跳机制当初要消灭的那种失效。

    方向上刻意不对称：只有**确证已死**才返回 False。
    误判"死"会放进第二个守护（正是锁要防的事），比误判"活"贵得多 ——
    后者最多让人手动清一次锁。
    """
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            k32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            ERROR_ACCESS_DENIED = 5
            ERROR_INVALID_PARAMETER = 87

            h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not h:
                err = ctypes.get_last_error() or k32.GetLastError()
                if err == ERROR_INVALID_PARAMETER:
                    return False  # 没有这个 PID
                if err == ERROR_ACCESS_DENIED:
                    return True   # 存在但没权限查 → 当作活着
                return None
            try:
                code = ctypes.c_ulong()
                if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
                    return None
                return code.value == STILL_ACTIVE
            finally:
                k32.CloseHandle(h)
        except Exception:  # noqa: BLE001
            return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:  # noqa: BLE001
        return None


def acquire_singleton(*, stale_after: float = 3600.0) -> tuple[bool, str]:
    """确保**只有一个守护在跑**。返回 (拿到锁, 说明)。

    这条护栏是被一次真实事故逼出来的：我用 `Get-Process` 查旧守护，输出是空的，
    就判它死了 —— 但它其实活着（空输出是终端编码把结果吞了）。
    于是我又起了第二个，**两个守护同时在等同一份额度**。

    额度一恢复，两个会同时对同一个 run 发 reholdout：
    逐条明细走 `append_jsonl`，两批 reps 追加进同一个文件，
    方差分解会把它当成一批同质数据 —— 正是 `archive_prev_detail` 专门要防的那种污染，
    而且**不报错**。所以宁可第二个实例拒绝启动。

    锁用 pid + 时间戳而不是文件存在性：进程被强杀时锁不会自己消失，
    只看"文件在不在"会导致永久锁死。超过 `stale_after` 没更新的锁按失效处理。
    """
    now = time.time()
    try:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        if LOCK_PATH.is_file():
            try:
                old = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                old = {}
            age = now - float(old.get("ts") or 0)
            old_pid = int(old.get("pid") or 0)
            # 时间戳新鲜**不代表持锁的进程还活着**：孤儿锁真出现过一次
            # （一次测试运行把锁刷成了"6 分钟前 / waiting_quota"，而守护早退了）。
            # 只在**确证已死**时接管；判不了就按活着处理，宁可让人手动清一次锁。
            alive = pid_alive(old_pid) if old_pid and old_pid != os.getpid() else None
            if alive is False:
                pass  # 持锁进程确证已死 → 落到下面接管
            elif age < stale_after and old_pid != os.getpid():
                return False, (
                    f"已有守护在跑（PID {old_pid}，锁 {age / 60:.1f} 分钟前刷新，"
                    f"状态 {old.get('state')}）。本实例退出，避免两个守护抢同一份额度 —— "
                    "两个同时发 reholdout 会把两批 reps 追加进同一个明细文件且不报错。"
                )
        LOCK_PATH.write_text(
            json.dumps({"pid": os.getpid(), "ts": now,
                        "iso": time.strftime("%Y-%m-%d %H:%M:%S"), "state": "starting"},
                       ensure_ascii=False),
            encoding="utf-8",
        )
        return True, f"取得守护锁（PID {os.getpid()}）"
    except Exception as exc:  # noqa: BLE001
        # 锁写不了也别拦住任务；但要说清楚护栏没生效
        return True, f"⚠ 守护锁不可用（{type(exc).__name__}），未启用单例保护"


def refresh_lock(state: str) -> None:
    """心跳时顺手刷锁，让"陈旧锁"判定有依据。"""
    try:
        LOCK_PATH.write_text(
            json.dumps({"pid": os.getpid(), "ts": time.time(),
                        "iso": time.strftime("%Y-%m-%d %H:%M:%S"), "state": state},
                       ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001
        pass


def release_lock() -> None:
    try:
        if LOCK_PATH.is_file():
            old = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            if int(old.get("pid") or 0) == os.getpid():
                LOCK_PATH.unlink()
    except Exception:  # noqa: BLE001
        pass


class keep_beating:
    """长操作期间持续心跳的上下文管理器。

    没有这个东西的话，`reholdout` 那一发 HTTP 可以跑一个多小时不返回 ——
    期间一次心跳都不写，检查器就会把**正在正常干活**的守护判成死的。
    而误报比晚发现更糟：报错两次之后人就不再信告警了。

    线程设 daemon：主流程结束时不该被仪表拖着不退出。
    """

    def __init__(self, state: str, every: int = 60, **extra: Any) -> None:
        self.state, self.every, self.extra = state, every, extra
        self._stop = threading.Event()
        self._t: threading.Thread | None = None

    def __enter__(self) -> "keep_beating":
        beat(self.state, **self.extra)

        def loop() -> None:
            n = 0
            while not self._stop.wait(self.every):
                n += 1
                beat(self.state, elapsed_min=n * self.every // 60, **self.extra)

        self._t = threading.Thread(target=loop, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._stop.set()
        if self._t:
            self._t.join(timeout=2)


def read() -> dict[str, Any] | None:
    if not BEAT_PATH.is_file():
        return None
    try:
        return json.loads(BEAT_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def age_seconds() -> float | None:
    row = read()
    if not row or not isinstance(row.get("ts"), (int, float)):
        return None
    return max(0.0, time.time() - float(row["ts"]))
