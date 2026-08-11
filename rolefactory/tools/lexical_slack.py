#!/usr/bin/env python3
"""尺子有多"死板"：`must_include` 是**精确子串**匹配，答对了但换了个说法就判 0。

起因是逐条读 Product 那道撑起全局的题（`show_case`）。基线把分母写成

    「全部自然新注册用户，含未完成引导、流失、沉默用户；不得只统计完成引导的」

语义完全正确，但那条断言要的是「全部新注册用户作为分母」这类**字面**，
于是判 **0/3**。它损失的不是能力分，是措辞分。

这件事为什么要紧：§19 量出 numeric 在 holdout 上**不区分两臂**（五席逐题打平），
也就是说 holdout 上的区分能力**全部来自 must_include 这类字面断言**。
那么"能区分的断言恰好是最脆的那种"就直接解释了「什么都判不出」——
Δ 里混了大量措辞噪声，而措辞与基因强弱无关。

本工具用**盘上已有的回答**离线重打分（0 额度），把"字面松紧"这一个旋钮单独拧：

  · 现行：某近义词整串出现在回答里才算命中
  · 放宽：某近义词的**字符二元组**有 ≥阈值 比例出现在回答里就算命中
    （中文没有空格，二元组是最省事又不离谱的近似）

只放宽 `must_include` / `lead_with`（都是"有没有覆盖到"的检查）。
**不动 `must_not_include`** —— 放宽它等于更容易判人说错话，方向相反。

一条关键的不对称（先说清楚，免得被当成"放水"）：
`gameability` 的堆词假答案是把所有近义词**原样拼起来**，它在现行匹配下就已经
拿满 `must_include`。放宽匹配**不会让它拿得更多** ——
所以这个旋钮只提高真实回答的命中率，不降低堆词地板（§13 那把刀不受影响）。

用法：python tools/lexical_slack.py [--thresh 0.8]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from app import objective  # noqa: E402

RUNS = ROOT / "data" / "runs"
SEATS = [
    ("Product", "20260809-191310-a7b2bd"), ("PM", "20260810-185143-6ea6f5"),
    ("Architect", "20260809-194427-8cfdb4"), ("Dev", "20260809-201229-aa45e1"),
    ("DevOps", "20260809-203635-e70531"), ("Evals", "20260810-181341-bbaec2"),
]
RELAXED = {"must_include", "lead_with"}
Z = 1.96


def bigrams(s: str) -> list[str]:
    s = "".join(s.split()).lower()
    return [s[i:i + 2] for i in range(len(s) - 1)] or ([s] if s else [])


def relaxed_hit(text: str, syns: list[str], thresh: float) -> bool:
    low = "".join(text.split()).lower()
    for s in syns:
        if s.lower() in text.lower():
            return True
        bg = bigrams(s)
        if not bg:
            continue
        cover = sum(1 for b in bg if b in low) / len(bg)
        if cover >= thresh:
            return True
    return False


def score_check(text: str, spec: dict[str, Any], ctype: str, thresh: float | None) -> float:
    """thresh=None → 用现行（精确）口径；给了数 → 放宽口径。"""
    if ctype == "lead_with":
        head = text[: int(spec.get("within_chars") or spec.get("head_chars") or 260)]
        text = head
    groups = objective._groups_of(spec)
    if not groups:
        return 0.0
    low = text.lower()
    hit = 0
    for _label, syns in groups:
        if thresh is None:
            ok = any(s.lower() in low for s in syns)
        else:
            ok = relaxed_hit(text, syns, thresh)
        hit += 1 if ok else 0
    return hit / len(groups)


def load_specs(run_id: str) -> dict[str, list[dict]]:
    """题号 → 归一化后的断言列表（含 groups 明细）。

    题面在 `state.json` 里（不是 `cases.json` —— 第一版猜错了目录，
    结果六席全报"读不到题面"。`show_case.py` 读的就是 state.json）。
    """
    p = RUNS / run_id / "state.json"
    if not p.is_file():
        return {}
    state = json.loads(p.read_text(encoding="utf-8"))
    out: dict[str, list[dict]] = {}
    for c in (state.get("cases") or []):
        cid = str(c.get("id") or "")
        checks = c.get("checks") or []
        try:
            checks = objective.normalize_checks(checks)
        except Exception:  # noqa: BLE001
            pass
        out[cid] = checks
    return out


def load_rows(run_id: str) -> tuple[list[dict], set[str]]:
    names: set[str] = set()
    rp = RUNS / run_id / "report.json"
    if rp.is_file():
        hold = (json.loads(rp.read_text(encoding="utf-8")).get("scores") or {}).get("holdout") or {}
        names = {str(c) for c in (hold.get("cases") or [])}
    rows: list[dict] = []
    for d in (RUNS / f"{run_id}-reholdout", RUNS / run_id):
        p = d / "results.jsonl"
        if not p.is_file():
            continue
        cand = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if len(cand) > len(rows):
            rows = cand
    return rows, names


def rescore(row: dict, specs: list[dict], thresh: float | None) -> float | None:
    text = str(row.get("reply") or "")
    if not text or not specs:
        return None
    tot = wsum = 0.0
    for spec in specs:
        w = float(spec.get("weight") or 0)
        ctype = str(spec.get("type") or "")
        if w <= 0:
            continue
        tot += w
        if ctype in RELAXED:
            s = score_check(text, spec, ctype, thresh)
        else:
            # 非放宽类型：沿用盘上已算好的分，避免重跑 numeric 解析引入新误差
            s = None
            for c in (row.get("checks") or []):
                if str(c.get("type")) == ctype and abs(float(c.get("weight") or 0) - w) < 1e-6:
                    s = float(c.get("score") or 0)
                    break
            if s is None:
                s = 0.0
        wsum += w * s
    return 100.0 * wsum / tot if tot > 0 else None


def stats(deltas: list[float]) -> tuple[float, float, float]:
    if len(deltas) < 2:
        return 0.0, 0.0, float("inf")
    m, sd = st.fmean(deltas), st.stdev(deltas)
    n = (Z * sd / abs(m)) ** 2 if abs(m) > 1e-9 else float("inf")
    return m, sd, n


def main() -> int:
    ap = argparse.ArgumentParser(description="量化字面匹配的松紧对判定的影响")
    ap.add_argument("--thresh", type=float, default=0.8)
    args = ap.parse_args()

    print(f"放宽口径：近义词的字符二元组覆盖率 ≥ {args.thresh:.0%} 即算命中"
          f"（只放宽 {'/'.join(sorted(RELAXED))}）\n")
    hdr = (f"{'席位':<11}{'题':>3}  {'现行Δ':>7}{'现行sd':>8}{'现行n':>8}  "
           f"{'放宽Δ':>7}{'放宽sd':>8}{'放宽n':>8}   变化")
    print(hdr)
    print("-" * len(hdr))

    any_row = False
    for seat, rid in SEATS:
        specs_by_case = load_specs(rid)
        rows, names = load_rows(rid)
        if not specs_by_case or not rows:
            print(f"{seat:<11}  —  读不到题面或明细（specs={len(specs_by_case)}）")
            continue
        cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in rows:
            c = str(r.get("case") or "")
            if names and c not in names:
                continue
            cells[(str(r.get("variant")), c)].append(r)
        arms = {a for a, _ in cells}
        champs = [a for a in arms if a != "baseline"]
        if "baseline" not in arms or len(champs) != 1:
            print(f"{seat:<11}  —  臂不唯一（{len(champs)}）")
            continue
        champ = champs[0]
        cases = sorted({c for a, c in cells if a == champ and ("baseline", c) in cells})

        d_now: list[float] = []
        d_rel: list[float] = []
        for c in cases:
            specs = specs_by_case.get(c) or []
            for thresh, bucket in ((None, d_now), (args.thresh, d_rel)):
                cv = [v for r in cells[(champ, c)] if (v := rescore(r, specs, thresh)) is not None]
                bv = [v for r in cells[("baseline", c)]
                      if (v := rescore(r, specs, thresh)) is not None]
                if cv and bv:
                    bucket.append(st.fmean(cv) - st.fmean(bv))
        if len(d_now) < 2 or len(d_rel) < 2:
            print(f"{seat:<11}  —  可用题不足（{len(d_now)}/{len(d_rel)}）")
            continue
        any_row = True
        m1, s1, n1 = stats(d_now)
        m2, s2, n2 = stats(d_rel)

        def fn(v: float) -> str:
            return f"{v:.0f}" if math.isfinite(v) and v < 99999 else "∞"

        better = "**更易判**" if n2 < n1 * 0.7 else ("更难判" if n2 > n1 * 1.4 else "基本不变")
        print(f"{seat:<11}{len(d_now):>3}  {m1:>+7.2f}{s1:>8.2f}{fn(n1):>8}  "
              f"{m2:>+7.2f}{s2:>8.2f}{fn(n2):>8}   {better}")

    if not any_row:
        print("\n没有可用数据：题面文件（cases.json / suite.json）可能不在这些 run 目录里。")
        print("这条本身是信息 —— 说明**离线重打分依赖的题面没随 run 落盘**，")
        print("那么任何「换个尺子重算」的分析都做不了，这是个该修的缺口。")
        return 1

    print("\n判读纪律：")
    print("  · 这是**单旋钮实验**：只动 must_include/lead_with 的字面松紧，其余分数沿用盘上值。")
    print("  · 放宽**不降低堆词地板**：堆词假答案把近义词原样拼起来，现行口径下已拿满")
    print("    must_include，放宽不会让它拿更多。所以这个旋钮与 §13 的抗刷分不冲突。")
    print("  · 但放宽会让**近义词表写得糙**的题变松 —— 二元组覆盖是近似，不是语义理解。")
    print("    所以它只能用来**估计措辞噪声的量级**，不能直接当新尺子上线。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
