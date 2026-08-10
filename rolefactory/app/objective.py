"""客观评分：把「答得好不好」拆成可程序校验的断言，纯 Python 打分，不过 LLM。

设计目标是**可复算**：同一份回答任何时候打出同一个分，分差不依赖裁判心情，也不吃同族模型
的天花板。代价是题目必须设计成有可验证答案（题面自带数据、关键结论唯一）。

check 类型：
- numeric        关键数值算对（支持 near 定位、单位、万/亿、百分比互认、容差）
- must_include   必须覆盖的要素（分组同义词，按组给部分分）
- must_not_include 禁止出现的错误断言（命中即 0）
- ask_back       信息不足时必须回问（要有问号 + 命中缺口关键词）
- min_items      必须列够条数（枚举行计数）
- lead_with      结论先行（关键词须出现在前 N 字符内）
- regex          自定义正则

总分 = Σ(weight × 该 check 得分) / Σweight × 100，得分∈[0,1]。
"""

from __future__ import annotations

import ast
import operator
import re
from typing import Any

CHECK_TYPES = (
    "numeric",
    "must_include",
    "must_not_include",
    "ask_back",
    "min_items",
    "lead_with",
    "regex",
)

_FULL_TO_HALF = str.maketrans(
    "０１２３４５６７８９％．，（）：；－ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ",
    "0123456789%.,():;-ABCDEFGHIJKLMNOPQRSTUVWXYZ",
)

_NUM = re.compile(r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|[-+]?\.\d+")
_SCALE = {"万": 1e4, "萬": 1e4, "亿": 1e8, "億": 1e8, "千": 1e3, "k": 1e3, "K": 1e3, "m": 1e6, "M": 1e6}
_ITEM_LINE = re.compile(r"^\s*(?:[-*•·]|\d+[.、)]|\(\d+\)|[一二三四五六七八九十]+[、.])\s*\S")


def normalize(text: str) -> str:
    t = str(text or "").translate(_FULL_TO_HALF)
    t = t.replace("％", "%").replace("\u00a0", " ")
    t = re.sub(r"[*_`#>]+", "", t)  # markdown 装饰不参与匹配
    return t


def _numbers_in(text: str) -> list[float]:
    out: list[float] = []
    for m in _NUM.finditer(text):
        raw = m.group(0).replace(",", "")
        try:
            val = float(raw)
        except ValueError:
            continue
        tail = text[m.end() : m.end() + 2]
        scale = 1.0
        for token, mult in _SCALE.items():
            if tail.startswith(token):
                scale = mult
                break
        out.append(val * scale)
        if scale != 1.0:
            out.append(val)
    return out


def _windows(text: str, near: list[str], width: int) -> list[str]:
    if not near:
        return [text]
    low = text.lower()
    spans: list[str] = []
    for kw in near:
        k = str(kw).lower().strip()
        if not k:
            continue
        start = 0
        while True:
            i = low.find(k, start)
            if i < 0:
                break
            spans.append(text[max(0, i - width) : i + len(k) + width])
            start = i + len(k)
    return spans or []


def _hit_numeric(text: str, spec: dict[str, Any]) -> tuple[float, str]:
    try:
        target = float(spec.get("target"))
    except (TypeError, ValueError):
        return 0.0, "check 缺 target"
    tol_raw = spec.get("tolerance")
    try:
        tol = float(tol_raw)
    except (TypeError, ValueError):
        tol = abs(target) * 0.02
    tol = max(tol, abs(target) * 1e-6)
    unit = str(spec.get("unit") or "").strip()
    near = [str(x) for x in (spec.get("near") or []) if str(x).strip()]
    width = int(spec.get("window") or 90)

    scopes = _windows(text, near, width)
    if near and not scopes:
        return 0.0, f"未提到 {near[0]} 附近的数值"
    for scope in scopes:
        for v in _numbers_in(scope):
            if abs(v - target) <= tol:
                return 1.0, f"命中 {v}（目标 {target}±{tol}）"
            if unit == "%" and abs(v * 100 - target) <= tol:
                return 1.0, f"命中 {v}（小数形式，等价 {v * 100}%）"
            if unit == "%" and abs(v / 100 - target) <= tol:
                return 1.0, f"命中 {v}（百分数形式，等价 {v / 100}）"
    return 0.0, f"未算出 {target}{unit}"


def _groups_of(spec: dict[str, Any]) -> list[tuple[str, list[str]]]:
    raw = spec.get("groups") or spec.get("any_of") or spec.get("keywords") or []
    out: list[tuple[str, list[str]]] = []
    for i, g in enumerate(raw):
        if isinstance(g, dict):
            label = str(g.get("label") or f"要素{i + 1}")
            syns = [str(x) for x in (g.get("any") or g.get("synonyms") or []) if str(x).strip()]
        elif isinstance(g, (list, tuple)):
            syns = [str(x) for x in g if str(x).strip()]
            label = syns[0] if syns else f"要素{i + 1}"
        else:
            syns = [str(g)]
            label = str(g)
        if syns:
            out.append((label, syns))
    return out


def _hit_must_include(text: str, spec: dict[str, Any]) -> tuple[float, str]:
    groups = _groups_of(spec)
    if not groups:
        return 0.0, "check 缺 groups"
    low = text.lower()
    hit, miss = [], []
    for label, syns in groups:
        if any(s.lower() in low for s in syns):
            hit.append(label)
        else:
            miss.append(label)
    score = len(hit) / len(groups)
    return score, f"覆盖 {len(hit)}/{len(groups)}" + (f"，缺：{'、'.join(miss[:4])}" if miss else "")


def _hit_must_not_include(text: str, spec: dict[str, Any]) -> tuple[float, str]:
    groups = _groups_of(spec)
    low = text.lower()
    bad = [label for label, syns in groups if any(s.lower() in low for s in syns)]
    if bad:
        return 0.0, f"出现禁止表述：{'、'.join(bad[:4])}"
    return 1.0, "无禁止表述"


def _hit_ask_back(text: str, spec: dict[str, Any]) -> tuple[float, str]:
    groups = _groups_of(spec)
    has_q = "?" in text or "？" in text or any(k in text for k in ("请确认", "需要确认", "想先确认", "能否提供"))
    if not groups:
        return (1.0, "有回问") if has_q else (0.0, "未回问")
    cover, _ = _hit_must_include(text, spec)
    score = cover * (1.0 if has_q else 0.5)
    return score, f"缺口覆盖 {cover:.2f}｜{'有' if has_q else '无'}明确回问"


def _hit_min_items(text: str, spec: dict[str, Any]) -> tuple[float, str]:
    need = max(1, int(spec.get("min") or spec.get("n") or 3))
    count = sum(1 for line in text.splitlines() if _ITEM_LINE.match(line))
    if count == 0:
        count = len(re.findall(r"(?:^|\n)\s*(?:第[一二三四五六七八九十]+|其[一二三四五六七八九十])", text))
    return min(1.0, count / need), f"枚举 {count} 条（要求 ≥{need}）"


def _hit_lead_with(text: str, spec: dict[str, Any]) -> tuple[float, str]:
    groups = _groups_of(spec)
    span = int(spec.get("first_chars") or 260)
    head = text[:span].lower()
    if not groups:
        return 0.0, "check 缺 groups"
    hit = [label for label, syns in groups if any(s.lower() in head for s in syns)]
    return (1.0, f"前 {span} 字内出现：{hit[0]}") if hit else (0.0, f"前 {span} 字内未先给结论")


def _hit_regex(text: str, spec: dict[str, Any]) -> tuple[float, str]:
    pat = str(spec.get("pattern") or "")
    if not pat:
        return 0.0, "check 缺 pattern"
    try:
        rx = re.compile(pat, re.I | re.S)
    except re.error as exc:
        return 0.0, f"正则非法：{exc}"
    m = rx.search(text)
    return (1.0, f"匹配 {m.group(0)[:40]}") if m else (0.0, "未匹配")


_HANDLERS = {
    "numeric": _hit_numeric,
    "must_include": _hit_must_include,
    "must_not_include": _hit_must_not_include,
    "ask_back": _hit_ask_back,
    "min_items": _hit_min_items,
    "lead_with": _hit_lead_with,
    "regex": _hit_regex,
}


def score_answer(reply: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    """纯确定性打分。返回 total(0-100) 与逐条明细。"""
    text = normalize(reply)
    rows: list[dict[str, Any]] = []
    acc = 0.0
    wsum = 0.0
    for spec in checks or []:
        ctype = str(spec.get("type") or "").strip()
        handler = _HANDLERS.get(ctype)
        try:
            w = float(spec.get("weight") or 0)
        except (TypeError, ValueError):
            w = 0.0
        if handler is None or w <= 0:
            continue
        try:
            got, note = handler(text, spec)
        except Exception as exc:  # noqa: BLE001 单条 check 异常不影响其余
            got, note = 0.0, f"check 异常：{type(exc).__name__}"
        got = max(0.0, min(1.0, float(got)))
        rows.append(
            {
                "id": str(spec.get("id") or ctype),
                "type": ctype,
                "weight": w,
                "score": round(got, 3),
                "note": note,
                "desc": str(spec.get("desc") or ""),
            }
        )
        acc += got * w
        wsum += w
    if wsum <= 0:
        return {"total": None, "checks": rows, "note": "无有效 check"}
    return {
        "total": round(acc / wsum * 100, 2),
        "checks": rows,
        "passed": sum(1 for r in rows if r["score"] >= 0.999),
        "count": len(rows),
    }


# ------------------------------------------------------------------ 出题自校

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_eval(expr: str) -> float:
    """只允许四则运算与括号的算术求值（校验出题给的 target 是否自洽）。"""
    e = str(expr or "").strip()
    e = e.replace("×", "*").replace("÷", "/").replace("，", "").replace(",", "")
    e = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", e)
    e = re.sub(r"[^0-9.+\-*/()\s]", "", e)
    if not e:
        raise ValueError("空表达式")

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError("非数字常量")
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError(f"不允许的表达式节点：{type(node).__name__}")

    return float(ev(ast.parse(e, mode="eval")))


def normalize_checks(raw: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for i, spec in enumerate(raw):
        if not isinstance(spec, dict):
            continue
        ctype = str(spec.get("type") or "").strip()
        if ctype not in CHECK_TYPES:
            continue
        try:
            w = float(spec.get("weight") or 0)
        except (TypeError, ValueError):
            w = 0.0
        if w <= 0:
            continue
        item = {k: v for k, v in spec.items() if k != "weight"}
        item["weight"] = w
        item["id"] = str(spec.get("id") or f"{ctype}_{i + 1}")
        out.append(item)
    return out


def verify_case(case: dict[str, Any]) -> tuple[bool, list[str]]:
    """出题自校：结构完整 + numeric 的 target 与 computation 自洽 + 权重和合理。

    自校不过的题会被丢弃重生成——避免用错的标准答案打分。
    """
    problems: list[str] = []
    checks = case.get("checks") or []
    if not checks:
        problems.append("无 check")
    kinds = {str(c.get("type")) for c in checks}
    if "numeric" not in kinds:
        problems.append("缺至少 1 个 numeric（客观题必须有可算的关键数值）")
    if "must_not_include" not in kinds:
        problems.append("缺 must_not_include（需要一条禁止性断言防套话）")
    wsum = sum(float(c.get("weight") or 0) for c in checks)
    if wsum <= 0:
        problems.append("权重和为 0")

    for c in checks:
        if str(c.get("type")) != "numeric":
            continue
        cid = c.get("id")
        comp = c.get("computation")
        if not comp:
            problems.append(f"{cid}: 缺 computation（无法复算 target）")
            continue
        try:
            got = safe_eval(str(comp))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{cid}: computation 无法求值（{exc}）")
            continue
        try:
            target = float(c.get("target"))
        except (TypeError, ValueError):
            problems.append(f"{cid}: target 非数字")
            continue
        tol = max(abs(target) * 0.01, 1e-9)
        try:
            tol = max(tol, float(c.get("tolerance")))
        except (TypeError, ValueError):
            pass
        if abs(got - target) > tol:
            problems.append(f"{cid}: computation={got:.4f} 与 target={target} 不一致，判为出题错误")

    user_text = "\n".join(m["content"] for m in case.get("messages") or [] if m.get("role") == "user")
    if len(_numbers_in(normalize(user_text))) < 3:
        problems.append("题面数字太少，无法自带数据求解")
    return (not problems), problems
