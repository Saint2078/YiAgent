#!/usr/bin/env python3
"""把历史题库拿新口径重校一遍，量出新加的硬校验会否掉多少题。

为什么需要：出题自校不过会**回喂重出，最多 3 次，之后静默丢题**（roles.py `one()`
吞掉异常返回 None）。所以收紧校验的代价有两笔，且都不写在任何日志里：

    1. 额度：每道被否的题多烧最多 2 次重出
    2. 题量：连败 3 次的维度直接少题，而 holdout 题量正是泛化判定的瓶颈

历史题库是**旧口径下生成**的，拿它当「模型自然产出的分布」来估这两笔代价，
比等额度恢复后实跑一轮再看要便宜得多（前者 0 额度）。

注意口径：这是**悲观上界**。实跑时新的出题提示词里已写明数值占比 55–80%
（roles.py `prompt_objective_suite`），模型会照着出；历史题库没见过这条要求。

用法：
    python tools/audit_cases.py                 # 汇总所有 run
    python tools/audit_cases.py --by-run        # 逐 run 明细
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from app import objective  # noqa: E402

RUNS = ROOT / "data" / "runs"


def load_cases(run_dir: Path) -> list[dict]:
    """只取客观题。主观打分那轮的题没有 checks，拿它算否决率会凭空多出一堆假阳性。"""
    st = run_dir / "state.json"
    if not st.is_file():
        return []
    try:
        state = json.loads(st.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    if str((state.get("scoring") or {}).get("mode") or "") == "judge":
        return []
    return [
        c for c in (state.get("cases") or [])
        if isinstance(c, dict) and (c.get("checks") or [])
    ]


def numeric_share(case: dict) -> float:
    checks = case.get("checks") or []
    total = sum(float(c.get("weight") or 0) for c in checks)
    if total <= 0:
        return 0.0
    num = sum(float(c.get("weight") or 0) for c in checks if c.get("type") == "numeric")
    return num / total


def main() -> int:
    ap = argparse.ArgumentParser(description="历史题库对当前校验口径的通过率")
    ap.add_argument("--by-run", action="store_true", help="逐 run 打印")
    ap.add_argument(
        "--raw", action="store_true",
        help="不过 normalize_checks 直接校验（看题库**原始**权重配比，而非实跑路径）",
    )
    args = ap.parse_args()

    rows: list[tuple[str, int, int, list[str], float]] = []
    for run_dir in sorted(p for p in RUNS.iterdir() if p.is_dir()):
        cases = load_cases(run_dir)
        if not cases:
            continue
        fails, reasons, shares = 0, [], []
        for c in cases:
            # 实跑路径是 normalize_checks → verify_case，审计要跟它一致，
            # 否则量的是「题库原样」而不是「这题能不能活下来」
            if not args.raw:
                c = {**c, "checks": objective.normalize_checks(
                    [dict(x) for x in (c.get("checks") or [])]
                )}
            shares.append(numeric_share(c))
            ok, problems = objective.verify_case(c)
            if not ok:
                fails += 1
                reasons.extend(problems)
        rows.append(
            (run_dir.name, len(cases), fails, reasons,
             sum(shares) / len(shares) if shares else 0.0)
        )

    if not rows:
        print("没有可审的题库（data/runs/*/state.json 都不含 cases）")
        return 1

    tot_cases = sum(r[1] for r in rows)
    tot_fail = sum(r[2] for r in rows)
    all_reasons = [x for r in rows for x in r[3]]

    if args.by_run:
        print(f"{'run':26} {'题数':>4} {'否决':>4} {'否决率':>7} {'均数值占比':>10}")
        for name, n, f, _, share in rows:
            print(f"{name:26} {n:>4} {f:>4} {f / n:>6.0%} {share:>10.0%}")
        print()

    print(f"合计：{tot_cases} 道题，新口径否决 {tot_fail} 道（{tot_fail / tot_cases:.0%}）")
    share_all = sum(r[4] * r[1] for r in rows) / tot_cases
    print(
        f"平均数值占比：{share_all:.0%}"
        f"（归一目标 {objective.NUMERIC_SHARE_TARGET:.0%}、兜底下限 40%）"
    )

    if all_reasons:
        from collections import Counter
        print("\n否决原因（按首词归并）：")
        for reason, cnt in Counter(r.split("：")[0].split("(")[0][:34] for r in all_reasons).most_common(8):
            print(f"  {cnt:>4}× {reason}")

    # 代价换算：被否的题最多再出 2 次；每维连败 3 次才丢题
    print(
        f"\n估算额度代价上界：{tot_fail} 道 × 最多 2 次重出 = {tot_fail * 2} 次多余出题调用"
        f"（约占一轮出题量的 {tot_fail * 2 / tot_cases:.0%}）"
    )
    print("这是悲观上界：新提示词已写明 55–80%，实跑时模型会照着出，历史题库没见过这条要求。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
