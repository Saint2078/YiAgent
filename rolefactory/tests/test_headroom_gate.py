"""筛题门槛 `roles.drop_saturated` 的护栏测试（离线，不发任何调用）。

这道门槛会**删题**，所以护栏比功能更重要：删多了会把维度删空、把题组删干，
而这两件事都不会报错，只会让后面的结论建立在残缺题组上。

用法：python -m tests.test_headroom_gate
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import roles  # noqa: E402


def case(cid: str, dim: str = "d1") -> dict:
    return {"id": cid, "dimension_key": dim, "dimension": dim}


class DropSaturatedTests(unittest.TestCase):
    def test_drops_only_above_ceiling(self):
        cs = [case("a"), case("b"), case("c"), case("d")]
        scores = {"a": 100.0, "b": 60.0, "c": 70.0, "d": 80.0}
        keep, dropped = roles.drop_saturated(cs, scores, ceiling=90.0)
        self.assertEqual([c["id"] for c in dropped], ["a"])
        self.assertEqual([c["id"] for c in keep], ["b", "c", "d"])

    def test_never_drops_more_than_half_a_dimension(self):
        # 一整维全是满分题：不许清空，只准扔一半（且扔最容易的）
        cs = [case(x) for x in "abcd"]
        scores = {"a": 100.0, "b": 99.0, "c": 98.0, "d": 97.0}
        keep, dropped = roles.drop_saturated(cs, scores, ceiling=90.0)
        self.assertEqual(len(dropped), 2, "扔超过了一半")
        self.assertEqual(len(keep), 2)
        # 留下的必须是**较难**的那两道（分数低的）
        self.assertEqual(sorted(c["id"] for c in keep), ["c", "d"])

    def test_two_case_dimension_keeps_one(self):
        cs = [case("a"), case("b")]
        keep, dropped = roles.drop_saturated(cs, {"a": 100.0, "b": 100.0}, ceiling=90.0)
        self.assertEqual(len(keep), 1)
        self.assertEqual(len(dropped), 1)

    def test_single_case_dimension_never_emptied(self):
        # 2 题 × 0.5 = 1 可扔；1 题 × 0.5 向下取整 = 0 可扔 → 单题维度必然留下
        keep, dropped = roles.drop_saturated([case("a")], {"a": 100.0}, ceiling=90.0)
        self.assertEqual([c["id"] for c in keep], ["a"])
        self.assertEqual(dropped, [])

    def test_stratification_preserved_across_dimensions(self):
        cs = [case("a1", "d1"), case("a2", "d1"), case("b1", "d2"), case("b2", "d2")]
        scores = {"a1": 100.0, "a2": 100.0, "b1": 50.0, "b2": 55.0}
        keep, _ = roles.drop_saturated(cs, scores, ceiling=90.0)
        dims = {c["dimension_key"] for c in keep}
        self.assertEqual(dims, {"d1", "d2"}, "有维度被整个扔空")

    def test_missing_score_is_treated_as_hardest(self):
        # 探针失败的题按最难处理：宁可留下钝题，也不能因为"没探到分"而误杀
        cs = [case("a"), case("b")]
        keep, dropped = roles.drop_saturated(cs, {"b": 100.0}, ceiling=90.0)
        self.assertEqual([c["id"] for c in keep], ["a"])
        self.assertEqual([c["id"] for c in dropped], ["b"])

    def test_ceiling_100_disables_gate(self):
        cs = [case("a"), case("b")]
        keep, dropped = roles.drop_saturated(cs, {"a": 100.0, "b": 100.0}, ceiling=100.0)
        self.assertEqual(len(keep), 2)
        self.assertEqual(dropped, [])

    def test_no_case_is_lost_or_duplicated(self):
        cs = [case(f"c{i}", f"d{i % 3}") for i in range(12)]
        scores = {f"c{i}": float(50 + i * 5) for i in range(12)}
        keep, dropped = roles.drop_saturated(cs, scores, ceiling=90.0)
        ids = [c["id"] for c in keep] + [c["id"] for c in dropped]
        self.assertEqual(sorted(ids), sorted(c["id"] for c in cs))
        self.assertEqual(len(set(ids)), len(cs), "有题被重复计入")


class ReserveTests(unittest.TestCase):
    """余量护栏：筛题**不许把 holdout 削小**。

    这条是空跑在真实题组上抓出来的：没有它时，`split_holdout` 每维只从尾部取
    `per_dim` 道且必须给 train 留 1 道，于是某维只剩 1 道就贡献 0 道 holdout ——
    实测 Product 的 holdout 从 5 道掉到 1 道。拿天花板问题换样本量问题，净亏。
    """

    def _suite(self, per_dim: int, dims: int = 3) -> list[dict]:
        return [case(f"d{d}c{i}", f"d{d}") for d in range(dims) for i in range(per_dim)]

    def test_no_op_when_no_slack(self):
        # 每维 2 道、holdout_per_dim=1 → 需保留 2 道 → 没有余量，必须什么都不扔
        cs = self._suite(per_dim=2)
        scores = {c["id"]: 100.0 for c in cs}
        keep, dropped = roles.drop_saturated(cs, scores, ceiling=90.0, reserve_per_dim=2)
        self.assertEqual(dropped, [], "没有余量时仍然扔了题")
        self.assertEqual(len(keep), len(cs))

    def test_drops_only_the_slack(self):
        # 每维 8 道、需保留 5 道 → 余量 3；半数上限 4 → 取小 = 3
        cs = self._suite(per_dim=8)
        scores = {c["id"]: 100.0 for c in cs}
        keep, dropped = roles.drop_saturated(cs, scores, ceiling=90.0, reserve_per_dim=5)
        self.assertEqual(len(dropped), 3 * 3, "每维应恰好扔 3 道")
        for d in range(3):
            left = [c for c in keep if c["dimension_key"] == f"d{d}"]
            self.assertEqual(len(left), 5)

    def test_holdout_never_shrinks(self):
        """真正要守的不变量：筛完之后 holdout 题量不许下降。"""
        for per_dim in (2, 4, 6, 8, 12):
            for hpd in (1, 2, 4):
                cs = self._suite(per_dim=per_dim)
                # 一半的题贴天花板，另一半正常
                scores = {c["id"]: (100.0 if i % 2 else 60.0) for i, c in enumerate(cs)}
                _, hold_before = roles.split_holdout(cs, per_dim=hpd)
                keep, _ = roles.drop_saturated(
                    cs, scores, ceiling=90.0, reserve_per_dim=1 + hpd
                )
                _, hold_after = roles.split_holdout(keep, per_dim=hpd)
                self.assertGreaterEqual(
                    len(hold_after), len(hold_before),
                    f"per_dim={per_dim} holdout_per_dim={hpd}："
                    f"holdout 从 {len(hold_before)} 掉到 {len(hold_after)}",
                )


class TrainCapTests(unittest.TestCase):
    """封顶模式：train 封顶、余量全给 holdout，于是加题不再牵动进化成本。

    默认模式下 train = `per_dim − holdout_per_dim`，多出的题全涌进 train，
    而 train 单价是 holdout 的 15 倍（30 次 vs 2 次评测）。筛题门槛要余量就得多出题，
    于是"门槛白配"那条分支反而最贵。封顶把这个耦合断开。
    """

    def _suite(self, per_dim: int, dims: int = 6) -> list[dict]:
        return [case(f"d{d}c{i:02d}", f"d{d}") for d in range(dims) for i in range(per_dim)]

    def test_train_size_is_capped_regardless_of_case_count(self):
        for per_dim in (4, 8, 14, 20):
            cs = self._suite(per_dim)
            train, hold = roles.split_holdout(cs, per_dim=99, train_per_dim=1)
            self.assertEqual(len(train), 6, f"per_dim={per_dim} 时 train 没被封住")
            self.assertEqual(len(hold), len(cs) - 6, "余量没有全部进 holdout")

    def test_surplus_goes_to_holdout_not_train(self):
        # 出题从 8 加到 14：holdout 应涨 36 道，train 一道不涨
        t1, h1 = roles.split_holdout(self._suite(8), per_dim=99, train_per_dim=1)
        t2, h2 = roles.split_holdout(self._suite(14), per_dim=99, train_per_dim=1)
        self.assertEqual(len(t1), len(t2), "加题把成本加到 train 上了")
        self.assertEqual(len(h2) - len(h1), 36)

    def test_default_mode_unchanged(self):
        """封顶模式是新增分支，不许动默认行为。"""
        cs = self._suite(8)
        base = roles.split_holdout(cs, per_dim=7)
        again = roles.split_holdout(cs, per_dim=7, train_per_dim=0)
        self.assertEqual([c["id"] for c in base[0]], [c["id"] for c in again[0]])
        self.assertEqual([c["id"] for c in base[1]], [c["id"] for c in again[1]])

    def test_train_never_empty_when_cases_are_scarce(self):
        # 某维只有 1 道题：宁可 holdout 空着，也不能让 train 空着
        cs = [case("a", "d1")]
        train, hold = roles.split_holdout(cs, per_dim=99, train_per_dim=1)
        self.assertEqual(len(train), 1)
        self.assertEqual(hold, [])

    def test_no_case_lost_or_duplicated(self):
        cs = self._suite(14)
        train, hold = roles.split_holdout(cs, per_dim=99, train_per_dim=2)
        ids = [c["id"] for c in train] + [c["id"] for c in hold]
        self.assertEqual(sorted(ids), sorted(c["id"] for c in cs))
        self.assertEqual(len(set(ids)), len(cs))

    def test_gate_capacity_no_longer_costs_evolution(self):
        """把成本算出来：封顶后可扔额度与进化评测**脱钩**。

        这条是整件事的目的，所以直接把两种配法的账并排断言，而不是只测行为。
        """
        dims, variants, gens, arms, hreps = 6, 10, 3, 2, 1

        def cost(per_dim: int, hpd: int, tpd: int, dropped_per_dim: int) -> tuple[int, int, int]:
            cs = self._suite(per_dim, dims)
            # 模拟筛题：每维扔掉 dropped_per_dim 道
            drop_ids = {
                f"d{d}c{i:02d}" for d in range(dims)
                for i in range(per_dim - dropped_per_dim, per_dim)
            }
            kept = [c for c in cs if c["id"] not in drop_ids]
            train, hold = roles.split_holdout(kept, per_dim=hpd, train_per_dim=tpd)
            return len(train) * variants * gens, len(hold) * arms * hreps, len(hold)

        # 默认模式：门槛"白配"（一道没扔）时进化成本翻 6 倍
        ev_worst, _, _ = cost(12, 6, 0, 0)
        ev_best, _, _ = cost(12, 6, 0, 5)
        self.assertEqual(ev_worst, 1080)
        self.assertEqual(ev_best, 180)

        # 封顶模式：扔多少都不影响进化成本
        for d in (0, 4, 8):
            ev, _, n_hold = cost(16, 99, 1, d)
            self.assertEqual(ev, 180, f"扔 {d} 道/维时进化成本变了")
            # 封顶模式下被扔的题直接从 holdout 里出（余量全归 holdout），
            # 所以出题量必须够大，扔满之后仍不低于原配法的 42 道 ——
            # per_dim=14 在扔满时只剩 36 道，是这条断言逼出来的。
            self.assertGreaterEqual(n_hold, 42, f"扔 {d} 道/维后 holdout 低于原配法的 42 道")

    def test_case_budget_must_cover_max_drop(self):
        """出题量的下限是算出来的，不是猜的：扔满之后仍要留住目标 holdout 题量。

        需求：`per_dim ≥ 目标holdout/维 + 可扔/维 + train封顶`。
        取目标 7 道/维（42 道）、train 封顶 1 → per_dim=15 是下限，14 不够。
        """
        dims = 6
        for per_dim, ok in ((14, False), (15, True), (16, True)):
            cs = self._suite(per_dim, dims)
            budget = min(per_dim // 2, per_dim - 2)  # reserve = train 1 + holdout 1
            drop_ids = {
                f"d{d}c{i:02d}" for d in range(dims)
                for i in range(per_dim - budget, per_dim)
            }
            kept = [c for c in cs if c["id"] not in drop_ids]
            _, hold = roles.split_holdout(kept, per_dim=99, train_per_dim=1)
            self.assertEqual(
                len(hold) >= 42, ok,
                f"per_dim={per_dim} 扔满后 holdout={len(hold)}，与预期（≥42 应为 {ok}）不符",
            )


class ProbeIndependenceTests(unittest.TestCase):
    """探针必须是**独立采样**，否则筛题与算分共用一次测量 → Δ 被选择偏差抬高。"""

    def test_probe_rep_differs_from_scoring_reps(self):
        from app import pipeline

        self.assertLess(pipeline.PROBE_REP, 0,
                        "探针 rep 必须落在评分用的 0..n 之外")

    def test_probe_salt_differs_from_scoring_salt(self):
        # 缓存键是 sig|case|rep{rep}；探针与 rep0 必须产生不同的键
        from app import pipeline

        probe = f"baseline|case1|rep{pipeline.PROBE_REP}"
        for r in range(8):
            self.assertNotEqual(probe, f"baseline|case1|rep{r}")

class ProbeBookkeepingTests(unittest.TestCase):
    """探针的记账：真跑一遍 `probe_baseline`（judge 打桩，不发请求），看它到底写了什么。

    这里刻意不用"读源码找字符串"那种测法 —— 第一版就是那么写的，结果被注释里
    解释「绝不写进 results.jsonl」的那句话本身给判失败了。**测行为，别测措辞。**
    """

    def _run_probe(self, scores, fail_ids=()):
        import asyncio
        import shutil

        from app import judge, pipeline, store

        cases = [case(cid) for cid in scores]
        rid = "test-probe-" + str(abs(hash(tuple(scores.items()))) % 10**8)
        d = store.run_dir(rid)
        shutil.rmtree(d, ignore_errors=True)

        run = pipeline.Run(run_id=rid, role="测试", params={"scoring_mode": "objective"})

        async def fake_eval_one(session, variant, c, *, rep, mode="judge", shadow_judge=False):
            self.assertEqual(rep, pipeline.PROBE_REP, "探针没用独立的 rep")
            if c["id"] in fail_ids:
                raise RuntimeError("boom")
            return {"variant": variant["id"], "case": c["id"], "score": scores[c["id"]]}

        orig = judge.eval_one
        judge.eval_one = fake_eval_one
        try:
            out = asyncio.run(pipeline.probe_baseline(run, None, cases))
        finally:
            judge.eval_one = orig
        return run, out, d

    def test_probe_writes_probe_json_and_not_results_jsonl(self):
        """探针数据**绝不能**进 results.jsonl —— 这条比它看起来重要得多。

        `variance_decomp` / `case_outliers` / `check_contrib` 都按 (variant, case) 读
        `results.jsonl`，而探针的 variant 同样是 baseline。混进去就会被当成基线臂的
        又一次重复，于是"用于选题的那次测量"悄悄流进"用于算分的那批数据"——
        正是这套设计要避开的选择偏差，而且**不会报错**。
        """
        import json as _json
        import shutil

        run, out, d = self._run_probe({"a": 60.0, "b": 100.0})
        try:
            self.assertFalse(
                (d / "results.jsonl").exists(),
                "探针把数据写进了 results.jsonl，会污染方差/离群工具",
            )
            p = d / "probe.json"
            self.assertTrue(p.is_file(), "探针分数没单独落盘，门槛的决策就不可复查")
            saved = _json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(saved["rep"], -1)
            self.assertEqual(saved["scores"], {"a": 60.0, "b": 100.0})
            self.assertEqual(out, {"a": 60.0, "b": 100.0})
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_all_probed_cases_are_recorded_not_only_dropped(self):
        """留下来的题为什么留，也要能复查 —— 只记被扔的等于只留半张账。"""
        import shutil

        run, _, d = self._run_probe({"a": 60.0, "b": 100.0, "c": 70.0})
        try:
            self.assertEqual(set(run.probe_scores), {"a", "b", "c"})
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_probe_failure_counted_separately_from_eval_failed(self):
        """探针失败不许计进 `eval_failed`：那会误触"复核失败就不写结果"的防线。"""
        import shutil

        run, out, d = self._run_probe({"a": 60.0, "b": 100.0}, fail_ids={"b"})
        try:
            self.assertEqual(run.probe_failed, 1)
            self.assertEqual(run.probe_done, 1)
            self.assertEqual(run.eval_failed, 0, "探针失败被记进了 eval_failed")
            self.assertEqual(run.eval_done, 0)
            # 探不到分的题不进 scores → drop_saturated 按「最难」处理 → 保留（不误杀）
            self.assertNotIn("b", out)
            keep, dropped = roles.drop_saturated(
                [case("a"), case("b")], out, ceiling=90.0, reserve_per_dim=1
            )
            self.assertIn("b", [c["id"] for c in keep])
            self.assertEqual(dropped, [])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_probe_counts_land_in_cost_denominator(self):
        """探针消耗 token 却不参与冠军对比：只算 eval_done 会让 tokens_per_eval 凭空变大。

        直接按报告里的算法核对：96 次探针 + 180 次评测、共 276k token，
        分母漏掉探针就会把 1000 报成 1533（高估 53%）。
        """
        toks, evals, probes = 276_000, 180, 96
        wrong = round(toks / evals)
        right = round(toks / (evals + probes))
        self.assertEqual(wrong, 1533)
        self.assertEqual(right, 1000)

        import inspect

        from app import pipeline

        self.assertIn(
            "run.eval_done + run.probe_done",
            inspect.getsource(pipeline.write_report),
            "单位成本的分母没算上探针，tokens_per_eval 会被高估",
        )


class DilutionVsDragTests(unittest.TestCase):
    """`ceiling_mech.classify` 的判读必须**跟着数据走**。

    这组测试的由来：那段判读的第一版写死在 print 里，于是在
    高基线组 Δ=−6.27、其余组 Δ=+5.21 的实测数据上照样印出
    「高基线组的 |Δ| 明显小于其余组」—— 6.27 明显大于 5.21，一句假话，而且不报错。
    今晚修的就是这一类，所以自己造的这个必须也钉住。
    """

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
        import ceiling_mech

        self.cm = ceiling_mech

    def test_near_zero_high_group_is_dilution(self):
        v = self.cm.classify(mh=0.2, ml=8.0, sh=1.0, sl=10.0)
        self.assertEqual(v["mechanism"], "dilution")

    def test_systematically_negative_high_group_is_drag(self):
        # 实测口径：高基线组 −6.27、其余 +5.21 → 拖拽，不是稀释
        v = self.cm.classify(mh=-6.27, ml=5.21, sh=7.15, sl=20.03)
        self.assertEqual(v["mechanism"], "drag")
        self.assertEqual(v["drag_toward"], "negative")

    def test_low_variance_high_group_falsifies_power_claim(self):
        """高基线组方差更小 → 扔掉会抬高 sd → 「扔了更准」被证伪。"""
        v = self.cm.classify(mh=-6.27, ml=5.21, sh=7.15, sl=20.03)
        self.assertEqual(v["sd_effect"], "drop_raises_sd")
        self.assertEqual(v["power_claim"], "falsified")

    def test_high_variance_high_group_does_not_falsify(self):
        v = self.cm.classify(mh=-6.0, ml=5.0, sh=30.0, sl=10.0)
        self.assertEqual(v["power_claim"], "not_falsified")

    def test_verdict_is_not_constant(self):
        """反向数据必须给出反向结论 —— 否则又是一句写死的话。"""
        a = self.cm.classify(mh=-6.0, ml=5.0, sh=7.0, sl=20.0)
        b = self.cm.classify(mh=6.0, ml=-5.0, sh=20.0, sl=7.0)
        self.assertNotEqual(a["drag_toward"], b["drag_toward"])
        self.assertNotEqual(a["sd_effect"], b["sd_effect"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
