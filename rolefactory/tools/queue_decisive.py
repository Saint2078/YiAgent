#!/usr/bin/env python3
"""等额度，然后跑**唯一一席值得花额度**的高重复复核：Evals。

选席位经过两道筛，不是只看便宜：

一、`decomp_table.py`（方差分解）：只有 Dev 与 Evals 的**题间差异 ≈ 0**，
    加重复就能把区间压到 |Δ| 以下，一道新题都不用出。其余四席的下限已高于 |Δ|。

二、`headroom.py`（天花板）：这两席的基线都贴着满分（Dev 94.9、Evals 94.8），
    平均只剩 5 分可涨、却有 95 分可跌 —— 量尺**上下不对称**，量出来的 Δ 系统性偏负。
    于是两席的处境完全不同：

    · Dev 的 Δ = **−0.87**（负）。在一把偏负的尺子上量出负数，
      分不清是"基因有害"还是"截断偏"。**判出来也不能得结论**，所以不值得花。
    · Evals 的 Δ = **+1.71**（正）。偏是往负的方向偏，却仍量出正数 ——
      这叫**保守估计**：真实效应至少这么大。判出来就是可辩护的结论。

所以只排 Evals，且把重复数从 9 抬到 15：reps=9 的半宽 1.69 对 |Δ|=1.71，
只差 0.02，属于"擦边判过"，任何漂移都会让它重新跨 0。

    Evals   reps=15 × 现有 6 题 = 180 次评测（半宽约 1.3，留出余量）

**仍然不保证赢**：+1.71 有可能就是收窄后仍跨 0。那也是结论 —— 明确的"效应小于
可测量下限"，比"判不了"有信息。

## 第二步：验证筛题门槛（`--gate-pilot`）

复核用的是**已有的题**，所以它一辈子也走不到 `probe` 相位 —— 筛题门槛
（PERF.md §18.6/§18.7）在复核里永远不会被执行。要验证它只能起一次新 run。

故队列排第二步：拿新配法（`per_dim=16 / train_per_dim=1 / headroom_ceiling=90`）
起**一次**新 run，**不采纳**（不动任何席位的落盘基因组），只回答三个问题：

1. 门槛真的扔题了吗？（还是又空转）
2. holdout 题量落在预期的 42–90 之间吗？
3. 进化评测是否如预期恒为 180 次（train 被封住）？

顺序是先复核后试跑：复核 180 次评测、可能直接产出第一个可辩护结论，
优先级高于验证一个已被 20 项单测和空跑覆盖的机制。

用法：python tools/queue_decisive.py [--probe-every 600] [--gate-pilot Evals|no]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# (席位, reps, 预计评测数)
# Dev 曾在这张表里（reps=28、336 次），后被拿掉：它的 Δ 是负的，而尺子本身偏负，
# 判出来也分不清是基因有害还是截断偏 —— 花 336 次买一个不能用的结论。
PLAN = [("Evals", 15, 180)]


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def seat_run(seat: str) -> str | None:
    p = ROOT.parent / "console" / "_workbench" / "AgentTeam" / "Develop" / seat / "genome.json"
    if not p.is_file():
        return None
    return (json.loads(p.read_text(encoding="utf-8")).get("source") or {}).get("run_id")


def gate_pilot(seat: str, probe_every: int) -> int:
    """起一次新 run 验证筛题门槛。**不采纳**，只看门槛有没有真的干活。"""
    import build_devteam as bd  # 复用同一份 RUN_PARAMS，避免参数漂移

    meta = next((m for m in bd.TEAM if m["seat"] == seat), None)
    if not meta:
        log(f"试跑：找不到席位 {seat}，跳过")
        return 0

    p = bd.RUN_PARAMS
    log(f"=== 门槛试跑（不采纳）：{seat} / {meta['factory_role']} ===")
    log(f"    配法 per_dim={p.get('per_dim')} train_per_dim={p.get('train_per_dim')} "
        f"headroom_ceiling={p.get('headroom_ceiling')}")

    # 等额度：先探一次，没额度就等（起 run 比复核贵，别在没额度时白起）
    while True:
        try:
            probe = subprocess.run(
                [sys.executable, str(HERE / "quota_probe.py")],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            if probe.returncode == 0:
                break
            log(f"    等额度…（{(probe.stdout or '').strip()[:60]}）")
        except Exception as exc:  # noqa: BLE001
            log(f"    额度探测异常 {type(exc).__name__}: {exc}")
        time.sleep(probe_every)

    try:
        rid = bd.start_run(meta["factory_role"])
        report = bd.wait_run(rid)
    except Exception as exc:  # noqa: BLE001
        log(f"试跑失败 {type(exc).__name__}: {exc}")
        return 1

    suite = report.get("suite") or {}
    dropped = suite.get("dropped_saturated") or []
    n_train, n_hold = len(suite.get("train") or []), len(suite.get("holdout") or [])
    ev = n_train * int(p.get("variants_per_gen") or 10) * int(p.get("generations") or 3)
    log(f"试跑 {rid} 完成：题 {suite.get('count')} 道｜扔 {len(dropped)} 道"
        f"｜train {n_train} / holdout {n_hold}｜进化评测约 {ev} 次")
    # 三条预期逐条对账，不合就明说（这次是验证，不是产出）
    checks = [
        ("门槛真的扔题了", len(dropped) > 0),
        ("holdout 落在 42–90", 42 <= n_hold <= 90),
        ("train 被封住（进化 ≈180 次）", ev <= 240),
    ]
    for name, ok in checks:
        log(f"    [{'ok ' if ok else 'FAIL'}] {name}")
    if dropped:
        shown = "、".join(f"{d.get('id')}({d.get('baseline')})" for d in dropped[:6])
        log(f"    被扔的题（基线分）：{shown}")
    log(f"    注意：此 run **未采纳**，不影响任何席位的落盘基因组。run_id={rid}")
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="等额度后跑高重复复核")
    ap.add_argument("--probe-every", type=int, default=600)
    ap.add_argument("--gate-pilot", default="Evals",
                    help="复核跑完后，用新配法起一次新 run 验证筛题门槛；no = 不跑")
    args = ap.parse_args()

    log(f"排队：{'、'.join(f'{s} reps={r}（{e}次）' for s, r, e in PLAN)}")
    for seat, reps, evals in PLAN:
        run_id = seat_run(seat)
        if not run_id:
            log(f"{seat}: 没有落盘基因组，跳过")
            continue
        log(f"=== {seat} run={run_id} reps={reps}（约 {evals} 次评测）===")
        rc = subprocess.run(
            [sys.executable, str(HERE / "run_reholdout.py"), run_id,
             "--reps", str(reps), "--seat", seat,
             "--wait-quota", "--probe-every", str(args.probe_every)],
            cwd=str(ROOT),
        ).returncode
        if rc == 2:
            # 额度中途又断（探针通过不代表跑得完一轮）。停在这里，别把后面那席也烧成半截。
            log(f"{seat}: 额度中途耗尽，队列中止（后面的席位没动）")
            return 2
        if rc != 0:
            log(f"{seat}: 失败 rc={rc}，队列中止")
            return rc
        log(f"{seat}: 完成并已传导到下游")
        # 复核换了数，处方表跟着变 —— 打一次给日志留痕
        subprocess.run([sys.executable, str(HERE / "decomp_table.py")], cwd=str(ROOT))

    if str(args.gate_pilot).lower() not in ("no", "none", "0", ""):
        gate_pilot(args.gate_pilot, args.probe_every)
    log("=== 队列结束 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
