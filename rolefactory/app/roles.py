"""角色 → 能力维度蓝图 → 题组（含裁判 rubric）。所有 LLM 调用 async，可维度级并行。"""

from __future__ import annotations

import asyncio
import hashlib
import re
import unicodedata
from typing import Any

from . import objective
from .anchors import anchor_brief
from .llm import Session

LEVELS = ("basic", "medium", "hard")


def slugify(role: str) -> str:
    raw = (role or "").strip()
    if not raw:
        raise ValueError("role required")
    ascii_part = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_part).strip("_").lower()
    if slug:
        return slug[:40]
    return "role_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


BLUEPRINT_SYS = """你是「Agent 能力建模师」。给定一个岗位角色，你要拆出这个角色**真正会被考核**的能力维度。

硬要求：
1. 维度必须可被一段对话考出来（纯文本输入输出、无工具、无代码执行）。不要写"用 Python 跑一下"这类维度。
2. 维度之间不能重叠；每个维度都要能写出"做得好"和"做得差"的可区分表现。
3. 至少有一个维度是**反直觉/易踩坑**的（多数人会答错的地方）。
4. 只输出 JSON，不要解释、不要代码块。

JSON 结构：
{
  "role": "角色名",
  "one_line": "这个角色的一句话职责",
  "dimensions": [
    {"key":"英文小写下划线id","name":"中文维度名","weight":整数(全部之和=100),
     "why":"为什么这个维度对该角色关键（1句）",
     "probe":"用什么样的问题能把这个维度考出来（1句）",
     "failure_modes":["典型失败表现1","典型失败表现2"]}
  ],
  "hard_constraints": ["该角色必须守住的边界/禁止事项"],
  "output_habits": ["该角色高质量回答应有的输出习惯"]
}"""


CASE_SYS = """你是「评测题目与裁判设计师」。给定角色、某个能力维度、难度，产出 1 道**可评分**的对话题。

硬要求：
1. 题面要有具体场景、具体数字/名称、具体干扰项；不能是"请介绍一下 X"这种泛问。
2. 题目必须能区分高低水平：设计一个陷阱（信息不全、指标口径歧义、前提错误、隐含风险等）。
3. criteria 里每个维度给 weight（之和=100），并给 4 档 rubric（90-100 / 70-89 / 60-69 / 0-59），
   每档写**可观察的行为**，不要写"回答得好"这类空话。
4. 纯文本可判：不得要求执行代码、访问文件或联网。
5. 只输出 JSON，不要解释、不要代码块。

JSON 结构：
{
 "title":"短标题",
 "description":"这道题在考什么（1句）",
 "messages":[{"role":"system","content":"场景设定：交给被测 Agent 的场景约束（不要写答案要点）"},
             {"role":"user","content":"用户的真实提问，含具体细节与干扰项"}],
 "requirements":["对回答的硬性要求1","要求2","要求3"],
 "criteria":{"评分维度名":{"weight":整数,"desc":"看什么","rubric":{"90-100":"...","70-89":"...","60-69":"...","0-59":"..."}}},
 "reference_answer":["参考答案要点1","要点2","要点3"],
 "trap":"这道题的陷阱是什么（1句，给裁判看）"
}"""


OBJECTIVE_CASE_SYS = """你是「客观评测题设计师」。产出 1 道**可程序判分**的对话题：判分完全靠字符串与数值断言，不靠人/模型主观评价。

铁律：
1. 题面必须**自带全部数据**（具体数字、口径说明、时间窗），不许要求联网、读文件或跑代码。
2. 必须存在**唯一正确的关键数值**，可由题面数字用四则运算算出。你要同时给出算式 computation，
   且 computation 的计算结果必须**严格等于** target（我会用程序复算，不一致就判你出题错误并丢弃）。
3. 必须埋一个**会导致算错或答错的陷阱**（口径混淆 / 分母选错 / 幸存者偏差 / 辛普森悖论 / 前提错误 /
   相关当因果 / 样本量不足），并用 must_include 要求答题者显式指出它。
4. 必须有一条 must_not_include：答题者若给出某个**典型错误断言或错误数值**就要被扣光这条分。
5. checks 权重之和 = 100。**数值类（numeric）总权重必须在 55–80 之间**，其余分给关键词类。
   原因是实测的：只把 must_include 同义词堆在一起、完全不讲道理的假答案，
   在旧配比（numeric 约 49）下能拿 67.6 分 —— 真实无基因基线才 83.7 分，
   等于八成分数不区分好坏。numeric 是假答案唯一拿不到的部分（见 PERF.md §13）。
6. 只输出 JSON，不要解释、不要代码块。

可用 check 类型与字段：
- {"type":"numeric","id":"...","weight":30,"desc":"...","target":数字,"tolerance":数字,"unit":"%或空",
   "near":["定位关键词"],"computation":"(1200-900)/1200*100"}
- {"type":"must_include","id":"...","weight":25,"desc":"...","groups":[{"label":"要素名","any":["同义词1","同义词2"]}]}
- {"type":"must_not_include","id":"...","weight":15,"desc":"...","groups":[{"label":"错误断言","any":["错误说法1","错误数值 42%"]}]}
- {"type":"ask_back","id":"...","weight":10,"desc":"...","groups":[{"label":"缺失字段","any":["口径","时间窗"]}]}
- {"type":"min_items","id":"...","weight":5,"desc":"...","min":3}
- {"type":"lead_with","id":"...","weight":5,"desc":"...","groups":[{"label":"结论先行","any":["结论","建议"]}],"first_chars":260}

同义词要写**答题者真会用的中文表述**（含常见缩写与英文术语），不要只写一种写法。

JSON 结构：
{
 "title":"短标题",
 "description":"这道题考什么（1句）",
 "messages":[{"role":"system","content":"场景约束，不含答案"},
             {"role":"user","content":"含全部数字与干扰项的真实提问"}],
 "requirements":["对回答的硬性要求（答题者可见）"],
 "ground_truth":{"key_number":"关键数值及其含义","reasoning":"正确解法 2-3 句","trap":"陷阱是什么"},
 "checks":[...]
}"""


async def plan_blueprint(
    session: Session, role: str, anchors: list[dict[str, Any]], *, mode: str = "judge"
) -> dict[str, Any]:
    extra = ""
    if mode == "objective":
        extra = (
            "\n\n额外硬约束（客观评测模式）：每个维度都要能被**可程序判分**的题考出来——"
            "即题面自带数据、存在唯一正确的关键数值或必须显式指出的特定错误。"
            "不要给出只能靠主观品味评价的维度（如「表达优雅」）；"
            "至少 2 个维度以数值计算或统计陷阱识别为核心。"
        )
    user = (
        f"角色：{role}\n\n"
        f"可参考的外部 benchmark 锚点（只借题型与评分口径，不要照搬题面）：\n{anchor_brief(anchors)}\n\n"
        f"请拆出 4-6 个能力维度。{extra}"
    )
    obj = await session.chat_json(
        [{"role": "system", "content": BLUEPRINT_SYS}, {"role": "user", "content": user}],
        purpose="blueprint",
        max_tokens=4096,
        temperature=0.5,
    )
    return normalize_blueprint(obj, role)


def normalize_blueprint(obj: Any, role: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError("blueprint 非对象")
    dims_raw = obj.get("dimensions") or obj.get("dims") or []
    dims: list[dict[str, Any]] = []
    for i, d in enumerate(dims_raw):
        if not isinstance(d, dict):
            continue
        name = str(d.get("name") or d.get("key") or f"维度{i + 1}").strip()
        key = str(d.get("key") or "").strip() or f"dim_{i + 1}"
        key = re.sub(r"[^a-z0-9_]+", "_", key.lower()).strip("_") or f"dim_{i + 1}"
        try:
            weight = int(float(d.get("weight") or 0))
        except (TypeError, ValueError):
            weight = 0
        dims.append(
            {
                "key": key,
                "name": name,
                "weight": max(0, weight),
                "why": str(d.get("why") or "").strip(),
                "probe": str(d.get("probe") or "").strip(),
                "failure_modes": [str(x) for x in (d.get("failure_modes") or [])][:4],
            }
        )
    if not dims:
        raise ValueError("blueprint 无维度")
    total = sum(d["weight"] for d in dims)
    if total <= 0:
        for d in dims:
            d["weight"] = round(100 / len(dims))
    return {
        "role": str(obj.get("role") or role).strip() or role,
        "role_id": slugify(role),
        "one_line": str(obj.get("one_line") or "").strip(),
        "dimensions": dims,
        "hard_constraints": [str(x) for x in (obj.get("hard_constraints") or [])][:8],
        "output_habits": [str(x) for x in (obj.get("output_habits") or [])][:8],
    }


def _norm_criteria(raw: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(raw, dict):
        return out
    for name, spec in raw.items():
        if not isinstance(spec, dict):
            continue
        try:
            w = int(float(spec.get("weight") or 0))
        except (TypeError, ValueError):
            w = 0
        rubric = spec.get("rubric") if isinstance(spec.get("rubric"), dict) else {}
        out[str(name)] = {
            "weight": max(0, w),
            "desc": str(spec.get("desc") or "").strip(),
            "rubric": {str(k): str(v) for k, v in rubric.items()},
        }
    total = sum(v["weight"] for v in out.values())
    if out and total <= 0:
        share = round(100 / len(out))
        for v in out.values():
            v["weight"] = share
    return out


def normalize_case(
    obj: Any, *, role_id: str, dim: dict[str, Any], level: str, idx: int, mode: str = "judge"
) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError("case 非对象")
    msgs_raw = obj.get("messages") or []
    messages: list[dict[str, str]] = []
    for m in msgs_raw:
        if not isinstance(m, dict):
            continue
        role_v = str(m.get("role") or "").strip()
        content = str(m.get("content") or "").strip()
        if role_v in ("system", "user", "assistant") and content:
            messages.append({"role": role_v, "content": content})
    if not any(m["role"] == "user" for m in messages):
        raise ValueError("case 缺 user 消息")
    criteria = _norm_criteria(obj.get("criteria"))
    checks = objective.normalize_checks(obj.get("checks"))
    if mode == "objective":
        if not checks:
            raise ValueError("case 缺可判分的 checks")
    elif not criteria:
        raise ValueError("case 缺 criteria")
    gt = obj.get("ground_truth") if isinstance(obj.get("ground_truth"), dict) else {}
    cid = f"{role_id}_{dim['key']}_{level}_{idx:02d}"
    return {
        "id": cid,
        "level": level if level in LEVELS else "medium",
        "dimension": dim["name"],
        "dimension_key": dim["key"],
        "scoring": "objective" if mode == "objective" else "judge",
        "title": str(obj.get("title") or dim["name"]).strip(),
        "description": str(obj.get("description") or "").strip(),
        "messages": messages,
        "requirements": [str(x) for x in (obj.get("requirements") or [])][:8],
        "criteria": criteria,
        "checks": checks,
        "ground_truth": {str(k): str(v) for k, v in gt.items()},
        "reference_answer": [str(x) for x in (obj.get("reference_answer") or [])][:8],
        "trap": str(obj.get("trap") or gt.get("trap") or "").strip(),
    }


async def gen_case(
    session: Session,
    *,
    blueprint: dict[str, Any],
    dim: dict[str, Any],
    level: str,
    idx: int,
    anchors: list[dict[str, Any]],
    avoid: list[str] | None = None,
) -> dict[str, Any]:
    avoid_txt = ""
    if avoid:
        avoid_txt = "\n\n已有题目标题（不要重复选题角度）：\n" + "\n".join(f"- {t}" for t in avoid[:8])
    user = (
        f"角色：{blueprint['role']}（{blueprint.get('one_line', '')}）\n"
        f"能力维度：{dim['name']}\n"
        f"为什么关键：{dim.get('why', '')}\n"
        f"考法提示：{dim.get('probe', '')}\n"
        f"典型失败表现：{'；'.join(dim.get('failure_modes') or []) or '（未给）'}\n"
        f"该角色硬边界：{'；'.join(blueprint.get('hard_constraints') or []) or '（未给）'}\n"
        f"难度：{level}\n\n"
        f"benchmark 锚点（借题型与评分口径）：\n{anchor_brief(anchors)}"
        f"{avoid_txt}\n\n请产出 1 道题。"
    )
    obj = await session.chat_json(
        [{"role": "system", "content": CASE_SYS}, {"role": "user", "content": user}],
        purpose="case",
        max_tokens=5120,
        temperature=0.75,
    )
    return normalize_case(obj, role_id=blueprint["role_id"], dim=dim, level=level, idx=idx)


async def gen_objective_case(
    session: Session,
    *,
    blueprint: dict[str, Any],
    dim: dict[str, Any],
    level: str,
    idx: int,
    anchors: list[dict[str, Any]],
    attempts: int = 3,
) -> dict[str, Any]:
    """出客观题并自校（复算 target）。自校不过就把问题回喂给模型重出，最多 attempts 次。"""
    base_user = (
        f"角色：{blueprint['role']}（{blueprint.get('one_line', '')}）\n"
        f"能力维度：{dim['name']}\n"
        f"为什么关键：{dim.get('why', '')}\n"
        f"考法提示：{dim.get('probe', '')}\n"
        f"典型失败表现：{'；'.join(dim.get('failure_modes') or []) or '（未给）'}\n"
        f"难度：{level}（hard 要求至少两步计算或需要先纠正题面前提）\n\n"
        f"benchmark 锚点（借题型与判分口径）：\n{anchor_brief(anchors)}\n\n"
        "请产出 1 道可程序判分的题。"
    )
    feedback = ""
    last_problems: list[str] = []
    for attempt in range(attempts):
        obj = await session.chat_json(
            [
                {"role": "system", "content": OBJECTIVE_CASE_SYS},
                {"role": "user", "content": base_user + feedback},
            ],
            purpose="case_objective",
            max_tokens=6144,
            temperature=0.7,
        )
        try:
            case = normalize_case(
                obj, role_id=blueprint["role_id"], dim=dim, level=level, idx=idx, mode="objective"
            )
        except ValueError as exc:
            last_problems = [str(exc)]
            feedback = f"\n\n上一版被判不合格：{exc}\n请修正后重出，仍然只输出 JSON。"
            continue
        ok, problems = objective.verify_case(case)
        if ok:
            case["verify"] = {"passed": True, "attempts": attempt + 1}
            return case
        last_problems = problems
        feedback = (
            "\n\n上一版自校未通过，问题如下，请逐条修正后重出（仍然只输出 JSON）：\n"
            + "\n".join(f"- {p}" for p in problems[:6])
        )
    raise ValueError("出题自校连续失败：" + "；".join(last_problems[:3]))


async def build_suite(
    session: Session,
    blueprint: dict[str, Any],
    anchors: list[dict[str, Any]],
    *,
    per_dim: int = 2,
    on_case=None,
    mode: str = "judge",
) -> list[dict[str, Any]]:
    """每维度出 per_dim 道题，全部并行。难度按 index 轮转 basic→medium→hard。"""
    tasks: list[asyncio.Task] = []
    plan: list[tuple[dict, str, int]] = []
    for dim in blueprint["dimensions"]:
        for i in range(per_dim):
            level = LEVELS[min(i, len(LEVELS) - 1)] if per_dim > 1 else "medium"
            plan.append((dim, level, i + 1))

    async def one(dim: dict, level: str, idx: int) -> dict[str, Any] | None:
        try:
            if mode == "objective":
                case = await gen_objective_case(
                    session, blueprint=blueprint, dim=dim, level=level, idx=idx, anchors=anchors
                )
            else:
                case = await gen_case(
                    session, blueprint=blueprint, dim=dim, level=level, idx=idx, anchors=anchors
                )
        except Exception as exc:  # noqa: BLE001 单题失败不拖垮整批
            if on_case:
                on_case(None, f"{dim['name']}/{level}: {type(exc).__name__}: {exc}")
            return None
        if on_case:
            on_case(case, None)
        return case

    for dim, level, idx in plan:
        tasks.append(asyncio.create_task(one(dim, level, idx)))
    done = await asyncio.gather(*tasks, return_exceptions=True)
    cases = [c for c in done if isinstance(c, dict)]
    cases.sort(key=lambda c: (c["dimension_key"], c["level"], c["id"]))
    return cases


def split_holdout(
    cases: list[dict[str, Any]], *, per_dim: int = 1
) -> tuple[list[dict], list[dict]]:
    """按维度分层切分：每维度最后 `per_dim` 道进 holdout，其余进 train。

    `per_dim` 必须能调，否则 holdout 题量被**维度数**锁死（每维恰好 1 道）：
    把出题量 `per_dim` 从 2 提到 10，train 从 6 涨到 54，而 holdout 还是 6 道。
    而 holdout 题量正是「能不能判定泛化」的瓶颈（见 PERF.md §10.1：
    6 道题时区间半宽下限 1.72 已大于实测效应 1.41，重复多少次都判不了）。

    每维至少留 1 道给 train：train 空了进化就没有可优化的目标。
    """
    keep = max(1, int(per_dim))
    by_dim: dict[str, list[dict]] = {}
    for c in cases:
        by_dim.setdefault(c["dimension_key"], []).append(c)
    train: list[dict] = []
    hold: list[dict] = []
    for _, group in sorted(by_dim.items()):
        group = sorted(group, key=lambda c: c["id"])
        take = min(keep, len(group) - 1)  # 单题维度 take=0 → 全进 train
        if take > 0:
            train.extend(group[:-take])
            hold.extend(group[-take:])
        else:
            train.extend(group)
    return train, hold
