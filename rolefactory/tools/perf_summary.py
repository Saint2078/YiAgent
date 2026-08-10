#!/usr/bin/env python3
"""汇总 run 的性能画像：并发利用率、阶段耗时、purpose 级 token/秒。

用法：
    python tools/perf_summary.py [run_id ...]      # 缺省汇总全部 run
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parents[1] / "data" / "runs"


def load(run_id: str) -> dict | None:
    p = RUNS / run_id / "report.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def summarize(r: dict) -> dict:
    perf = r.get("performance") or {}
    llm = perf.get("llm") or {}
    wall = float(r.get("wall_seconds") or 0) or 1.0
    api_s = float(llm.get("api_seconds_sum") or 0)
    conc = int((r.get("params") or {}).get("concurrency") or 0)
    gens = r.get("generations") or []
    gen_s = sum(float(g.get("seconds") or 0) for g in gens)
    hold_s = float(((r.get("scores") or {}).get("holdout") or {}).get("seconds") or 0)
    return {
        "run_id": r.get("run_id"),
        "role": r.get("role"),
        "wall": round(wall, 1),
        "calls": llm.get("calls"),
        "api_calls": llm.get("api_calls"),
        "cache_hits": llm.get("cache_hits"),
        "hit_rate": llm.get("cache_hit_rate"),
        "retries": llm.get("retries"),
        "errors": llm.get("errors"),
        "p50": llm.get("latency_p50"),
        "p90": llm.get("latency_p90"),
        "max": llm.get("latency_max"),
        "api_seconds_sum": round(api_s, 1),
        # 在跑并发数 = LLM 占用秒 / 墙钟秒；对比 concurrency 上限看闸门是否吃满
        "eff_parallel": round(api_s / wall, 2),
        "conc_cap": conc,
        "util_vs_cap": round(api_s / wall / conc, 2) if conc else None,
        "evals": perf.get("evals"),
        "tokens": llm.get("total_tokens"),
        "tokens_per_eval": perf.get("tokens_per_eval"),
        "evals_per_minute": perf.get("evals_per_minute"),
        "gen_seconds": round(gen_s, 1),
        "holdout_seconds": round(hold_s, 1),
        # 进化+holdout 之外的时间：蓝图/出题/基因库/基线等前置阶段
        "prep_seconds": round(wall - gen_s - hold_s, 1),
        "by_purpose": llm.get("by_purpose") or {},
        "params": {
            k: (r.get("params") or {}).get(k)
            for k in (
                "per_dim",
                "generations",
                "variants_per_gen",
                "reps",
                "elite",
                "patience",
                "min_gain",
                "scoring_mode",
            )
        },
    }


def main(argv: list[str]) -> int:
    ids = argv[1:] or sorted(p.name for p in RUNS.iterdir() if p.is_dir())
    rows = []
    for rid in ids:
        r = load(rid)
        if r:
            rows.append(summarize(r))
    if not rows:
        print("no runs", file=sys.stderr)
        return 2

    print(
        f"{'run_id':24} {'role':16} {'wall':>7} {'api_s':>8} {'par':>5} {'cap':>4} "
        f"{'util':>5} {'calls':>6} {'hit':>5} {'retry':>5} {'tok/eval':>9} {'prep':>7} {'gens':>7} {'hold':>6}"
    )
    for s in rows:
        print(
            f"{str(s['run_id']):24} {str(s['role'])[:16]:16} {s['wall']:7.1f} {s['api_seconds_sum']:8.1f} "
            f"{s['eff_parallel']:5.2f} {str(s['conc_cap']):>4} {str(s['util_vs_cap']):>5} "
            f"{str(s['calls']):>6} {str(s['hit_rate']):>5} {str(s['retries']):>5} "
            f"{str(s['tokens_per_eval']):>9} {s['prep_seconds']:7.1f} {s['gen_seconds']:7.1f} {s['holdout_seconds']:6.1f}"
        )

    print("\n按用途拆时（秒 / calls / tokens）")
    for s in rows:
        print(f"\n{s['run_id']} · {s['role']} · params={s['params']}")
        print(f"  p50={s['p50']} p90={s['p90']} max={s['max']} evals={s['evals']}")
        for k, v in sorted(s["by_purpose"].items(), key=lambda kv: -float(kv[1].get("seconds") or 0)):
            print(
                f"  {k:28} calls={int(v.get('calls') or 0):4} hits={int(v.get('cache_hits') or 0):3} "
                f"s={float(v.get('seconds') or 0):8.1f} tok={int(v.get('tokens') or 0):7}"
            )

    tw = sum(s["wall"] for s in rows)
    print(f"\n合计 wall={tw:.1f}s ({tw/60:.1f}min) · runs={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
