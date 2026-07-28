"""YiAgent CLI — Pi-style chat/print with genome load."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from yiagent.agent import AgentSession
from yiagent.genome import load_bank, variant_map
from yiagent.providers import resolve_api_key


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="yiagent",
        description="YiAgent entity: genome + Skills (gene cassettes) + Pi-style tools.",
    )
    p.add_argument("--model", "-m", default="kimi-k2.5", help="model id from yiagent.providers")
    p.add_argument("--api-key", default=None, help="API key (else env for provider)")
    p.add_argument("--bank", type=Path, default=None, help="allele bank JSON path")
    p.add_argument("--variant", "-v", default=None, help="variant id (default: first / champion)")
    p.add_argument("--host", default=None, help="optional host system overlay")
    p.add_argument("--cwd", type=Path, default=None, help="workspace for tools")
    p.add_argument("--no-tools", action="store_true", help="disable read/write/edit/bash")
    p.add_argument(
        "--skill",
        action="append",
        default=[],
        dest="skills",
        help="extra Skill id (repeatable); merges with variant.skills",
    )
    p.add_argument("--max-turns", type=int, default=16)

    sub = p.add_subparsers(dest="cmd", required=True)

    chat = sub.add_parser("chat", help="interactive REPL")
    chat.add_argument("--list-variants", action="store_true")

    run = sub.add_parser("run", help="one-shot prompt (like pi print)")
    run.add_argument("prompt", nargs="+", help="user prompt words")

    sub.add_parser("variants", help="list variants in bank")

    return p


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


def _session_from_args(args: argparse.Namespace) -> AgentSession:
    bank = load_bank(args.bank)
    vid = _pick_variant(bank, args.variant)
    key = args.api_key or resolve_api_key(model=args.model)
    return AgentSession(
        model=args.model,
        api_key=key,
        bank=bank,
        variant_id=vid,
        host=args.host,
        cwd=args.cwd or Path.cwd(),
        max_turns=args.max_turns,
        enable_tools=not args.no_tools,
        skill_ids=list(args.skills or []) or None,
        on_event=_print_event if args.cmd == "chat" else None,
    )


def _print_event(ev: dict) -> None:
    t = ev.get("type")
    if t == "tool_call":
        print(f"  ⚙ {ev.get('name')}({ev.get('arguments')})", file=sys.stderr)
    elif t == "tool_result":
        preview = (ev.get("result") or "").replace("\n", " ")[:120]
        print(f"  ← {preview}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "variants":
        bank = load_bank(args.bank)
        for vid, v in variant_map(bank).items():
            print(f"{vid}\t{v.get('title') or ''}")
        return 0

    try:
        sess = _session_from_args(args)
    except Exception as e:  # noqa: BLE001
        print(f"yiagent: {e}", file=sys.stderr)
        return 2

    meta = sess.variant or {}
    print(
        f"# YiAgent · {meta.get('id', '?')} · {meta.get('title', '')} · model={args.model}",
        file=sys.stderr,
    )

    if args.cmd == "run":
        prompt = " ".join(args.prompt).strip()
        if not prompt:
            print("yiagent: empty prompt", file=sys.stderr)
            return 2
        try:
            out = sess.prompt(prompt)
        except Exception as e:  # noqa: BLE001
            print(f"yiagent: {e}", file=sys.stderr)
            return 1
        print(out)
        return 0

    # chat REPL
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
            print("(reset)", file=sys.stderr)
            continue
        try:
            out = sess.prompt(line)
        except Exception as e:  # noqa: BLE001
            print(f"error: {e}", file=sys.stderr)
            continue
        print(f"agent> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
