#!/usr/bin/env python3
"""归档一次 evolve run 到 experiments/<YYYYMMDD>_<runid>/。

拷贝 report.json / report.md，并写一份 README.md 记录复跑口径
（启动命令、关键 env、manifest id、运行参数）。纯 stdlib，本机可跑，不依赖 Docker。

用法：
    python3 experiments/archive_evolve_run.py <run_id>
    python3 experiments/archive_evolve_run.py --run-dir factory/save/evolve/<run_id>
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAVE = REPO_ROOT / "factory" / "save" / "evolve"
DEFAULT_OUT = REPO_ROOT / "experiments"


def _readme(report: dict, *, run_dir: Path, dest: Path, archived_at: str) -> str:
    """归档 README：复跑口径（命令 / env / manifest id / 运行参数）。"""
    run_id = str(report.get("run_id") or run_dir.name)
    manifest_id = (report.get("manifest") or {}).get("id") or ""
    params = report.get("params") or {}
    body = {
        "api_key": "<你的 key>",
        "model": report.get("model") or "k3",
        "manifest_id": manifest_id or "<manifest_id>",
        **{k: v for k, v in params.items() if not k.startswith("manifest_")},
    }
    curl = (
        "curl -s -X POST http://localhost:8787/api/evolve/start \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        f"  -d '{json.dumps(body, ensure_ascii=False)}'"
    )
    return f"""# evolve run 归档 `{run_id}`

| 项 | 值 |
|----|-----|
| run id | `{run_id}` |
| 归档时间 | {archived_at} |
| 来源 | `{run_dir}` |
| manifest | `{manifest_id or "（内联/未记录）"}` |
| 模型 | {report.get('model')} |
| 停止原因 | {report.get('stop_reason')} |
| 总墙钟 | {report.get('wall_total_sec')} 秒 |

产物：`report.json`（完整度量：token_by_stage / wall_by_stage / 门禁 p·CI /
失败率 / 分层均分）、`report.md`（人读版）。

## 复跑口径

前置：factory 服务在 `:8787`（`docker compose -f factory/compose.yml up`），
key 走请求体 / 环境变量 / `secrets/kimi_coding_plan.key` 任一。

起飞前检查（应先跑）：

```
curl -s 'http://localhost:8787/api/evolve/preflight?manifest_id={manifest_id or '<manifest_id>'}'
```

启动（参数取自原 run 的 report.params）：

```
{curl}
```

相关 env：`YIAGENT_HOF_ENABLED=1`（名人堂上报，opt-in）、`YIAGENT_HOF_URL`。

原 run 完整参数：

```json
{json.dumps(params, ensure_ascii=False, indent=2)}
```
"""


def archive_run(
    run_dir: str | Path,
    out_dir: str | Path = DEFAULT_OUT,
    *,
    now: float | None = None,
) -> Path:
    """把 run_dir 的 report 产物归档到 out_dir/<YYYYMMDD>_<runid>/，返回归档目录。"""
    run_dir = Path(run_dir)
    report_path = run_dir / "report.json"
    if not report_path.is_file():
        raise FileNotFoundError(f"report not found: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    run_id = str(report.get("run_id") or run_dir.name)
    stamp = time.strftime("%Y%m%d", time.gmtime(now))
    dest = Path(out_dir) / f"{stamp}_{run_id}"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(report_path, dest / "report.json")
    md_path = run_dir / "report.md"
    if md_path.is_file():
        shutil.copy2(md_path, dest / "report.md")
    archived_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    (dest / "README.md").write_text(
        _readme(report, run_dir=run_dir, dest=dest, archived_at=archived_at),
        encoding="utf-8",
    )
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="归档 evolve run 到 experiments/")
    parser.add_argument("run_id", nargs="?", help="run id（在 --save-dir 下找）")
    parser.add_argument("--run-dir", help="直接指定 run 目录（优先于 run_id）")
    parser.add_argument("--save-dir", default=str(DEFAULT_SAVE), help="evolve save 根目录")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT), help="归档输出根目录")
    args = parser.parse_args(argv)
    if args.run_dir:
        run_dir = Path(args.run_dir)
    elif args.run_id:
        run_dir = Path(args.save_dir) / args.run_id
    else:
        parser.error("给 run_id 或 --run-dir 之一")
    try:
        dest = archive_run(run_dir, args.out_dir)
    except FileNotFoundError as e:
        print(f"归档失败：{e}", file=sys.stderr)
        return 1
    print(f"已归档 → {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
