"""YiAgent CLI — Hermes-inspired: chat/TUI, setup/doctor/config, continue/resume."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from yiagent.agent import AgentSession
from yiagent.cli.doctor import get_cfg_model, get_cfg_variant, run_doctor
from yiagent.config_store import (
    apply_runtime_env,
    bootstrap_home,
    config_path,
    env_path,
    get_nested,
    load_config,
    save_config,
    set_nested,
)
from yiagent.genome import load_bank, variant_map
from yiagent.home import get_home, workspace_path
from yiagent.providers import models_public, resolve_api_key
from yiagent import sessions as sesslib

_SUBCOMMANDS = frozenset(
    {
        "chat",
        "run",
        "variants",
        "setup",
        "doctor",
        "config",
        "model",
        "sessions",
        "improve",
    }
)


def _add_session_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "-c",
        "--continue",
        nargs="?",
        const="",
        default=None,
        dest="continue_session",
        help="resume latest session (or named session)",
    )
    p.add_argument(
        "-r",
        "--resume",
        default=None,
        dest="resume",
        help="resume session by id or title",
    )


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--model", "-m", default=None, help="model id (default: config model.default)")
    p.add_argument("--api-key", default=None, help="API key (else .env / process env)")
    p.add_argument("--bank", type=Path, default=None, help="allele bank JSON path")
    p.add_argument("--variant", "-v", default=None, help="variant id (default: config agent.variant)")
    p.add_argument("--host", default=None, help="optional host system overlay")
    p.add_argument("--cwd", type=Path, default=None, help="workspace for tools")
    p.add_argument("--no-tools", action="store_true", help="disable read/write/edit/bash")
    p.add_argument(
        "--skill",
        action="append",
        default=[],
        dest="skills",
        help="extra Skill id (repeatable)",
    )
    p.add_argument("--max-turns", type=int, default=None)
    p.add_argument("--tui", action="store_true", help="force Textual TUI (chat)")
    p.add_argument("--cli", action="store_true", help="force classic REPL (chat)")
    _add_session_flags(p)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="yiagent",
        description=(
            "YiAgent — gene-assembled agent CLI (Hermes-style home/config).\n"
            "Default command: chat. Durable state: $YIAGENT_HOME or ~/.yiagent"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  yiagent --tui\n"
            "  yiagent --tui -c\n"
            "  yiagent --tui --continue\n"
            "  yiagent --tui -r 20260409_000000_aa11bb\n"
            '  yiagent --tui --resume "my session"\n'
            "  yiagent sessions\n"
        ),
    )
    p.add_argument("--version", action="store_true", help="print version and exit")
    p.add_argument("--tui", action="store_true", help="force Textual TUI")
    p.add_argument("--cli", action="store_true", help="force classic REPL")
    _add_session_flags(p)
    sub = p.add_subparsers(dest="cmd")

    chat = sub.add_parser("chat", help="interactive chat / TUI (default)")
    _common(chat)
    chat.add_argument("-q", "--quiet-prompt", default=None, help="one-shot prompt then exit")

    run = sub.add_parser("run", help="one-shot prompt")
    _common(run)
    run.add_argument("prompt", nargs="+", help="user prompt words")

    sub.add_parser("variants", help="list genome variants")
    sub.add_parser("sessions", help="list saved chat sessions")

    setup = sub.add_parser("setup", help="seed YIAGENT_HOME (config.yaml + .env)")
    setup.add_argument("--force", action="store_true", help="overwrite example files")

    doctor = sub.add_parser("doctor", help="check home, config, keys, bank")
    doctor.add_argument("--fix", action="store_true", help="seed missing home files")

    cfg = sub.add_parser("config", help="show/get/set config.yaml")
    cfg_sub = cfg.add_subparsers(dest="config_cmd")
    cfg_sub.add_parser("show", help="print config (default)")
    cfg_sub.add_parser("path", help="print config.yaml path")
    cfg_sub.add_parser("env-path", help="print .env path")
    g = cfg_sub.add_parser("get", help="get dotted key")
    g.add_argument("key")
    s = cfg_sub.add_parser("set", help="set dotted key")
    s.add_argument("key")
    s.add_argument("value")

    model = sub.add_parser("model", help="list / show default model")
    model_sub = model.add_subparsers(dest="model_cmd")
    model_sub.add_parser("list", help="list catalog (default)")
    model_sub.add_parser("show", help="show configured default")

    improve = sub.add_parser(
        "improve",
        help="export session → improve-pack for factory, or --apply best_genome",
    )
    improve.add_argument(
        "-r",
        "--resume",
        default=None,
        dest="improve_session",
        help="session id/title to export (default: latest)",
    )
    improve.add_argument("--oral", default=None, help="override screening intent")
    improve.add_argument("--notes", default="", help="failure notes for factory refine")
    improve.add_argument(
        "--apply",
        type=Path,
        default=None,
        help="apply factory best_genome.json into ~/.yiagent",
    )
    improve.add_argument("--bank", type=Path, default=None, help="allele bank for export")

    return p


def _normalize_argv(argv: list[str]) -> list[str]:
    """Hermes-style: bare invocation or leading flags → chat."""
    if not argv:
        return ["chat"]
    if argv[0] in ("-h", "--help", "--version"):
        return argv
    if argv[0] not in _SUBCOMMANDS:
        return ["chat", *argv]
    return argv


def _pick_variant(bank: dict, variant_id: str | None) -> str:
    if variant_id:
        return variant_id
    variants = bank.get("variants") or []
    for pref in ("var.champion", "var.balanced_philosopher"):
        if any(v.get("id") == pref for v in variants):
            return pref
    if not variants:
        raise SystemExit("bank has no variants")
    return str(variants[0]["id"])


def _resolve_runtime(args: argparse.Namespace) -> tuple[dict[str, Any], str, str, Path]:
    home = apply_runtime_env()
    cfg = load_config(home)
    model = args.model or get_cfg_model(cfg)
    variant = args.variant or get_cfg_variant(cfg)
    agent = cfg.get("agent") if isinstance(cfg.get("agent"), dict) else {}
    max_turns = args.max_turns
    if max_turns is None:
        max_turns = int(agent.get("max_turns") or 16)
    args.max_turns = max_turns
    if args.cwd is not None:
        cwd = args.cwd
    else:
        cwd = workspace_path(home, configured=str(cfg.get("workspace") or "workspace"))
    return cfg, model, variant, cwd


def _bank_source(args: argparse.Namespace, cfg: dict[str, Any]) -> Path | None:
    if getattr(args, "bank", None):
        return args.bank
    agent = cfg.get("agent") if isinstance(cfg.get("agent"), dict) else {}
    bp = agent.get("bank") if isinstance(agent, dict) else None
    if bp:
        return Path(str(bp))
    return None


def _session_from_args(args: argparse.Namespace, *, for_chat: bool) -> AgentSession:
    cfg, model, variant, cwd = _resolve_runtime(args)
    bank = load_bank(_bank_source(args, cfg))
    vid = _pick_variant(bank, variant)
    key = args.api_key or resolve_api_key(model=model)
    return AgentSession(
        model=model,
        api_key=key,
        bank=bank,
        variant_id=vid,
        host=args.host,
        cwd=cwd,
        max_turns=args.max_turns,
        enable_tools=not args.no_tools,
        skill_ids=list(args.skills or []) or None,
        cfg=cfg,
        on_event=_print_event if for_chat else None,
    )


def _print_event(ev: dict) -> None:
    t = ev.get("type")
    if t == "tool_call":
        print(f"  ⚙ {ev.get('name')}({ev.get('arguments')})", file=sys.stderr)
    elif t == "tool_result":
        preview = (ev.get("result") or "").replace("\n", " ")[:120]
        print(f"  ← {preview}", file=sys.stderr)


def _resolve_resume_record(args: argparse.Namespace, *, source: str, cwd: Path) -> dict[str, Any] | None:
    """Hermes: --resume wins; --continue [name] → latest or named."""
    home = get_home()
    resume = getattr(args, "resume", None)
    cont = getattr(args, "continue_session", None)
    if resume:
        rec = sesslib.resolve_session(str(resume), home)
        if not rec:
            raise SystemExit(f"yiagent: session not found: {resume}")
        return rec
    if cont is None:
        return None
    if cont != "":
        rec = sesslib.resolve_session(str(cont), home)
        if not rec:
            raise SystemExit(f"yiagent: session not found: {cont}")
        return rec
    rec = sesslib.latest_session(source=source, cwd=str(cwd.resolve()), home=home)
    if not rec:
        raise SystemExit("yiagent: no previous session to continue")
    return rec


def _attach_persist(
    agent: AgentSession,
    *,
    source: str,
    model: str,
    variant_id: str | None,
    record: dict[str, Any] | None,
) -> dict[str, Any]:
    """Create or reuse session record; wire agent.on_persist."""
    if record:
        rec = dict(record)
        rec["ended_at"] = None
        if record.get("messages"):
            agent.load_messages(list(record["messages"]), keep_system=True)
    else:
        rec = sesslib.create_record(
            source=source,
            model=model,
            variant_id=variant_id,
            cwd=agent.cwd,
            messages=list(agent.messages),
            title=None,
        )

    def _persist(messages: list[dict[str, Any]]) -> None:
        rec["messages"] = messages
        rec["model"] = model
        if not rec.get("title") or rec["title"] == rec["id"]:
            for m in messages:
                if m.get("role") == "user" and isinstance(m.get("content"), str):
                    rec["title"] = sesslib.title_from_prompt(m["content"], rec["id"])
                    break
        sesslib.save_session(rec)

    agent.on_persist = _persist
    agent.persist_id = rec["id"]
    sesslib.save_session(rec)
    return rec


def _cmd_setup(args: argparse.Namespace) -> int:
    home = bootstrap_home(force=bool(args.force))
    print(f"YIAGENT_HOME={home}")
    print(f"config: {config_path(home)}")
    print(f"env:    {env_path(home)}")
    print("Edit .env with your API key, then: yiagent doctor")
    return 0


def _cmd_config(args: argparse.Namespace) -> int:
    home = apply_runtime_env()
    cmd = args.config_cmd or "show"
    if cmd == "path":
        print(config_path(home))
        return 0
    if cmd == "env-path":
        print(env_path(home))
        return 0
    cfg = load_config(home)
    if cmd == "get":
        print(get_nested(cfg, args.key, ""))
        return 0
    if cmd == "set":
        val: Any = args.value
        if val.lower() in ("true", "false"):
            val = val.lower() == "true"
        elif val.isdigit():
            val = int(val)
        set_nested(cfg, args.key, val)
        save_config(cfg, home)
        print(f"set {args.key} = {val}")
        return 0
    from yiagent.config_store import _dump_simple_yaml

    print(_dump_simple_yaml(cfg), end="")
    return 0


def _cmd_model(args: argparse.Namespace) -> int:
    home = apply_runtime_env()
    cfg = load_config(home)
    cmd = args.model_cmd or "list"
    if cmd == "show":
        print(get_cfg_model(cfg))
        return 0
    for row in models_public():
        print(f"{row.get('id')}\t{row.get('provider')}\t{row.get('label') or ''}")
    return 0


def _cmd_improve(args: argparse.Namespace) -> int:
    home = apply_runtime_env()
    from yiagent.improve_pack import apply_best_genome, export_from_session_id

    if args.apply:
        path = Path(args.apply)
        if not path.is_file():
            print(f"yiagent: apply file not found: {path}", file=sys.stderr)
            return 2
        try:
            info = apply_best_genome(path, home)
        except Exception as e:  # noqa: BLE001
            print(f"yiagent: apply failed: {e}", file=sys.stderr)
            return 1
        print(f"applied variant={info['variant_id']}")
        print(f"bank={info['bank_path']}")
        print(f"config={info['config']}")
        print("next: yiagent --tui   # uses agent.bank + agent.variant")
        return 0

    cfg = load_config(home)
    bank_path = args.bank
    if bank_path is None:
        agent = cfg.get("agent") if isinstance(cfg.get("agent"), dict) else {}
        if agent.get("bank"):
            bank_path = Path(str(agent["bank"]))
    try:
        pack, path = export_from_session_id(
            getattr(args, "improve_session", None),
            failure_notes=str(args.notes or ""),
            oral=args.oral,
            bank_path=bank_path,
            home=home,
        )
    except FileNotFoundError as e:
        print(f"yiagent: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"yiagent: improve export failed: {e}", file=sys.stderr)
        return 1
    print(path)
    print(f"kind={pack.get('kind')} session={pack.get('session_id')} seed={ (pack.get('seed') or {}).get('variant_id') }")
    print("open factory: http://localhost:8787  → Step1「改进包」载入此 JSON")
    return 0


def _cmd_sessions(_args: argparse.Namespace) -> int:
    apply_runtime_env()
    rows = sesslib.list_sessions()
    if not rows:
        print("(no sessions)")
        return 0
    for s in rows:
        print(
            f"{s.get('id')}\t{s.get('source')}\t{s.get('title') or ''}\t{s.get('updated_at') or ''}"
        )
    return 0


def _wants_tui(args: argparse.Namespace, cfg: dict[str, Any]) -> bool:
    if getattr(args, "cli", False):
        return False
    if getattr(args, "tui", False):
        return True
    disp = cfg.get("display") if isinstance(cfg.get("display"), dict) else {}
    iface = str((disp or {}).get("interface") or "").strip().lower()
    if iface == "cli":
        return False
    if iface == "tui":
        return sys.stdin.isatty() and sys.stdout.isatty()
    return sys.stdin.isatty() and sys.stdout.isatty()


def _run_chat_loop(sess: AgentSession) -> int:
    print("Type a message. Empty line or /exit to quit. /reset clears history.", file=sys.stderr)
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            break
        if not line or line in ("/exit", "/quit"):
            break
        if line == "/reset":
            sess.reset_messages()
            if sess.on_persist:
                sess.on_persist(list(sess.messages))
            print("(reset)", file=sys.stderr)
            continue
        try:
            out = sess.prompt(line)
        except Exception as e:  # noqa: BLE001
            print(f"error: {e}", file=sys.stderr)
            continue
        print(f"agent> {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(_normalize_argv(raw))

    # Merge top-level session/tui flags onto chat args when present on root parser
    # (argparse only sets them on the subparser we routed into).

    if args.version or (not args.cmd and "--version" in raw):
        from importlib.metadata import version

        try:
            print(version("yiagent"))
        except Exception:  # noqa: BLE001
            print("0.2.0")
        return 0

    cmd = args.cmd or "chat"

    if cmd == "setup":
        return _cmd_setup(args)
    if cmd == "doctor":
        return run_doctor(fix=bool(getattr(args, "fix", False)))
    if cmd == "config":
        return _cmd_config(args)
    if cmd == "model":
        return _cmd_model(args)
    if cmd == "sessions":
        return _cmd_sessions(args)
    if cmd == "improve":
        return _cmd_improve(args)
    if cmd == "variants":
        apply_runtime_env()
        bank = load_bank()
        for vid, v in variant_map(bank).items():
            print(f"{vid}\t{v.get('title') or ''}")
        return 0

    if cmd in ("run",) or getattr(args, "quiet_prompt", None):
        try:
            sess = _session_from_args(args, for_chat=False)
        except Exception as e:  # noqa: BLE001
            print(f"yiagent: {e}", file=sys.stderr)
            print("hint: yiagent setup && yiagent doctor", file=sys.stderr)
            return 2
        meta = sess.variant or {}
        cfg, model, _, _ = _resolve_runtime(args)
        title = f"{meta.get('id', '?')} · {meta.get('title', '')} · model={model}"
        if cmd == "run":
            print(f"# YiAgent · {title}", file=sys.stderr)
            prompt = " ".join(args.prompt).strip()
            if not prompt:
                print("yiagent: empty prompt", file=sys.stderr)
                return 2
            try:
                print(sess.prompt(prompt))
            except Exception as e:  # noqa: BLE001
                print(f"yiagent: {e}", file=sys.stderr)
                return 1
            return 0
        print(f"# YiAgent · {title}", file=sys.stderr)
        try:
            print(sess.prompt(args.quiet_prompt))
        except Exception as e:  # noqa: BLE001
            print(f"yiagent: {e}", file=sys.stderr)
            return 1
        return 0

    # interactive chat
    cfg, model, variant, cwd = _resolve_runtime(args)
    use_tui = _wants_tui(args, cfg)
    source = "tui" if use_tui else "cli"
    try:
        resume_rec = _resolve_resume_record(args, source=source, cwd=cwd)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2

    try:
        sess = _session_from_args(args, for_chat=not use_tui)
    except Exception as e:  # noqa: BLE001
        print(f"yiagent: {e}", file=sys.stderr)
        print("hint: yiagent setup && yiagent doctor", file=sys.stderr)
        return 2

    vid = (sess.variant or {}).get("id")
    rec = _attach_persist(
        sess,
        source=source,
        model=model,
        variant_id=str(vid) if vid else variant,
        record=resume_rec,
    )
    resumed = resume_rec is not None
    meta = sess.variant or {}
    title = (
        f"{rec.get('id')} · {rec.get('title') or ''} · "
        f"{meta.get('id', '?')} · model={model}"
    )
    if resumed:
        print(f"# resume {rec.get('id')} · {rec.get('title')}", file=sys.stderr)

    if use_tui:
        from yiagent.cli.tui import run_tui

        return run_tui(
            session=sess,
            title=title,
            session_id=str(rec.get("id")),
            resumed=resumed,
        )

    print(f"# YiAgent · {title}", file=sys.stderr)
    return _run_chat_loop(sess)


if __name__ == "__main__":
    raise SystemExit(main())
