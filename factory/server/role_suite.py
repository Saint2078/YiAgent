"""角色工厂：角色名 → 能力维度蓝图 → 题组（含裁判 rubric）→ suite 落盘 → manifest。

链路定位：本模块只负责「出题与出裁判」这一段。落盘后的 suite 直接被
case_library 索引，manifest 交给已有 /api/evolve/start 做基因搜索与 holdout 鉴定。

benchmark 在此阶段的作用是**锚点参考**：注入题型/难度/评测口径，并登记来源。
原题实跑（DABstep / DABench 等）需要数据文件与代码执行沙箱，不在本模块范围。
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from case_library import LIBRARY, ROOT_FACTORY, ROOT_YIAGENT
from generate import _chat_json, normalize_case
from testset import build_manifest, save_manifest

ROLE_SOURCE = "role"
SCHEMA = "yiagent.factory.role_blueprint"
VERSION = 1
BLUEPRINT_DIR = ROOT_FACTORY / "save" / "roles"
BENCH_INDEX_PATH = ROOT_FACTORY / "fixtures" / "benchmark_index.json"

LEVELS = ("basic", "medium", "hard")


# ---------------------------------------------------------------- paths


def resolve_case_home() -> Path:
    """返回 case 总目录（其下为 source/suite/testcases.jsonl）。"""
    env = (os.environ.get("YIAGENT_CASE_ROOT") or "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            # env 指向某一 source（其子目录直接带 jsonl）→ home 为其父
            try:
                if any((c / "testcases.jsonl").is_file() for c in p.iterdir() if c.is_dir()):
                    return p.parent
            except OSError:
                pass
            return p
    for cand in (ROOT_YIAGENT / "case", Path("/app/case"), ROOT_FACTORY / "case"):
        if cand.is_dir():
            return cand
    return ROOT_YIAGENT / "case"


def suite_path(role_id: str) -> Path:
    return resolve_case_home() / ROLE_SOURCE / role_id / "testcases.jsonl"


def slugify_role(role: str) -> str:
    """角色名 → 稳定 suite id。中文等非 ASCII 保留可读片段 + 短哈希。"""
    raw = (role or "").strip()
    if not raw:
        raise ValueError("role required")
    ascii_part = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_part).strip("_").lower()
    if slug:
        return slug[:40]
    # 纯中文角色名：用短哈希保证确定性（同名同 id）
    import hashlib

    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    return f"role_{h}"


# ---------------------------------------------------------------- anchors


def load_bench_index() -> dict[str, Any]:
    if not BENCH_INDEX_PATH.is_file():
        return {"benchmarks": []}
    try:
        return json.loads(BENCH_INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"benchmarks": []}


_CJK = re.compile(r"[\u4e00-\u9fff]")


def _expand_terms(queries: list[str], *, limit: int = 40) -> list[str]:
    """检索词展开。中文无分词，按 2/3 字滑窗切片，保证「数据分析专家」能命中「数据分析」。"""
    terms: list[str] = []
    for q in queries:
        for tok in re.split(r"[\s,，、/|·()（）]+", str(q or "").lower()):
            tok = tok.strip()
            if len(tok) < 2:
                continue
            terms.append(tok)
            if _CJK.search(tok) and len(tok) > 2:
                for n in (2, 3):
                    for i in range(len(tok) - n + 1):
                        terms.append(tok[i : i + n])
    return list(dict.fromkeys(terms))[:limit]


def _score_bench(entry: dict, terms: list[str]) -> int:
    blob = " ".join(
        [
            str(entry.get("id") or ""),
            str(entry.get("title") or ""),
            str(entry.get("about") or ""),
            " ".join(entry.get("capabilities") or []),
            " ".join(entry.get("keywords") or []),
        ]
    ).lower()
    return sum(1 for t in terms if t and t in blob)


def retrieve_anchors(
    queries: list[str], *, role: str = "", limit_bench: int = 4, limit_cases: int = 6
) -> dict[str, Any]:
    """锚点检索：① benchmark 策展索引 ② 本地已有题库。只返回引用，不复制题面。"""
    terms = _expand_terms([role, *(queries or [])])

    index = load_bench_index()
    scored = []
    for entry in index.get("benchmarks") or []:
        s = _score_bench(entry, terms)
        if s > 0:
            scored.append((s, entry))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("id"))))
    bench = [
        {
            "id": e.get("id"),
            "title": e.get("title"),
            "about": e.get("about"),
            "task_shape": e.get("task_shape"),
            "scoring": e.get("scoring"),
            "path": e.get("path"),
            "pulled": bool(e.get("pulled")),
            "runnable_here": bool(e.get("runnable_here")),
            "match": s,
        }
        for s, e in scored[:limit_bench]
    ]

    local: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for q in (queries or [])[:6]:
        try:
            page = LIBRARY.list_cases(q=str(q), limit=4)
        except Exception:  # noqa: BLE001
            continue
        for it in page.get("items") or []:
            key = (it.get("suite") or "", it.get("id") or "")
            if key in seen:
                continue
            seen.add(key)
            local.append(
                {
                    "suite": it.get("suite"),
                    "id": it.get("id"),
                    "title": it.get("title"),
                    "dimension": it.get("dimension"),
                    "matched_query": q,
                }
            )
            if len(local) >= limit_cases:
                break
        if len(local) >= limit_cases:
            break

    return {"benchmarks": bench, "local_cases": local, "terms": terms}


def _anchor_brief(anchors: dict[str, Any]) -> str:
    rows = []
    for b in anchors.get("benchmarks") or []:
        rows.append(
            f"- {b.get('id')} · {b.get('title')}：题型={b.get('task_shape') or '—'}；"
            f"判分={b.get('scoring') or '—'}"
        )
    if not rows:
        return "（无匹配 benchmark 锚点，按角色常识设计）"
    return "\n".join(rows)


# ---------------------------------------------------------------- blueprint


def plan_blueprint(api_key: str, model: str, role: str, *, anchors: dict | None = None) -> dict[str, Any]:
    """角色名 → 能力维度蓝图（可打分、拉得开差距的维度）。"""
    role = (role or "").strip()
    if not role:
        raise ValueError("role required")
    anchors = anchors or {"benchmarks": [], "local_cases": []}
    system = (
        "你是 Agent 能力评估设计师。只输出合法 JSON，不要 markdown。\n"
        "任务：把一个角色名拆成 4–6 个「能拉开差距」的能力维度，供后续出题与打分。\n"
        "硬性：维度必须是这个角色的分水岭能力，不要写「沟通能力」这类放到任何角色都成立的泛项；"
        "每维必须写清常见失败样态；weight 之和为 100。"
    )
    user = f"""角色名：{role}

已检索到的 benchmark 锚点（供参考题型与判分口径，不要照抄）：
{_anchor_brief(anchors)}

输出 schema：
{{
  "role_id": "英文小写下划线",
  "display_name": "{role}",
  "summary": "一句话职责",
  "users": "服务对象是谁",
  "deliverables": ["典型交付物1","2"],
  "dimensions": [
    {{"key":"英文小写下划线","label":"中文维度名","weight":25,
      "why":"为什么这维是该角色的分水岭",
      "failure_modes":["常见失败样态1","2"],
      "probe":"一句话说明这维该怎么考"}}
  ],
  "hard_constraints": ["该角色不可逾越的硬约束"],
  "denylist": ["典型不该做的事（用于扣分）"],
  "anchor_queries": ["用于检索题库/benchmark 的关键词"]
}}
要求：dimensions 4–6 条；weight 合计 100；probe 必须可落成一道能打分的题。"""
    data = _chat_json(api_key, model, system, user, max_tokens=3000)
    return normalize_blueprint(data, role=role, anchors=anchors)


def normalize_blueprint(data: dict, *, role: str, anchors: dict | None = None) -> dict[str, Any]:
    role = (role or "").strip()
    display = str(data.get("display_name") or role).strip() or role
    rid_raw = str(data.get("role_id") or "").strip()
    role_id = re.sub(r"[^a-z0-9_]+", "_", rid_raw.lower()).strip("_") or slugify_role(role)
    dims_in = data.get("dimensions") or []
    dims: list[dict[str, Any]] = []
    if isinstance(dims_in, list):
        for i, d in enumerate(dims_in):
            if not isinstance(d, dict):
                continue
            label = str(d.get("label") or d.get("key") or f"维度{i + 1}").strip()
            key_raw = str(d.get("key") or "").strip().lower()
            key = re.sub(r"[^a-z0-9_]+", "_", key_raw).strip("_") or f"dim{i + 1}"
            fm = d.get("failure_modes") or []
            if isinstance(fm, str):
                fm = [fm]
            dims.append(
                {
                    "key": key,
                    "label": label,
                    "weight": float(d.get("weight") or 0),
                    "why": str(d.get("why") or ""),
                    "probe": str(d.get("probe") or ""),
                    "failure_modes": [str(x) for x in fm if str(x).strip()][:6],
                }
            )
    dims = dims[:6]
    if not dims:
        raise ValueError("blueprint has no dimensions")
    total = sum(d["weight"] for d in dims)
    if total <= 0:
        for d in dims:
            d["weight"] = round(100 / len(dims), 1)
    elif abs(total - 100) > 0.5:
        for d in dims:
            d["weight"] = round(d["weight"] * 100 / total, 1)

    def _list(field: str) -> list[str]:
        v = data.get(field) or []
        if isinstance(v, str):
            v = [v]
        return [str(x) for x in v if str(x).strip()][:8]

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "role": role,
        "role_id": role_id,
        "display_name": display,
        "summary": str(data.get("summary") or ""),
        "users": str(data.get("users") or ""),
        "deliverables": _list("deliverables"),
        "dimensions": dims,
        "hard_constraints": _list("hard_constraints"),
        "denylist": _list("denylist"),
        "anchor_queries": _list("anchor_queries") or [role],
        "anchors": anchors or {"benchmarks": [], "local_cases": []},
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def save_blueprint(bp: dict) -> Path:
    BLUEPRINT_DIR.mkdir(parents=True, exist_ok=True)
    path = BLUEPRINT_DIR / f"{bp['role_id']}.json"
    path.write_text(json.dumps(bp, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_blueprint(role_id: str) -> dict[str, Any]:
    path = BLUEPRINT_DIR / f"{(role_id or '').strip()}.json"
    if not path.is_file():
        raise KeyError(f"blueprint not found: {role_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_blueprints() -> list[dict[str, Any]]:
    if not BLUEPRINT_DIR.is_dir():
        return []
    out = []
    for p in sorted(BLUEPRINT_DIR.glob("*.json")):
        try:
            bp = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        out.append(
            {
                "role_id": bp.get("role_id"),
                "display_name": bp.get("display_name"),
                "role": bp.get("role"),
                "dimensions": [d.get("label") for d in bp.get("dimensions") or []],
                "created_at": bp.get("created_at"),
                "cases": count_suite_cases(str(bp.get("role_id") or "")),
            }
        )
    return out


# ---------------------------------------------------------------- cases


def generate_dim_case(
    api_key: str,
    model: str,
    bp: dict,
    dim: dict,
    *,
    level: str = "basic",
    variant_no: int = 1,
) -> dict[str, Any]:
    """为某一能力维度出一道可打分的题（含裁判 rubric）。"""
    level = (level or "basic").strip().lower()
    if level not in LEVELS:
        level = "basic"
    depth = {
        "basic": "常规工作场景，信息基本齐备",
        "medium": "信息有缺口或相互冲突，需要取舍与追问",
        "hard": "含陷阱：诉求越界 / 数据不可信 / 约束互斥，必须显式拒绝或升级",
    }[level]
    system = (
        "你是筛选题与评分标准设计师。只输出合法 JSON，不要 markdown。\n"
        "设计一道该角色真实工作里会遇到的开放题 + 多维评分标准。\n"
        "硬性：criteria 各维 weight 之和为 100；rubric 用 90-100/70-89/60-69/0-59 四档文字；"
        "题干里不得出现评分标准或答案；不要写成「请分析以下论证的谬误」这类通用批判性思维题。"
    )
    user = f"""角色：{bp.get('display_name')}（{bp.get('summary')}）
服务对象：{bp.get('users')}
硬约束：{'; '.join(bp.get('hard_constraints') or []) or '—'}
不该做（用于扣分）：{'; '.join(bp.get('denylist') or []) or '—'}

本题只考这一个维度：
- 维度：{dim.get('label')}（key={dim.get('key')}）
- 为何是分水岭：{dim.get('why')}
- 怎么考：{dim.get('probe')}
- 常见失败样态：{'; '.join(dim.get('failure_modes') or []) or '—'}

难度：{level} —— {depth}
第 {variant_no} 道（同维度多题时请换场景，不要换皮）。

benchmark 锚点（参考题型与判分口径，不要照抄题面）：
{_anchor_brief(bp.get('anchors') or {})}

输出 schema：
{{
  "id": "{bp.get('role_id')}_{dim.get('key')}_{variant_no:03d}",
  "title": "短标题",
  "description": "一句话说明测什么",
  "messages": [
    {{"role":"system","content":"选手 system：只写角色与场景，不写评分标准"}},
    {{"role":"user","content":"原题用户提问：给足场景细节，含至少一个需要判断取舍的点"}}
  ],
  "requirements": ["可检验要求1","2","3"],
  "criteria": {{
    "维度名": {{"weight":40,"desc":"考察什么","rubric":{{"90-100":"...","70-89":"...","60-69":"...","0-59":"..."}}}}
  }},
  "reference_answer": ["满分答案的关键要点"]
}}
要求：criteria 至少 3 维，其中一维必须直接对应「{dim.get('label')}」；至少一维用于抓上面的失败样态。"""
    data = _chat_json(api_key, model, system, user, max_tokens=3800)
    case = normalize_case(data, f"{bp.get('display_name')} · {dim.get('label')}")
    case["dimension"] = str(dim.get("label") or dim.get("key") or "")
    case["dimension_key"] = str(dim.get("key") or "")
    case["level"] = level
    case["role_id"] = bp.get("role_id")
    return case


def to_raw_row(case: dict) -> dict[str, Any]:
    """factory case → case_library 期望的 jsonl 行（levels 包裹）。"""
    level = (case.get("level") or "basic").strip().lower()
    if level not in LEVELS:
        level = "basic"
    return {
        "id": case.get("id") or f"case_{uuid.uuid4().hex[:8]}",
        "title": case.get("title") or case.get("id"),
        "description": case.get("description") or "",
        "dimension": case.get("dimension") or "",
        "test_type": f"role:{case.get('role_id') or 'unknown'}",
        "origin": "role_factory",
        "levels": {
            level: {
                "messages": case.get("messages") or [],
                "requirements": case.get("requirements") or [],
                "criteria": case.get("criteria") or {},
                "reference_answer": case.get("reference_answer") or [],
            }
        },
    }


def write_suite(role_id: str, cases: list[dict], *, replace: bool = True) -> dict[str, Any]:
    """落盘 case/role/{role_id}/testcases.jsonl 并让 LIBRARY 重新索引。

    同 id 的题按 level 合并（同一 id 可同时有 basic/medium/hard）。
    """
    path = suite_path(role_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows: dict[str, dict] = {}
    if not replace and path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("id"):
                rows[str(row["id"])] = row

    for case in cases:
        row = to_raw_row(case)
        cid = str(row["id"])
        if cid in rows:
            rows[cid]["levels"].update(row["levels"])
        else:
            rows[cid] = row

    with path.open("w", encoding="utf-8") as f:
        for cid in sorted(rows):
            f.write(json.dumps(rows[cid], ensure_ascii=False) + "\n")

    LIBRARY.reload()
    return {"path": str(path), "suite": role_id, "source": ROLE_SOURCE, "cases": len(rows)}


def count_suite_cases(role_id: str) -> int:
    path = suite_path(role_id)
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def build_role_cases(
    api_key: str,
    model: str,
    bp: dict,
    *,
    per_dim: int = 2,
    levels: list[str] | None = None,
    on_case=None,
) -> list[dict[str, Any]]:
    """按维度批量出题。levels 为空则 basic 起，第 2 道升 medium。"""
    per_dim = max(1, min(int(per_dim), 4))
    dims = bp.get("dimensions") or []
    out: list[dict[str, Any]] = []
    for dim in dims:
        for i in range(per_dim):
            if levels:
                level = levels[i % len(levels)]
            else:
                level = "basic" if i == 0 else ("medium" if i == 1 else "hard")
            case = generate_dim_case(
                api_key, model, bp, dim, level=level, variant_no=i + 1
            )
            out.append(case)
            if on_case:
                on_case(case)
    return out


# ---------------------------------------------------------------- build job


PHASES = ("anchors", "blueprint", "cases", "suite", "manifest", "done")


@dataclass
class RoleBuild:
    """一次「角色 → 题组+裁判」构建。基因搜索仍走 /api/evolve/start。"""

    id: str
    role: str
    model: str
    per_dim: int
    size: int
    holdout_ratio: float
    seed: int
    replace: bool
    status: str = "running"  # running | done | error | aborted
    phase: str = "anchors"
    role_id: str | None = None
    blueprint: dict | None = None
    anchors: dict | None = None
    suite: dict | None = None
    manifest: dict | None = None
    cases: list[dict] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    error: str | None = None
    planned_cases: int = 0
    created_at: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )
    updated_at: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )
    lock: threading.Lock = field(default_factory=threading.Lock)
    _abort: threading.Event = field(default_factory=threading.Event)

    def log(self, msg: str) -> None:
        with self.lock:
            self.logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
            self.logs = self.logs[-80:]
            self.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def touch(self, phase: str | None = None) -> None:
        with self.lock:
            if phase:
                self.phase = phase
            self.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def aborted(self) -> bool:
        return self._abort.is_set()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            done = len(self.cases)
            return {
                "id": self.id,
                "schema": "yiagent.factory.role_build",
                "status": self.status,
                "phase": self.phase,
                "phases": list(PHASES),
                "role": self.role,
                "role_id": self.role_id,
                "model": self.model,
                "params": {
                    "per_dim": self.per_dim,
                    "size": self.size,
                    "holdout_ratio": self.holdout_ratio,
                    "seed": self.seed,
                    "replace": self.replace,
                },
                "progress": {"cases_done": done, "cases_planned": self.planned_cases},
                "blueprint": self.blueprint,
                "anchors": self.anchors,
                "suite": self.suite,
                "manifest": self.manifest,
                "cases": [
                    {
                        "id": c.get("id"),
                        "title": c.get("title"),
                        "dimension": c.get("dimension"),
                        "level": c.get("level"),
                        "criteria": list((c.get("criteria") or {}).keys()),
                        "requirements": c.get("requirements") or [],
                    }
                    for c in self.cases
                ],
                "logs": list(self.logs),
                "error": self.error,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "next_step": (
                    {
                        "api": "POST /api/evolve/start",
                        "body": {"manifest_id": (self.manifest or {}).get("id"), "oral": self.role},
                        "note": "题组已就绪 → 交给进化做基因搜索与 holdout 鉴定",
                    }
                    if self.manifest
                    else None
                ),
            }


class RoleBuildManager:
    def __init__(self) -> None:
        self._runs: dict[str, RoleBuild] = {}
        self._lock = threading.Lock()

    def get(self, run_id: str) -> RoleBuild | None:
        with self._lock:
            return self._runs.get(run_id)

    def abort(self, run_id: str) -> RoleBuild:
        run = self.get(run_id)
        if not run:
            raise KeyError(run_id)
        run._abort.set()
        if run.status == "running":
            run.status = "aborted"
        run.touch()
        return run

    def start(
        self,
        api_key: str,
        model: str,
        role: str,
        *,
        per_dim: int = 2,
        size: int = 10,
        holdout_ratio: float = 0.3,
        seed: int = 42,
        replace: bool = True,
    ) -> RoleBuild:
        role = (role or "").strip()
        if not role:
            raise ValueError("role required")
        run = RoleBuild(
            id=uuid.uuid4().hex[:12],
            role=role,
            model=model,
            per_dim=max(1, min(int(per_dim), 4)),
            size=max(1, min(int(size), 60)),
            holdout_ratio=max(0.0, min(float(holdout_ratio), 0.5)),
            seed=int(seed),
            replace=bool(replace),
        )
        with self._lock:
            self._runs[run.id] = run
        threading.Thread(
            target=self._work, args=(run, api_key.strip()), daemon=True
        ).start()
        return run

    def _work(self, run: RoleBuild, api_key: str) -> None:
        try:
            run.log(f"角色 = {run.role}")
            anchors = retrieve_anchors([run.role], role=run.role)
            run.anchors = anchors
            run.log(
                f"锚点：benchmark {len(anchors['benchmarks'])} 条 · 本地题 {len(anchors['local_cases'])} 条"
            )
            if run.aborted():
                return
            run.touch("blueprint")

            bp = plan_blueprint(api_key, run.model, run.role, anchors=anchors)
            # 蓝图给出的检索词再补一轮锚点
            more = retrieve_anchors(bp.get("anchor_queries") or [], role=run.role)
            bp["anchors"] = {
                "benchmarks": more["benchmarks"] or anchors["benchmarks"],
                "local_cases": more["local_cases"] or anchors["local_cases"],
            }
            run.blueprint = bp
            run.role_id = bp["role_id"]
            save_blueprint(bp)
            dims = bp.get("dimensions") or []
            run.planned_cases = len(dims) * run.per_dim
            run.log(
                "蓝图：" + " / ".join(f"{d['label']}({d['weight']})" for d in dims)
            )
            if run.aborted():
                return
            run.touch("cases")

            def _on_case(case: dict) -> None:
                with run.lock:
                    run.cases.append(case)
                    done = len(run.cases)
                run.log(f"出题 {done}/{run.planned_cases} · {case.get('title')}")

            cases: list[dict] = []
            for dim in dims:
                if run.aborted():
                    return
                for i in range(run.per_dim):
                    if run.aborted():
                        return
                    level = "basic" if i == 0 else ("medium" if i == 1 else "hard")
                    case = generate_dim_case(
                        api_key, run.model, bp, dim, level=level, variant_no=i + 1
                    )
                    cases.append(case)
                    _on_case(case)

            run.touch("suite")
            run.suite = write_suite(bp["role_id"], cases, replace=run.replace)
            run.log(f"题组落盘 {run.suite['path']} · {run.suite['cases']} 题")

            run.touch("manifest")
            size = min(run.size, max(1, len(cases)))
            manifest = build_manifest(
                f"{bp.get('display_name')} · 角色工厂题组",
                suites=[bp["role_id"]],
                level="basic",
                size=size,
                seed=run.seed,
                holdout_ratio=run.holdout_ratio,
            )
            manifest["role_id"] = bp["role_id"]
            save_manifest(manifest)
            run.manifest = manifest
            run.log(
                f"manifest {manifest['id']} · 进化集 {len(manifest['cases'])} · holdout {len(manifest['holdout'])}"
            )
            run.status = "done"
            run.touch("done")
        except Exception as e:  # noqa: BLE001
            run.error = str(e)[:1200]
            run.status = "error"
            run.log(f"失败：{run.error[:200]}")
            run.touch()


ROLE_MANAGER = RoleBuildManager()
