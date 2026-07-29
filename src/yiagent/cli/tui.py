"""YiAgent chat TUI (Textual) — Hermes-style full-screen terminal UI + session resume."""

from __future__ import annotations

from typing import Any, Callable

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown, Static


class UserBubble(Markdown):
    """User message."""


class AgentBubble(Markdown):
    """Agent / tool status message."""


class YiAgentTUI(App[None]):
    """Full-screen chat for AgentSession."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #status {
        dock: top;
        height: 1;
        padding: 0 1;
        color: $text-muted;
        background: $surface;
    }
    #chat-view {
        height: 1fr;
        padding: 0 1;
    }
    UserBubble {
        background: $primary 12%;
        margin: 1 8 0 0;
        padding: 1 2;
    }
    AgentBubble {
        background: $success 10%;
        margin: 1 0 0 8;
        padding: 1 2;
        border: tall $success 40%;
    }
    AgentBubble.tool {
        background: $warning 8%;
        border: tall $warning 40%;
        color: $text-muted;
    }
    AgentBubble.error {
        background: $error 15%;
        border: tall $error;
    }
    #prompt {
        dock: bottom;
        margin: 0 1 1 1;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+d", "quit", "Quit"),
        ("ctrl+l", "clear_chat", "Clear"),
    ]

    def __init__(
        self,
        *,
        session: Any,
        title: str,
        session_id: str | None = None,
        resumed: bool = False,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        super().__init__()
        self.session = session
        self._title = title
        self._session_id = session_id
        self._resumed = resumed
        self._busy = False
        self._external_on_event = on_event
        prev = getattr(session, "on_event", None)

        def _fanout(ev: dict[str, Any]) -> None:
            if prev:
                prev(ev)
            self.call_from_thread(self._handle_event, ev)
            if self._external_on_event:
                self._external_on_event(ev)

        session.on_event = _fanout

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(self._title, id="status")
        with VerticalScroll(id="chat-view"):
            if self._resumed:
                yield AgentBubble(
                    f"Resumed session `{self._session_id}`.\n"
                    "Continue typing · `/reset` · `Ctrl+C` quit"
                )
            else:
                yield AgentBubble(
                    "YiAgent TUI ready. Type a message and Enter.\n"
                    "`/reset` · `Ctrl+C` quit · resume later with `yiagent --tui -c`"
                )
        yield Input(placeholder="Message… (/reset clears history)", id="prompt")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "YiAgent"
        self.sub_title = self._title
        self.query_one("#prompt", Input).focus()
        if self._resumed:
            self._replay_history()

    def _replay_history(self) -> None:
        view = self.query_one("#chat-view", VerticalScroll)
        for m in self.session.messages:
            role = m.get("role")
            content = m.get("content")
            if role == "system" or not isinstance(content, str) or not content.strip():
                continue
            if role == "user":
                view.mount(UserBubble(content))
            elif role == "assistant":
                view.mount(AgentBubble(content))
            elif role == "tool":
                preview = content.replace("\n", " ")[:200]
                view.mount(AgentBubble(f"← `{preview}`", classes="tool"))
        view.scroll_end(animate=False)

    def action_clear_chat(self) -> None:
        view = self.query_one("#chat-view", VerticalScroll)
        view.remove_children()

    def _handle_event(self, ev: dict[str, Any]) -> None:
        kind = ev.get("type")
        view = self.query_one("#chat-view", VerticalScroll)
        if kind == "tool_call":
            name = ev.get("name") or "?"
            args = (ev.get("arguments") or "")[:200]
            bubble = AgentBubble(f"**⚙ {name}**\n```\n{args}\n```", classes="tool")
            view.mount(bubble)
            view.scroll_end(animate=False)
        elif kind == "tool_result":
            preview = (ev.get("result") or "").replace("\n", " ")[:240]
            bubble = AgentBubble(f"← `{preview}`", classes="tool")
            view.mount(bubble)
            view.scroll_end(animate=False)

    @on(Input.Submitted, "#prompt")
    async def on_submit(self, event: Input.Submitted) -> None:
        text = (event.value or "").strip()
        event.input.clear()
        if not text:
            return
        if text in ("/exit", "/quit"):
            self.exit()
            return
        if text == "/reset":
            self.session.reset_messages()
            if getattr(self.session, "on_persist", None):
                self.session.on_persist(list(self.session.messages))
            view = self.query_one("#chat-view", VerticalScroll)
            await view.mount(AgentBubble("*(history reset)*", classes="tool"))
            return
        if self._busy:
            self.notify("Still working…", severity="warning")
            return

        view = self.query_one("#chat-view", VerticalScroll)
        await view.mount(UserBubble(text))
        reply = AgentBubble("*thinking…*")
        await view.mount(reply)
        view.scroll_end(animate=False)
        self._busy = True
        event.input.disabled = True
        self.run_turn(text, reply)

    @work(thread=True)
    def run_turn(self, prompt: str, reply: AgentBubble) -> None:
        try:
            out = self.session.prompt(prompt)
            self.call_from_thread(reply.update, out or "*(empty)*")
        except Exception as e:  # noqa: BLE001
            self.call_from_thread(reply.remove_class, "tool")
            self.call_from_thread(reply.add_class, "error")
            self.call_from_thread(reply.update, f"**error:** {e}")
        finally:
            self.call_from_thread(self._finish_turn)

    def _finish_turn(self) -> None:
        self._busy = False
        inp = self.query_one("#prompt", Input)
        inp.disabled = False
        inp.focus()
        self.query_one("#chat-view", VerticalScroll).scroll_end(animate=False)


def run_tui(
    *,
    session: Any,
    title: str,
    session_id: str | None = None,
    resumed: bool = False,
) -> int:
    """Launch Textual chat; return process exit code."""
    try:
        import textual  # noqa: F401
    except ImportError:
        print(
            "yiagent: TUI needs `textual`. Rebuild image or: pip install textual",
            file=__import__("sys").stderr,
        )
        return 2
    app = YiAgentTUI(
        session=session,
        title=title,
        session_id=session_id,
        resumed=resumed,
    )
    app.run()
    return 0
