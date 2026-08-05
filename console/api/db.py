"""01 SQLite migrate runner（Demo 项目 API 用；与 opc-engineering/01-storage 同契约）。"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent
MIGRATIONS_DIR = MODULE_ROOT / "migrations"
DEFAULT_DB = Path(os.environ.get("OPC_01_DB", "/data/opc.sqlite"))

_VERSION_RE = re.compile(r"^(\d+)_.*\.sql$")


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or os.environ.get("OPC_01_DB", str(DEFAULT_DB)))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migration_files(migrations_dir: Path) -> list[tuple[int, Path]]:
    out: list[tuple[int, Path]] = []
    for p in sorted(migrations_dir.glob("*.sql")):
        m = _VERSION_RE.match(p.name)
        if m:
            out.append((int(m.group(1)), p))
    return sorted(out)


def migrate(conn: sqlite3.Connection, migrations_dir: str | Path | None = None) -> list[int]:
    mdir = Path(migrations_dir or MIGRATIONS_DIR)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version INTEGER PRIMARY KEY,"
        " applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))"
        ")"
    )
    conn.commit()
    applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
    newly: list[int] = []
    for version, path in _migration_files(mdir):
        if version in applied:
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        newly.append(version)
    return newly
