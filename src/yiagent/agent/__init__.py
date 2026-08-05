"""Pi-style agent session: genome system + core tools + Skill cassettes."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Callable

from yiagent.assembly import PACK_KIND, assemble_vector, marker_line
from yiagent.genome import (
    assemble_from_ids,
    assemble_system,
    load_bank,
    load_skill,
    load_skills,
    skill_openai_tools,
)
from yiagent.prompt_layers import compose_system
from yiagent.providers import (
    TokenMeter,
    chat_completions,
    extract_content,
    resolve_api_key,
)
from yiagent.tools import OPENAI_TOOL_SPECS, ToolError, _safe_path, dispatch, make_tools


DEFAULT_HOST = (
    "你是 YiAgent 实体运行时：按已装载的 G1–G5 基因组与 Skills（外部基因盒）行事。"
    "需要读文件、改文件或跑命令时，使用提供的工具；完成后用自然语言回答用户。"
)


def _attach_skill_handlers(tools: dict, cwd: Path, skills: list[dict[str, Any]]) -> None:
    """Register skill tool callables into the dispatch map."""
    root = cwd.resolve()

    def notes_summary(path: str) -> str:
        p = _safe_path(root, path)
        if not p.is_file():
            raise ToolError(f"not a file: {path}")
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        preview = "\n".join(lines[:40])
        return f"notes_summary {p.name}: {len(lines)} non-empty lines\n{preview}"

    builtins = {"notes_summary": notes_summary}
    for sk in skills:
        for t in sk.get("tools") or []:
            name = t.get("name")
            if not name or name in tools:
                continue
            handler = t.get("handler") or ""
            if handler.startswith("builtin:"):
                key = handler.split(":", 1)[1]
                if key in builtins:
                    tools[name] = builtins[key]
                else:
                    missing = name

                    def _missing(**_kw: Any) -> str:
                        return f"error: builtin handler missing for {missing}"

                    tools[name] = _missing
            else:
                stub = name

                def _stub(**_kwargs: Any) -> str:
                    return f"error: skill tool {stub} has no handler wired"

                tools[name] = _stub


class AgentSession:
    """Minimal Pi-like harness: messages + tools + genome/Skills assemble."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        system: str | None = None,
        bank: dict[str, Any] | str | Path | None = None,
        variant_id: str | None = None,
        vector: dict[str, Any] | None = None,
        host: str | None = None,
        cwd: str | Path | None = None,
        max_turns: int = 16,
        enable_tools: bool = True,
        skill_ids: list[str] | None = None,
        cfg: dict[str, Any] | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or resolve_api_key(model=model)
        self.cwd = Path(cwd or Path.cwd()).resolve()
        self.max_turns = max(1, int(max_turns))
        self.enable_tools = enable_tools
        self.on_event = on_event
        self.cfg = cfg
        self.meter = TokenMeter()
        self.tools = make_tools(self.cwd) if enable_tools else {}
        self.bank: dict[str, Any] | None = None
        self.variant: dict[str, Any] | None = None
        self.skills: list[dict[str, Any]] = []
        self.genome_pack: dict[str, Any] | None = None  # B1 表达载体配置包（可观测标记）
        self._openai_tools: list[dict[str, Any]] = list(OPENAI_TOOL_SPECS) if enable_tools else []

        if system:
            genome_text = system
        elif vector is not None:
            # B4A：直接消费装配产物（`yiagent assemble` 落盘的 vector JSON），
            # 基因组文本与 Skill 盒都从配置包复原，与装配时同一口径
            if vector.get("kind") != PACK_KIND:
                raise ValueError(f"vector 不是装配产物（kind 应为 {PACK_KIND}）")
            self.genome_pack = vector
            genome_text = str((vector.get("runtime") or {}).get("genome_system") or "")
            if not genome_text.strip():
                raise ValueError("vector 缺 runtime.genome_system，数据不完整")
            try:
                self.skills = [
                    load_skill(str(s.get("id")))
                    for s in (vector.get("markers") or {}).get("skills") or []
                    if s.get("id")
                ]
            except FileNotFoundError as exc:
                raise ValueError(f"vector 引用的 Skill 不存在: {exc}") from exc
        elif variant_id:
            genome_text, self.bank, self.variant, self.skills = assemble_from_ids(
                host=host or DEFAULT_HOST,
                bank=bank,
                variant_id=variant_id,
                skill_ids=skill_ids,
            )
        else:
            b = load_bank(bank)
            self.bank = b
            variants = b.get("variants") or []
            if not variants:
                raise ValueError("bank has no variants")
            self.variant = variants[0]
            self.skills = load_skills(b, self.variant, skill_ids=skill_ids)
            genome_text = assemble_system(
                host or DEFAULT_HOST, b, self.variant, skills=self.skills
            )

        # B1 表达载体：凡走基因组装配的路径都过装配规则 + 校验，
        # 坏基因在此被 AssemblyBlocked 阻断；配置包挂到 session 供观测
        if self.variant is not None:
            self.genome_pack = assemble_vector(
                host or DEFAULT_HOST,
                bank=self.bank,
                variant=self.variant,
                skills=self.skills,
            )
            genome_text = self.genome_pack["runtime"]["genome_system"]

        # Full prompt: Genome + Runtime rules + AGENTS.md (rules never enter bank)
        sys_text = compose_system(genome_text, cwd=self.cwd, cfg=cfg)

        if enable_tools and self.skills:
            _attach_skill_handlers(self.tools, self.cwd, self.skills)
            for t in skill_openai_tools(self.skills):
                # strip internal keys before sending to API
                clean = {
                    "type": t["type"],
                    "function": t["function"],
                }
                self._openai_tools.append(clean)

        self.messages: list[dict[str, Any]] = [{"role": "system", "content": sys_text}]
        self.persist_id: str | None = None
        self.on_persist: Callable[[list[dict[str, Any]]], None] | None = None
        if self.genome_pack is not None:
            # 可观测标记进事件流：一次装配可审计、可复现
            self._emit(
                "genome_pack",
                line=marker_line(self.genome_pack),
                markers=self.genome_pack["markers"],
            )

    def load_messages(self, messages: list[dict[str, Any]], *, keep_system: bool = True) -> None:
        """Replace history (for session resume). Optionally keep current system prompt."""
        cleaned = [m for m in messages if isinstance(m, dict) and m.get("role")]
        if keep_system and self.messages and self.messages[0].get("role") == "system":
            sys = self.messages[0]
            rest = [m for m in cleaned if m.get("role") != "system"]
            self.messages = [sys, *rest]
        else:
            self.messages = cleaned or self.messages

    def _persist(self) -> None:
        if self.on_persist:
            self.on_persist(list(self.messages))

    def _emit(self, kind: str, **payload: Any) -> None:
        if self.on_event:
            self.on_event({"type": kind, **payload})

    def prompt(self, user: str, *, stream_text: bool = False) -> str:
        """Run one user turn through the tool loop; return final assistant text."""
        self.messages.append({"role": "user", "content": user})
        self._emit("user", text=user)
        out = self._loop(stream_text=stream_text)
        self._persist()
        return out

    def _loop(self, *, stream_text: bool = False) -> str:
        tools_param = self._openai_tools if self.enable_tools else None
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
