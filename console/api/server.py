#!/usr/bin/env python3
"""CEO 工作台 · 项目 SoR API（同卷 SQLite · 对齐 01-storage）。"""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import db as store
import kb as kb_store

# 桌面 opc/项目 → 容器 /workbench/项目（每项目一文件夹）
OPC_PROJECTS_DIR = os.environ.get("OPC_PROJECTS_DIR", "/workbench/项目")
# yitech002 五门：按门过滤种子项目（opc / yiagent / erp / founder-ip / cashflow）
SITE_GATE = (os.environ.get("SITE_GATE") or "opc").strip() or "opc"

STATUS_TO_UI = {
    "active": "进行中",
    "paused": "等人",
    "done": "已完成",
    "cancelled": "已取消",
    "archived": "已归档",
}
STATUS_FROM_UI = {
    "进行中": "active",
    "等人": "paused",
    "已完成": "done",
    "已取消": "cancelled",
    "已归档": "archived",
}

SEED_ALL = [
    {
        "project_id": "p11",
        "title": "YiAgent 开源计划",
        "category": "战略",
        "status": "active",
        "team": "开发团队",
        "owner": "CTO",
        "progress": 20,
        "due_text": "2026 H2",
        "risk": "产品边界与对外口径待对齐",
        "channel": "team-dev",
        "pillar": "影响力计划",
        "customer": None,
    },
    {
        "project_id": "p12",
        "title": "创始人 IP",
        "category": "战略",
        "status": "active",
        "team": "营销团队",
        "owner": "CMO / 你",
        "progress": 15,
        "due_text": "持续",
        "risk": "叙事与 ASE 主推需同频，避免分心",
        "channel": "team-mkt",
        "pillar": "影响力计划",
        "customer": None,
    },
    {
        "project_id": "p13",
        "title": "公司战略调整",
        "category": "战略",
        "status": "paused",
        "team": "战略委员会",
        "owner": "你",
        "progress": 40,
        "due_text": "待拍板",
        "risk": "收敛正本待确认后才能下拆举措",
        "channel": "team-strategy",
        "pillar": "治理",
        "customer": None,
    },
    {
        "project_id": "p14",
        "title": "现金流增强",
        "category": "战略",
        "status": "active",
        "team": "战略委员会",
        "owner": "你",
        "progress": 5,
        "due_text": "2026 H2",
        "risk": "手段未收敛；勿摊成第四条业务线",
        "channel": "team-strategy",
        "pillar": "经营",
        "customer": None,
    },
    {
        "project_id": "p15",
        "title": "ERP开发",
        "category": "客户",
        "status": "active",
        "team": "开发团队",
        "owner": "你",
        "progress": 5,
        "due_text": "模拟交付",
        "risk": "旧交付在「以前的文件」；本期按流程重演，勿与既成代码混为同一验收线",
        "channel": "team-dev",
        "pillar": "客户交付",
        "customer": "虫控数字化（脱敏示例）",
    },
    {
        "project_id": "p2",
        "title": "ASE FDE 样板交付（一体机/单场景）",
        "category": "客户",
        "status": "active",
        "team": "开发团队",
        "owner": "CTO",
        "progress": 58,
        "due_text": "8 月",
        "risk": "关键动作必须人审；有 SKU 非纯人天",
        "channel": "team-dev",
        "pillar": "ASE 平台",
        "customer": "样板客户（FDE）",
    },
    {
        "project_id": "p3",
        "title": "熟人/校友会 · AI 咨询 L1 诊断",
        "category": "客户",
        "status": "active",
        "team": "销售交付",
        "owner": "你 / CMO",
        "progress": 35,
        "due_text": "2026 H2",
        "risk": "约 20% 资源；作决策入口转 ASE",
        "channel": "team-sales",
        "pillar": "AI 咨询",
        "customer": "熟人/校友会线索",
    },
    {
        "project_id": "p8",
        "title": "华数智造 · 续约与交付收尾",
        "category": "客户",
        "status": "active",
        "team": "销售交付",
        "owner": "销售交付",
        "progress": 72,
        "due_text": "本月",
        "risk": "收款确认在审批篮",
        "channel": "team-sales",
        "pillar": "AI 咨询",
        "customer": "华数智造",
    },
    {
        "project_id": "p9",
        "title": "星河物流 · 验收纪要",
        "category": "客户",
        "status": "paused",
        "team": "销售交付",
        "owner": "Delivery",
        "progress": 88,
        "due_text": "本周",
        "risk": "验收纪要待客户签",
        "channel": "team-sales",
        "pillar": "ASE 平台",
        "customer": "星河物流",
    },
]

# 主控保留公司/客户样板；业务线项目各归一门
GATE_SEED_IDS = {
    "opc": {"p13", "p2", "p3", "p8", "p9"},
    "yiagent": {"p11"},
    "erp": {"p15"},
    "founder-ip": {"p12"},
    "cashflow": {"p14"},
}
_seed_ids = GATE_SEED_IDS.get(SITE_GATE, GATE_SEED_IDS["opc"])
SEED = [p for p in SEED_ALL if p["project_id"] in _seed_ids]

_lock = threading.Lock()
_conn = None


def projects_root() -> str:
    return OPC_PROJECTS_DIR


def sanitize_folder_name(title: str, pid: str) -> str:
    name = (title or "").strip() or pid
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "", name)
    name = name.strip(" .") or pid
    if name in (".", ".."):
        name = pid
    return name


def _read_project_marker(folder: str) -> str | None:
    marker = os.path.join(folder, ".opc-project-id")
    try:
        if os.path.isfile(marker):
            return open(marker, encoding="utf-8").read().strip() or None
    except OSError:
        return None
    return None


def project_folder_name(pid: str, title: str) -> str:
    """可读标题优先；已被其它项目占用时加 __project_id。"""
    base = sanitize_folder_name(title, pid)
    root = projects_root()
    candidate = os.path.join(root, base)
    if os.path.isdir(candidate):
        existing = _read_project_marker(candidate)
        if existing in (None, pid):
            return base
        return f"{base}__{pid}"
    # 已有带 id 后缀的目录
    alt = f"{base}__{pid}"
    if os.path.isdir(os.path.join(root, alt)):
        return alt
    return base


def ensure_research_folder(project_abs: str, title: str, rel_project: str) -> tuple[str, list[dict[str, str]]]:
    """项目下固定子目录「项目调研」；返回相对路径与文件列表。"""
    research_abs = os.path.join(project_abs, "项目调研")
    rel = f"{rel_project}/项目调研"
    files: list[dict[str, str]] = []
    try:
        os.makedirs(research_abs, exist_ok=True)
        readme = os.path.join(research_abs, "README.md")
        if not os.path.isfile(readme):
            with open(readme, "w", encoding="utf-8") as f:
                f.write(
                    f"# {title} · 项目调研\n\n"
                    f"调研材料、竞品、赛道笔记放此目录。\n\n"
                    f"- 工作台路径: `{rel}`\n"
                )
        for name in sorted(os.listdir(research_abs)):
            if name.startswith("."):
                continue
            path = os.path.join(research_abs, name)
            if os.path.isfile(path):
                files.append({"name": name, "path": f"{rel}/{name}"})
    except OSError as e:
        print(f"[projects-api] ensure research folder failed: {e}", flush=True)
    return rel, files


def ensure_project_folder(pid: str, title: str) -> str:
    """确保磁盘文件夹存在；返回相对路径 `项目/<名>`。"""
    root = projects_root()
    try:
        os.makedirs(root, exist_ok=True)
    except OSError as e:
        print(f"[projects-api] mkdir projects root failed: {e}", flush=True)
        return f"项目/{sanitize_folder_name(title, pid)}"

    name = project_folder_name(pid, title)
    abs_path = os.path.join(root, name)
    rel = f"项目/{name}"
    try:
        os.makedirs(abs_path, exist_ok=True)
        with open(os.path.join(abs_path, ".opc-project-id"), "w", encoding="utf-8") as f:
            f.write(pid + "\n")
        readme = os.path.join(abs_path, "README.md")
        if not os.path.isfile(readme):
            with open(readme, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n- project_id: `{pid}`\n- 工作台路径: `{rel}`\n")
        ensure_research_folder(abs_path, title, rel)
    except OSError as e:
        print(f"[projects-api] ensure project folder failed ({pid}): {e}", flush=True)
    return rel


def ensure_all_project_folders(conn) -> None:
    rows = conn.execute("SELECT project_id, title FROM project").fetchall()
    for r in rows:
        ensure_project_folder(r["project_id"], r["title"])


def get_conn():
    global _conn
    if _conn is None:
        _conn = store.connect()
        store.migrate(_conn)
        seed_if_empty(_conn)
        try:
            ensure_all_project_folders(_conn)
        except Exception as e:  # noqa: BLE001 — 启动时文件夹失败不挡 API
            print(f"[projects-api] sync project folders: {e}", flush=True)
        try:
            with _lock:
                result = kb_store.seed_if_empty(_conn)
            if result:
                print(
                    f"[projects-api] kb seed imported {result.get('imported')} docs from {result.get('roots')}",
                    flush=True,
                )
        except Exception as e:  # noqa: BLE001
            print(f"[projects-api] kb seed: {e}", flush=True)
    return _conn


def seed_if_empty(conn) -> None:
    n = conn.execute("SELECT COUNT(*) FROM project").fetchone()[0]
    if n > 0:
        return
    for p in SEED:
        conn.execute(
            """
            INSERT INTO project(
              project_id, title, category, owner, status, team, progress,
              due_text, risk, customer, pillar, channel
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                p["project_id"],
                p["title"],
                p["category"],
                p["owner"],
                p["status"],
                p["team"],
                p["progress"],
                p["due_text"],
                p["risk"],
                p["customer"],
                p["pillar"],
                p["channel"],
            ),
        )
    conn.commit()


def row_to_ui(r) -> dict[str, Any]:
    pid = r["project_id"]
    title = r["title"]
    name = project_folder_name(pid, title)
    rel = f"项目/{name}"
    abs_path = os.path.join(projects_root(), name)
    research_rel = f"{rel}/项目调研"
    research_files: list[dict[str, str]] = []
    if os.path.isdir(abs_path):
        research_rel, research_files = ensure_research_folder(abs_path, title, rel)
    return {
        "id": pid,
        "title": title,
        "category": r["category"],
        "status": STATUS_TO_UI.get(r["status"], r["status"]),
        "team": r["team"] or "",
        "owner": r["owner"] or "",
        "progress": int(r["progress"] or 0),
        "due": r["due_text"] or "",
        "risk": r["risk"] or "",
        "customer": r["customer"] or "",
        "pillar": r["pillar"] or "",
        "channel": r["channel"] or "",
        "folder": rel,
        "researchFolder": research_rel,
        "researchFiles": research_files,
        "updated_at": r["updated_at"],
    }


def list_projects(category: str | None = None) -> list[dict[str, Any]]:
    conn = get_conn()
    with _lock:
        if category and category in ("战略", "客户"):
            rows = conn.execute(
                "SELECT * FROM project WHERE category=? ORDER BY updated_at DESC",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM project ORDER BY updated_at DESC").fetchall()
    return [row_to_ui(r) for r in rows]


def get_project(pid: str) -> dict[str, Any] | None:
    conn = get_conn()
    with _lock:
        r = conn.execute("SELECT * FROM project WHERE project_id=?", (pid,)).fetchone()
    return row_to_ui(r) if r else None


def create_project(body: dict[str, Any]) -> dict[str, Any]:
    pid = body.get("id") or f"p-{uuid.uuid4().hex[:8]}"
    title = (body.get("title") or "未命名项目").strip() or "未命名项目"
    category = body.get("category") if body.get("category") in ("战略", "客户") else "战略"
    status_ui = body.get("status") or "进行中"
    status = STATUS_FROM_UI.get(status_ui, "active")
    if status not in STATUS_TO_UI:
        status = "active"
    conn = get_conn()
    with _lock:
        conn.execute(
            """
            INSERT INTO project(
              project_id, title, category, owner, status, team, progress,
              due_text, risk, customer, pillar, channel
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                pid,
                title,
                category,
                body.get("owner") or "你",
                status,
                body.get("team") or "",
                int(body.get("progress") or 0),
                body.get("due") or body.get("due_text") or "",
                body.get("risk") or "",
                body.get("customer") or None,
                body.get("pillar") or "",
                body.get("channel") or "team-strategy",
            ),
        )
        conn.commit()
    ensure_project_folder(pid, title)
    return get_project(pid)  # type: ignore


def patch_project(pid: str, body: dict[str, Any]) -> dict[str, Any] | None:
    conn = get_conn()
    with _lock:
        cur = conn.execute("SELECT * FROM project WHERE project_id=?", (pid,)).fetchone()
        if not cur:
            return None
        fields = {
            "title": body.get("title", cur["title"]),
            "category": body.get("category", cur["category"]),
            "owner": body.get("owner", cur["owner"]),
            "team": body.get("team", cur["team"]),
            "progress": int(body["progress"]) if "progress" in body else cur["progress"],
            "due_text": body.get("due", body.get("due_text", cur["due_text"])),
            "risk": body.get("risk", cur["risk"]),
            "customer": body.get("customer", cur["customer"]),
            "pillar": body.get("pillar", cur["pillar"]),
            "channel": body.get("channel", cur["channel"]),
        }
        if fields["category"] not in ("战略", "客户"):
            fields["category"] = cur["category"]
        if "status" in body:
            st = STATUS_FROM_UI.get(body["status"], body["status"])
            fields["status"] = st if st in STATUS_TO_UI else cur["status"]
        else:
            fields["status"] = cur["status"]
        conn.execute(
            """
            UPDATE project SET
              title=?, category=?, owner=?, status=?, team=?, progress=?,
              due_text=?, risk=?, customer=?, pillar=?, channel=?,
              updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
            WHERE project_id=?
            """,
            (
                fields["title"],
                fields["category"],
                fields["owner"],
                fields["status"],
                fields["team"],
                fields["progress"],
                fields["due_text"],
                fields["risk"],
                fields["customer"],
                fields["pillar"],
                fields["channel"],
                pid,
            ),
        )
        conn.commit()
    return get_project(pid)


def archive_project(pid: str) -> dict[str, Any] | None:
    return patch_project(pid, {"status": "已归档"})


def delete_project(pid: str) -> bool:
    conn = get_conn()
    with _lock:
        cur = conn.execute("SELECT project_id FROM project WHERE project_id=?", (pid,)).fetchone()
        if not cur:
            return False
        conn.execute("DELETE FROM task WHERE project_id=?", (pid,))
        conn.execute("DELETE FROM project WHERE project_id=?", (pid,))
        conn.commit()
    return True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        pass

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, body: Any) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read(self) -> dict[str, Any]:
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8") or "{}")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        u = urlparse(self.path)
        if u.path in ("/healthz", "/api/healthz"):
            self._json(200, {"ok": True})
            return
        if u.path == "/api/kb/docs":
            qs = parse_qs(u.query)
            cat = (qs.get("category") or [None])[0]
            q = (qs.get("q") or [None])[0]
            conn = get_conn()
            with _lock:
                docs = kb_store.list_docs(conn, category=cat or None, q=q or None)
            self._json(200, {"docs": docs})
            return
        if u.path.startswith("/api/kb/docs/"):
            doc_id = u.path[len("/api/kb/docs/") :].strip("/")
            if not doc_id or "/" in doc_id:
                self._json(400, {"error": "id_required"})
                return
            conn = get_conn()
            with _lock:
                doc = kb_store.get_doc(conn, doc_id)
            if not doc:
                self._json(404, {"error": "not_found"})
                return
            self._json(200, {"doc": doc})
            return
        if u.path == "/api/projects":
            qs = parse_qs(u.query)
            cat = (qs.get("category") or [None])[0]
            self._json(200, {"projects": list_projects(cat)})
            return
        if u.path.startswith("/api/projects/"):
            pid = u.path[len("/api/projects/") :].strip("/")
            p = get_project(pid)
            if not p:
                self._json(404, {"error": "not_found"})
                return
            self._json(200, {"project": p})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        u = urlparse(self.path)
        if u.path == "/api/kb/import":
            conn = get_conn()
            with _lock:
                result = kb_store.import_markdown_dirs(conn)
            self._json(200, result)
            return
        if u.path == "/api/kb/docs":
            conn = get_conn()
            with _lock:
                doc = kb_store.create_doc(conn, self._read())
            self._json(201, {"doc": doc})
            return
        if u.path == "/api/projects":
            p = create_project(self._read())
            self._json(201, {"project": p})
            return
        if u.path.startswith("/api/projects/") and u.path.rstrip("/").endswith("/archive"):
            pid = u.path[len("/api/projects/") :].rstrip("/").removesuffix("/archive").strip("/")
            if not pid:
                self._json(400, {"error": "id_required"})
                return
            p = archive_project(pid)
            if not p:
                self._json(404, {"error": "not_found"})
                return
            self._json(200, {"project": p})
            return
        self._json(404, {"error": "not_found"})

    def do_PATCH(self) -> None:
        u = urlparse(self.path)
        if u.path.startswith("/api/kb/docs/"):
            doc_id = u.path[len("/api/kb/docs/") :].strip("/")
            if not doc_id or "/" in doc_id:
                self._json(400, {"error": "id_required"})
                return
            conn = get_conn()
            with _lock:
                doc = kb_store.patch_doc(conn, doc_id, self._read())
            if not doc:
                self._json(404, {"error": "not_found"})
                return
            self._json(200, {"doc": doc})
            return
        if u.path.startswith("/api/projects/"):
            pid = u.path[len("/api/projects/") :].strip("/")
            p = patch_project(pid, self._read())
            if not p:
                self._json(404, {"error": "not_found"})
                return
            self._json(200, {"project": p})
            return
        self._json(404, {"error": "not_found"})

    def do_DELETE(self) -> None:
        u = urlparse(self.path)
        if u.path.startswith("/api/kb/docs/"):
            doc_id = u.path[len("/api/kb/docs/") :].strip("/")
            if not doc_id or "/" in doc_id:
                self._json(400, {"error": "id_required"})
                return
            conn = get_conn()
            with _lock:
                ok = kb_store.delete_doc(conn, doc_id)
            if not ok:
                self._json(404, {"error": "not_found"})
                return
            self._json(200, {"ok": True, "id": doc_id})
            return
        if u.path.startswith("/api/projects/"):
            pid = u.path[len("/api/projects/") :].strip("/")
            if not pid or "/" in pid:
                self._json(400, {"error": "id_required"})
                return
            if not delete_project(pid):
                self._json(404, {"error": "not_found"})
                return
            self._json(200, {"ok": True, "id": pid})
            return
        self._json(404, {"error": "not_found"})


def main() -> None:
    get_conn()
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8090"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"projects-api on {host}:{port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
