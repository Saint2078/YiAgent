"""Agent 知识库：Markdown 导入 SQLite + CRUD。"""
from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import Any

VIS = {"human_only", "ai_ok", "both", "deny_ai", "agent_api"}

# 文件名关键词 → category
_CAT_HINTS = (
    ("评分", "scoring"),
    ("COVER", "scoring"),
    ("FOACA", "scoring"),
    ("分类", "taxonomy"),
    ("架构", "taxonomy"),
    ("三层", "taxonomy"),
)

_LAYER_RE = re.compile(r"^(00|01|02)[-_]")


def _now_sql() -> str:
    return "strftime('%Y-%m-%dT%H:%M:%fZ','now')"


def seed_dirs() -> list[Path]:
    dirs: list[Path] = []
    for key in ("KB_SEED_DIR", "KB_DOCS_DIR"):
        raw = (os.environ.get(key) or "").strip()
        if not raw:
            continue
        p = Path(raw)
        if p.is_dir():
            dirs.append(p)
    return dirs


def guess_category(name: str, body: str) -> str:
    # 文件名优先，避免正文里顺带提到「评分」把分类文档打错类
    for tip, cat in _CAT_HINTS:
        if tip in name:
            return cat
    head = body[:400]
    for tip, cat in _CAT_HINTS:
        if tip in head:
            return cat
    return "general"


def guess_layer(name: str) -> str | None:
    m = _LAYER_RE.match(name)
    return m.group(1) if m else None


def title_from_md(name: str, body: str) -> str:
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip() or name
    return Path(name).stem


def slugify(title: str) -> str:
    s = re.sub(r"\s+", "-", title.strip().lower())
    s = re.sub(r"[^\w\u4e00-\u9fff\-]+", "", s)
    return (s[:80] or "doc").strip("-")


def doc_id_for_path(path: Path, root: Path) -> str:
    try:
        rel = str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        rel = path.name
    h = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:10]
    stem = re.sub(r"[^\w\u4e00-\u9fff\-]+", "-", path.stem)[:24].strip("-") or "doc"
    return f"kb-{stem}-{h}"


def row_to_dict(r, *, with_body: bool = True) -> dict[str, Any]:
    d = {
        "id": r["doc_id"],
        "title": r["title"],
        "slug": r["slug"] or "",
        "category": r["category"] or "general",
        "layer": r["layer"],
        "visibility": r["visibility"] or "human_only",
        "agent_slice": r["agent_slice"],
        "source_path": r["source_path"],
        "version": r["version"] or "v0",
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
        "excerpt": "",
    }
    body = r["body_md"] or ""
    if with_body:
        d["body_md"] = body
    # 摘要：去掉标题行后前 160 字
    plain = re.sub(r"^#+\s*", "", body, flags=re.M)
    plain = re.sub(r"\s+", " ", plain).strip()
    d["excerpt"] = plain[:160]
    return d


def list_docs(conn, *, category: str | None = None, q: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM kb_doc WHERE 1=1"
    args: list[Any] = []
    if category:
        sql += " AND category=?"
        args.append(category)
    if q:
        sql += " AND (title LIKE ? OR body_md LIKE ? OR source_path LIKE ?)"
        like = f"%{q}%"
        args.extend([like, like, like])
    sql += " ORDER BY updated_at DESC"
    rows = conn.execute(sql, args).fetchall()
    return [row_to_dict(r, with_body=False) for r in rows]


def get_doc(conn, doc_id: str) -> dict[str, Any] | None:
    r = conn.execute("SELECT * FROM kb_doc WHERE doc_id=?", (doc_id,)).fetchone()
    return row_to_dict(r, with_body=True) if r else None


def create_doc(conn, body: dict[str, Any]) -> dict[str, Any]:
    doc_id = (body.get("id") or f"kb-{uuid.uuid4().hex[:10]}").strip()
    title = (body.get("title") or "未命名文档").strip() or "未命名文档"
    md = body.get("body_md") if body.get("body_md") is not None else ""
    category = (body.get("category") or "general").strip() or "general"
    visibility = body.get("visibility") if body.get("visibility") in VIS else "human_only"
    layer = body.get("layer")
    slug = (body.get("slug") or slugify(title)).strip()
    conn.execute(
        f"""
        INSERT INTO kb_doc(
          doc_id, title, slug, category, layer, visibility,
          body_md, agent_slice, source_path, version
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            doc_id,
            title,
            slug,
            category,
            layer,
            visibility,
            str(md),
            body.get("agent_slice"),
            body.get("source_path"),
            body.get("version") or "v0",
        ),
    )
    conn.commit()
    return get_doc(conn, doc_id)  # type: ignore


def patch_doc(conn, doc_id: str, body: dict[str, Any]) -> dict[str, Any] | None:
    cur = conn.execute("SELECT * FROM kb_doc WHERE doc_id=?", (doc_id,)).fetchone()
    if not cur:
        return None
    title = body.get("title", cur["title"])
    category = body.get("category", cur["category"]) or "general"
    visibility = body.get("visibility", cur["visibility"])
    if visibility not in VIS:
        visibility = cur["visibility"]
    layer = body["layer"] if "layer" in body else cur["layer"]
    md = body["body_md"] if "body_md" in body else cur["body_md"]
    slug = body.get("slug", cur["slug"]) or slugify(str(title))
    agent_slice = body["agent_slice"] if "agent_slice" in body else cur["agent_slice"]
    version = body.get("version", cur["version"]) or "v0"
    conn.execute(
        f"""
        UPDATE kb_doc SET
          title=?, slug=?, category=?, layer=?, visibility=?,
          body_md=?, agent_slice=?, version=?,
          updated_at={_now_sql()}
        WHERE doc_id=?
        """,
        (title, slug, category, layer, visibility, str(md), agent_slice, version, doc_id),
    )
    conn.commit()
    return get_doc(conn, doc_id)


def delete_doc(conn, doc_id: str) -> bool:
    cur = conn.execute("DELETE FROM kb_doc WHERE doc_id=?", (doc_id,))
    conn.commit()
    return cur.rowcount > 0


def upsert_from_file(conn, path: Path, root: Path) -> str:
    text = path.read_text(encoding="utf-8")
    # strip YAML frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2].lstrip("\n")
    title = title_from_md(path.name, text)
    category = guess_category(path.name, text)
    layer = guess_layer(path.name)
    doc_id = doc_id_for_path(path, root)
    try:
        rel = str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        rel = path.name
    existing = conn.execute("SELECT doc_id FROM kb_doc WHERE doc_id=?", (doc_id,)).fetchone()
    if existing:
        conn.execute(
            f"""
            UPDATE kb_doc SET
              title=?, category=?, layer=?, body_md=?, source_path=?,
              slug=?, updated_at={_now_sql()}
            WHERE doc_id=?
            """,
            (title, category, layer, text, rel, slugify(title), doc_id),
        )
    else:
        conn.execute(
            """
            INSERT INTO kb_doc(
              doc_id, title, slug, category, layer, visibility,
              body_md, source_path, version
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                doc_id,
                title,
                slugify(title),
                category,
                layer,
                "human_only",
                text,
                rel,
                "v0",
            ),
        )
    return doc_id


def import_markdown_dirs(conn, dirs: list[Path] | None = None) -> dict[str, Any]:
    roots = dirs if dirs is not None else seed_dirs()
    imported: list[str] = []
    skipped = 0
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            if path.name.upper() == "README.MD" and path.parent == root:
                # 仍导入 README，便于索引
                pass
            try:
                doc_id = upsert_from_file(conn, path, root)
                imported.append(doc_id)
            except OSError:
                skipped += 1
    conn.commit()
    return {"imported": len(imported), "ids": imported, "skipped": skipped, "roots": [str(r) for r in roots]}


def seed_if_empty(conn) -> dict[str, Any] | None:
    n = conn.execute("SELECT COUNT(*) FROM kb_doc").fetchone()[0]
    if n > 0:
        return None
    return import_markdown_dirs(conn)
