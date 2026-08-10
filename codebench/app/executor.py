"""Deterministic Python sandbox: write code+tests, run under timeout, no network assumed at compose.

M0: process isolation inside the codebench container (not DinD).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from typing import Any


DRIVER = textwrap.dedent(
    """
    import importlib.util
    import sys
    import traceback

    spec = importlib.util.spec_from_file_location("solution", "solution.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["solution"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    # expose solution symbols into tests namespace
    g = {"__name__": "__test__"}
    g.update({k: getattr(mod, k) for k in dir(mod) if not k.startswith("_")})
    with open("tests.py", "r", encoding="utf-8") as f:
        src = f.read()
    try:
        exec(compile(src, "tests.py", "exec"), g, g)
        print("CODEBENCH_OK")
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    """
)


def run_python(
    code: str,
    tests: str,
    *,
    timeout_s: float = 8.0,
    mem_mb: int = 256,
) -> dict[str, Any]:
    work = tempfile.mkdtemp(prefix="cb_")
    try:
        sol = os.path.join(work, "solution.py")
        tst = os.path.join(work, "tests.py")
        drv = os.path.join(work, "driver.py")
        with open(sol, "w", encoding="utf-8") as f:
            f.write(code if code.endswith("\n") else code + "\n")
        with open(tst, "w", encoding="utf-8") as f:
            f.write(tests if tests.endswith("\n") else tests + "\n")
        with open(drv, "w", encoding="utf-8") as f:
            f.write(DRIVER)

        env = os.environ.copy()
        env["PYTHONHASHSEED"] = "0"
        # Drop proxy / HF noise; compose also sets network_mode none for runner jobs later
        for k in list(env):
            if k.lower().endswith("_proxy") or k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
                env.pop(k, None)

        preexec = None
        if os.name == "posix" and hasattr(os, "setrlimit"):
            import resource

            def _limit() -> None:
                soft = mem_mb * 1024 * 1024
                try:
                    resource.setrlimit(resource.RLIMIT_AS, (soft, soft))
                except (ValueError, OSError):
                    pass
                try:
                    resource.setrlimit(resource.RLIMIT_CPU, (int(timeout_s) + 1, int(timeout_s) + 1))
                except (ValueError, OSError):
                    pass

            preexec = _limit

        try:
            kwargs: dict[str, Any] = dict(
                cwd=work,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
            )
            if preexec is not None:
                kwargs["preexec_fn"] = preexec
            p = subprocess.run([sys.executable, "-I", drv], **kwargs)
            out = (p.stdout or "") + (p.stderr or "")
            ok = p.returncode == 0 and "CODEBENCH_OK" in (p.stdout or "")
            return {
                "ok": ok,
                "exit_code": p.returncode,
                "timed_out": False,
                "stdout": p.stdout or "",
                "stderr": p.stderr or "",
                "combined": out[-8000:],
            }
        except subprocess.TimeoutExpired as e:
            return {
                "ok": False,
                "exit_code": -1,
                "timed_out": True,
                "stdout": (e.stdout or "") if isinstance(e.stdout, str) else "",
                "stderr": (e.stderr or "") if isinstance(e.stderr, str) else "",
                "combined": "TIMEOUT",
            }
    finally:
        shutil.rmtree(work, ignore_errors=True)
