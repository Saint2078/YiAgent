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
import os
import subprocess
import sys
import time
from typing import Any
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

sys.path.insert(0, str(HERE))
import heartbeat  # noqa: E402

# 服务端 `POST /api/run/{id}/reholdout` 把 reps 截到 8（成本护栏）。
# 排计划时就按这个上限算，否则**日志里的评测数是假的**：
# 实测按 reps=15 排、日志写「约 180 次」，服务端静默截成 8，盘上只有 96 次。
SERVER_REPS_CAP = 8

# (席位, reps, 预计评测数)
# Dev 曾在这张表里（reps=28、336 次），后被拿掉：它的 Δ 是负的，而尺子本身偏负，
# 判出来也分不清是基因有害还是截断偏 —— 花 336 次买一个不能用的结论。
#
# reps 写 8 而不是 15：**不是妥协，是因为超过上限的部分本来也没用** ——
# 方差分解显示 Evals 的"重复下限"（1.96·σ_h/√n = 2.33）已经高于 |Δ|=0.2，
# 也就是 reps 加到无穷都压不到能判出的程度，能压的只有题量。
PLAN = [("Evals", SERVER_REPS_CAP, 6 * 2 * SERVER_REPS_CAP)]


# 日志不该有能力弄死任务：管道上 stdout 编码是 gbk，一个 `⚠` 就能抛 UnicodeEncodeError。
# 实测崩过一次，且崩在门槛四条检查都跑完之后，把已经拿到的结论一起带走了。
heartbeat.force_utf8_output()


def log(msg: str) -> None:
    try:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        # reconfigure 没生效的兜底（例如 stdout 被换成了不支持 reconfigure 的对象）
        safe = msg.encode("ascii", "replace").decode("ascii")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {safe}", flush=True)


def load_report(run_id: str) -> dict[str, Any]:
    """从盘上读 report.json。

    给中断的试跑用：run 崩在 baseline 之后，`wait_run` 抛异常，但门槛与切分
    早在 probe/bank 相位就落盘了。这条路让"已经拿到的结论"不跟着异常一起丢掉。
    """
    p = ROOT / "data" / "runs" / run_id / "report.json"
    if not p.is_file():
        return {}
    try:
        out = json.loads(p.read_text(encoding="utf-8"))
        return out if isinstance(out, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


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
    n_probe = 0
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
        n_probe += 1
        heartbeat.beat("pilot_waiting_quota", seat=seat, probes=n_probe)
        time.sleep(probe_every)

    rid = None
    report: dict[str, Any] = {}
    aborted_note = ""
    try:
        # 一次完整 run 要跑很久，期间持续心跳
        with heartbeat.keep_beating("pilot_running", seat=seat):
            rid = bd.start_run(meta["factory_role"])
            report = bd.wait_run(rid)
    except Exception as exc:  # noqa: BLE001
        aborted_note = f"{type(exc).__name__}: {exc}"
        log(f"试跑中断 {aborted_note}")
        # **别就这么走了**：门槛与切分在 probe/bank 相位就已完成并落盘，
        # 而本次试跑要验的**恰恰只是它们**。后面 baseline/evolve 因额度断掉，
        # 不影响这四条检查的可判性。
        #
        # 实测被咬过：额度在 baseline 35/72 处耗尽，这里直接 return 1，
        # 于是「门槛扔了 29 道、holdout 91 道、train 封在 6 道」这个**已经拿到的结论**
        # 被一并丢掉，日志只剩一行"试跑失败"。等下一次额度再跑一遍要 10 分钟以上，
        # 而答案早就在盘上。
        report = load_report(rid) if rid else {}
        if not (report.get("suite") or {}).get("holdout"):
            log("    盘上也没有切分结果 —— 这次确实什么都没验到")
            heartbeat.beat("pilot_failed", seat=seat, note=aborted_note)
            return 1
        log(f"    但门槛与切分已落盘，下面四条检查仍然可判（数据取自 {rid}/report.json）")

    suite = report.get("suite") or {}
    dropped = suite.get("dropped_saturated") or []
    n_train, n_hold = len(suite.get("train") or []), len(suite.get("holdout") or [])
    ev = n_train * int(p.get("variants_per_gen") or 10) * int(p.get("generations") or 3)
    log(f"试跑 {rid} 完成：题 {suite.get('count')} 道｜扔 {len(dropped)} 道"
        f"｜train {n_train} / holdout {n_hold}｜进化评测约 {ev} 次")
    # 三条预期逐条对账，不合就明说（这次是验证，不是产出）
    # 预期区间跟着配法算，别写死数字（配法从 16 改到 21 之后 42–90 就已经是旧账）
    dims = 6
    per_dim = int(p.get("per_dim") or 0)
    hold_max = per_dim * dims - int(p.get("train_per_dim") or 1) * dims
    hold_min = dims * -(-per_dim // 2) - dims  # 6·⌈per_dim/2⌉ − 6
    # 55 是**务实下限**，不是"算出来的保本线"：那个反算值的 90% 区间跨三个数量级
    # （`need_n_ci.py`，PERF.md §18.11），没有分辨力。这里只保证题量不退回小样本。
    floor_cases = 55
    checks = [
        ("门槛真的扔题了", len(dropped) > 0),
        (f"holdout 落在 {hold_min}–{hold_max}", hold_min <= n_hold <= hold_max),
        ("train 被封住（进化 ≈180 次）", ev <= 240),
        (f"holdout ≥ 题量下限 {floor_cases}", n_hold >= floor_cases),
    ]
    for name, ok in checks:
        log(f"    [{'ok ' if ok else 'FAIL'}] {name}")
    if dropped:
        shown = "、".join(f"{d.get('id')}({d.get('baseline')})" for d in dropped[:6])
        log(f"    被扔的题（基线分）：{shown}")
    log(f"    注意：此 run **未采纳**，不影响任何席位的落盘基因组。run_id={rid}")
    if aborted_note:
        # 检查过了不等于试跑成功。**两件事必须分开说**，否则"四条 ok"会被读成
        # "整条流水线验通了"，而实际上 baseline 之后一步都没跑。
        log(f"    ⚠ 但这次 run 本身是**中断的**（{aborted_note}）：")
        log("      已验：出题 → 门槛筛题 → 切分（含成本封顶）")
        log("      未验：baseline / 进化 / holdout —— 这些要等额度")
        heartbeat.beat("pilot_partial", seat=seat, run_id=rid, note=aborted_note)
        return 0 if all(ok for _, ok in checks) else 1
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="等额度后跑高重复复核")
    ap.add_argument("--probe-every", type=int, default=600)
    # 试跑席位选 PM（原为 Evals）。**理由已经换过一次**，记清楚免得又拿旧理由办事：
    #  · 原理由（作废）："alloc.py 反算出 PM 是唯一另一个够得着的席位（55 道）"。
    #    `need_n_ci.py` 证明那个反算值 90% 区间跨 186×–1925×，撑不起"够得着/够不着"。
    #  · 现理由（站得住）：① Evals 的判定已由 reps=15 复核买到，不必再买第二遍；
    #    ② PM 有 reps=3 明细可供事后对照；③ 现有 5–6 道题**确定**判不出任何东西，
    #    所以"加题"这条路值得先在一席上验通 —— 至于加到 60 道够不够，跑完才知道。
    ap.add_argument("--gate-pilot", default="PM",
                    help="复核跑完后，用新配法起一次新 run 验证筛题门槛；no = 不跑")
    # 跳过复核这条路是**为了不重复烧已经买到的答案**。
    #
    # Evals 的 reps=8 复核已经跑完（Δ配对=0.20，CI95 含 0，判不了），
    # 而方差分解证明**再加重复也压不到能判出**（重复下限 2.33 > |Δ|=0.20）。
    # 所以重跑它就是花 96 次评测买同一个"判不了" —— 额度本就稀缺，不值。
    ap.add_argument("--skip-reholdout", action="store_true",
                    help="不跑 PLAN 里的复核，直接进门槛试跑（复核已完成时用）")
    args = ap.parse_args()

    # 单例保护：两个守护同时等同一份额度，恢复时会对同一个 run 各发一次 reholdout，
    # 两批 reps 追加进同一个明细文件且不报错。实测发生过一次（见日志 F39）。
    ok, why = heartbeat.acquire_singleton()
    log(why)
    if not ok:
        return 3

    plan = [] if args.skip_reholdout else PLAN
    if args.skip_reholdout:
        log("跳过复核（--skip-reholdout）：Evals 的 reps=8 复核已完成且判不了，"
            "而重复下限 2.33 > |Δ|=0.20 —— 再跑一遍是花 96 次评测买同一个答案")
    else:
        log(f"排队：{'、'.join(f'{s} reps={r}（{e}次）' for s, r, e in plan)}")
    for seat, reps, evals in plan:
        run_id = seat_run(seat)
        if not run_id:
            log(f"{seat}: 没有落盘基因组，跳过")
            continue
        log(f"=== {seat} run={run_id} reps={reps}（约 {evals} 次评测）===")
        # 告诉子进程"锁已经由父进程持有了"，否则它会看到一把新鲜锁并拒绝启动
        child_env = dict(os.environ, YIAGENT_WATCH_LOCK_HELD="1")
        rc = subprocess.run(
            [sys.executable, str(HERE / "run_reholdout.py"), run_id,
             "--reps", str(reps), "--seat", seat,
             "--wait-quota", "--probe-every", str(args.probe_every)],
            cwd=str(ROOT), env=child_env,
        ).returncode
        if rc == 2:
            # 额度中途又断（探针通过不代表跑得完一轮）。停在这里，别把后面那席也烧成半截。
            log(f"{seat}: 额度中途耗尽，队列中止（后面的席位没动）")
            heartbeat.beat("aborted_quota", seat=seat, note="额度中途耗尽，需人工重启")
            return 2
        if rc != 0:
            log(f"{seat}: 失败 rc={rc}，队列中止")
            heartbeat.beat("aborted_error", seat=seat, note=f"rc={rc}")
            return rc
        log(f"{seat}: 完成并已传导到下游")
        # 复核换了数，处方表跟着变 —— 打一次给日志留痕
        subprocess.run([sys.executable, str(HERE / "decomp_table.py")], cwd=str(ROOT))

    if str(args.gate_pilot).lower() not in ("no", "none", "0", ""):
        gate_pilot(args.gate_pilot, args.probe_every)
    log("=== 队列结束 ===")
    # 正常收尾也要留痕：否则"心跳停了"分不清是**跑完了**还是**死了**
    heartbeat.beat("finished", note="队列正常结束，无待办")
    heartbeat.release_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
