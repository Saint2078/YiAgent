#!/usr/bin/env python3
"""一次请求探 Kimi 额度是否恢复：用服务端自己的密钥，别在本机复制密钥。

`ok=1` 即额度可用；`ok=0` 且 errors 里带 403/access_terminated 即仍在封顶。
无人值守时循环调用它做门控，避免额度没恢复就白跑一整轮实跑。
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime

BASE = "http://127.0.0.1:8790"


def probe(timeout: float = 120.0) -> dict:
    req = urllib.request.Request(
        f"{BASE}/api/perf/probe",
        data=json.dumps({"n": 1, "concurrency": 1, "max_tokens": 512}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:  # 服务端自己报错（如 500）也当探测失败
        return {"ok": 0, "requests": 1, "http_error": e.code, "body": e.read()[:400].decode("utf-8", "replace")}
    except Exception as e:  # noqa: BLE001
        return {"ok": 0, "requests": 1, "error": str(e)[:200]}


def main() -> int:
    d = probe()
    ok = int(d.get("ok") or 0) > 0
    stamp = datetime.now().strftime("%H:%M:%S")
    if ok:
        print(f"{stamp} QUOTA OK  wall={d.get('wall_seconds')}s retries={d.get('retries')}")
    else:
        why = d.get("http_error") or d.get("error") or "上游拒绝（多为 403 额度封顶）"
        print(f"{stamp} QUOTA DOWN  {why}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
