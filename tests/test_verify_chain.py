"""证据链对账器自身的测试：它必须**抓得到**断链。

一个永远返回 ok 的验证器比没有验证器更糟 —— 它会让人以为核过了。
所以这里逐项把真实产物复制到临时目录、动手改坏，再断言对账器报出对应问题。

全程离线，不动仓库里的真实产物（只读复制）。
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEAT = "PM"


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_chain", REPO / "scripts" / "verify_chain.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class ChainVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vc = _load_module()
        src = cls.vc.DEVELOP / SEAT / "genome.json"
        if not src.is_file():
            raise unittest.SkipTest("本机没有落盘产物；跑 scripts/build_agent_entities.py 后生效")

    def setUp(self):
        """把 PM 一席的五件产物复制进临时树，并把对账器的路径指过去。"""
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        vc = self.vc

        self.develop = self.tmp / "Develop"
        self.banks = self.tmp / "banks"
        self.runs = self.tmp / "runs"
        (self.develop / SEAT).mkdir(parents=True)
        self.banks.mkdir()

        for name in ("genome.json", "vector.json"):
            shutil.copy(vc.DEVELOP / SEAT / name, self.develop / SEAT / name)
        shutil.copy(vc.BANKS / f"{SEAT}.bank.json", self.banks / f"{SEAT}.bank.json")

        run_id = json.loads((self.develop / SEAT / "genome.json").read_text(encoding="utf-8"))[
            "source"
        ]["run_id"]
        (self.runs / run_id).mkdir(parents=True)
        for name in ("genome_card.json", "report.json"):
            shutil.copy(vc.RUNS / run_id / name, self.runs / run_id / name)

        self._orig = (vc.DEVELOP, vc.BANKS, vc.RUNS)
        vc.DEVELOP, vc.BANKS, vc.RUNS = self.develop, self.banks, self.runs
        self.addCleanup(self._restore)

    def _restore(self):
        self.vc.DEVELOP, self.vc.BANKS, self.vc.RUNS = self._orig

    # ---- 工具 ----
    def _patch(self, path: Path, fn):
        obj = json.loads(path.read_text(encoding="utf-8"))
        fn(obj)
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    def _run(self) -> dict:
        return self.vc.check_seat(SEAT)

    def _assert_catches(self, keyword: str, result: dict):
        self.assertFalse(result["ok"], "改坏了却报 ok")
        self.assertTrue(
            any(keyword in p for p in result["problems"]),
            f"没抓到「{keyword}」，实际报的是 {result['problems']}",
        )

    # ---- 先确认基线是干净的，否则后面的断言没有意义 ----
    def test_untampered_passes(self):
        r = self._run()
        self.assertTrue(r["ok"], f"未改动却报问题：{r['problems']}")

    def test_catches_edited_slot_text(self):
        # 最隐蔽的一种：基因组文本被手改，等位 id 与哈希都还在
        gp = self.develop / SEAT / "genome.json"
        self._patch(gp, lambda g: g["slots"]["G1"].update(text=g["slots"]["G1"]["text"] + "（手改）"))
        self._assert_catches("文本哈希不一致", self._run())

    def test_catches_hash_mismatch(self):
        gp = self.develop / SEAT / "genome.json"
        self._patch(gp, lambda g: g["source"].update(genome_hash="0" * 64))
        self._assert_catches("gene hash 不一致", self._run())

    def test_catches_verdict_drift(self):
        # 载体上的判定被改成「已证明」，而基因组仍是「判不了」
        vp = self.develop / SEAT / "vector.json"
        self._patch(
            vp,
            lambda v: v["markers"]["provenance"].update(
                verdict={"generalizes": True, "label": "已证明"}
            ),
        )
        self._assert_catches("判定不一致", self._run())

    def test_catches_overclaim(self):
        # 判定仍是「判不了」，但 claim 改成宣称更强 —— 这正是整套门禁要防的事
        vp = self.develop / SEAT / "vector.json"
        self._patch(vp, lambda v: v["markers"]["provenance"].update(claim="本席基因比无基因更强"))
        self._assert_catches("未证明泛化却宣称更强", self._run())

    def test_catches_contrast_inheriting_record(self):
        bp = self.banks / f"{SEAT}.bank.json"

        def strip(b):
            for v in b["variants"]:
                if v["id"].endswith(".all_weak"):
                    v.pop("provenance", None)

        self._patch(bp, strip)
        self._assert_catches("全弱对照没自带血统", self._run())

    def test_catches_same_id_different_text(self):
        # bank 与基因组的等位 id 一致但内容不同 —— 装出来的 Agent 带的不是被鉴定的那段文本
        bp = self.banks / f"{SEAT}.bank.json"
        champ_g1 = json.loads((self.develop / SEAT / "genome.json").read_text(encoding="utf-8"))[
            "slots"
        ]["G1"]["allele_id"]

        def tamper(b):
            for a in b["alleles"]["G1"]:
                if a["id"] == champ_g1:
                    a["text"] = a["text"] + "（被替换）"

        self._patch(bp, tamper)
        self._assert_catches("bank 与基因组不同", self._run())

    def test_catches_absolute_source_path(self):
        vp = self.develop / SEAT / "vector.json"
        self._patch(vp, lambda v: v["markers"]["source"].update(path="/repo/x/bank.json"))
        self._assert_catches("绝对路径", self._run())

    def test_catches_missing_evidence(self):
        run_id = json.loads((self.develop / SEAT / "genome.json").read_text(encoding="utf-8"))[
            "source"
        ]["run_id"]
        (self.runs / run_id / "report.json").unlink()
        self._assert_catches("缺 report.json", self._run())

    # ---- 数字同源（第 7 条）：这两例是真实踩过的坑，不是假想 ----

    def test_catches_reps_from_other_source(self):
        """Δ 来自 reps=3 的复核、reps 却标 1 —— 哈希与判定都对，只有这一栏矛盾。

        实测发生过：导出血统时 Δ 从卡片取、reps 从原报告取。前六条检查全绿。
        """
        vp = self.develop / SEAT / "vector.json"
        self._patch(vp, lambda v: v["markers"]["provenance"]["holdout"].update(reps=1))
        r = self._run()
        self._assert_catches("holdout.reps", r)
        self.assertTrue(any("不同源" in p for p in r["problems"]))

    def test_catches_delta_from_other_source(self):
        vp = self.develop / SEAT / "vector.json"
        self._patch(
            vp, lambda v: v["markers"]["provenance"]["holdout"].update(delta_weighted=99.9)
        )
        self._assert_catches("holdout.delta_weighted", self._run())

    def test_catches_card_not_regenerated_after_reholdout(self):
        """复核落盘了、卡片没重生成 —— 下游拿到的全是复核前的数，且零报错。"""
        run_id = json.loads((self.develop / SEAT / "genome.json").read_text(encoding="utf-8"))[
            "source"
        ]["run_id"]
        (self.runs / run_id / "reholdout.json").write_text(
            json.dumps({"reps": 3, "delta_weighted": 7.77,
                        "paired": {"mean_delta": 7.5, "cases": 6}}),
            encoding="utf-8",
        )
        cp = self.runs / run_id / "genome_card.json"
        self._patch(cp, lambda c: c["scores"].update(holdout_source="run"))
        self._assert_catches("卡片仍在用原报告", self._run())


class AllSeatsConsistentTests(unittest.TestCase):
    """六席证据链必须全自洽 —— 把对账从「记得跑一下」变成测试会挂的事。

    注意这只保证证据没被改坏，不代表基因更强（后者看 holdout 区间）。
    """

    def test_all_seats(self):
        vc = _load_module()
        if not (vc.DEVELOP).is_dir():
            self.skipTest("本机没有落盘产物；跑 scripts/build_agent_entities.py 后生效")
        for seat in vc.SEATS:
            with self.subTest(seat=seat):
                r = vc.check_seat(seat)
                self.assertTrue(r["ok"], f"{seat} 证据链断：{r['problems']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
