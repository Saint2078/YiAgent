#!/usr/bin/env python3
"""把 `scripts/hooks/` 里的钩子装到本仓的 `.git/hooks/`。

为什么要有这一步：git 不会版本化 `.git/hooks/`，所以钩子必须存在版本库里、
再显式安装。少了这步，换台机器 clone 下来钩子就**静默不存在** ——
而"安全检查静默失效"比没有检查更糟，因为人以为它在。

用法：
    python scripts/install_hooks.py            # 装到本仓
    python scripts/install_hooks.py --check    # 只检查是否已装（CI/自检用）
"""
from __future__ import annotations

import argparse
import shutil
import stat
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "hooks"


def git_dir(start: Path) -> Path | None:
    r = subprocess.run(
        ["git", "rev-parse", "--git-dir"], cwd=str(start),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        return None
    p = Path((r.stdout or "").strip())
    return p if p.is_absolute() else (start / p).resolve()


def main() -> int:
    ap = argparse.ArgumentParser(description="安装 git 钩子")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    gd = git_dir(HERE.parent)
    if not gd:
        print("✗ 不在 git 仓里，无法安装钩子")
        return 1
    dst_dir = gd / "hooks"
    dst_dir.mkdir(parents=True, exist_ok=True)

    rc = 0
    for src in sorted(SRC.iterdir()):
        if src.suffix == ".py" or not src.is_file():
            continue
        dst = dst_dir / src.name
        installed = dst.is_file() and dst.read_text(encoding="utf-8", errors="replace") == \
            src.read_text(encoding="utf-8", errors="replace")
        if args.check:
            print(f"{'✓' if installed else '✗'} {src.name} "
                  f"{'已安装且最新' if installed else '**未安装或已过期**'}")
            rc = rc or (0 if installed else 1)
            continue
        shutil.copyfile(src, dst)
        dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"✓ 已安装 {src.name} → {dst}")

    if not args.check:
        print("\n自检：故意造一行假密钥试一次")
        print("  python scripts/hooks/scan_secrets.py <某个含 sk-xxxx 的文件>")
        print("绕过（应当是刻意行为）：git commit --no-verify")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
