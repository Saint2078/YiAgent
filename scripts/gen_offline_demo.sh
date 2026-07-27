#!/usr/bin/env bash
# Rebuild demo/ as an offline twin of factory/www, hydrated from demo_pack.json.
# Requires: factory container up (docker compose -f factory/compose.yml up -d).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

cp "$ROOT/factory/www/styles.css" "$ROOT/demo/styles.css"
# Keep offline api()/boot() patches in demo/app.js — only refresh styles by default.
# To re-sync app.js from www, copy then re-apply patches manually or re-run the agent.

docker compose -f factory/compose.yml exec -T factory python - <<'PY'
import json
from pathlib import Path
from jobs import MANAGER

pack = json.loads(Path("/app/fixtures/demo_pack.json").read_text(encoding="utf-8"))
sess = MANAGER._session_from_pack(pack, frozen=True)
snap = sess.snapshot()
snap["id"] = "offline-frozen-demo"
Path("/app/save/_offline_snap.json").write_text(
    json.dumps(snap, ensure_ascii=False), encoding="utf-8"
)
print("snap phase=", snap.get("phase"), "baseline=", len(snap.get("baseline_summaries") or []))
PY

python3 - <<'PY'
import json
from pathlib import Path
root = Path(__file__).resolve().parent.parent if False else Path(".")
# script cwd is ROOT
snap = json.loads(Path("factory/save/_offline_snap.json").read_text(encoding="utf-8"))
models = [
    {"id": "k3", "label": "Kimi 3"},
    {"id": "kimi-k2.6", "label": "Kimi 2.6"},
]
Path("demo/snap.js").write_text(
    "/* Generated from factory/fixtures/demo_pack.json — do not edit by hand. */\n"
    "window.YIAGENT_OFFLINE = true;\n"
    "window.DEMO_SNAP = "
    + json.dumps(snap, ensure_ascii=False)
    + ";\n"
    "window.DEMO_MODELS = "
    + json.dumps(models, ensure_ascii=False)
    + ";\n",
    encoding="utf-8",
)
Path("demo/snap.json").write_text(
    json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
Path("factory/save/_offline_snap.json").unlink(missing_ok=True)
print("wrote demo/snap.js + demo/snap.json")
PY

python3 - <<'PY2'
import re
from pathlib import Path
root = Path("demo")
html = (root / "index.html").read_text(encoding="utf-8")
css = (root / "styles.css").read_text(encoding="utf-8")
snap = (root / "snap.js").read_text(encoding="utf-8")
app = (root / "app.js").read_text(encoding="utf-8")
html = re.sub(r"<script>\s*\(function \(\) \{.*?</script>\s*", "", html, count=1, flags=re.S)
html = html.replace('<link rel="stylesheet" href="./styles.css" />', "<style>\n" + css + "\n</style>")
html = html.replace('<script src="./snap.js"></script>', "<script>\n" + snap + "\n</script>")
html = html.replace('<script src="./app.js"></script>', "<script>\n" + app + "\n</script>")
(root / "yiagent-offline-demo.html").write_text(html, encoding="utf-8")
print("wrote demo/yiagent-offline-demo.html")
PY2

echo "OK: open demo/index.html (file://) — same UI as :8787, no API."
echo "Preview: https://htmlpreview.github.io/?https://raw.githubusercontent.com/Saint2078/YiAgent/main/demo/yiagent-offline-demo.html"
