#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "runs"


def dump(label: str, run_id: str) -> None:
    r = json.loads((ROOT / run_id / "report.json").read_text(encoding="utf-8"))
    fails = [x for x in (r.get("results") or []) if not x.get("passed")]
    print("=" * 60)
    print(f"{label} fails {len(fails)}/{r.get('n_total')}")
    for i, x in enumerate(fails, 1):
        print(f"--- {i}. [{x.get('difficulty')}] {x.get('question_id')} {x.get('question_title')}")
        print(
            f"    platform={x.get('platform')} n_ok={x.get('n_ok')}/{x.get('n_tests')} "
            f"pub={x.get('n_public_tests')} priv={x.get('n_private_tests')}"
        )
        print(f"    detail={x.get('detail')!r}")
        prev = (x.get("code_preview") or "").replace("\n", "\\n")
        print(f"    code_preview={prev[:400]!r}")


if __name__ == "__main__":
    dump("基因组", "20260809-142513-cmp-2b92-genome")
    dump("裸跑", "20260809-142513-cmp-2b92-bare")
