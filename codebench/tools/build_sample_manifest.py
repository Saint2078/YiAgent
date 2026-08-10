#!/usr/bin/env python3
"""从物化题包导出**可提交**的轻量抽样清单（无测例负载）。

物化包 `sample50_release_v5.json` 含 public+private 测例负载（~370MB），不入 git；
本清单只留 meta + 每题标识/难度/日期/测例条数 + 题面 sha256，用于复现与核对。

用法（宿主机直接跑，只读 JSON，不起服务）：
    python tools/build_sample_manifest.py [in.json] [out.json]
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
DEFAULT_IN = HERE / "data" / "sample50_release_v5.json"
DEFAULT_OUT = HERE / "data" / "sample50_release_v5.manifest.json"

FIELDS = (
    "question_id",
    "question_title",
    "platform",
    "difficulty",
    "contest_date",
    "n_public_tests",
    "n_private_tests",
)


def _sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def build(src: Path, out: Path) -> dict:
    payload = json.loads(src.read_text(encoding="utf-8"))
    problems = payload.get("problems") or []
    rows = []
    for p in problems:
        row = {k: p.get(k) for k in FIELDS}
        row["question_content_sha256"] = _sha256(p.get("question_content") or "")
        row["has_starter_code"] = bool((p.get("starter_code") or "").strip())
        rows.append(row)
    manifest = {
        "schema": "yiagent.codebench.sample_manifest/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": src.name,
        "source_bytes": src.stat().st_size,
        "note": "测例负载不入库；用 tools/build_sample50.py + 相同 seed/release 可重建物化包。",
        "meta": payload.get("meta") or {},
        "problems": rows,
    }
    out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str]) -> int:
    src = Path(argv[1]) if len(argv) > 1 else DEFAULT_IN
    out = Path(argv[2]) if len(argv) > 2 else DEFAULT_OUT
    if not src.is_file():
        print(f"missing sample pack: {src}", file=sys.stderr)
        return 2
    m = build(src, out)
    print(f"wrote {out} · problems={len(m['problems'])} · seed={m['meta'].get('seed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
