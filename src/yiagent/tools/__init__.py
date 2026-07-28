"""Pi-style builtin tools: read / write / edit / bash (cwd-scoped)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

ToolFn = Callable[..., str]


class ToolError(RuntimeError):
    pass


def _safe_path(cwd: Path, path: str) -> Path:
    raw = Path(path)
    target = (cwd / raw).resolve() if not raw.is_absolute() else raw.resolve()
    root = cwd.resolve()
    try:
        target.relative_to(root)
    except ValueError as e:
        raise ToolError(f"path escapes workspace: {path}") from e
    return target


def make_tools(cwd: str | Path | None = None) -> dict[str, ToolFn]:
    root = Path(cwd or os.getcwd()).resolve()

    def read_file(path: str, offset: int = 1, limit: int = 400) -> str:
        p = _safe_path(root, path)
        if not p.is_file():
            raise ToolError(f"not a file: {path}")
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(1, int(offset)) - 1
        end = start + max(1, int(limit))
        chunk = lines[start:end]
        numbered = [f"{i + start + 1:>6}|{line}" for i, line in enumerate(chunk)]
        return "\n".join(numbered) if numbered else "(empty)"

    def write_file(path: str, content: str) -> str:
        p = _safe_path(root, path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content if content is not None else "", encoding="utf-8")
        return f"wrote {p.relative_to(root)} ({len(content or '')} chars)"

    def edit_file(path: str, old_string: str, new_string: str) -> str:
        p = _safe_path(root, path)
        if not p.is_file():
            raise ToolError(f"not a file: {path}")
        text = p.read_text(encoding="utf-8")
        if old_string not in text:
            raise ToolError("old_string not found")
        count = text.count(old_string)
        if count > 1:
            raise ToolError(f"old_string matches {count} times; make it unique")
        p.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")
        return f"edited {p.relative_to(root)}"

    def bash(command: str, timeout: int = 60) -> str:
        if not command or not str(command).strip():
            raise ToolError("empty command")
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=max(1, int(timeout)),
            )
        except subprocess.TimeoutExpired as e:
            raise ToolError(f"timeout after {timeout}s") from e
        out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        out = out.strip() or "(no output)"
        if proc.returncode != 0:
            return f"exit {proc.returncode}\n{out}"
        return out

    return {
        "read": read_file,
        "write": write_file,
        "edit": edit_file,
        "bash": bash,
    }


OPENAI_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read a text file under the workspace (numbered lines).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer", "description": "1-based start line"},
                    "limit": {"type": "integer", "description": "max lines"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": "Write/create a text file under the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit",
            "description": "Replace an exact unique substring in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command in the workspace cwd.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
                "required": ["command"],
            },
        },
    },
]


def dispatch(tools: dict[str, ToolFn], name: str, arguments: dict[str, Any] | str) -> str:
    fn = tools.get(name)
    if not fn:
        return f"error: unknown tool {name}"
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) if arguments.strip() else {}
        except json.JSONDecodeError:
            return f"error: invalid JSON arguments: {arguments[:200]}"
    if not isinstance(arguments, dict):
        return "error: arguments must be an object"
    try:
        return fn(**arguments)
    except TypeError as e:
        return f"error: bad arguments: {e}"
    except ToolError as e:
        return f"error: {e}"
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"
