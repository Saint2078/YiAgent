"""Judge v2 (ported from XSCT research runner) — 0–100 dims + weight average."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from kimi_client import chat_completions, extract_content


def parse_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("no json object")
    raw = m.group(0)
    try:
        return json.loads(raw)
    except Exception:
        raw2 = re.sub(r",\s*}", "}", raw)
        raw2 = re.sub(r",\s*]", "]", raw2)
        return json.loads(raw2)


def dim_scores(criteria: dict, dims: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, meta in criteria.items():
        if not isinstance(meta, dict):
            continue
        ds = dims.get(name)
        s = ds.get("score") if isinstance(ds, dict) else ds
        if s is None:
            continue
        out[name] = float(s)
    return out


def weighted(criteria: dict, scores: dict[str, float]) -> float | None:
    tw = acc = 0.0
    for name, meta in criteria.items():
        if not isinstance(meta, dict):
            continue
        w = float(meta.get("weight") or 0)
        if w <= 0 or name not in scores:
            continue
        acc += scores[name] * w
        tw += w
    return round(acc / tw, 2) if tw else None


def scale_diagnostics(criteria: dict, scores: dict[str, float]) -> dict[str, Any]:
    if not scores:
        return {"ok": False, "reason": "empty_dims"}
    vals = list(scores.values())
    mx, mn = max(vals), min(vals)
    weights = {
        n: float(m["weight"])
        for n, m in criteria.items()
        if isinstance(m, dict) and float(m.get("weight") or 0) > 0
    }
    if mx <= 10.5 and mn >= 0:
        return {
            "ok": False,
            "reason": "scale_0_10",
            "fix": "multiply_10",
            "fixed": {k: round(min(100.0, v * 10.0), 2) for k, v in scores.items()},
        }
    if mx <= 45 and all(name in weights for name in scores):
        ratios = []
        for name, s in scores.items():
            w = weights[name]
            if w <= 0:
                continue
            ratios.append(s / w)
        if ratios and min(ratios) >= 0.5 and max(ratios) <= 1.05:
            return {
                "ok": False,
                "reason": "weight_share_scale",
                "fix": "share_to_100",
                "fixed": {
                    k: round(min(100.0, (scores[k] / weights[k]) * 100.0), 2) for k in scores
                },
            }
    if mx > 45 or mx >= 60:
        return {"ok": True, "reason": "scale_0_100"}
    return {"ok": False, "reason": "ambiguous_low_band", "fix": "retry"}


def build_judge_messages(body: dict, content: str) -> list[dict]:
    requirements = body.get("requirements") or []
    criteria = body.get("criteria") or {}
    ref = body.get("reference_answer")
    ref_text = "\n\n".join(map(str, ref)) if isinstance(ref, list) else str(ref or "")
    crit_lines = []
    for k, v in criteria.items():
        if not isinstance(v, dict):
            continue
        rub = v.get("rubric") or []
        if isinstance(rub, dict):
            rub_txt = " | ".join(f"{kk}:{vv}" for kk, vv in rub.items())
        elif isinstance(rub, list):
            rub_txt = " | ".join(map(str, rub))
        else:
            rub_txt = str(rub)
        crit_lines.append(
            f"- {k}: weight={v.get('weight')} (仅用于加权，不是该维满分)\n"
            f"  desc={v.get('desc')}\n"
            f"  rubric={rub_txt}"
        )
    system = (
        "你是严格但标尺正确的裁判。只输出合法 JSON。\n"
        "硬性规则：\n"
        "1) dimension_scores.*.score 必须是 0–100 百分制，对照各维 rubric 的 90-100/70-89/… 档。\n"
        "2) 禁止把 weight 当作该维满分打「份额分」。\n"
        "3) 禁止 0–10 分制。优秀作答应各维通常 ≥85。\n"
        "4) overall_score = 各维 score 按 weight 加权平均。\n"
        "5) reason 简短；字符串内勿未转义换行。"
    )
    user = f"""只输出一个合法 JSON 对象，不要 markdown。schema：
{{"dimension_scores":{{"<dim>":{{"score":0-100,"reason":"短"}}}},"overall_score":0-100,"overall_comment":"短","hard_requirement_fails":[],"scale_check":"each_dim_0_to_100"}}

requirements:
{json.dumps(requirements, ensure_ascii=False)}

criteria:
{chr(10).join(crit_lines)}

reference_answer:
{ref_text[:5000]}

candidate_output:
{content[:10000]}
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def normalize_judgment(criteria: dict, judged: dict) -> dict[str, Any]:
    dims_raw = judged.get("dimension_scores") or {}
    scores = dim_scores(criteria, dims_raw)
    diag = scale_diagnostics(criteria, scores)
    applied = None
    final_scores = scores
    if not diag.get("ok") and diag.get("fix") in ("multiply_10", "share_to_100"):
        final_scores = diag["fixed"]
        applied = diag["reason"]
        fixed_dims = {}
        for name, meta in dims_raw.items():
            if name not in final_scores:
                fixed_dims[name] = meta
                continue
            if isinstance(meta, dict):
                fixed_dims[name] = {**meta, "score": final_scores[name], "rescale": applied}
            else:
                fixed_dims[name] = final_scores[name]
        judged = {**judged, "dimension_scores": fixed_dims}
    w = weighted(criteria, final_scores)
    score = w
    if score is None:
        try:
            score = float(judged.get("overall_score")) if judged.get("overall_score") is not None else None
        except Exception:
            score = None
    ok = bool(diag.get("ok")) or applied is not None or (score is not None and score >= 50)
    if score is not None and final_scores and max(final_scores.values()) >= 60:
        ok = True
    judged["overall_score_weighted"] = score
    if applied:
        judged["scale_fix_applied"] = applied
    return {"ok": ok, "score": score, "judgment": judged, "scores_used": final_scores, "diag": diag}


def judge_once(api_key: str, model: str, body: dict, content: str) -> dict[str, Any]:
    criteria = body.get("criteria") or {}
    raw = extract_content(
        chat_completions(api_key, model, build_judge_messages(body, content), max_tokens=1600)
    )
    judged = parse_json(raw)
    return normalize_judgment(criteria, judged)


def judge_with_retries(
    api_key: str, model: str, body: dict, content: str, max_attempts: int = 3
) -> dict[str, Any]:
    last = None
    attempts = []
    for i in range(max_attempts):
        try:
            result = judge_once(api_key, model, body, content)
            attempts.append({"attempt": i + 1, "ok": result["ok"], "score": result["score"]})
            last = result
            if result["ok"]:
                last["attempts"] = attempts
                return last
            if result["diag"].get("fix") == "retry":
                time.sleep(0.6)
                continue
            if result["score"] is not None and result["judgment"].get("scale_fix_applied"):
                last["attempts"] = attempts
                return last
        except Exception as e:  # noqa: BLE001
            attempts.append({"attempt": i + 1, "error": str(e)})
            time.sleep(0.8)
    if last is None:
        raise RuntimeError(f"judge failed: {attempts}")
    last["attempts"] = attempts
    last["ok"] = False
    return last
