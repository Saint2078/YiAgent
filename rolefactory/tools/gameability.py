#!/usr/bin/env python3
"""尺子能被堆词蒙到多少分：造几个作弊答案去打，用真实题目量化（离线，不花额度）。

报告里一直挂着一条免责声明：「断言里的关键词匹配可被堆词部分蒙到」。那是**定性**的，
没人知道到底能蒙多少 —— 而这决定了 numeric 权重该不该再提。现在可以直接量：
题面与断言都在库里，作弊答案由程序拼，打分是确定性的。

四个对照答案（都不含任何真实推理）：

| 名字 | 构造 | 想测什么 |
|---|---|---|
| `empty` | 空字符串 | 分数地板 |
| `soup` | 把所有 `must_include` 同义词拼起来 | 纯堆词能拿多少 |
| `soup_num` | 堆词 + 把 `numeric` 的 target 直接抄进去 | 「知道答案但不讲道理」能拿多少 |
| `soup_safe` | 堆词 + 每个禁词前加否定词 | 能不能靠「都否一遍」白拿禁词分 |

`soup_num` 是上界参考：真实答题者拿不到标准答案。`soup_safe` 是**对新修的
`must_not_include` 口径做压力测试** —— 如果它拿满分，说明免扣规则被滥用了。

用法：
    python tools/gameability.py                 # 全部有题面的 run
    python tools/gameability.py <run_id> ...
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RUNS = ROOT / "data" / "runs"

from app import objective  # noqa: E402
from app.objective import score_answer  # noqa: E402


def _syns(spec: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for g in spec.get("groups") or []:
        if isinstance(g, dict):
            out.extend(str(s) for s in (g.get("any") or []) if str(s).strip())
        elif isinstance(g, (list, tuple)):
            out.extend(str(s) for s in g)
        else:
            out.append(str(g))
    return out


def fake_answers(checks: list[dict[str, Any]]) -> dict[str, str]:
    """按题面断言拼作弊答案。注意只用断言里**公开给答题者看不到**的东西是不行的，
    所以这些答案代表的是「知道评分规则的人能拿多少」，是上界而非真实水平。"""
    include, forbid, numbers = [], [], []
    for c in checks:
        t = str(c.get("type"))
        if t in ("must_include", "ask_back", "lead_with"):
            include.extend(_syns(c))
        elif t == "must_not_include":
            forbid.extend(_syns(c))
        elif t == "numeric":
            tgt = c.get("target")
            if isinstance(tgt, (int, float)):
                near = _syns(c) or [str(x) for x in (c.get("near") or [])]
                unit = str(c.get("unit") or "")
                numbers.append(f"{(near[0] + '：') if near else ''}{tgt}{unit}")

    soup = "；".join(include) or "（无要素）"
    return {
        "empty": "",
        "soup": soup,
        "soup_num": soup + "。" + "；".join(numbers),
        # 每个禁词前塞否定词：测新口径会不会被「都否一遍」白拿分
        "soup_safe": soup + "。" + "；".join(f"不能{p}" for p in forbid),
    }


def reweight(checks: list[dict[str, Any]], numeric_share: float) -> list[dict[str, Any]]:
    """按目标占比重排权重，用来回答「占比抬到 X 时堆词地板降到多少」。

    实现直接借 `objective.rebalance_numeric`（出题时也用它），避免两处各写一份缩放
    公式、答案对不上。
    """
    return objective.rebalance_numeric([dict(c) for c in checks], target=numeric_share)


def analyse(
    run_id: str, *, target_share: float | None = None, raw: bool = False
) -> dict[str, Any] | None:
    sp = RUNS / run_id / "state.json"
    if not sp.is_file():
        return None
    state = json.loads(sp.read_text(encoding="utf-8"))
    cases = [c for c in state.get("cases") or [] if c.get("checks")]
    if not cases or str((state.get("params") or {}).get("scoring_mode")) != "objective":
        return None

    per_kind: dict[str, list[float]] = {}
    shares: list[float] = []
    for case in cases:
        # 出题时 normalize_checks 会把 numeric 占比归一化，落盘的老题库没经过这一步。
        # 默认按**实跑路径**量，否则报出来的地板是历史配比下的、跟现在的尺子无关。
        checks = (
            case["checks"] if raw
            else objective.normalize_checks([dict(c) for c in case["checks"]])
        )
        total = sum(float(c.get("weight") or 0) for c in checks)
        num = sum(float(c.get("weight") or 0) for c in checks if str(c.get("type")) == "numeric")
        if total > 0:
            shares.append(num / total * 100)
        answers = fake_answers(checks)
        for name, text in answers.items():
            got = score_answer(text, checks)
            if got.get("total") is not None:
                per_kind.setdefault(name, []).append(float(got["total"]))
        if target_share:
            got = score_answer(answers["soup"], reweight(checks, target_share))
            if got.get("total") is not None:
                per_kind.setdefault("soup_reweighted", []).append(float(got["total"]))

    # 真实分数参照：无基因基线与冠军（训练题均值，取报告里的加权分）
    base = (state.get("baseline") or {}).get("weighted")
    champ = (state.get("champion") or {}).get("weighted")
    return {
        "run_id": run_id,
        "role": state.get("role"),
        "cases": len(cases),
        "fake": {k: round(statistics.fmean(v), 2) for k, v in per_kind.items()},
        "numeric_share": round(statistics.fmean(shares), 1) if shares else None,
        "baseline_weighted": base,
        "champion_weighted": champ,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="量化尺子被堆词蒙分的程度（离线）")
    ap.add_argument("runs", nargs="*")
    ap.add_argument(
        "--target-numeric",
        type=float,
        default=None,
        metavar="占比",
        help="假设出题时要求 numeric 权重占比达到该值（如 0.6），算堆词地板会降到多少",
    )
    ap.add_argument(
        "--raw", action="store_true",
        help="按题库落盘的原始权重量（不过 normalize_checks），用于对比归一化前后的地板",
    )
    args = ap.parse_args()
    ids = args.runs or sorted(d.name for d in RUNS.iterdir() if (d / "state.json").is_file())

    rows = [
        d for rid in ids
        if (d := analyse(rid, target_share=args.target_numeric, raw=args.raw))
    ]
    if not rows:
        print("没有可分析的客观题 run")
        return 2

    print("作弊答案能拿多少分（同一批真实题目，打分口径为当前口径）\n")
    print("| run | 角色 | 空答 | 纯堆词 | 堆词+抄数值 | 堆词+都否一遍 | 真实基线 | 真实冠军 |")
    print("|---|---|---|---|---|---|---|---|")
    for d in rows:
        f = d["fake"]
        print(
            f"| {d['run_id'][:15]} | {d['role']} | {f.get('empty', 0):.1f} | **{f.get('soup', 0):.1f}** |"
            f" {f.get('soup_num', 0):.1f} | {f.get('soup_safe', 0):.1f} |"
            f" {d['baseline_weighted']} | {d['champion_weighted']} |"
        )

    soup = statistics.fmean([d["fake"].get("soup", 0) for d in rows])
    soup_num = statistics.fmean([d["fake"].get("soup_num", 0) for d in rows])
    safe = statistics.fmean([d["fake"].get("soup_safe", 0) for d in rows])
    bases = [d["baseline_weighted"] for d in rows if isinstance(d["baseline_weighted"], (int, float))]
    base = statistics.fmean(bases) if bases else None

    print(f"\n均值：纯堆词 {soup:.1f} 分 · 堆词+抄数值 {soup_num:.1f} 分 · 堆词+都否一遍 {safe:.1f} 分")
    if base:
        print(f"真实无基因基线均值 {base:.1f} 分 —— 堆词答案拿到基线的 {soup / base:.0%}")
    shares = [d["numeric_share"] for d in rows if d.get("numeric_share")]
    if shares:
        print(f"当前 numeric 权重占比均值 {statistics.fmean(shares):.0f}%")
    if args.target_numeric:
        rw = [d["fake"].get("soup_reweighted") for d in rows if d["fake"].get("soup_reweighted")]
        if rw:
            new = statistics.fmean(rw)
            print(
                f"若把 numeric 占比抬到 {args.target_numeric:.0%}：堆词地板 {soup:.1f} → **{new:.1f}**"
                + (f"（占基线 {new / base:.0%}）" if base else "")
            )
    print(
        "\n怎么读：\n"
        "  · 纯堆词分数**高**说明关键词类断言给分太松，应提 numeric 权重或改断言写法；\n"
        "  · 「堆词+都否一遍」若明显高于「纯堆词」，说明新修的免扣规则被滥用了 ——\n"
        "    这是对 must_not_include 新口径的压力测试，应当**接近**纯堆词而非更高；\n"
        "  · 「堆词+抄数值」是上界参考：真实答题者拿不到 target，只有出题人有。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
