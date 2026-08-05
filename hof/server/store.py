"""名人堂 SQLite 存储层：submissions / genomes / allele_stats 三张文表。

- submissions：逐份上报流水（含接收/拒绝状态与原因），排行榜聚合的原料；
- genomes：gene_hash 去重后的完整基因组（bank + variant），供 seed 下载；
- allele_stats：每条等位在其出场 genome 中的表现快照，等位边际表现（PBIL）的原料。
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggregate import beta_shrink, merge_dim_means, merge_weighted_mean_sdv

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contributor_id TEXT NOT NULL,
  gene_hash TEXT NOT NULL,
  model TEXT NOT NULL DEFAULT '',
  submitted_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'accepted',
  reason TEXT NOT NULL DEFAULT '',
  composite REAL,
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_submissions_gene ON submissions(gene_hash, status);
CREATE INDEX IF NOT EXISTS idx_submissions_id ON submissions(id);

CREATE TABLE IF NOT EXISTS genomes (
  gene_hash TEXT PRIMARY KEY,
  genome_json TEXT NOT NULL,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  n_submissions INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS allele_stats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slot TEXT NOT NULL,
  allele_id TEXT NOT NULL,
  gene_hash TEXT NOT NULL,
  dim_means_json TEXT NOT NULL DEFAULT '{}',
  composite REAL
);
CREATE INDEX IF NOT EXISTS idx_allele_slot ON allele_stats(slot, allele_id);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    """线程安全的 SQLite 存取（每操作一条短连接，MVP 规模足够）。"""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ---------------- 写入 ----------------

    def record_submission(
        self,
        payload: dict,
        *,
        status: str = "accepted",
        reason: str = "",
    ) -> int:
        """记录一份上报（accepted 时同步 upsert genome + 写 allele_stats）。"""
        genome = payload.get("genome") or {}
        evaluation = payload.get("evaluation") or {}
        gene_hash = str(genome.get("gene_hash") or "")
        model = str(evaluation.get("model") or "")
        composite = (evaluation.get("stats") or {}).get("composite")
        try:
            composite = float(composite) if composite is not None else None
        except (TypeError, ValueError):
            composite = None
        now = utcnow()
        submitted_at = str(payload.get("submitted_at") or now)
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO submissions (contributor_id, gene_hash, model, submitted_at,"
                " status, reason, composite, payload_json) VALUES (?,?,?,?,?,?,?,?)",
                (
                    str(payload.get("contributor_id") or ""),
                    gene_hash,
                    model,
                    submitted_at,
                    status,
                    reason,
                    composite,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            sub_id = int(cur.lastrowid)
            if status == "accepted" and gene_hash:
                conn.execute(
                    "INSERT INTO genomes (gene_hash, genome_json, first_seen, last_seen, n_submissions)"
                    " VALUES (?,?,?,?,1)"
                    " ON CONFLICT(gene_hash) DO UPDATE SET"
                    "   genome_json=excluded.genome_json,"
                    "   last_seen=excluded.last_seen,"
                    "   n_submissions=genomes.n_submissions+1",
                    (gene_hash, json.dumps(genome, ensure_ascii=False), now, now),
                )
                self._insert_allele_rows(conn, gene_hash, genome, evaluation)
        return sub_id

    @staticmethod
    def _insert_allele_rows(conn, gene_hash: str, genome: dict, evaluation: dict) -> None:
        bank = genome.get("bank") or {}
        variant_id = genome.get("variant_id")
        variant = next(
            (v for v in bank.get("variants") or [] if v.get("id") == variant_id),
            None,
        )
        if not variant and bank.get("variants"):
            variant = bank["variants"][0]
        slots = (variant or {}).get("slots") or {}
        dim_means = evaluation.get("dim_means") or {}
        composite = (evaluation.get("stats") or {}).get("composite")
        try:
            composite = float(composite) if composite is not None else None
        except (TypeError, ValueError):
            composite = None
        dim_json = json.dumps(dim_means, ensure_ascii=False)
        for slot, allele_id in slots.items():
            if not allele_id:
                continue
            conn.execute(
                "INSERT INTO allele_stats (slot, allele_id, gene_hash, dim_means_json, composite)"
                " VALUES (?,?,?,?,?)",
                (str(slot), str(allele_id), gene_hash, dim_json, composite),
            )

    # ---------------- 读取 ----------------

    def leaderboard(
        self,
        *,
        dimension: str = "",
        model: str = "",
        suite: str = "",
        min_n: int = 3,
        limit: int = 50,
        m: float = 5.0,
        prior: float = 75.0,
    ) -> list[dict[str, Any]]:
        """按 (gene_hash, model) 分组聚合 accepted 上报，按 shrunk composite 排序。

        dimension 非空时：只统计 dim_means 含该维度的上报，且排名改用该维度均分的收缩值。
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT contributor_id, gene_hash, model, submitted_at, payload_json"
                " FROM submissions WHERE status='accepted'"
            ).fetchall()
        groups: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            try:
                payload = json.loads(row["payload_json"])
            except (TypeError, ValueError):
                continue
            ev = payload.get("evaluation") or {}
            stats = ev.get("stats") or {}
            dims = ev.get("dim_means") or {}
            if model and row["model"] != model:
                continue
            if suite:
                cases = ((ev.get("testset") or {}).get("cases")) or []
                if not any(c.get("suite") == suite for c in cases if isinstance(c, dict)):
                    continue
            if dimension and dimension not in dims:
                continue
            key = (row["gene_hash"], row["model"])
            g = groups.setdefault(
                key,
                {
                    "gene_hash": row["gene_hash"],
                    "model": row["model"],
                    "contributor_id": row["contributor_id"],
                    "last_seen": row["submitted_at"],
                    "records": [],
                    "composites": [],
                    "dims": [],
                    "demand_tags": set(),
                },
            )
            try:
                n = int(stats.get("n") or 0)
                mean = float(stats.get("mean"))
                sdv = float(stats.get("sdv") or 0.0)
            except (TypeError, ValueError):
                continue
            g["records"].append((mean, sdv, n))
            comp = stats.get("composite")
            if comp is not None:
                g["composites"].append((float(comp), max(n, 1)))
            g["dims"].append((dims, max(n, 1)))
            if row["submitted_at"] > g["last_seen"]:
                g["last_seen"] = row["submitted_at"]
            for tag in ((payload.get("context") or {}).get("demand_tags")) or []:
                g["demand_tags"].add(str(tag))

        out = []
        for g in groups.values():
            mean, sdv, n = merge_weighted_mean_sdv(g["records"])
            if n < min_n:
                continue
            merged_dims = merge_dim_means(g["dims"])
            if dimension:
                rank_base = merged_dims.get(dimension)
                if rank_base is None:
                    continue
            else:
                comp_records = [(c, 0.0, w) for c, w in g["composites"]]
                rank_base, _, _ = merge_weighted_mean_sdv(comp_records)
                if not g["composites"]:
                    rank_base = mean
            shrunk = beta_shrink(rank_base, n, m=m, prior=prior)
            out.append(
                {
                    "gene_hash": g["gene_hash"],
                    "model": g["model"],
                    "mean": round(mean, 3),
                    "sdv": round(sdv, 3),
                    "n": n,
                    "composite": round(rank_base, 3),
                    "shrunk": round(shrunk, 3),
                    "dimension": dimension or None,
                    "dim_means": {k: round(v, 3) for k, v in merged_dims.items()},
                    "demand_tags": sorted(g["demand_tags"]),
                    "contributor_id": g["contributor_id"],
                    "last_seen": g["last_seen"],
                }
            )
        out.sort(key=lambda x: x["shrunk"], reverse=True)
        return out[:limit]

    def get_genome(self, gene_hash: str) -> dict[str, Any] | None:
        """返回完整基因组，并展开为 factory evolve/start 可直接使用的 seed 格式。

        返回 {gene_hash, variant_id, title, bank, slots, slot_texts}：
        bank+variant 为原始存档；slots/slot_texts 与 factory `_seed_from_variant` 同构，
        `bank_from_improve_seed` 可直接消费。
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT genome_json, first_seen, last_seen, n_submissions FROM genomes WHERE gene_hash=?",
                (gene_hash,),
            ).fetchone()
        if not row:
            return None
        genome = json.loads(row["genome_json"])
        bank = genome.get("bank") or {}
        variant_id = genome.get("variant_id")
        variant = next(
            (v for v in bank.get("variants") or [] if v.get("id") == variant_id),
            None,
        ) or (bank.get("variants") or [{}])[0]
        slots = dict(variant.get("slots") or {})
        slot_texts: dict[str, Any] = {}
        for slot, allele_id in slots.items():
            allele = next(
                (a for a in bank.get("alleles", {}).get(slot) or [] if a.get("id") == allele_id),
                None,
            )
            slot_texts[slot] = {
                "allele_id": allele_id,
                "allele": (
                    {"id": allele.get("id"), "label": allele.get("label"), "text": allele.get("text")}
                    if allele
                    else None
                ),
            }
        return {
            "gene_hash": gene_hash,
            "variant_id": variant.get("id"),
            "title": variant.get("title"),
            "bank": bank,
            "slots": slots,
            "slot_texts": slot_texts,
            "first_seen": row["first_seen"],
            "last_seen": row["last_seen"],
            "n_submissions": row["n_submissions"],
        }

    def allele_performance(self, slot: str = "", limit: int = 50) -> list[dict[str, Any]]:
        """等位边际表现：每条等位在其出场 genome 中的平均 composite 与 dim_means 均值。"""
        sql = "SELECT slot, allele_id, gene_hash, dim_means_json, composite FROM allele_stats"
        args: tuple = ()
        if slot:
            sql += " WHERE slot=?"
            args = (slot,)
        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        groups: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            key = (row["slot"], row["allele_id"])
            g = groups.setdefault(key, {"slot": row["slot"], "allele_id": row["allele_id"],
                                        "composites": [], "dims": [], "gene_hashes": set()})
            g["gene_hashes"].add(row["gene_hash"])
            if row["composite"] is not None:
                g["composites"].append(float(row["composite"]))
            try:
                dims = json.loads(row["dim_means_json"] or "{}")
            except (TypeError, ValueError):
                dims = {}
            g["dims"].append((dims, 1))
        out = []
        for g in groups.values():
            comps = g["composites"]
            out.append(
                {
                    "slot": g["slot"],
                    "allele_id": g["allele_id"],
                    "appearances": len(g["dims"]),
                    "n_genomes": len(g["gene_hashes"]),
                    "composite": round(sum(comps) / len(comps), 3) if comps else None,
                    "dim_means": {k: round(v, 3) for k, v in merge_dim_means(g["dims"]).items()},
                }
            )
        out.sort(key=lambda x: (x["composite"] is None, -(x["composite"] or 0)))
        return out[:limit]

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) c FROM submissions").fetchone()["c"]
            accepted = conn.execute(
                "SELECT COUNT(*) c FROM submissions WHERE status='accepted'"
            ).fetchone()["c"]
            genomes = conn.execute("SELECT COUNT(*) c FROM genomes").fetchone()["c"]
            contributors = conn.execute(
                "SELECT COUNT(DISTINCT contributor_id) c FROM submissions"
            ).fetchone()["c"]
            models = conn.execute(
                "SELECT model, COUNT(*) c FROM submissions WHERE status='accepted'"
                " GROUP BY model ORDER BY c DESC"
            ).fetchall()
        return {
            "submissions_total": total,
            "submissions_accepted": accepted,
            "submissions_rejected": total - accepted,
            "genomes": genomes,
            "contributors": contributors,
            "models": {row["model"]: row["c"] for row in models if row["model"]},
        }

    def recent_submissions(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, contributor_id, gene_hash, model, submitted_at, status, reason, composite"
                " FROM submissions ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "contributor_id": row["contributor_id"],
                "gene_hash": row["gene_hash"],
                "model": row["model"],
                "submitted_at": row["submitted_at"],
                "status": row["status"],
                "reason": row["reason"],
                "composite": row["composite"],
            }
            for row in rows
        ]
