"""作答 + 裁判。裁判按题目自带 criteria/rubric 逐项打分，加权得总分。"""

from __future__ import annotations

import json
from typing import Any

from . import objective
from .llm import Session

JUDGE_SYS = """你是严格的评测裁判。按给定评分维度与 rubric 给被测回答打分。

硬要求：
1. 每个维度独立打 0-100 分，必须落在 rubric 描述的档位区间内，并引用回答中的具体片段作为证据。
2. 严格。没做到就是没做到；模板化、空泛、把要求复述一遍而无实质内容 → 60 分以下。
3. 只输出 JSON，不要解释、不要代码块。

JSON 结构：
{"scores":{"维度名":{"score":整数,"evidence":"回答中的具体证据或缺失点"}},
 "hit_trap": true/false,
 "summary":"一句话总评"}
其中 hit_trap 表示回答是否**识别并处理了**题目的陷阱。"""


def shadow_criteria(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """客观题没有 rubric。做主观对照时给一套通用 rubric，模拟「常见 LLM 裁判」设置。"""
    if case.get("criteria"):
        return case["criteria"]
    return {
        "答案正确性": {
            "weight": 45,
            "desc": "关键数值与结论是否正确",
            "rubric": {
                "90-100": "关键数值算对且口径写明，结论与数据一致",
                "70-89": "方向对，个别数值或口径有偏差",
                "60-69": "只给方法没给数值，或数值明显错",
                "0-59": "答错或答非所问",
            },
        },
        "口径与陷阱": {
            "weight": 35,
            "desc": "是否识别题面埋的陷阱并显式指出",
            "rubric": {
                "90-100": "点出陷阱并说明为何会算错，给出正确处理",
                "70-89": "提到风险但没点透",
                "60-69": "隐含带过",
                "0-59": "直接踩坑",
            },
        },
        "可执行性": {
            "weight": 20,
            "desc": "结论先行、条目清晰、可直接拿去做决策",
            "rubric": {
                "90-100": "结论先行 + 分条 + 明确下一步",
                "70-89": "结构基本清晰",
                "60-69": "冗长需要读者自行提炼",
                "0-59": "无结构",
            },
        },
    }


def compose_messages(variant_system: str, case: dict[str, Any]) -> list[dict[str, str]]:
    """system = 基因组文本 +（题目场景约束）；user/assistant 沿用题面。"""
    case_sys = next((m["content"] for m in case["messages"] if m["role"] == "system"), "")
    sys_parts = [variant_system.strip()]
    if case_sys.strip():
        sys_parts.append(f"【本次场景约束】\n{case_sys.strip()}")
    msgs = [{"role": "system", "content": "\n\n".join(p for p in sys_parts if p)}]
    msgs.extend([m for m in case["messages"] if m["role"] != "system"])
    return msgs


async def answer(
    session: Session, variant: dict[str, Any], case: dict[str, Any], *, rep: int, max_tokens: int = 4096
) -> str:
    # k3 属推理模型，max_tokens 需含推理开销，给足以免空回复重试
    return await session.chat(
        compose_messages(variant["system"], case),
        purpose="answer",
        max_tokens=max_tokens,
        temperature=0.7,
        salt=f"{variant['sig']}|{case['id']}|rep{rep}",
    )


def _criteria_brief(case: dict[str, Any]) -> str:
    lines = []
    for name, spec in case["criteria"].items():
        bands = "；".join(f"{k}: {v}" for k, v in (spec.get("rubric") or {}).items())
        lines.append(f"- {name}（权重{spec['weight']}）{spec.get('desc', '')}\n  档位：{bands}")
    return "\n".join(lines)


async def judge(session: Session, case: dict[str, Any], reply: str) -> dict[str, Any]:
    user = (
        f"【题目】{case['title']}\n{case.get('description', '')}\n\n"
        f"【用户提问】\n"
        + "\n".join(m["content"] for m in case["messages"] if m["role"] == "user")
        + "\n\n【硬性要求】\n"
        + ("\n".join(f"- {r}" for r in case.get("requirements") or []) or "（无）")
        + "\n\n【参考答案要点】\n"
        + ("\n".join(f"- {r}" for r in case.get("reference_answer") or []) or "（无）")
        + f"\n\n【本题陷阱】{case.get('trap') or '（无）'}"
        + f"\n\n【评分维度与 rubric】\n{_criteria_brief(case)}"
        + f"\n\n【被测回答】\n{reply[:12000]}"
    )
    obj = await session.chat_json(
        [{"role": "system", "content": JUDGE_SYS}, {"role": "user", "content": user}],
        purpose="judge",
        max_tokens=4096,
        temperature=0.0,
    )
    return score_of(obj, case)


def score_of(obj: Any, case: dict[str, Any]) -> dict[str, Any]:
    scores_raw = obj.get("scores") if isinstance(obj, dict) else None
    if not isinstance(scores_raw, dict):
        raise ValueError("judge 缺 scores")
    by_dim: dict[str, dict[str, Any]] = {}
    total_w = 0.0
    acc = 0.0
    for name, spec in case["criteria"].items():
        got = scores_raw.get(name)
        if not isinstance(got, dict):
            # 名称不完全一致时做一次宽松匹配
            got = next(
                (v for k, v in scores_raw.items() if isinstance(v, dict) and (k in name or name in k)),
                None,
            )
        if not isinstance(got, dict):
            continue
        try:
            s = float(got.get("score"))
        except (TypeError, ValueError):
            continue
        s = max(0.0, min(100.0, s))
        w = float(spec.get("weight") or 0)
        by_dim[name] = {"score": round(s, 1), "weight": w, "evidence": str(got.get("evidence") or "")[:400]}
        total_w += w
        acc += s * w
    if total_w <= 0:
        raise ValueError("judge 无有效维度分")
    return {
        "total": round(acc / total_w, 2),
        "by_criterion": by_dim,
        "hit_trap": bool(obj.get("hit_trap")) if isinstance(obj, dict) else False,
        "summary": str(obj.get("summary") or "")[:300] if isinstance(obj, dict) else "",
    }


async def eval_one(
    session: Session,
    variant: dict[str, Any],
    case: dict[str, Any],
    *,
    rep: int,
    mode: str = "judge",
    shadow_judge: bool = False,
) -> dict[str, Any]:
    """mode=objective 时用程序化断言打分（不过 LLM）；shadow_judge 只做对照，不参与选种。"""
    reply = await answer(session, variant, case, rep=rep)
    row: dict[str, Any] = {
        "variant": variant["id"],
        "sig": variant["sig"],
        "case": case["id"],
        "dimension_key": case["dimension_key"],
        "dimension": case["dimension"],
        "rep": rep,
        "mode": mode,
        "reply_chars": len(reply),
        "reply": reply,
    }
    if mode == "objective":
        # 打分前再过一遍 normalize_checks。新题在出题时已归一化，这里是**幂等**的；
        # 意义在旧 run 的 holdout 复核：那批题是旧口径生成的（权重未归一、同义词里
        # 泄着 numeric 答案），直接拿来打分就会写出「标称 v3、实际按旧尺子量」的结果，
        # 而 scorer_version 会理直气壮地写 3（PERF.md §14）。
        checks = objective.normalize_checks([dict(c) for c in (case.get("checks") or [])])
        res = objective.score_answer(reply, checks)
        if res.get("total") is None:
            raise ValueError(f"客观打分失败：{res.get('note')}")
        row.update(
            {
                "score": res["total"],
                "checks": res["checks"],
                "checks_passed": res.get("passed"),
                "checks_count": res.get("count"),
                "hit_trap": _trap_from_checks(res["checks"]),
            }
        )
        if shadow_judge:
            try:
                jres = await judge(session, {**case, "criteria": shadow_criteria(case)}, reply)
                row["judge_score"] = jres["total"]
                row["judge_summary"] = jres["summary"]
            except Exception as exc:  # noqa: BLE001 对照失败不影响主分
                row["judge_error"] = f"{type(exc).__name__}: {exc}"
        return row

    res = await judge(session, case, reply)
    row.update(
        {
            "score": res["total"],
            "hit_trap": res["hit_trap"],
            "summary": res["summary"],
            "by_criterion": res["by_criterion"],
        }
    )
    return row


def _trap_from_checks(checks: list[dict[str, Any]]) -> bool | None:
    """陷阱识别率：以 must_include 里带 trap 语义的条目为准，没有就返回 None。"""
    rows = [c for c in checks if c["type"] == "must_include"]
    if not rows:
        return None
    return all(c["score"] >= 0.999 for c in rows)


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)
