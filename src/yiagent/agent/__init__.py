"""Pi-style agent session: genome system + tool loop."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Callable

from yiagent.genome import assemble_from_ids, assemble_system, load_bank
from yiagent.providers import (
    TokenMeter,
    chat_completions,
    extract_content,
    resolve_api_key,
)
from yiagent.tools import OPENAI_TOOL_SPECS, dispatch, make_tools

DEFAULT_HOST = (
    "你是 YiAgent 实体运行时：按已装载的 G1–G5 基因组行事。"
    "需要读文件、改文件或跑命令时，使用提供的工具；完成后用自然语言回答用户。"
)


class AgentSession:
    """Minimal Pi-like harness: messages + tools + genome-assembled system."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        system: str | None = None,
        bank: dict[str, Any] | str | Path | None = None,
        variant_id: str | None = None,
        host: str | None = None,
        cwd: str | Path | None = None,
        max_turns: int = 16,
        enable_tools: bool = True,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or resolve_api_key(model=model)
        self.cwd = Path(cwd or Path.cwd()).resolve()
        self.max_turns = max(1, int(max_turns))
        self.enable_tools = enable_tools
        self.on_event = on_event
        self.meter = TokenMeter()
        self.tools = make_tools(self.cwd) if enable_tools else {}
        self.bank: dict[str, Any] | None = None
        self.variant: dict[str, Any] | None = None

        if system:
            sys_text = system
        elif variant_id:
            sys_text, self.bank, self.variant = assemble_from_ids(
                host=host or DEFAULT_HOST,
                bank=bank,
                variant_id=variant_id,
            )
        else:
            # Default demo genome
            b = load_bank(bank)
            self.bank = b
            variants = b.get("variants") or []
            if not variants:
                raise ValueError("bank has no variants")
            self.variant = variants[0]
            sys_text = assemble_system(host or DEFAULT_HOST, b, self.variant)

        self.messages: list[dict[str, Any]] = [{"role": "system", "content": sys_text}]

    def _emit(self, kind: str, **payload: Any) -> None:
        if self.on_event:
            self.on_event({"type": kind, **payload})

    def prompt(self, user: str, *, stream_text: bool = False) -> str:
        """Run one user turn through the tool loop; return final assistant text."""
        self.messages.append({"role": "user", "content": user})
        self._emit("user", text=user)
        return self._loop(stream_text=stream_text)

    def _loop(self, *, stream_text: bool = False) -> str:
        tools_param = OPENAI_TOOL_SPECS if self.enable_tools else None
        final = ""
        with self.meter.activate():
            for _ in range(self.max_turns):
                kwargs: dict[str, Any] = {
                    "api_key": self.api_key,
                    "model": self.model,
                    "messages": self.messages,
                    "purpose": "agent",
                    "max_tokens": 4096,
                }
                if tools_param:
                    kwargs["tools"] = tools_param
                resp = chat_completions(**kwargs)
                msg = ((resp.get("choices") or [{}])[0].get("message")) or {}
                content = extract_content(resp)
                tool_calls = msg.get("tool_calls") or []

                if tool_calls and self.enable_tools:
                    # Persist assistant message with tool_calls
                    assistant_msg: dict[str, Any] = {
                        "role": "assistant",
                        "content": content or None,
                        "tool_calls": tool_calls,
                    }
                    self.messages.append(assistant_msg)
                    self._emit("assistant_tools", tool_calls=tool_calls, text=content or "")
                    for tc in tool_calls:
                        tid = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                        fn = (tc.get("function") or {}) if isinstance(tc, dict) else {}
                        name = fn.get("name") or ""
                        raw_args = fn.get("arguments") or "{}"
                        self._emit("tool_call", name=name, arguments=raw_args, id=tid)
                        result = dispatch(self.tools, name, raw_args)
                        self._emit("tool_result", name=name, id=tid, result=result[:4000])
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tid,
                                "content": result[:12000],
                            }
                        )
                    continue

                # No tools — final answer
                final = content
                self.messages.append({"role": "assistant", "content": final})
                self._emit("assistant", text=final)
                break
            else:
                final = final or "(max tool turns reached)"
                self._emit("error", text=final)
        return final

    def reset_messages(self, *, keep_system: bool = True) -> None:
        if keep_system and self.messages:
            sys = self.messages[0]
            self.messages = [sys] if sys.get("role") == "system" else []
        else:
            self.messages = []
