#!/usr/bin/env python3
"""提交前扫一遍暂存内容里的凭证。

由来：一次 `git add -A` 把 `console/_workbench/运行数据/agent-bridge/providers.json`
扫进了提交并推到了 GitHub。那个文件**正是放模型凭证的地方** ——
这次核查是 4 字节空对象，所以没泄露，但那是运气。

设计上的两条纪律（都会决定这东西是否真的有用）：

1. **不能误报**。误报一次人就加 `--no-verify`，加两次就把钩子删了 ——
   于是"有钩子"变成纯粹的心理安慰。所以只匹配"确实带值"的模式：
   文档里写 `api_key` 这个词、代码里读 `os.environ["API_KEY"]` 都不能拦。
2. **不能漏报**。漏报比没有更糟：它给人一种"扫过了所以安全"的错觉。
   所以覆盖真实会出现的形态（sk- 开头、Bearer、AKIA、私钥头、赋值带长值）。

用法：python scripts/hooks/scan_secrets.py [--staged | 文件...]
退出码：0 干净 / 1 命中
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# (名字, 正则)。一律要求**有值**，而不是只出现关键词。
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # OpenAI / Moonshot / Anthropic 风格：sk- 开头的长串
    ("sk- 形式的密钥", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}")),
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b")),
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack Token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}\b")),
    ("Bearer 令牌", re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{24,}")),
    ("私钥文件头", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    # 赋值形态：key/secret/token/password = "足够长的字面值"
    # 关键在于**排除**占位符与环境变量读取，否则误报会淹掉真信号
    (
        "疑似硬编码凭证赋值",
        re.compile(
            r"""(?ix)
            \b(?:api[_-]?key|secret|token|password|passwd|access[_-]?key)\b
            \s*[:=]\s*
            ['"]([^'"\s]{16,})['"]
            """
        ),
    ),
]

# 占位符白名单：这些"值"不是凭证。命中后需再过一遍这里。
PLACEHOLDER = re.compile(
    r"""(?ix)
    ^(?:
      \$\{.*\}            |   # ${VAR}
      \{\{.*\}\}          |   # {{ var }}
      (?:your|my|the)[_\-]?.* |
      x{6,}               |
      \*{6,}              |
      \.{3,}              |
      (?:changeme|placeholder|example|sample|dummy|redacted|test|fake|none|null)\b.*  |
      (?:sk-)?(?:xxx|abc123|1234).*
    )$
    """
)
# 明显是"从环境读"的写法，整行跳过
ENV_READ = re.compile(r"(?i)(os\.environ|getenv|process\.env|System\.getenv|\$env:)")

# 显式豁免标记。**必须逐行标注，不支持整文件豁免** ——
# 整文件豁免会随时间腐化（文件后来加进了真凭证也没人知道），逐行则可被 review 与 grep 审计。
#
# 这个机制不是"为了方便"加的：钩子第一次真用就拦下了它自己的测试文件
# （`tests/test_scan_secrets.py` 里必然写着假密钥）。当时有两条路 ——
# 用 `--no-verify` 绕过（等于开始训练自己忽略告警），或把豁免做成显式且可审计的。
# 选后者。
ALLOWLIST = re.compile(r"(?i)(allowlist[\s-]secret|pragma:\s*allowlist)")

SKIP_SUFFIX = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".sqlite", ".db", ".woff", ".woff2", ".ttf", ".mp4", ".mp3", ".whl",
}
MAX_BYTES = 2_000_000
SELF = Path(__file__).name


def staged_files() -> list[Path]:
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return [Path(p) for p in (r.stdout or "").splitlines() if p.strip()]


def scan_text(text: str) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    for i, line in enumerate(text.splitlines(), 1):
        if ENV_READ.search(line) or ALLOWLIST.search(line):
            continue
        for name, pat in PATTERNS:
            m = pat.search(line)
            if not m:
                continue
            val = m.group(1) if m.groups() else m.group(0)
            if PLACEHOLDER.match(val.strip()):
                continue
            masked = val[:4] + "…" + val[-2:] if len(val) > 8 else "…"
            hits.append((i, name, masked))
            break
    return hits


def scan_file(p: Path) -> list[tuple[int, str, str]]:
    if p.suffix.lower() in SKIP_SUFFIX or not p.is_file():
        return []
    # 别扫自己：这个文件里全是凭证的**正则**，扫自己必然自爆
    if p.name == SELF:
        return []
    try:
        if p.stat().st_size > MAX_BYTES:
            return []
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return []
    return scan_text(text)


def main() -> int:
    ap = argparse.ArgumentParser(description="扫暂存内容里的凭证")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--staged", action="store_true", help="扫 git 暂存区（钩子用这个）")
    args = ap.parse_args()

    targets = staged_files() if (args.staged or not args.files) else [Path(f) for f in args.files]
    bad: list[tuple[Path, int, str, str]] = []
    for p in targets:
        for line, name, masked in scan_file(p):
            bad.append((p, line, name, masked))

    if not bad:
        return 0

    print("✗ 提交被拦下：暂存内容里发现疑似凭证\n", file=sys.stderr)
    for p, line, name, masked in bad:
        print(f"  {p}:{line}  {name}  值≈{masked}", file=sys.stderr)
    print(
        "\n处置：\n"
        "  · 真是凭证 → 从暂存区移除（git restore --staged <file>），"
        "改从环境变量读，并把文件加进 .gitignore\n"
        "  · **已经推过** → 换掉那把密钥。删提交不等于撤销泄露，"
        "GitHub 上的历史与缓存仍可取到\n"
        "  · 确认是误报 → 在那一行加 `allowlist secret` 注释（逐行、可审计），"
        "或收窄模式\n"
        "    最后手段才是 git commit --no-verify —— 绕过一次，"
        "下次就更容易再绕一次",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
