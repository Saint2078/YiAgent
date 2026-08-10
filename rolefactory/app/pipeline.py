"""全链路流水线：角色名 → 锚点 → 蓝图 → 题组+裁判 → 基因库 → 基线 → 多代进化 → holdout → 冠军报告。

并发模型：一次 run 一个 Session（共享信号量/缓存/预算）。同一代内所有
(变体 × 题 × 重复) 的「作答→裁判」全部并行提交，由信号量限流。
"""

from __future__ import annotations

import asyncio
import random
import statistics
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from . import anchors as anchors_mod
from . import genes, judge, objective, roles, store
from .config import SETTINGS
from .llm import Budget, Session

PHASES = ("anchors", "blueprint", "cases", "bank", "baseline", "evolve", "holdout", "done")


# ------------------------------------------------------------------ 聚合


def aggregate(rows: list[dict[str, Any]], blueprint: dict[str, Any]) -> dict[str, Any]:
    """题级取重复均值 → 维度均值 → 按蓝图权重加权；composite 扣一个稳定性罚项。"""
    if not rows:
        return {"n": 0, "mean": None, "weighted": None, "composite": None, "by_dimension": {}, "std": None}
    by_case: dict[str, list[float]] = {}
    dim_of: dict[str, str] = {}
    traps: list[bool] = []
    judge_scores: list[float] = []
    check_pass: list[float] = []
    for r in rows:
        by_case.setdefault(r["case"], []).append(float(r["score"]))
        dim_of[r["case"]] = r["dimension_key"]
        if r.get("hit_trap") is not None:
            traps.append(bool(r.get("hit_trap")))
        if r.get("judge_score") is not None:
            judge_scores.append(float(r["judge_score"]))
        if r.get("checks_count"):
            check_pass.append(float(r.get("checks_passed") or 0) / float(r["checks_count"]))
    case_means = {c: statistics.fmean(v) for c, v in by_case.items()}

    by_dim: dict[str, list[float]] = {}
    for case_id, m in case_means.items():
        by_dim.setdefault(dim_of[case_id], []).append(m)
    dim_means = {k: round(statistics.fmean(v), 2) for k, v in by_dim.items()}

    weights = {d["key"]: float(d["weight"]) for d in blueprint["dimensions"]}
    wsum = sum(weights.get(k, 0.0) for k in dim_means) or 0.0
    weighted = (
        round(sum(dim_means[k] * weights.get(k, 0.0) for k in dim_means) / wsum, 2) if wsum > 0 else None
    )
    vals = list(case_means.values())
    mean = round(statistics.fmean(vals), 2)
    std = round(statistics.pstdev(vals), 2) if len(vals) > 1 else 0.0
    base = weighted if weighted is not None else mean
    return {
        "n": len(rows),
        "cases": len(case_means),
        "mean": mean,
        "weighted": weighted,
        "std": std,
        "composite": round(base - 0.5 * std, 2),
        "by_dimension": dim_means,
        "by_case": {k: round(v, 2) for k, v in case_means.items()},
        "trap_rate": round(sum(1 for t in traps if t) / len(traps), 3) if traps else None,
        "min_case": round(min(vals), 2),
        "max_case": round(max(vals), 2),
        "spread": round(max(vals) - min(vals), 2),
        "check_pass_rate": round(statistics.fmean(check_pass), 3) if check_pass else None,
        "judge_shadow": round(statistics.fmean(judge_scores), 2) if judge_scores else None,
    }


def bootstrap_ci(diffs: list[float], *, iters: int = 2000, seed: int = 20260811) -> list[float] | None:
    """配对差值均值的 95% 自助置信区间。

    题数只有 5–6 时，`mean_delta` 的点估计不足以判定优劣：换一组题就可能翻符号。
    这里对「题」重采样（配对结构天然保留），给出区间；区间跨 0 就是判不了，不许当赢。
    固定 seed，同一份 by_case 复算得同一区间。
    """
    n = len(diffs)
    if n < 3:
        return None
    rng = random.Random(seed)
    means = [statistics.fmean(rng.choices(diffs, k=n)) for _ in range(iters)]
    means.sort()
    lo = means[int(0.025 * iters)]
    hi = means[min(iters - 1, int(0.975 * iters))]
    return [round(lo, 2), round(hi, 2)]


def paired_delta(champ: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    a, b = champ.get("by_case") or {}, base.get("by_case") or {}
    common = sorted(set(a) & set(b))
    if not common:
        return {"cases": 0}
    diffs = [a[c] - b[c] for c in common]
    ci = bootstrap_ci(diffs)
    return {
        "cases": len(common),
        "mean_delta": round(statistics.fmean(diffs), 2),
        "improved": sum(1 for d in diffs if d > 0.5),
        "regressed": sum(1 for d in diffs if d < -0.5),
        "worst": round(min(diffs), 2),
        "best": round(max(diffs), 2),
        "sd_delta": round(statistics.stdev(diffs), 2) if len(diffs) > 1 else None,
        "mean_delta_ci95": ci,
        # 区间整体在 0 以上/以下才算判定成立；跨 0 一律「判不了」
        "significant": (bool(ci[0] > 0 or ci[1] < 0) if ci else None),
    }


# ------------------------------------------------------------------ run 状态


@dataclass
class Run:
    run_id: str
    role: str
    params: dict[str, Any]
    created_at: float = field(default_factory=time.time)
    # created_at 是可读时间戳；时长一律用单调钟，避免容器时钟被校正后出现负数
    created_mono: float = field(default_factory=time.monotonic)
    status: str = "running"
    phase: str = "anchors"
    error: str = ""
    logs: list[str] = field(default_factory=list)
    anchors: list[dict] = field(default_factory=list)
    blueprint: dict[str, Any] = field(default_factory=dict)
    cases: list[dict] = field(default_factory=list)
    train_ids: list[str] = field(default_factory=list)
    holdout_ids: list[str] = field(default_factory=list)
    bank: dict[str, list[dict]] = field(default_factory=dict)
    generations: list[dict] = field(default_factory=list)
    baseline: dict[str, Any] = field(default_factory=dict)
    all_weak: dict[str, Any] = field(default_factory=dict)
    champion: dict[str, Any] = field(default_factory=dict)
    holdout: dict[str, Any] = field(default_factory=dict)
    eval_done: int = 0
    eval_total: int = 0
    eval_failed: int = 0
    phase_seconds: dict[str, float] = field(default_factory=dict)
    session: Session | None = None
    task: asyncio.Task | None = None

    def mark(self, phase: str, seconds: float) -> None:
        self.phase_seconds[phase] = round(self.phase_seconds.get(phase, 0.0) + max(0.0, seconds), 1)

    @property
    def role_id(self) -> str:
        return self.blueprint.get("role_id") or roles.slugify(self.role)

    def log(self, msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        self.logs.append(line)
        if len(self.logs) > 400:
            del self.logs[: len(self.logs) - 400]
        print(f"{self.run_id} {line}", flush=True)

    def snapshot(self, *, full: bool = False) -> dict[str, Any]:
        s = self.session
        wall = (s.wall if s else max(0.0, time.monotonic() - self.created_mono))
        llm = s.meter.snapshot() if s else {}
        throughput = None
        if llm.get("api_calls") and wall > 0:
            throughput = round(llm["api_calls"] / wall, 2)
        out: dict[str, Any] = {
            "run_id": self.run_id,
            "role": self.role,
            "role_id": self.role_id,
            "params": self.params,
            "status": self.status,
            "phase": self.phase,
            "error": self.error,
            "created_at": round(self.created_at, 3),
            "wall_seconds": round(wall, 1),
            "progress": {
                "phases": list(PHASES),
                "phase_index": PHASES.index(self.phase) if self.phase in PHASES else 0,
                "eval_done": self.eval_done,
                "eval_total": self.eval_total,
                "eval_failed": self.eval_failed,
                "phase_seconds": self.phase_seconds,
            },
            "llm": {**llm, "calls_per_second": throughput, "model": (s.model if s else SETTINGS.model),
                    "concurrency": (s.concurrency if s else SETTINGS.concurrency)},
            "anchors": self.anchors,
            "blueprint": self.blueprint,
            "cases_count": len(self.cases),
            "train_ids": self.train_ids,
            "holdout_ids": self.holdout_ids,
            "bank_summary": {
                slot: [
                    {"id": a["id"], "label": a["label"], "strength": a["strength"]} for a in self.bank.get(slot, [])
                ]
                for slot, _ in genes.SLOTS
            }
            if self.bank
            else {},
            "generations": [
                {
                    "gen": g["gen"],
                    "evaluated": g["evaluated"],
                    "best": g["best"],
                    "mean": g["mean"],
                    "variants": g["variants"],
                    "seconds": g["seconds"],
                }
                for g in self.generations
            ],
            "scoring": scoring_summary(self),
            "baseline": self.baseline,
            "all_weak": self.all_weak,
            "champion": self.champion,
            "holdout": self.holdout,
            "logs": self.logs[-60:],
        }
        if full:
            out["cases"] = self.cases
            out["bank"] = self.bank
            out["logs"] = self.logs
        return out

    def persist(self) -> None:
        d = store.run_dir(self.run_id)
        store.write_json(d / "state.json", self.snapshot(full=True))


# ------------------------------------------------------------------ 评测批


async def eval_batch(
    run: Run,
    session: Session,
    variants: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    reps: int,
    *,
    shadow_judge: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """并行跑 (变体 × 题 × 重复)，返回 variant_id → rows。"""
    jobs: list[tuple[dict, dict, int]] = [
        (v, c, r) for v in variants for c in cases for r in range(reps)
    ]
    run.eval_total += len(jobs)
    out: dict[str, list[dict[str, Any]]] = {v["id"]: [] for v in variants}
    rows_for_disk: list[dict[str, Any]] = []
    lock = asyncio.Lock()

    mode = str(run.params.get("scoring_mode") or "judge")

    async def one(v: dict, c: dict, r: int) -> None:
        try:
            row = await judge.eval_one(
                session, v, c, rep=r, mode=mode, shadow_judge=shadow_judge and mode == "objective"
            )
        except Budget:
            raise
        except Exception as exc:  # noqa: BLE001 单点失败不拖垮整批
            async with lock:
                run.eval_failed += 1
                run.eval_done += 1
            run.log(f"eval 失败 {v['id']}/{c['id']}#{r}: {type(exc).__name__}: {exc}")
            return
        async with lock:
            out[v["id"]].append(row)
            rows_for_disk.append(row)
            run.eval_done += 1
            done, total = run.eval_done, run.eval_total
        if done % 5 == 0 or done == total:
            run.log(f"评测进度 {done}/{total}｜tokens={session.meter.total_tokens}")

    await asyncio.gather(*(asyncio.create_task(one(v, c, r)) for v, c, r in jobs))
    if rows_for_disk:
        store.append_jsonl(store.run_dir(run.run_id) / "results.jsonl", rows_for_disk)
    return out


# ------------------------------------------------------------------ 主流程


async def execute(run: Run, api_key: str) -> None:
    p = run.params
    session = Session(
        api_key,
        p.get("model"),
        concurrency=p.get("concurrency"),
        budget_tokens=p.get("budget_tokens"),
        budget_seconds=p.get("budget_seconds"),
    )
    run.session = session
    rng = random.Random(int(p.get("seed") or 42))
    reps = max(1, int(p.get("reps") or 1))
    # holdout 只有 2 个臂（冠军 vs 无基因基线）、5–6 道题，是全流程最便宜的一段，
    # 却是「有没有泛化」的唯一判据。单独把重复次数抬上去买信噪比，代价约一个批次。
    hold_reps = max(reps, int(p.get("holdout_reps") or 3))
    t_phase = time.monotonic()

    try:
        # 1) 锚点
        run.phase = "anchors"
        run.anchors = anchors_mod.retrieve(run.role, limit=int(p.get("anchor_limit") or 5))
        run.log(f"锚点命中 {len(run.anchors)} 条：{', '.join(a['id'] for a in run.anchors) or '（无）'}")
        run.persist()

        # 2) 蓝图
        run.phase = "blueprint"
        t_phase = time.monotonic()
        mode = str(p.get("scoring_mode") or "judge")
        run.blueprint = await roles.plan_blueprint(session, run.role, run.anchors, mode=mode)
        run.mark("blueprint", time.monotonic() - t_phase)
        run.log(
            f"蓝图 {len(run.blueprint['dimensions'])} 维度（{time.monotonic() - t_phase:.1f}s）："
            + "、".join(f"{d['name']}{d['weight']}" for d in run.blueprint["dimensions"])
        )
        run.persist()

        # 3) 题组 + 裁判（维度级并行）
        # 基因库只拿前几道题的标题当上下文，够用了就开工，与剩余出题（含长尾）并行。
        run.phase = "cases"
        t_phase = time.monotonic()
        bank_ready = asyncio.Event()
        bank_cue = max(2, min(4, int(p.get("per_dim") or 2) * len(run.blueprint["dimensions"])))

        def on_case(case: dict | None, err: str | None) -> None:
            if case:
                run.cases.append(case)
                run.log(f"出题 {len(run.cases)}：[{case['dimension']}/{case['level']}] {case['title']}")
                if len(run.cases) >= bank_cue:
                    bank_ready.set()
            elif err:
                run.log(f"出题失败 {err}")

        run.cases = []
        suite_task = asyncio.create_task(
            roles.build_suite(
                session,
                run.blueprint,
                run.anchors,
                per_dim=int(p.get("per_dim") or 2),
                on_case=on_case,
                mode=mode,
            )
        )
        cue_task = asyncio.create_task(bank_ready.wait())
        await asyncio.wait({suite_task, cue_task}, return_when=asyncio.FIRST_COMPLETED)
        cue_task.cancel()
        bank_task: asyncio.Task | None = None
        if run.cases:
            run.phase = "bank"
            t_bank = time.monotonic()
            bank_task = asyncio.create_task(
                genes.build_bank(session, run.blueprint, list(run.cases))
            )
            run.log(f"基因库与出题并行开工（已就绪 {len(run.cases)} 题）")
        run.phase = "cases"
        try:
            cases = await suite_task
        except BaseException:
            if bank_task:
                bank_task.cancel()
            raise
        if not cases:
            if bank_task:
                bank_task.cancel()
            raise RuntimeError("题组为空")
        run.cases = cases
        train, hold = roles.split_holdout(cases, per_dim=int(p.get("holdout_per_dim") or 1))
        run.train_ids = [c["id"] for c in train]
        run.holdout_ids = [c["id"] for c in hold]
        store.save_suite(run.role_id, cases, run.blueprint)
        run.mark("cases", time.monotonic() - t_phase)
        run.log(
            f"题组 {len(cases)} 道（{time.monotonic() - t_phase:.1f}s）｜train {len(train)} / holdout {len(hold)}"
        )
        if len(hold) < 20:
            # 判定力话说在前头：题量不够时事后再解释「为什么判不了」没有意义。
            run.log(
                f"⚠ holdout 仅 {len(hold)} 道：按 PERF.md §10.1 的方差量级，"
                "低于约 20 道时大概率判不出实测效应（调 holdout_per_dim 加题）"
            )
        run.persist()

        # 4) 基因库（多半已在出题期间跑掉大半）
        run.phase = "bank"
        if bank_task is None:
            t_bank = time.monotonic()
            bank_task = asyncio.create_task(genes.build_bank(session, run.blueprint, cases))
        run.bank = await bank_task
        run.mark("bank", time.monotonic() - t_bank)
        run.log(
            f"基因库就绪（{time.monotonic() - t_bank:.1f}s，与出题重叠）："
            + "｜".join(f"{s}×{len(run.bank[s])}" for s, _ in genes.SLOTS)
        )
        run.persist()

        # 5) 基线（无基因 + 全弱基因）与第 0 代合批
        # 两者互不依赖，合成一个批次少一次 barrier：一代的墙钟由最慢那条决定，批越少越省。
        run.phase = "baseline"
        t_phase = time.monotonic()
        base_v = genes.baseline_variant()
        weak_v = genes.all_weak_variant(run.bank)
        shadow = bool(p.get("judge_shadow", True))

        max_gen = max(1, int(p.get("generations") or 3))
        pop_n = max(2, int(p.get("variants_per_gen") or 6))
        elite_k = max(1, int(p.get("elite") or 2))
        min_gain = float(p.get("min_gain") or 0.5)

        seen: set[str] = set()
        population = genes.seed_population(run.bank, pop_n, rng)
        for v in population:
            seen.add(v["sig"])

        run.log(
            f"基线 + 第 0 代合批：{2 + len(population)} 个变体 × {len(train)} 题 × {reps} 次"
        )
        got = await eval_batch(
            run, session, [base_v, weak_v] + population, train, reps, shadow_judge=shadow
        )
        run.baseline = {"variant": base_v, **aggregate(got[base_v["id"]], run.blueprint)}
        run.all_weak = {"variant": weak_v, **aggregate(got[weak_v["id"]], run.blueprint)}
        gen0_rows: dict[str, list[dict[str, Any]]] | None = {v["id"]: got[v["id"]] for v in population}
        run.mark("baseline+gen0", time.monotonic() - t_phase)
        run.log(
            f"基线 weighted={run.baseline.get('weighted')}｜全弱基因 weighted={run.all_weak.get('weighted')}"
            f"（{time.monotonic() - t_phase:.1f}s）"
        )
        run.persist()

        # 6) 多代进化
        run.phase = "evolve"
        hof: list[dict[str, Any]] = []
        best_composite = float("-inf")
        stagnant = 0

        for gen in range(max_gen):
            t_gen = time.monotonic()
            if gen == 0 and gen0_rows is not None:
                got, gen0_rows = gen0_rows, None
                run.log(f"第 0 代复用合批结果：{len(population)} 个变体")
            else:
                run.log(f"第 {gen} 代：{len(population)} 个变体 × {len(train)} 题 × {reps} 次")
                got = await eval_batch(run, session, population, train, reps)
            scored: list[dict[str, Any]] = []
            for v in population:
                agg = aggregate(got[v["id"]], run.blueprint)
                if agg.get("composite") is None:
                    continue
                scored.append({**v, **agg})
            if not scored:
                raise RuntimeError(f"第 {gen} 代无有效评分")
            scored.sort(key=lambda x: (-(x["composite"]), -(x["weighted"] or 0)))
            hof.extend(scored)
            hof.sort(key=lambda x: -(x["composite"]))
            hof = hof[:12]

            gen_rec = {
                "gen": gen,
                "evaluated": len(scored),
                "best": scored[0]["composite"],
                "best_weighted": scored[0]["weighted"],
                "mean": round(statistics.fmean([s["composite"] for s in scored]), 2),
                "seconds": round(time.monotonic() - t_gen, 1),
                "variants": [
                    {
                        "id": s["id"],
                        "origin": s["origin"],
                        "labels": s["labels"],
                        "choice": s["choice"],
                        "weighted": s["weighted"],
                        "composite": s["composite"],
                        "std": s["std"],
                        "min_case": s["min_case"],
                        "spread": s.get("spread"),
                        "check_pass_rate": s.get("check_pass_rate"),
                        "by_dimension": s["by_dimension"],
                    }
                    for s in scored
                ],
            }
            run.generations.append(gen_rec)
            run.champion = {
                k: hof[0][k]
                for k in (
                    "id", "sig", "gen", "origin", "choice", "labels", "system",
                    "weighted", "composite", "mean", "std", "min_case", "max_case", "spread",
                    "by_dimension", "by_case", "trap_rate", "check_pass_rate", "judge_shadow",
                    "n", "cases",
                )
                if k in hof[0]
            }
            run.mark("evolve", time.monotonic() - t_gen)
            run.log(
                f"第 {gen} 代最优 composite={scored[0]['composite']} weighted={scored[0]['weighted']}"
                f"｜{scored[0]['origin']}｜{time.monotonic() - t_gen:.1f}s"
            )
            run.persist()

            gain = scored[0]["composite"] - best_composite if best_composite > float("-inf") else 999.0
            best_composite = max(best_composite, scored[0]["composite"])
            if gain < min_gain:
                stagnant += 1
                run.log(f"增益 {gain:+.2f} < {min_gain}，停滞 {stagnant} 代")
            else:
                stagnant = 0
            if stagnant >= int(p.get("patience") or 1):
                run.log("触发早停：连续停滞")
                break
            if gen == max_gen - 1:
                break
            if session.meter.total_tokens > session.budget_tokens * 0.75:
                run.log("预算用掉 75%，停止繁殖")
                break
            elites = hof[:elite_k]
            population = genes.breed(elites, run.bank, pop_n, gen + 1, rng, seen)
            if not population:
                run.log("无新组合可繁殖，收敛")
                break

        # 7) holdout 鉴定
        if hold and run.champion:
            run.phase = "holdout"
            t_phase = time.monotonic()
            champ_v = next((h for h in hof if h["id"] == run.champion["id"]), hof[0])
            champ_slim = {
                "id": champ_v["id"], "sig": champ_v["sig"], "system": champ_v["system"],
                "choice": champ_v["choice"], "labels": champ_v["labels"],
            }
            got = await eval_batch(
                run, session, [champ_slim, base_v], hold, hold_reps, shadow_judge=bool(p.get("judge_shadow", True))
            )
            champ_h = aggregate(got[champ_slim["id"]], run.blueprint)
            base_h = aggregate(got[base_v["id"]], run.blueprint)
            run.holdout = {
                "cases": run.holdout_ids,
                "reps": hold_reps,
                "champion": champ_h,
                "baseline": base_h,
                "delta_weighted": (
                    round((champ_h.get("weighted") or 0) - (base_h.get("weighted") or 0), 2)
                    if champ_h.get("weighted") is not None and base_h.get("weighted") is not None
                    else None
                ),
                "paired": paired_delta(champ_h, base_h),
                "generalization_gap": (
                    round((run.champion.get("weighted") or 0) - (champ_h.get("weighted") or 0), 2)
                    if champ_h.get("weighted") is not None
                    else None
                ),
                "seconds": round(time.monotonic() - t_phase, 1),
            }
            run.mark("holdout", time.monotonic() - t_phase)
            run.log(
                f"holdout 冠军={champ_h.get('weighted')} 基线={base_h.get('weighted')}"
                f" Δ={run.holdout.get('delta_weighted')}｜泛化差={run.holdout.get('generalization_gap')}"
            )

        run.phase = "done"
        run.status = "done"
        write_report(run)
        run.log(f"完成｜wall={session.wall:.1f}s｜tokens={session.meter.total_tokens}")
        run.persist()

    except Budget as exc:
        run.status = "aborted"
        run.error = str(exc)
        run.log(f"中止：{exc}")
        write_report(run)
        run.persist()
    except asyncio.CancelledError:
        run.status = "aborted"
        run.error = "cancelled"
        run.log("已取消")
        run.persist()
        raise
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.error = f"{type(exc).__name__}: {exc}"
        run.log(f"失败：{run.error}")
        run.persist()


async def reholdout(run_id: str, api_key: str, *, reps: int = 3) -> dict[str, Any]:
    """对一次**已完成**的 run 只重跑 holdout 相位，结果单独落盘，不改原报告。

    为什么值得一条单独的路径：holdout 是「这套基因到底有没有泛化」的唯一判据，
    却只有 2 个臂 × 5–6 题 —— 重跑一次约 90s，重跑整条流水线要十分钟。
    而 `reps=1` 判出的结论噪声大到会翻符号（实测项目经理 Δ 从 −2.74 变 +1.46），
    所以旧 run 需要一个便宜的复核入口。

    原报告保持不可变（审计要求），复核结果写 `reholdout.json`；
    `tools/genome_card.py` 发现该文件时优先采用，并在卡片上标注 holdout 来源。
    """
    d = store.run_dir(run_id)
    state = store.read_json(d / "state.json")
    if not isinstance(state, dict):
        raise RuntimeError(f"run {run_id} 没有 state.json，无法复核")
    if (state.get("status") or "") != "done":
        raise RuntimeError(f"run {run_id} 状态为 {state.get('status')}，只复核 done 的")
    champ = state.get("champion") or {}
    if not champ.get("system"):
        raise RuntimeError(f"run {run_id} 没有冠军基因组，无法复核")
    hold_ids = set(state.get("holdout_ids") or [])
    hold = [c for c in (state.get("cases") or []) if c.get("id") in hold_ids]
    if not hold:
        raise RuntimeError(f"run {run_id} 没有 holdout 题，无法复核")

    p = dict(state.get("params") or {})
    reps = max(1, int(reps))
    # role_id 是从 blueprint 推出的只读属性，给了 blueprint 就自然对上
    run = Run(run_id=f"{run_id}-reholdout", role=str(state.get("role") or ""), params=p)
    run.blueprint = state.get("blueprint") or {}
    run.cases = hold
    run.phase = "holdout"
    session = Session(
        api_key,
        p.get("model"),
        concurrency=p.get("concurrency"),
        budget_tokens=p.get("budget_tokens"),
        budget_seconds=p.get("budget_seconds"),
    )
    run.session = session
    champ_arm = {
        "id": champ.get("id") or "champion",
        "sig": champ.get("sig") or "champion",
        "system": champ["system"],
        "choice": champ.get("choice") or {},
        "labels": champ.get("labels") or {},
    }
    base_arm = genes.baseline_variant()
    t0 = time.monotonic()
    got = await eval_batch(
        run, session, [champ_arm, base_arm], hold, reps, shadow_judge=False
    )
    if run.eval_failed:
        # 关键防线：部分失败会静默降级成「只剩缓存那一次重复」，算出来的区间看着更硬其实是假的。
        # 宁可不写，也不能让半截数据混进证据链（额度耗尽 / 限流时就会走到这）。
        raise RuntimeError(
            f"复核失败 {run.eval_failed}/{run.eval_total} 条，不写结果（避免把半截采样当证据）："
            + "；".join(run.logs[-3:])
        )
    champ_h = aggregate(got[champ_arm["id"]], run.blueprint)
    base_h = aggregate(got[base_arm["id"]], run.blueprint)
    prev = ((state.get("holdout") or {}).get("delta_weighted"))
    out = {
        "schema": "yiagent.rolefactory.reholdout/1",
        "run_id": run_id,
        "role": state.get("role"),
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "cases": sorted(hold_ids),
        "reps": reps,
        # 复核复用缓存的回答，但用**当时**的打分代码。若原 run 是旧口径打的，
        # 这份 holdout 就与它的 train 分不同尺 —— 必须记下来，否则无从察觉。
        "scorer_version": objective.SCORER_VERSION,
        "previous": {
            "reps": (state.get("holdout") or {}).get("reps") or 1,
            "delta_weighted": prev,
            "scorer_version": (state.get("scoring") or {}).get("scorer_version"),
        },
        "champion": champ_h,
        "baseline": base_h,
        "delta_weighted": (
            round((champ_h.get("weighted") or 0) - (base_h.get("weighted") or 0), 2)
            if champ_h.get("weighted") is not None and base_h.get("weighted") is not None
            else None
        ),
        "paired": paired_delta(champ_h, base_h),
        "evals": {"done": run.eval_done, "failed": run.eval_failed, "total": run.eval_total},
        "seconds": round(time.monotonic() - t0, 1),
        "tokens": session.meter.total_tokens,
        # 复核最容易踩的坑是「大部分评测静默失败、结果看起来跟原来一样」，所以把日志带出来
        "logs": run.logs[-20:],
        "llm": session.meter.snapshot(),
    }
    store.write_json(d / "reholdout.json", out)
    return out


def scoring_summary(run: Run) -> dict[str, Any]:
    """评分体系说明 + 区分度实测：客观分与影子裁判分各自的分布跨度。"""
    mode = str(run.params.get("scoring_mode") or "judge")
    check_types: dict[str, dict[str, float]] = {}
    for c in run.cases:
        for chk in c.get("checks") or []:
            row = check_types.setdefault(chk["type"], {"count": 0, "weight": 0.0})
            row["count"] += 1
            row["weight"] += float(chk.get("weight") or 0)

    obj_vals: list[float] = []
    judge_vals: list[float] = []
    for src in (run.baseline, run.all_weak, run.champion):
        if src.get("weighted") is not None:
            obj_vals.append(float(src["weighted"]))
        if src.get("judge_shadow") is not None:
            judge_vals.append(float(src["judge_shadow"]))
    variant_vals = [
        v["weighted"] for g in run.generations for v in g.get("variants") or [] if v.get("weighted") is not None
    ]

    def spread(vals: list[float]) -> dict[str, Any]:
        if not vals:
            return {"n": 0}
        return {
            "n": len(vals),
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "spread": round(max(vals) - min(vals), 2),
            "std": round(statistics.pstdev(vals), 2) if len(vals) > 1 else 0.0,
        }

    return {
        "mode": mode,
        # 分数只在同一打分口径版本内可比。写进报告，跨版本对比时才有据可查。
        "scorer_version": objective.SCORER_VERSION if mode == "objective" else None,
        "how": (
            "客观：每题自带可程序校验的断言（数值/必含/禁含/回问/条数/结论先行），"
            "纯 Python 打分，同一回答任何时候复算同分；LLM 只负责出题与作答，不参与判分。"
            if mode == "objective"
            else "主观：LLM 裁判按题目 rubric 逐项打分。"
        ),
        "check_types": {k: {"count": int(v["count"]), "weight_sum": round(v["weight"], 1)} for k, v in sorted(check_types.items())},
        "verified_cases": sum(1 for c in run.cases if (c.get("verify") or {}).get("passed")),
        "objective_spread_arms": spread(obj_vals),
        "objective_spread_variants": spread(variant_vals),
        "judge_shadow_spread_arms": spread(judge_vals),
        "note": (
            "objective_spread_* 与 judge_shadow_spread_* 放在一起看：跨度越大说明该口径越能拉开差距。"
        ),
    }


def parallel_profile(run: Run, llm: dict[str, Any], wall: float) -> dict[str, Any]:
    """并发画像：真实在跑并发 = API 占用秒 / 墙钟秒（排队时间已剔除）。

    - `effective_parallel` 贴近 `concurrency_cap` → 闸门是瓶颈，可加并发；
    - 远低于上限 → 瓶颈在批次结构（barrier / 长尾），加并发无用。
    """
    api_s = float(llm.get("api_seconds_sum") or 0.0)
    queue_s = float(llm.get("queue_seconds_sum") or 0.0)
    cap = int((run.session.concurrency if run.session else SETTINGS.concurrency) or 1)
    eff = round(api_s / wall, 2) if wall > 0 else None
    return {
        "concurrency_cap": cap,
        "effective_parallel": eff,
        "utilization_vs_cap": round(eff / cap, 3) if eff is not None and cap else None,
        "inflight_peak": llm.get("inflight_peak"),
        "api_seconds_sum": round(api_s, 1),
        "queue_seconds_sum": round(queue_s, 1),
        "queue_share": round(queue_s / (api_s + queue_s), 3) if (api_s + queue_s) > 0 else None,
        "serial_seconds_equivalent": round(api_s, 1),
        "speedup_vs_serial": round(api_s / wall, 2) if wall > 0 else None,
        "hedges": llm.get("hedges"),
        "hedge_wins": llm.get("hedge_wins"),
        "latency": {
            "p50": llm.get("latency_p50"),
            "p90": llm.get("latency_p90"),
            "p99": llm.get("latency_p99"),
            "max": llm.get("latency_max"),
        },
        "note": (
            "排队秒数不计入 API 秒数；hedges 为长尾补发次数，hedge_wins 为补发先到的次数"
            "（被丢弃的那份仍消耗了服务端 token，未计入本地 tokens）。"
        ),
    }


def write_report(run: Run) -> None:
    s = run.session
    llm = s.meter.snapshot() if s else {}
    wall = s.wall if s else 0.0
    champ = run.champion or {}
    base = run.baseline or {}
    delta = (
        round((champ.get("weighted") or 0) - (base.get("weighted") or 0), 2)
        if champ.get("weighted") is not None and base.get("weighted") is not None
        else None
    )
    report = {
        "run_id": run.run_id,
        "role": run.role,
        "role_id": run.role_id,
        "status": run.status,
        "params": run.params,
        "created_at": run.created_at,
        "wall_seconds": round(wall, 1),
        "performance": {
            "llm": llm,
            "evals": {"done": run.eval_done, "failed": run.eval_failed, "total": run.eval_total},
            "api_calls_per_second": round(llm.get("api_calls", 0) / wall, 2) if wall > 0 else None,
            "evals_per_minute": round(run.eval_done / wall * 60, 1) if wall > 0 else None,
            "tokens_per_eval": round(llm.get("total_tokens", 0) / run.eval_done) if run.eval_done else None,
            "phase_seconds": run.phase_seconds,
            "parallel": parallel_profile(run, llm, wall),
        },
        "blueprint": run.blueprint,
        "anchors": run.anchors,
        "suite": {
            "count": len(run.cases),
            "train": run.train_ids,
            "holdout": run.holdout_ids,
            "path": f"case/role/{run.role_id}/testcases.jsonl",
        },
        "bank": run.bank,
        "scoring": scoring_summary(run),
        "scores": {
            "baseline_no_genes": base,
            "all_weak_genes": run.all_weak,
            "champion_train": champ,
            "delta_train_weighted": delta,
            "paired_train": paired_delta(champ, base) if champ and base else {},
            "holdout": run.holdout,
        },
        "generations": run.generations,
        "champion_genome": {
            "system": champ.get("system"),
            "choice": champ.get("choice"),
            "labels": champ.get("labels"),
        },
        "caveats": (
            [
                "打分为程序化断言，可复算；但题目与标准答案由 LLM 生成，已用 computation 重算自校，仍可能存在设计偏差。",
                "断言里的关键词匹配可被堆词部分蒙到；用 numeric（权重≥35）与 must_not_include 压制，不能完全排除。",
                "must_not_include 自 2026-08-11 起区分「主张错误说法」与「引用它并否掉」"
                "（同句、词前 40 字内有否定线索才免扣）；此前的 run 未享此修正，"
                "其分数含约 2 分/条的误扣噪声，跨日期对比请先跑 tools/rescore.py 对齐口径。",
                "benchmark 仅作题型/口径锚点，非原题实跑（DABstep/DABench 需数据文件与代码沙箱）。",
                "样本量小（题数×重复数），分差需配合 paired 明细与 std 一起读，不做显著性声明。",
            ]
            if str(run.params.get("scoring_mode")) == "objective"
            else [
                "裁判为同族模型（k3）自评，存在同源偏差；跨模型交叉裁判未做。",
                "题目由 LLM 生成、benchmark 仅作题型/口径锚点，非原题实跑（DABstep/DABench 需数据文件与代码沙箱）。",
                "样本量小（题数×重复数），分差需配合 paired 明细与 std 一起读，不做显著性声明。",
            ]
        ),
    }
    if (llm.get("hedges") or 0) > 0:
        report["caveats"].append(
            f"长尾对冲：补发 {llm['hedges']} 次、其中 {llm.get('hedge_wins') or 0} 次由补发先返回；"
            "被丢弃那份的服务端 token 未计入本地计量，实际用量略高于报告值。"
        )
    if run.eval_failed:
        # 单点失败不拖垮整批（设计如此），但失败的那几条不会进 aggregate ——
        # 分数是从更少的样本上算出来的，这件事必须写在脸上，不能只留一个计数。
        rate = run.eval_failed / run.eval_total if run.eval_total else 0
        report["caveats"].insert(
            0,
            f"⚠ 有 {run.eval_failed}/{run.eval_total} 条评测失败（{rate:.0%}，多见于额度耗尽或限流）："
            "失败条目未计入均值，相关分数的实际样本量小于名义值，分差与区间都要打折看。",
        )
    store.write_json(store.run_dir(run.run_id) / "report.json", report)


# ------------------------------------------------------------------ 管理器


class Manager:
    def __init__(self) -> None:
        self.runs: dict[str, Run] = {}

    def start(self, role: str, params: dict[str, Any], api_key: str) -> Run:
        run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        run = Run(run_id=run_id, role=role.strip(), params=params)
        self.runs[run_id] = run
        run.log(f"启动：角色「{run.role}」参数={params}")
        run.task = asyncio.create_task(execute(run, api_key))
        return run

    def get(self, run_id: str) -> Run | None:
        return self.runs.get(run_id)

    def abort(self, run_id: str) -> bool:
        run = self.runs.get(run_id)
        if not run:
            return False
        if run.session:
            run.session.abort("manual")
        run.status = "aborting"
        return True


MANAGER = Manager()
