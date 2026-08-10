"""从模型输出抽取 python 代码块。"""
from __future__ import annotations

import re


def extract_python(text: str) -> str:
    if not text:
        return ""
    # ```python ... ```
    blocks = re.findall(r"```(?:python|Python)\s*\n([\s\S]*?)```", text)
    if blocks:
        return blocks[-1].strip() + "\n"
    blocks = re.findall(r"```\s*\n([\s\S]*?)```", text)
    if blocks:
        return blocks[-1].strip() + "\n"
    return text.strip() + ("\n" if text.strip() else "")
