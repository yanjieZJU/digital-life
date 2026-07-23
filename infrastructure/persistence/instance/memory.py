"""Per-instance memory DB: ``apps/<id>/data/memory.db``.

Long-lived memory the LLM reads as context (injected via fake-tool rules).
Three tables:

- ``seg_digest``: per-wake 段压缩摘要（"我做过什么"的低分辨率回放）
- ``slow_var``:  慢变量当前值（自我认知 / 社交关系 / 任务板 等），只留 latest 版本
- ``chat_fact``: 跨 wake 的对话事实流水（chat 维度，原文），上一版散在 messages.chat_id

This module owns schema only. Reads/writes from callers move here once
agents are migrated. Until then the legacy ``memory_layers.db`` /
``tasks.db`` continue to drive the live runtime.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from infrastructure.config import get_app_instance_id, get_instance_data_dir
from infrastructure.persistence.instance.base import InstanceDB


SCHEMA_SEG_DIGEST = """
CREATE TABLE IF NOT EXISTS seg_digest (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id TEXT NOT NULL,
    wake_id INTEGER,
    wake_seq INTEGER,
    layer TEXT NOT NULL,
    period TEXT NOT NULL,
    digest TEXT NOT NULL,
    llm_summary TEXT,
    tool_summary TEXT,
    start_time REAL,
    end_time REAL,
    parent_ids TEXT,
    created_at REAL NOT NULL,
    fallback INTEGER DEFAULT 0,
    UNIQUE(instance_id, layer, period)
);
CREATE INDEX IF NOT EXISTS idx_seg_layer ON seg_digest(layer);
CREATE INDEX IF NOT EXISTS idx_seg_period ON seg_digest(period);
CREATE INDEX IF NOT EXISTS idx_seg_start ON seg_digest(start_time);
CREATE INDEX IF NOT EXISTS idx_seg_wake ON seg_digest(instance_id, wake_seq);
"""

SCHEMA_SLOW_VAR = """
CREATE TABLE IF NOT EXISTS slow_var (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    scope_id TEXT NOT NULL DEFAULT '*',
    content TEXT NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(instance_id, kind, scope_id)
);
CREATE INDEX IF NOT EXISTS idx_slow_kind ON slow_var(instance_id, kind);
"""

SCHEMA_CHAT_FACT = """
CREATE TABLE IF NOT EXISTS chat_fact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    speaker TEXT NOT NULL,
    speaker_name TEXT,
    text TEXT,
    payload TEXT,
    said_at REAL NOT NULL,
    source_ref TEXT
);
CREATE INDEX IF NOT EXISTS idx_chat_fact_chat ON chat_fact(chat_id, said_at);
CREATE INDEX IF NOT EXISTS idx_chat_fact_speaker ON chat_fact(speaker, said_at);
"""

SCHEMA_CONTACT = """
CREATE TABLE IF NOT EXISTS contact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    blocked INTEGER NOT NULL DEFAULT 0,
    block_reason TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'human',
    updated_at TEXT NOT NULL,
    UNIQUE(instance_id, contact_id)
);
CREATE INDEX IF NOT EXISTS idx_contact_kind ON contact(instance_id, kind);
CREATE INDEX IF NOT EXISTS idx_contact_blocked ON contact(instance_id, blocked);
"""

SCHEMA_CONTACT_IDS = """
CREATE TABLE IF NOT EXISTS contact_ids (
    contact_id TEXT NOT NULL,
    instance_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    platform_id TEXT NOT NULL,
    PRIMARY KEY (contact_id, platform, platform_id)
);
CREATE INDEX IF NOT EXISTS idx_contact_ids_lookup ON contact_ids(platform, platform_id);
"""

SCHEMA_NURTURE_LOG = """
CREATE TABLE IF NOT EXISTS nurture_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id TEXT NOT NULL,
    at TEXT NOT NULL,
    kind TEXT NOT NULL,
    deltas_json TEXT NOT NULL DEFAULT '{}',
    raw_text TEXT,
    source TEXT
);
CREATE INDEX IF NOT EXISTS idx_nurture_at ON nurture_log(at DESC);
"""


class MemoryDB(InstanceDB):
    SCHEMA_SQL = (
        SCHEMA_SEG_DIGEST,
        SCHEMA_SLOW_VAR,
        SCHEMA_CHAT_FACT,
        SCHEMA_CONTACT,
        SCHEMA_CONTACT_IDS,
        SCHEMA_NURTURE_LOG,
    )

    def __init__(self, db_path: Path | None = None, instance_id: str | None = None) -> None:
        if db_path is None:
            db_path = get_instance_data_dir(instance_id) / "memory.db"
        super().__init__(db_path)
        self.instance_id = instance_id or get_app_instance_id() or ""

    # ---- seg_digest -------------------------------------------------------

    def upsert_seg_digest(self, **fields: Any) -> int:
        """Insert or update by (layer, period).

        Mirrors the legacy ``memory_layers`` table — call sites that write
        per-wake 段摘要 should switch here once audit migration lands.
        """
        layer = fields["layer"]
        period = fields["period"]
        content = fields.get("digest") or ""
        llm_summary = fields.get("llm_summary")
        tool_summary = fields.get("tool_summary")
        start_time = fields.get("start_time")
        end_time = fields.get("end_time")
        parent_ids = fields.get("parent_ids")
        if isinstance(parent_ids, (list, tuple)):
            parent_ids = json.dumps(parent_ids, ensure_ascii=False, default=str)
        fallback = int(bool(fields.get("fallback", False)))
        created_at = fields.get("created_at") or time.time()
        wake_id = fields.get("wake_id")
        wake_seq = fields.get("wake_seq")

        cur = self.execute(
            """INSERT INTO seg_digest
            (instance_id, wake_id, wake_seq, layer, period, digest, llm_summary,
             tool_summary, start_time, end_time, parent_ids, created_at, fallback)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(instance_id, layer, period) DO UPDATE SET
                wake_id = excluded.wake_id,
                wake_seq = excluded.wake_seq,
                digest = excluded.digest,
                llm_summary = excluded.llm_summary,
                tool_summary = excluded.tool_summary,
                start_time = excluded.start_time,
                end_time = excluded.end_time,
                parent_ids = excluded.parent_ids,
                created_at = excluded.created_at,
                fallback = excluded.fallback
            """,
            (
                self.instance_id, wake_id, wake_seq, layer, period, content,
                llm_summary, tool_summary, start_time, end_time, parent_ids,
                created_at, fallback,
            ),
        )
        self.commit()
        return int(cur.lastrowid)

    def list_recent_seg_digests(
        self,
        *,
        layer: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM seg_digest WHERE instance_id = ?"
        params: list[Any] = [self.instance_id]
        if layer:
            sql += " AND layer = ?"
            params.append(layer)
        sql += " ORDER BY start_time DESC, id DESC LIMIT ?"
        params.append(limit)
        return self.fetchall(sql, tuple(params))

    # ---- slow_var ---------------------------------------------------------

    def set_slow_var(self, *, kind: str, content: str, scope_id: str = "*") -> int:
        cur = self.execute(
            """INSERT INTO slow_var (instance_id, kind, scope_id, content, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(instance_id, kind, scope_id) DO UPDATE SET
                 content = excluded.content,
                 updated_at = excluded.updated_at""",
            (self.instance_id, kind, scope_id, content, time.time()),
        )
        self.commit()
        return int(cur.lastrowid)

    def get_slow_var(self, kind: str, scope_id: str = "*") -> dict[str, Any] | None:
        return self.fetchone(
            "SELECT * FROM slow_var WHERE instance_id = ? AND kind = ? AND scope_id = ?",
            (self.instance_id, kind, scope_id),
        )

    def list_slow_vars(self, *, kind: str | None = None) -> list[dict[str, Any]]:
        if kind:
            return self.fetchall(
                "SELECT * FROM slow_var WHERE instance_id = ? AND kind = ? ORDER BY kind, scope_id",
                (self.instance_id, kind),
            )
        return self.fetchall(
            "SELECT * FROM slow_var WHERE instance_id = ? ORDER BY kind, scope_id",
            (self.instance_id,),
        )

    # ---- chat_fact --------------------------------------------------------

    def append_chat_fact(
        self,
        *,
        chat_id: str,
        speaker: str,
        text: str | None = None,
        speaker_name: str | None = None,
        payload: dict[str, Any] | None = None,
        said_at: float | None = None,
        source_ref: str | None = None,
    ) -> int:
        cur = self.execute(
            """INSERT INTO chat_fact
            (instance_id, chat_id, speaker, speaker_name, text, payload, said_at, source_ref)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                self.instance_id,
                chat_id,
                speaker,
                speaker_name,
                text,
                json.dumps(payload, ensure_ascii=False, default=str) if payload else None,
                said_at if said_at is not None else time.time(),
                source_ref,
            ),
        )
        self.commit()
        return int(cur.lastrowid)

    def list_chat_facts(
        self,
        chat_id: str,
        *,
        limit: int = 50,
        speaker: str | None = None,
    ) -> list[dict[str, Any]]:
        if speaker:
            rows = self.fetchall(
                "SELECT * FROM chat_fact WHERE chat_id = ? AND speaker = ? "
                "ORDER BY said_at DESC, id DESC LIMIT ?",
                (chat_id, speaker, limit),
            )
        else:
            rows = self.fetchall(
                "SELECT * FROM chat_fact WHERE chat_id = ? "
                "ORDER BY said_at DESC, id DESC LIMIT ?",
                (chat_id, limit),
            )
        results: list[dict[str, Any]] = []
        for r in reversed(rows):
            payload = r.get("payload")
            if payload:
                try:
                    r["payload"] = json.loads(payload)
                except Exception:
                    pass
            results.append(r)
        return results

    # ---- contact ----------------------------------------------------------

    def upsert_contact(
        self,
        contact_id: str,
        *,
        name: str | None = None,
        kind: str = "human",
        notes: str | None = None,
        blocked: bool | None = None,
        block_reason: str | None = None,
    ) -> str:
        """Insert-or-update by (instance_id, contact_id). Returns the contact_id."""
        existing = self.fetchone(
            "SELECT * FROM contact WHERE instance_id = ? AND contact_id = ?",
            (self.instance_id, contact_id),
        )
        now = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        if existing:
            self.execute(
                """UPDATE contact SET
                    name = COALESCE(?, name),
                    notes = COALESCE(?, notes),
                    kind = COALESCE(?, kind),
                    blocked = COALESCE(?, blocked),
                    block_reason = COALESCE(?, block_reason),
                    updated_at = ?
                   WHERE instance_id = ? AND contact_id = ?""",
                (
                    name,
                    notes,
                    kind,
                    int(blocked) if blocked is not None else None,
                    block_reason,
                    now,
                    self.instance_id,
                    contact_id,
                ),
            )
        else:
            self.execute(
                """INSERT INTO contact
                (instance_id, contact_id, name, kind, notes, blocked, block_reason, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    self.instance_id,
                    contact_id,
                    name or "",
                    kind,
                    notes or "",
                    int(blocked) if blocked is not None else 0,
                    block_reason or "",
                    now,
                ),
            )
        self.commit()
        return contact_id

    def get_contact(self, contact_id: str) -> dict[str, Any] | None:
        return self.fetchone(
            "SELECT * FROM contact WHERE instance_id = ? AND contact_id = ?",
            (self.instance_id, contact_id),
        )

    def find_by_platform(self, platform: str, platform_id: str) -> dict[str, Any] | None:
        row = self.fetchone(
            "SELECT c.* FROM contact c "
            "JOIN contact_ids i ON i.contact_id = c.contact_id "
            "  AND i.instance_id = c.instance_id "
            "WHERE i.platform = ? AND i.platform_id = ?",
            (platform, platform_id),
        )
        return row

    def link_platform(self, contact_id: str, platform: str, platform_id: str) -> None:
        self.execute(
            """INSERT OR IGNORE INTO contact_ids
            (contact_id, instance_id, platform, platform_id) VALUES (?, ?, ?, ?)""",
            (contact_id, self.instance_id, platform, platform_id),
        )
        self.commit()

    def list_contacts(self, *, kind: str | None = None) -> list[dict[str, Any]]:
        if kind:
            return self.fetchall(
                "SELECT * FROM contact WHERE instance_id = ? AND kind = ? "
                "ORDER BY updated_at DESC",
                (self.instance_id, kind),
            )
        return self.fetchall(
            "SELECT * FROM contact WHERE instance_id = ? ORDER BY updated_at DESC",
            (self.instance_id,),
        )

    # ---- nurture_log ------------------------------------------------------

    def log_nurture(
        self,
        *,
        kind: str,
        deltas: dict[str, float] | None = None,
        raw_text: str | None = None,
        source: str | None = None,
        at: str | None = None,
    ) -> int:
        cur = self.execute(
            """INSERT INTO nurture_log
            (instance_id, at, kind, deltas_json, raw_text, source)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                self.instance_id,
                at or time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                kind,
                json.dumps(deltas or {}, ensure_ascii=False),
                raw_text,
                source,
            ),
        )
        self.commit()
        return int(cur.lastrowid)

    def list_nurture(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.fetchall(
            "SELECT * FROM nurture_log WHERE instance_id = ? "
            "ORDER BY log_id DESC LIMIT ?",
            (self.instance_id, limit),
        )
        for r in rows:
            try:
                r["deltas_json"] = json.loads(r["deltas_json"] or "{}")
            except Exception:
                r["deltas_json"] = {}
        return rows
