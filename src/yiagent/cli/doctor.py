"""yiagent doctor — Hermes-style health checks."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from yiagent.config_store import apply_runtime_env, config_path, env_path, load_config
from yiagent.genome import load_bank, variant_map
from yiagent.home import get_home, workspace_path
from yiagent.providers import PROVIDERS, model_entry, resolve_api_key
from yiagent.providers.auth import AuthError


def run_doctor(*, fix: bool = False) -> int:
    """Print checks; return 0 if healthy enough to chat, else 1."""
    from yiagent.config_store import bootstrap_home

    home = get_home()
    if fix:
        bootstrap_home(home)
    apply_runtime_env(home)
    cfg = load_config(home)
    model = str(get_cfg_model(cfg))
    variant = str(get_cfg_variant(cfg))
    ws = workspace_path(home, configured=str(cfg.get("workspace") or "workspace"))

    checks: list[tuple[str, bool, str]] = []

    checks.append(("YIAGENT_HOME", home.is_dir(), str(home)))
    checks.append(("config.yaml", config_path(home).is_file(), str(config_path(home))))
    checks.append((".env", env_path(home).is_file(), str(env_path(home))))
    checks.append(("workspace writable", _writable(ws), str(ws)))

    try:
        bank = load_bank()
        variants = variant_map(bank)
        ok_v = variant in variants
        checks.append(("default bank", True, f"{len(variants)} variants"))
        checks.append(("variant", ok_v, variant if ok_v else f"{variant} (missing)"))
    except Exception as e:  # noqa: BLE001
        checks.append(("default bank", False, str(e)))
        ok_v = False

    meta = model_entry(model) or {}
    pid = meta.get("provider") or "?"
    checks.append(("model id", bool(meta), f"{model} ({pid})"))

    key_ok = False
    key_msg = "missing"
    try:
        resolve_api_key(model=model)
        key_ok = True
        key_msg = "resolved"
    except AuthError as e:
        key_msg = str(e)
    checks.append(("API key", key_ok, key_msg))

    # Provider catalog presence
    checks.append(("providers catalog", bool(PROVIDERS), f"{len(PROVIDERS)} providers"))

    failed = 0
    for name, ok, detail in checks:
        mark = "ok" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"  [{mark}] {name}: {detail}", file=sys.stderr)

    if failed:
        print(
            f"yiagent doctor: {failed} issue(s). Try: yiagent setup  |  yiagent doctor --fix",
            file=sys.stderr,
        )
        return 1
    print("yiagent doctor: all clear", file=sys.stderr)
    return 0


def get_cfg_model(cfg: dict[str, Any]) -> str:
    m = cfg.get("model") or {}
    if isinstance(m, dict):
        return str(m.get("default") or "kimi-k2.5")
    return "kimi-k2.5"


def get_cfg_variant(cfg: dict[str, Any]) -> str:
    a = cfg.get("agent") or {}
    if isinstance(a, dict):
        return str(a.get("variant") or "var.champion")
    return "var.champion"


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".yiagent_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False
