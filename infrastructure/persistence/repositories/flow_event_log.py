"""SQLite persistence for cross-layer flow EventLogs."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any

from domain.flow_event_log import FlowEvent, FlowEventLog, flow_event_from_dict
from infrastructure.persistence import sqlite


class SQLiteFlowEventLogRepository:
    """Persist flow EventLogs in project runtime state.db.

    This repository intentionally uses its own tables and does not reuse the
    legacy lifecycle `events` queue.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._memory_conn: sqlite.Connection | None = None
        self._ensure_schema()

    def start_log(self, log: FlowEventLog) -> FlowEventLog:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO flow_event_logs (
                    run_id, employee_id, message_event_id, status, started_at, ended_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.run_id,
                    log.employee_id,
                    log.message_event_id,
                    log.status,
                    log.started_at,
                    log.ended_at,
                    _json(log.metadata),
                ),
            )
        return log

    def append_event(self, event: FlowEvent) -> FlowEvent:
        self._ensure_log_for_event(event)
        with self._connect() as conn:
            sequence = event.sequence
            if sequence is None:
                row = conn.execute(
                    "SELECT COALESCE(MAX(sequence), -1) + 1 AS next_sequence "
                    "FROM flow_event_log_events WHERE run_id = ?",
                    (event.run_id,),
                ).fetchone()
                sequence = int(row["next_sequence"])
                event = replace(event, sequence=sequence)
            conn.execute(
                """
                INSERT INTO flow_event_log_events (
                    id, run_id, sequence, type, layer, source, timestamp,
                    employee_id, message_event_id, parent_event_id, causation_event_id,
                    correlation_id, payload_json, summary, severity
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.run_id,
                    sequence,
                    event.type,
                    event.layer,
                    event.source,
                    event.timestamp,
                    event.employee_id,
                    event.message_event_id,
                    event.parent_event_id,
                    event.causation_event_id,
                    event.correlation_id,
                    _json(event.payload),
                    event.summary,
                    event.severity,
                ),
            )
        return event

    def finish_log(self, run_id: str, *, status: str) -> None:
        from domain.lifecycle.clock import now_iso as _now_iso
        with self._connect() as conn:
            conn.execute(
                "UPDATE flow_event_logs SET status = ?, ended_at = COALESCE(ended_at, ?) WHERE run_id = ?",
                (status, _now_iso(), run_id),
            )

    def get(self, run_id: str) -> FlowEventLog | None:
        with self._connect() as conn:
            log_row = conn.execute("SELECT * FROM flow_event_logs WHERE run_id = ?", (run_id,)).fetchone()
            if log_row is None:
                return None
            rows = conn.execute(
                "SELECT * FROM flow_event_log_events WHERE run_id = ? ORDER BY sequence, timestamp, id",
                (run_id,),
            ).fetchall()
        events = tuple(_row_to_event(row) for row in rows)
        return FlowEventLog(
            run_id=log_row["run_id"],
            employee_id=log_row["employee_id"],
            message_event_id=log_row["message_event_id"],
            status=log_row["status"],
            root_event_id=events[0].id if events else None,
            started_at=log_row["started_at"],
            ended_at=log_row["ended_at"],
            metadata=_loads(log_row["metadata_json"]),
            events=events,
        )

    def _ensure_log_for_event(self, event: FlowEvent) -> None:
        self.start_log(
            FlowEventLog(
                run_id=event.run_id,
                employee_id=event.employee_id,
                message_event_id=event.message_event_id,
                metadata={"created_by": "SQLiteFlowEventLogRepository.ensure_log"},
            )
        )

    def _connect(self) -> sqlite.Connection:
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            if self._memory_conn is None:
                self._memory_conn = sqlite.connect(":memory:")
                self._memory_conn.row_factory = sqlite.Row
            return self._memory_conn
        conn = sqlite.connect(str(self.db_path))
        conn.row_factory = sqlite.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS flow_event_logs (
                    run_id TEXT PRIMARY KEY,
                    employee_id TEXT,
                    message_event_id TEXT,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

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

                CREATE UNIQUE INDEX IF NOT EXISTS idx_flow_event_log_events_run_sequence
                ON flow_event_log_events(run_id, sequence);

                CREATE INDEX IF NOT EXISTS idx_flow_event_log_events_layer
                ON flow_event_log_events(run_id, layer, sequence);
                """
            )


def _row_to_event(row: Any) -> FlowEvent:
    return flow_event_from_dict(
        {
            "id": row["id"],
            "run_id": row["run_id"],
            "sequence": row["sequence"],
            "type": row["type"],
            "layer": row["layer"],
            "source": row["source"],
            "timestamp": row["timestamp"],
            "employee_id": row["employee_id"],
            "message_event_id": row["message_event_id"],
            "parent_event_id": row["parent_event_id"],
            "causation_event_id": row["causation_event_id"],
            "correlation_id": row["correlation_id"],
            "payload": _loads(row["payload_json"]),
            "summary": row["summary"],
            "severity": row["severity"],
        }
    )


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True, default=str)


def _loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


__all__ = ["SQLiteFlowEventLogRepository"]
