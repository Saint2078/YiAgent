#!/usr/bin/env python3
"""用当前打分口径重算历史实跑，看结论会不会变 —— 纯离线，不花额度。

为什么能这么做：客观打分是**确定性**的（程序化断言），而每条回答的原文都存在
`results.jsonl` 里、题面断言存在 `state.json` 里。所以换了口径之后，不必重跑 LLM
就能知道「如果当初用新尺子量，冠军还是这个冠军吗、holdout 分差还是这个方向吗」。

这件事必须做，因为 `must_not_include` 的旧口径把「引用错误说法去反驳」也扣光了
（`tools/audit_checks.py`：402 条扣光里 32% 属于此类，折算约 2.0 分/条评测），
而进化要检出的分差只有 1–8 分 —— **同一量级的偏差足以改变结论**。

**不改原报告**：原始记录不可变（审计要求）。结果写 `rescore.json`，
并在标准输出给出「结论是否翻转」的对照。

用法：
    python tools/rescore.py                 # 全部有明细的 run
    python tools/rescore.py <run_id> ...
    python tools/rescore.py --write         # 额外落盘 rescore.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RUNS = ROOT / "data" / "runs"

from app import objective  # noqa: E402
from app.objective import score_answer  # noqa: E402


def _checks_by_case(run_id: str, *, raw: bool = False) -> dict[str, list[dict[str, Any]]]:
    """题目断言。默认过一遍 `normalize_checks`，与出题时的实跑路径一致。

    这一步不是可选的润色：现在的 normalize_checks 会**删掉泄露答案的同义词**并
    归一化 numeric 权重占比（PERF.md §13–14）。落盘题库是旧口径生成的，不过这一步
    就等于拿旧尺子重算，问不出「新尺子下结论会不会变」。
    """
    p = RUNS / run_id / "state.json"
    if not p.is_file():
        return {}
    state = json.loads(p.read_text(encoding="utf-8"))
    out: dict[str, list[dict[str, Any]]] = {}
    for c in state.get("cases") or []:
        checks = c.get("checks") or []
        if not raw:
            checks = objective.normalize_checks([dict(x) for x in checks])
        out[c["id"]] = checks
    return out


def _state(run_id: str) -> dict[str, Any]:
    p = RUNS / run_id / "state.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def rescore_run(run_id: str) -> dict[str, Any] | None:
    rp = RUNS / run_id / "results.jsonl"
    if not rp.is_file():
        return None
    checks = _checks_by_case(run_id)
    state = _state(run_id)
    holdout = set(state.get("holdout_ids") or [])

    rows = [json.loads(x) for x in rp.read_text(encoding="utf-8").splitlines() if x.strip()]
    # (臂, 题) → 新旧分数列表；只处理客观题（judge 模式没法离线重算）
    old_s: dict[tuple[str, str], list[float]] = defaultdict(list)
    new_s: dict[tuple[str, str], list[float]] = defaultdict(list)
    changed = 0
    for r in rows:
        if str(r.get("mode")) != "objective":
            continue
        case_id, arm = str(r.get("case")), str(r.get("variant"))
        spec = checks.get(case_id)
        if not spec:
            continue
        got = score_answer(str(r.get("reply") or ""), spec)
        if got.get("total") is None:
            continue
        old = float(r.get("score") or 0)
        new = float(got["total"])
        old_s[(arm, case_id)].append(old)
        new_s[(arm, case_id)].append(new)
        if abs(new - old) > 0.005:
            changed += 1

    if not new_s:
        return {"run_id": run_id, "note": "无可离线重算的客观题评测"}

    def arm_mean(store, arm: str, cases: set[str] | None = None) -> float | None:
        vals = [
            statistics.fmean(v)
            for (a, c), v in store.items()
            if a == arm and (cases is None or c in cases)
        ]
        return round(statistics.fmean(vals), 2) if vals else None

    arms = sorted({a for a, _ in new_s})
    train_cases = {c for _, c in new_s} - holdout
    champ = state.get("champion") or {}
    # 冠军臂在明细里叫 `variant`，值等于 state.champion.id（形如 g1_e90baf41b636）
    champ_id = str(champ.get("id") or champ.get("sig") or "")

    per_arm = []
    for a in arms:
        per_arm.append(
            {
                "arm": a,
                "old_train": arm_mean(old_s, a, train_cases),
                "new_train": arm_mean(new_s, a, train_cases),
                "old_holdout": arm_mean(old_s, a, holdout) if holdout else None,
                "new_holdout": arm_mean(new_s, a, holdout) if holdout else None,
            }
        )

    def rank(key: str) -> list[str]:
        vals = [(x["arm"], x[key]) for x in per_arm if x[key] is not None]
        return [a for a, _ in sorted(vals, key=lambda kv: -kv[1])]

    old_rank, new_rank = rank("old_train"), rank("new_train")
    base = next((x for x in per_arm if x["arm"] == "baseline"), None)
    champ_row = next((x for x in per_arm if x["arm"] == champ_id), None)

    def delta(x: dict[str, Any] | None, y: dict[str, Any] | None, key: str) -> float | None:
        if not x or not y or x[key] is None or y[key] is None:
            return None
        return round(x[key] - y[key], 2)

    return {
        "run_id": run_id,
        "role": state.get("role"),
        "evaluations_rescored": sum(len(v) for v in new_s.values()),
        "score_changed": changed,
        "champion_arm": champ_id or None,
        "arms": per_arm,
        "old_top": old_rank[0] if old_rank else None,
        "new_top": new_rank[0] if new_rank else None,
        "champion_still_top": (bool(new_rank) and new_rank[0] == champ_id) if champ_id else None,
        "old_holdout_delta": delta(champ_row, base, "old_holdout"),
        "new_holdout_delta": delta(champ_row, base, "new_holdout"),
        "old_train_delta": delta(champ_row, base, "old_train"),
        "new_train_delta": delta(champ_row, base, "new_train"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="用当前打分口径重算历史实跑（离线）")
    ap.add_argument("runs", nargs="*")
    ap.add_argument("--write", action="store_true", help="把结果写进 run 目录 rescore.json")
    args = ap.parse_args()

    ids = args.runs or sorted(d.name for d in RUNS.iterdir() if (d / "results.jsonl").is_file())
    flips: list[str] = []
    sign_flips: list[str] = []
    print("重打分对照（旧口径 → 新口径）\n")
    for rid in ids:
        d = rescore_run(rid)
        if d is None or d.get("note"):
            print(f"{rid}  {(d or {}).get('note', '无明细')}")
            continue
        print(
            f"{rid}  {d['role']}  重算 {d['evaluations_rescored']} 条，"
            f"其中 {d['score_changed']} 条分数变了"
        )
        print(
            f"    train Δ（冠军−基线）  {d['old_train_delta']} → {d['new_train_delta']}"
            f"    holdout Δ  {d['old_holdout_delta']} → {d['new_holdout_delta']}"
        )
        if d["champion_still_top"] is False:
            flips.append(f"{rid}（{d['role']}）：新口径下最优是 {d['new_top']}，不是当初的冠军")
            print(f"    ** 冠军换人：{d['old_top']} → {d['new_top']}")
        o, n = d["old_holdout_delta"], d["new_holdout_delta"]
        if o is not None and n is not None and (o > 0) != (n > 0):
            sign_flips.append(f"{rid}（{d['role']}）：holdout Δ {o:+} → {n:+}")
            print("    ** holdout 分差符号翻转")
        if args.write:
            (RUNS / rid / "rescore.json").write_text(
                json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    print("\n结论：")
    print(f"  · 冠军选择被改变的 run：{len(flips)}")
    for f in flips:
        print(f"      {f}")
    print(f"  · holdout 分差符号翻转的 run：{len(sign_flips)}")
    for f in sign_flips:
        print(f"      {f}")
    print(
        "\n注：这是**同一批回答**在两把尺子下的对照，不是新实跑。"
        "\n它能回答「口径偏差有没有改变结论」，但不能替代按新口径重跑一次进化 ——"
        "\n当初的搜索路径是在旧尺子下走出来的，换尺子后更优的变体可能根本没被生成。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
