#!/usr/bin/env python3
"""把 rolefactory 实跑冠军装成**可运行的 Agent 实体**，并做出厂检验。

这条链路此前是断的：工厂能产冠军基因、`yiagent` 能装配载体，但两边格式不同，
六席冠军一直只是 JSON，不是能跑的东西。本脚本串起全程：

    实跑 report.json
      → export_yiagent_bank.py   （工厂格式 → yiagent 基因库）
      → recipient.import_genome  （校验 + 装配成表达载体）
      → phenotype.smoke_report   （offline 出厂检验，不触网不调 LLM）
      → 登记表 agent-entities.md （每席一行：哈希 / 检验 / 能宣称什么）

出厂检验只做**声明层**：结构、G1/G2 是否真进 system、工具挂载与声明是否一致。
**行为层**（真答一句话）必须人显式触发 `yiagent smoke <vector> --live`，
本脚本一次真实 LLM 调用都不发。

用法：
    python scripts/build_agent_entities.py            # 六席全建
    python scripts/build_agent_entities.py --seat PM
    python scripts/build_agent_entities.py --check     # 只检验现有载体，不重装
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from yiagent.assembly import AssemblyBlocked, generalizes, marker_line  # noqa: E402
from yiagent.phenotype import smoke_report  # noqa: E402
from yiagent.recipient import import_genome  # noqa: E402

SEATS = ["Product", "PM", "Architect", "Dev", "DevOps", "Evals"]
SEAT_DIR = REPO / "console" / "_workbench" / "AgentTeam" / "Develop"
BANK_DIR = REPO / "rolefactory" / "data" / "yiagent_banks"
EXPORTER = REPO / "rolefactory" / "tools" / "export_yiagent_bank.py"
REGISTRY = REPO.parent / "工作台" / "AgentTeam" / "agent-entities.md"

# 运行时宿主层：只讲「怎么干活」，不碰身份与边界——那是 G1/G2 的事，
# 精度顺序 G2 > Runtime > AGENTS.md，宿主层越权会被 G2 压住。
HOST = (
    "你在 YiAgent 运行时中作为 Develop 团队的一席工作：按已装载的 G1–G5 基因组行事。"
    "回答先给结论，再给依据；需要读写文件或执行命令时使用提供的工具。"
    "事实、推断、假设分开表述；没有依据的地方标注「未核实」。"
)


def _fixed_stamp(bank: dict[str, Any]) -> str:
    """装配时间锚在**实跑发生的时刻**，不是 now()、也不是导出时刻。

    实跑时刻是这份基因唯一不变的时间事实，所以同一个 run 无论何时重新导出、
    重新装配，载体都逐字节一致 —— 这是「可复现交付」的字面含义。
    """
    pr = (bank.get("meta") or {}).get("provenance") or {}
    for key in ("run_at", "exported_at"):  # exported_at 只为兼容早期导出的 bank
        stamp = str(pr.get(key) or "").strip()
        if stamp:
            return stamp.replace("+00:00", "Z")
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_bank(seat: str, refresh: bool) -> Path | None:
    path = BANK_DIR / f"{seat}.bank.json"
    if path.is_file() and not refresh:
        return path
    # 显式给 --out，并核对文件真的被重写了。
    # 起因是一次静默失效：导出器 --seat 曾把文件写进 run 目录，而这里只检查
    # yiagent_banks/ 下**存在**同名文件 —— 于是 --refresh 跑完，旧基因库继续被装配，
    # 判定还是复核前的「reps=1 判不了」，全程零报错（verify_chain 才把它抓出来）。
    before = path.stat().st_mtime_ns if path.is_file() else 0
    r = subprocess.run(
        [sys.executable, str(EXPORTER), "--seat", seat, "--out", str(path)],
        cwd=str(REPO / "rolefactory"), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        print(f"  {seat}: 导出基因库失败 — {(r.stderr or r.stdout or '').strip()[-300:]}")
        return None
    if not path.is_file():
        print(f"  {seat}: 导出器没有写出 {path}")
        return None
    if refresh and path.stat().st_mtime_ns == before:
        print(f"  {seat}: 基因库未被重写（仍是旧文件），拒绝拿它装配：{path}")
        return None
    return path


def build_one(seat: str, *, refresh: bool, check_only: bool) -> dict[str, Any] | None:
    out_dir = SEAT_DIR / seat
    vector_path = out_dir / "vector.json"

    if check_only:
        if not vector_path.is_file():
            print(f"  {seat}: 没有载体，跳过（先不加 --check 建一次）")
            return None
        pack = json.loads(vector_path.read_text(encoding="utf-8"))
    else:
        bank_path = ensure_bank(seat, refresh)
        if not bank_path:
            return None
        bank = json.loads(bank_path.read_text(encoding="utf-8"))
        champion = next(
            (v for v in bank.get("variants") or [] if v.get("role_in_pack") == "champion"), None
        )
        if not champion:
            print(f"  {seat}: 基因库里没有 champion variant，跳过")
            return None
        try:
            pack = import_genome(
                bank_path, host=HOST, variant_id=champion["id"],
                assembled_at=_fixed_stamp(bank),
            )
        except AssemblyBlocked as exc:
            print(f"  {seat}: 装配被阻断 — {exc}")
            return None
        out_dir.mkdir(parents=True, exist_ok=True)
        vector_path.write_text(
            json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    report = smoke_report(pack)
    markers = pack.get("markers") or {}
    pr = markers.get("provenance") or {}
    failed = [c["name"] for c in report["checks"] if not c["ok"]]
    print(f"  {seat:10} 检验={report['status']:4} 哈希={str(markers.get('gene_hash'))[:16]} "
          f"判定={(pr.get('verdict') or {}).get('label')}")
    if failed:
        print(f"             未过项: {', '.join(failed)}")
    return {
        "seat": seat,
        "vector": vector_path,
        "pack": pack,
        "smoke": report,
        "provenance": pr,
        "proven": generalizes(pack),
    }


def _int_or_dash(v: Any) -> str:
    return "—" if v is None else f"{float(v):+.2f}" if isinstance(v, (int, float)) else str(v)


def write_registry(rows: list[dict[str, Any]]) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    proven = sum(1 for r in rows if r["proven"] is True)
    lines = [
        "# Develop 六席 · Agent 实体登记表",
        "",
        f"由 `scripts/build_agent_entities.py` 生成 · {now}",
        "",
        "每一行是一个**能跑的 Agent 实体**（表达载体已落盘），不是纸面基因组。",
        "链路：rolefactory 实跑冠军 → yiagent 基因库 → 表达载体 → offline 出厂检验。",
        "",
        f"**当前 {proven}/{len(rows)} 席能宣称「基因让它更强」**。",
        "「判不了」不是好消息也不是坏消息，是**证据不足**：holdout 只有 5–6 题，",
        "`reps=1` 时配对区间跨 0，符号会翻（PM 实测 Δ 从 −2.74 翻到 +1.46）。",
        "",
        "⚠ **下表的 train Δ 出自旧打分口径**（`must_not_include` 会把「引用错误说法去反驳」",
        "也扣光，实测 32% 的扣分属误判，见 `rolefactory/PERF.md` §12）。按修好的口径离线重算：",
        "2/9 个 run 的冠军会换人，项目经理 train Δ 由 +2.50 变 **−1.66**。",
        "holdout 分差无符号翻转，故「几席已证明」的结论不变。要拿到干净的冠军需重跑（花额度）。",
        "",
        "| 席位 | 出厂检验 | gene_hash | train Δ | holdout Δ | 泛化鉴定 | 可宣称 |",
        "|------|----------|-----------|---------|-----------|----------|--------|",
    ]
    for r in rows:
        pr = r["provenance"]
        hold = pr.get("holdout") or {}
        verdict = pr.get("verdict") or {}
        claim = "**可称更强**" if r["proven"] is True else "仅「由实跑冠军装配」"
        lines.append(
            f"| {r['seat']} | {r['smoke']['status']} | `{str(pr.get('genome_hash'))[:12]}` "
            f"| {_int_or_dash(pr.get('delta_train_weighted'))} "
            f"| {_int_or_dash(hold.get('delta_weighted'))} (reps={hold.get('reps')}) "
            f"| {verdict.get('label') or '—'} | {claim} |"
        )
    lines += [
        "",
        "## 怎么用",
        "",
        "```bash",
        "# 真的跟它对话（US-004「可直接调用」就是这一行）",
        "yiagent --vector console/_workbench/AgentTeam/Develop/Dev/vector.json",
        "",
        "# 装配（默认放行，但会把「不得宣称更强」打在输出里）",
        "yiagent assemble rolefactory/data/yiagent_banks/PM.bank.json \\",
        "  --variant var.<role_id>.champion",
        "",
        "# 生产投放：泛化未证明则拒装（退出码 3）",
        "yiagent assemble ... --require-generalization",
        "",
        "# 出厂检验（offline，不触网）",
        "yiagent smoke console/_workbench/AgentTeam/Develop/PM/vector.json",
        "",
        "# 行为层鉴定：真实 LLM 调用，只能人显式触发",
        "yiagent smoke .../vector.json --live",
        "",
        "# 证据链对账：报告/卡片/基因组/基因库/载体五处是否仍一致（断链退出码 1）",
        "python scripts/verify_chain.py",
        "```",
        "",
        "`--vector` 直启这条路径由 `tests/test_factory_intake.py::EntityCallableTests` 守着：",
        "它按用户真会敲的那一行解析、构造会话，并断言 G1/G2 等位真进了 system、",
        "血统（含泛化判定）跟着会话走。**但一次真实调用都没发** —— 行为层仍须你显式跑 `--live`。",
        "",
        "## 每席产物",
        "",
        "| 文件 | 是什么 |",
        "|------|--------|",
        "| `console/_workbench/AgentTeam/Develop/<席位>/genome.json` | 冠军基因组（含 genome_hash 与判定） |",
        "| `console/_workbench/AgentTeam/Develop/<席位>/vector.json` | **表达载体**：可运行配置包 |",
        "| `rolefactory/data/yiagent_banks/<席位>.bank.json` | yiagent 格式基因库（含全弱对照 variant） |",
        "| `rolefactory/data/runs/<run_id>/genome_card.md` | 基因组卡：消融贡献 + 复现配方 |",
        "",
        "这五处任一被手改、或某一步忘了重跑，链条就断了 —— **而断了不会有任何报错**：",
        "基因照样装配、Agent 照样启动，只是它宣称的战绩不再对应它实际带的基因。",
        "`scripts/verify_chain.py` 就是把这件事变成一条非零退出码（六席自洽也由测试守着）。",
        "",
        "## 对照实验",
        "",
        "每份基因库都附了一条 `var.<role_id>.all_weak`（全部取弱等位、同槽位结构）。",
        "想直观看「基因到底起没起作用」，把它也装一份，两个载体各问同一句话即可，",
        "不必回工厂重跑。注意这只是**观感对照**，不构成统计证据 —— 统计结论看 holdout 区间。",
    ]
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n登记表 → {REGISTRY}")


def main() -> int:
    ap = argparse.ArgumentParser(description="实跑冠军 → 可运行 Agent 实体")
    ap.add_argument("--seat", help="只建某一席")
    ap.add_argument("--refresh", action="store_true", help="强制重新导出基因库")
    ap.add_argument("--check", action="store_true", help="只检验现有载体，不重装")
    ap.add_argument("--no-registry", action="store_true", help="不写登记表")
    args = ap.parse_args()

    seats = [args.seat] if args.seat else SEATS
    print(f"建 Agent 实体：{seats}")
    rows = [
        row for seat in seats
        if (row := build_one(seat, refresh=args.refresh, check_only=args.check))
    ]
    if not rows:
        print("没有任何实体建成")
        return 1

    bad = [r["seat"] for r in rows if r["smoke"]["status"] != "ok"]
    if bad:
        print(f"\n出厂检验未过：{bad}")
    if not args.no_registry and not args.seat:
        write_registry(rows)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
