#!/usr/bin/env python3
"""单独构建 50 题抽样（避免占满 API 进程内存）。"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, "/srv")
os.environ.setdefault("CB_LCB_ROOT", "/lcb")
os.environ.setdefault("CB_DATA_DIR", "/data")
os.environ.setdefault("HF_HOME", "/data/hf")

from app.sample50 import SEED, RELEASE, build_sample  # noqa: E402
from pathlib import Path

out = Path(os.environ["CB_DATA_DIR"]) / "sample50_release_v5.json"
print("building", out, "seed", SEED, "release", RELEASE, flush=True)
meta = build_sample(out)
print("OK", meta, flush=True)
