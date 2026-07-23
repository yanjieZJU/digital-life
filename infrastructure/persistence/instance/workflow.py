"""Per-instance workflow DB: ``apps/<id>/data/workflow.db``.

Engine plumbing — what events are queued, what timers are armed, what
affairs are in flight, plus the flow-event audit trail. Schema mirrors
the existing tables in ``state.db`` so callers can lift move by move
without renegotiating data shapes.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from infrastructure.config import get_app_instance_id, get_instance_data_dir
from infrastructure.persistence.instance.base import InstanceDB


SCHEMA_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    fire_at TEXT,
    kind TEXT,
    consumed_at TEXT,
    target_affair_id TEXT,
    consumed_by_session_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_unconsumed ON events(consumed_at, channel);
"""

SCHEMA_TIMERS = """
CREATE TABLE IF NOT EXISTS timers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_kind TEXT NOT NULL,
    fire_at TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    fired_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_timers_due ON timers(fired_at, fire_at);
"""

SCHEMA_AFFAIRS = """
CREATE TABLE IF NOT EXISTS affairs (
    affair_id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    deadline TEXT,
    session_id TEXT,
    mental_context TEXT,
    history_digest TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    meta_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_affairs_status ON affairs(status);
CREATE INDEX IF NOT EXISTS idx_affairs_priority ON affairs(priority DESC);
"""

SCHEMA_WAIT_INTENTS = """
CREATE TABLE IF NOT EXISTS wait_intents (
    affair_id TEXT PRIMARY KEY REFERENCES affairs(affair_id) ON DELETE CASCADE,
    wait_type TEXT NOT NULL,
    resume_when TEXT NOT NULL,
    interval_seconds INTEGER,
    max_wait_until TEXT,
    reason TEXT,
    resume_action TEXT,
    blocked_at TEXT NOT NULL,
    meta_json TEXT NOT NULL DEFAULT '{}'
);
"""

SCHEMA_HEARTBEATS = """
CREATE TABLE IF NOT EXISTS heartbeats (
    hb_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fired_at TEXT NOT NULL,
    woke_affair_id TEXT,
    reflect INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);
"""

SCHEMA_FLOW_RUNS = """
CREATE TABLE IF NOT EXISTS flow_event_logs (
    run_id TEXT PRIMARY KEY,
    employee_id TEXT,
    message_event_id TEXT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_flow_runs_employee ON flow_event_logs(employee_id, started_at DESC);
"""

SCHEMA_FLOW_EVENTS = """
CREATE TABLE IF NOT EXISTS flow_event_log_events (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    type TEXT NOT NULL,
    layer TEXT NOT NULL,
    source TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    employee_id TEXT,
    message_event_id TEXT,
    parent_event_id TEXT,
    causation_event_id TEXT,
    correlation_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    summary TEXT NOT NULL DEFAULT '',
    severity TEXT NOT NULL DEFAULT 'info',
    FOREIGN KEY (run_id) REFERENCES flow_event_logs(run_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_flow_events_run_sequence
    ON flow_event_log_events(run_id, sequence);
CREATE INDEX IF NOT EXISTS idx_flow_events_layer
    ON flow_event_log_events(run_id, layer, sequence);
"""


class WorkflowDB(InstanceDB):
    SCHEMA_SQL = (
        SCHEMA_EVENTS,
        SCHEMA_TIMERS,
        SCHEMA_AFFAIRS,
        SCHEMA_WAIT_INTENTS,
        SCHEMA_HEARTBEATS,
        SCHEMA_FLOW_RUNS,
        SCHEMA_FLOW_EVENTS,
    )

    def __init__(self, db_path: Path | None = None, instance_id: str | None = None) -> None:
        if db_path is None:
            db_path = get_instance_data_dir(instance_id) / "workflow.db"
        super().__init__(db_path)
        self.instance_id = instance_id or get_app_instance_id() or ""

    # ---- events -----------------------------------------------------------

    def enqueue_event(self, channel: str, payload: dict[str, Any], *, kind: str | None = None,
                      fire_at: str | None = None) -> int:
        cur = self.execute(
            """INSERT INTO events (channel, payload, created_at, kind, fire_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                channel,
                json.dumps(payload, ensure_ascii=False, default=str),
                _now_iso(),
                kind,
                fire_at,
            ),
        )
        self.commit()
        return int(cur.lastrowid)

    def claim_next_event(self, channel: str) -> dict[str, Any] | None:
        row = self.fetchone(
            "SELECT * FROM events WHERE channel = ? AND consumed_at IS NULL "
            "ORDER BY event_id LIMIT 1",
            (channel,),
        )
        if not row:
            return None
        self.execute(
            "UPDATE events SET consumed_at = ? WHERE event_id = ?",
            (_now_iso(), row["event_id"]),
        )
        self.commit()
        return row

    # ---- timers -----------------------------------------------------------

    def arm_timer(self, event_kind: str, fire_at: str, payload: dict[str, Any] | None = None) -> int:
        cur = self.execute(
            """INSERT INTO timers (event_kind, fire_at, payload_json, created_at)
               VALUES (?, ?, ?, ?)""",
            (event_kind, fire_at, json.dumps(payload or {}, ensure_ascii=False), _now_iso()),
        )
        self.commit()
        return int(cur.lastrowid)

    def fire_due_timers(self, *, now_iso: str | None = None) -> list[dict[str, Any]]:
        now = now_iso or _now_iso()
        rows = self.fetchall(
            "SELECT * FROM timers WHERE fired_at IS NULL AND fire_at <= ? ORDER BY fire_at",
            (now,),
        )
        if not rows:
            return []
        ids = tuple(r["id"] for r in rows)
        placeholders = ",".join("?" for _ in ids)
        self.execute(
            f"UPDATE timers SET fired_at = ? WHERE id IN ({placeholders})",
            (now, *ids),
        )
        self.commit()
        return rows

    # ---- affairs ----------------------------------------------------------

    def upsert_affair(self, **fields: Any) -> str:
        affair_id = fields["affair_id"]
        exists = self.fetchone("SELECT affair_id FROM affairs WHERE affair_id = ?", (affair_id,))
        meta = fields.get("meta_json") or {}
        if isinstance(meta, dict):
            meta = json.dumps(meta, ensure_ascii=False, default=str)
        now = _now_iso()
        if exists:
            self.execute(
                """UPDATE affairs SET
                    goal = COALESCE(?, goal),
                    status = COALESCE(?, status),
                    priority = COALESCE(?, priority),
                    deadline = COALESCE(?, deadline),
                    session_id = COALESCE(?, session_id),
                    mental_context = COALESCE(?, mental_context),
                    history_digest = COALESCE(?, history_digest),
                    completed_at = COALESCE(?, completed_at),
                    meta_json = COALESCE(?, meta_json),
                    updated_at = ?
                   WHERE affair_id = ?""",
                (
                    fields.get("goal"),
                    fields.get("status"),
                    fields.get("priority"),
                    fields.get("deadline"),
                    fields.get("session_id"),
                    fields.get("mental_context"),
                    fields.get("history_digest"),
                    fields.get("completed_at"),
                    meta if fields.get("meta_json") is not None else None,
                    now,
                    affair_id,
                ),
            )
        else:
            self.execute(
                """INSERT INTO affairs
                (affair_id, goal, status, priority, deadline, session_id,
                 mental_context, history_digest, created_at, updated_at, meta_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    affair_id,
                    fields["goal"],
                    fields["status"],
                    int(fields.get("priority") or 0),
                    fields.get("deadline"),
                    fields.get("session_id"),
                    fields.get("mental_context"),
                    fields.get("history_digest"),
                    now,
                    now,
                    meta,
                ),
            )
        self.commit()
        return affair_id

    def list_affairs(self, *, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            return self.fetchall(
                "SELECT * FROM affairs WHERE status = ? ORDER BY priority DESC, updated_at DESC",
                (status,),
            )
        return self.fetchall(
            "SELECT * FROM affairs ORDER BY priority DESC, updated_at DESC"
        )


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
