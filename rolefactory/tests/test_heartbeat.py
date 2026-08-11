"""心跳与健康检查的测试（离线）。

为什么这个也要测：这套东西的**唯一价值**是"没消息时能分清好消息和坏消息"。
它自己判错就比没有更糟 —— 误报两次之后人就不再看告警了，
那时真死了也没人知道。所以三种"心跳停止"必须被区分开：
跑完了 / 死了 / 中途没额度停了。

用法：python -m tests.test_heartbeat
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import heartbeat  # noqa: E402


class BeatTests(unittest.TestCase):
    def setUp(self):
        self.orig = heartbeat.BEAT_PATH
        self.tmp = ROOT / "data" / "_test_heartbeat.json"
        heartbeat.BEAT_PATH = self.tmp
        self.tmp.unlink(missing_ok=True)

    def tearDown(self):
        self.tmp.unlink(missing_ok=True)
        Path(str(self.tmp) + ".tmp").unlink(missing_ok=True)
        heartbeat.BEAT_PATH = self.orig

    def test_beat_writes_state_and_extras(self):
        heartbeat.beat("waiting_quota", probes=3, waited_min=30)
        row = heartbeat.read()
        self.assertEqual(row["state"], "waiting_quota")
        self.assertEqual(row["probes"], 3)
        self.assertIsInstance(row["ts"], float)

    def test_started_ts_survives_later_beats(self):
        """「连续活了多久」要能回答，所以起始时间不能被后续心跳覆盖。"""
        heartbeat.beat("waiting_quota")
        first = heartbeat.read()["started_ts"]
        time.sleep(0.01)
        heartbeat.beat("waiting_quota", probes=2)
        self.assertEqual(heartbeat.read()["started_ts"], first)

    def test_read_returns_none_when_absent(self):
        self.assertIsNone(heartbeat.read())
        self.assertIsNone(heartbeat.age_seconds())

    def test_corrupt_file_does_not_raise(self):
        """读到半个文件也不能抛 —— 仪表坏了不该拖垮被观测的东西。"""
        self.tmp.write_text("{ not json", encoding="utf-8")
        self.assertIsNone(heartbeat.read())

    def test_beat_never_raises(self):
        """写失败必须静默：心跳只是仪表，不是任务。"""
        deep = ROOT / "data" / "_t_beat" / "x.json"
        heartbeat.BEAT_PATH = deep
        litter = ROOT / "data" / "_t_dir.json.tmp"
        try:
            heartbeat.beat("waiting_quota")  # 目录会被创建，这条应当成功
            # 指向一个已存在的**目录** → 原子替换必然失败，用来验"失败也不抛"
            heartbeat.BEAT_PATH = ROOT / "data" / "_t_dir"
            (ROOT / "data" / "_t_dir").mkdir(parents=True, exist_ok=True)
            heartbeat.beat("waiting_quota")
        except Exception as exc:  # noqa: BLE001
            self.fail(f"beat 抛了异常：{type(exc).__name__}: {exc}")
        finally:
            # 测试不该留垃圾在仓里：上一版把 data.json.tmp 落在了 rolefactory/ 根下，
            # 直到 git status 才发现 —— 一个测试制造的未跟踪文件。
            litter.unlink(missing_ok=True)
            deep.unlink(missing_ok=True)
            for d in (ROOT / "data" / "_t_beat", ROOT / "data" / "_t_dir"):
                if d.is_dir():
                    for f in d.iterdir():
                        f.unlink(missing_ok=True)
                    d.rmdir()

    def test_waited_min_is_zero_on_first_probe(self):
        """刚启动不能报"已等 10 分钟"。

        实测第一版就是这样（`waited_min = (n+1)*every//60`，而那次 sleep 还没发生）。
        仪表上的数必须字面为真，否则读它的人会据此判断"等了很久还没恢复"。
        """
        import re

        src = (ROOT / "tools" / "run_reholdout.py").read_text(encoding="utf-8")
        m = re.search(r'beat\(\s*"waiting_quota",\s*probes=([^,]+),\s*waited_min=([^)]+)\)', src)
        self.assertIsNotNone(m, "找不到等额度那处心跳调用")
        # 用求值代替读措辞：n=0（一次都没等过）时 waited_min 必须是 0
        n, every = 0, 600
        self.assertEqual(eval(m.group(2), {}, {"n": n, "every": every}), 0)
        self.assertEqual(eval(m.group(1), {}, {"n": n, "every": every}), 1)

    def test_keep_beating_refreshes_during_long_op(self):
        """长操作期间必须持续心跳，否则正在干活的会被判成死的。"""
        with heartbeat.keep_beating("reholdout_running", every=1, seat="PM"):
            first = heartbeat.read()["ts"]
            time.sleep(1.4)
            later = heartbeat.read()["ts"]
        self.assertGreater(later, first, "长操作期间心跳没有刷新")


class SingletonTests(unittest.TestCase):
    """两个守护同时跑会污染证据且不报错 —— 这条护栏必须真的拦住。"""

    def setUp(self):
        self.orig = heartbeat.LOCK_PATH
        self.tmp = ROOT / "data" / "_test_watch.lock"
        heartbeat.LOCK_PATH = self.tmp
        self.tmp.unlink(missing_ok=True)

    def tearDown(self):
        self.tmp.unlink(missing_ok=True)
        heartbeat.LOCK_PATH = self.orig

    def test_first_instance_gets_lock(self):
        ok, why = heartbeat.acquire_singleton()
        self.assertTrue(ok)
        self.assertIn("取得守护锁", why)

    def test_second_instance_is_refused(self):
        """用别的 pid 写一把新鲜锁，本进程必须被拒。"""
        self.tmp.write_text(json.dumps({
            "pid": 999999, "ts": time.time(), "state": "waiting_quota",
        }), encoding="utf-8")
        ok, why = heartbeat.acquire_singleton()
        self.assertFalse(ok, "第二个实例没被拦住 —— 会和第一个抢同一份额度")
        self.assertIn("999999", why)

    def test_stale_lock_is_taken_over(self):
        """进程被强杀时锁不会自己消失。只看"文件在不在"会永久锁死。"""
        self.tmp.write_text(json.dumps({
            "pid": 999999, "ts": time.time() - 7200, "state": "waiting_quota",
        }), encoding="utf-8")
        ok, _ = heartbeat.acquire_singleton(stale_after=3600)
        self.assertTrue(ok, "陈旧锁没被接管 —— 守护再也起不来了")

    def test_corrupt_lock_is_taken_over(self):
        self.tmp.write_text("{ not json", encoding="utf-8")
        ok, _ = heartbeat.acquire_singleton()
        self.assertTrue(ok)

    def test_release_only_removes_own_lock(self):
        """别把别人的锁删了 —— 那等于把单例保护关掉。"""
        self.tmp.write_text(json.dumps({"pid": 999999, "ts": time.time()}), encoding="utf-8")
        heartbeat.release_lock()
        self.assertTrue(self.tmp.is_file(), "释放锁时删掉了别的进程的锁")


class HealthVerdictTests(unittest.TestCase):
    """三种「心跳停止」必须被分开：跑完了 / 死了 / 没额度停了。"""

    def setUp(self):
        self.tmp = ROOT / "data" / "watch_heartbeat.json"
        self.backup = self.tmp.read_bytes() if self.tmp.is_file() else None

    def tearDown(self):
        if self.backup is not None:
            self.tmp.write_bytes(self.backup)
        else:
            self.tmp.unlink(missing_ok=True)

    def _run(self, state: str, age_s: float) -> tuple[int, str]:
        self.tmp.parent.mkdir(parents=True, exist_ok=True)
        self.tmp.write_text(json.dumps({
            "ts": time.time() - age_s, "iso": "2026-08-11 08:00:00",
            "started_ts": time.time() - age_s - 100,
            "started_iso": "2026-08-11 07:58:00",
            "pid": 1, "state": state, "note": "t",
        }), encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "watch_health.py"), "--every", "600"],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        return r.returncode, (r.stdout or "")

    def test_fresh_beat_is_alive(self):
        rc, out = self._run("waiting_quota", 60)
        self.assertEqual(rc, 0)
        self.assertIn("存活", out)

    def test_stale_beat_is_dead(self):
        rc, out = self._run("waiting_quota", 3600)
        self.assertEqual(rc, 1)
        self.assertIn("已死", out)

    def test_finished_is_not_reported_as_dead(self):
        """跑完之后心跳自然停止 —— 报"已死"就是误报，误报会让人不再信告警。"""
        rc, out = self._run("finished", 7200)
        self.assertEqual(rc, 0)
        self.assertNotIn("已死", out)
        self.assertIn("正常跑完", out)

    def test_quota_abort_is_flagged_but_distinct(self):
        rc, out = self._run("aborted_quota", 7200)
        self.assertEqual(rc, 1)
        self.assertIn("额度", out)
        self.assertNotIn("已死", out)

    def test_missing_file_is_failure(self):
        self.tmp.unlink(missing_ok=True)
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "watch_health.py")],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(r.returncode, 1)
        self.assertIn("从没", r.stdout or "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
