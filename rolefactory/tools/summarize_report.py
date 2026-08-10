"""把 report.json 压成一页人读的摘要：性能、评分体系、各臂分数、维度对比、冠军槽位。

用法：python tools/summarize_report.py data/runs/<run_id>/report.json
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path


def main(path: str) -> None:
    r = json.load(io.open(path, encoding="utf-8-sig"))
    perf, s = r["performance"], r["scores"]
    llm = perf["llm"]
    out: list[str] = []
    add = out.append

    add(f"# {r['role']}（{r['role_id']}）· run {r['run_id']} · {r['status']}")
    add("")
    add("## 性能")
    add(
        f"墙钟 {r['wall_seconds']}s｜API 调用 {llm['api_calls']}｜tokens {llm['total_tokens']}"
        f"｜评测 {perf['evals']['done']}/{perf['evals']['total']}（失败 {perf['evals']['failed']}）"
    )
    add(
        f"单条评测 {perf['tokens_per_eval']} tokens｜吞吐 {perf['api_calls_per_second']} 次/秒"
        f"｜延时 p50 {llm['latency_p50']}s / p90 {llm['latency_p90']}s｜缓存命中 {llm['cache_hits']}"
    )
    add("")
    sc = r.get("scoring") or {}
    add("## 评分体系")
    add(f"模式：{sc.get('mode')}｜出题自校通过 {sc.get('verified_cases')} 题")
    for k, v in (sc.get("check_types") or {}).items():
        add(f"- {k}：{v['count']} 条，权重合 {v['weight_sum']}")
    for key, label in (
        ("objective_spread_arms", "客观分跨度（对照臂）"),
        ("objective_spread_variants", "客观分跨度（全部变体）"),
        ("judge_shadow_spread_arms", "影子裁判跨度"),
    ):
        d = sc.get(key) or {}
        if d.get("n"):
            add(f"- {label}：{d['min']} – {d['max']}（跨度 {d['spread']}，σ {d['std']}，n={d['n']}）")
    add("")
    add("## 分数")
    add(
        f"进化集：基线 {s['baseline_no_genes']['weighted']}｜全弱基因 {s['all_weak_genes']['weighted']}"
        f"｜冠军 {s['champion_train']['weighted']}（Δ {s['delta_train_weighted']}）"
    )
    ct = s["champion_train"]
    add(
        f"冠军稳定性：σ {ct['std']}｜题级跨度 {ct.get('spread')}｜最低题 {ct['min_case']}"
        f"｜断言全通率 {ct.get('check_pass_rate')}"
    )
    add(f"进化集 paired：{json.dumps(s['paired_train'], ensure_ascii=False)}")
    hd = s.get("holdout") or {}
    if hd:
        add(
            f"holdout：基线 {hd['baseline']['weighted']}｜冠军 {hd['champion']['weighted']}"
            f"｜Δ {hd['delta_weighted']}｜泛化差 {hd['generalization_gap']}"
        )
        add(f"holdout paired：{json.dumps(hd['paired'], ensure_ascii=False)}")
    add("")
    add("## 维度对比（冠军 vs 基线，进化集）")
    names = {d["key"]: d["name"] for d in r["blueprint"]["dimensions"]}
    weights = {d["key"]: d["weight"] for d in r["blueprint"]["dimensions"]}
    for k, name in names.items():
        c = (ct.get("by_dimension") or {}).get(k)
        b = (s["baseline_no_genes"].get("by_dimension") or {}).get(k)
        delta = round(c - b, 2) if c is not None and b is not None else None
        add(f"- {name}（权重 {weights[k]}）：冠军 {c}｜基线 {b}｜Δ {delta}")
    add("")
    add("## 各代与消融")
    for g in r["generations"]:
        add(f"第 {g['gen']} 代：最优 composite {g['best']}｜均值 {g['mean']}｜{g['seconds']}s")
        for v in g["variants"]:
            add(
                f"  - {v['origin']}：加权 {v['weighted']}｜composite {v['composite']}"
                f"｜σ {v['std']}｜最低题 {v['min_case']}"
            )
    add("")
    add("## 冠军槽位")
    for slot, label in (r["champion_genome"]["labels"] or {}).items():
        add(f"- {slot}：{label}")
    add("")
    add(f"题库：{r['suite']['count']} 题 → {r['suite']['path']}")
    add("")
    add("## caveats")
    for c in r.get("caveats") or []:
        add(f"- {c}")

    dest = Path(path).with_name("SUMMARY.md")
    dest.write_text("\n".join(out), encoding="utf-8")
    print(f"written {dest}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "report.json")
