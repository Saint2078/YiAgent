#!/usr/bin/env python3
"""把 factory Develop 冠军槽位写进 app.js 的 DNA_GENOMES（同角色 v1.1）。"""
from __future__ import annotations

import json
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "console" / "app.js"
V11 = Path(__file__).resolve().parents[2] / "console" / "_workbench" / "AgentTeam" / "dna-genomes-v11.json"

# DNA_GENOMES id → seat file already in dna-genomes-v11.json keys


def js_escape(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def slots_js(slots: dict) -> str:
    lines = ['    "slots": {']
    order = ["G1", "G2", "G3", "G4", "G5"]
    for i, k in enumerate(order):
        sl = slots[k]
        comma = "," if i < len(order) - 1 else ""
        lines.append(f'      "{k}": {{')
        lines.append(f'        "key": {js_escape(sl["key"])},')
        lines.append(f'        "label": {js_escape(sl["label"])},')
        lines.append(f'        "text": {js_escape(sl["text"])}')
        lines.append(f"      }}{comma}")
    lines.append("    }")
    return "\n".join(lines)


def main() -> int:
    data = json.loads(V11.read_text(encoding="utf-8"))
    text = APP.read_text(encoding="utf-8")
    for gid, payload in data.items():
        # match object starting with "id": "<gid>" within DNA_GENOMES
        pat = re.compile(
            rf'(\{{\s*\n\s*"id": "{re.escape(gid)}",[\s\S]*?"genomePack": "[^"]+",\n)([\s\S]*?)(\n  \}})',
            re.M,
        )

        def repl(m: re.Match) -> str:
            head = m.group(1)
            # inject version after genomePack line area — rebuild middle from payload
            # Keep id/role/title/path/agentId/genomePack from head; replace status+slots
            # Simpler: replace only slots block inside match
            body = m.group(0)
            body2 = re.sub(
                r'"status":\s*"[^"]*"',
                '"status": "ready"',
                body,
                count=1,
            )
            # add version field if missing
            if '"version"' not in body2:
                body2 = body2.replace(
                    '"status": "ready"',
                    f'"status": "ready",\n    "version": "1.1",\n    "factory_run": {js_escape(payload["source_run"])},\n    "factory_champ": {payload["champ"]}',
                    1,
                )
            else:
                body2 = re.sub(r'"version":\s*"[^"]*"', '"version": "1.1"', body2, count=1)
            body2 = re.sub(
                r'"slots":\s*\{[\s\S]*?\n    \}',
                slots_js(payload["slots"]),
                body2,
                count=1,
            )
            return body2

        new_text, n = pat.subn(repl, text, count=1)
        if n != 1:
            raise SystemExit(f"DNA_GENOMES id={gid} not patched (n={n})")
        text = new_text
        print("patched", gid, "champ", payload["champ"])
    APP.write_text(text, encoding="utf-8")
    print("wrote", APP)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
