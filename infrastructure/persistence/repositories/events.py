"""Event repository contracts and storage implementations."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable

from domain.core.contracts import EventQueue, EventRegistry
from domain.core.models import EventInstance, EventStatus, EventTriggerType, EventTypeDefinition
from infrastructure.persistence import sqlite


class InMemoryEventQueue:
    """Small queue implementation before the repository-backed version exists."""

    def __init__(self) -> None:
        self._events: list[EventInstance] = []

    def enqueue(self, event: EventInstance) -> EventInstance:
        self._events.append(event)
        return event

    def next_pending(self, agent_id: str | None = None) -> EventInstance | None:
        for event in self._events:
            if event.status != EventStatus.PENDING:
                continue
            if agent_id is not None and event.agent_id not in (None, agent_id):
                continue
            event.status = EventStatus.RUNNING
            return event
        return None

    def mark_done(self, event_id: str) -> None:
        event = self._find(event_id)
        event.status = EventStatus.DONE

    def mark_blocked(self, event_id: str) -> None:
        event = self._find(event_id)
        event.status = EventStatus.BLOCKED

    def pending(self) -> tuple[EventInstance, ...]:
        return tuple(event for event in self._events if event.status == EventStatus.PENDING)

    def _find(self, event_id: str) -> EventInstance:
        for event in self._events:
            if event.id == event_id:
                return event
        raise KeyError(event_id)


class InMemoryEventRegistry:
    """Minimal registry used for bootstrapping and tests."""

    def __init__(self) -> None:
        self._definitions: dict[str, EventTypeDefinition] = {}

    def register(self, definition: EventTypeDefinition) -> None:
        if definition.type_id in self._definitions:
            raise ValueError(f"event type already registered: {definition.type_id}")
        self._definitions[definition.type_id] = definition

    def get(self, type_id: str) -> EventTypeDefinition | None:
        return self._definitions.get(type_id)

    def list(self) -> tuple[EventTypeDefinition, ...]:
        return tuple(self._definitions.values())


class SQLiteEventQueue:
    """SQLite-backed event queue for runtime event persistence."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._ensure_schema()

    def enqueue(self, event: EventInstance) -> EventInstance:
        now = _now()
        event.created_at = event.created_at or now
        event.updated_at = event.updated_at or now
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO event_runtime_queue (
                    id, type_id, trigger_type, payload_json, status, agent_id,
                    workspace_id, context_hint, fire_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _event_row_values(event),
            )
        return event

    def next_pending(self, agent_id: str | None = None) -> EventInstance | None:
        with self._connect() as conn:
            params: list[Any] = [EventStatus.PENDING.value, _now()]
            agent_clause = ""
            if agent_id is not None:
                agent_clause = "AND (agent_id IS NULL OR agent_id = ?)"
                params.append(agent_id)
            row = conn.execute(
                f"""
                SELECT *
                FROM event_runtime_queue
                WHERE status = ?
                  AND (fire_at IS NULL OR fire_at <= ?)
                  {agent_clause}
                ORDER BY COALESCE(fire_at, created_at), created_at, id
                LIMIT 1
                """,
                params,
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE event_runtime_queue SET status = ?, updated_at = ? WHERE id = ?",
                (EventStatus.RUNNING.value, _now(), row["id"]),
            )
            claimed = conn.execute("SELECT * FROM event_runtime_queue WHERE id = ?", (row["id"],)).fetchone()
        return _row_to_event(claimed)

    def mark_done(self, event_id: str) -> None:
        self.mark_status(event_id, EventStatus.DONE)

    def mark_blocked(self, event_id: str) -> None:
        self.mark_status(event_id, EventStatus.BLOCKED)

    def mark_status(self, event_id: str, status: EventStatus) -> None:
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE event_runtime_queue SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, _now(), event_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(event_id)

    def pending(self) -> tuple[EventInstance, ...]:
        return self._list_by_status((EventStatus.PENDING,))

    def get(self, event_id: str) -> EventInstance | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM event_runtime_queue WHERE id = ?", (event_id,)).fetchone()
        return _row_to_event(row) if row is not None else None

    def _list_by_status(self, statuses: Iterable[EventStatus]) -> tuple[EventInstance, ...]:
        status_values = tuple(status.value for status in statuses)
        placeholders = ", ".join("?" for _ in status_values)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM event_runtime_queue
                WHERE status IN ({placeholders})
                ORDER BY COALESCE(fire_at, created_at), created_at, id
                """,
                status_values,
            ).fetchall()
        return tuple(_row_to_event(row) for row in rows)

    def _connect(self) -> sqlite.Connection:
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite.connect(str(self.db_path))
        conn.row_factory = sqlite.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS event_runtime_queue (
                    id TEXT PRIMARY KEY,
                    type_id TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    agent_id TEXT,
                    workspace_id TEXT,
                    context_hint TEXT NOT NULL DEFAULT '',
                    fire_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_event_runtime_queue_pending
                ON event_runtime_queue(status, fire_at, created_at)
                """
            )


class SQLiteEventRegistry:
    """SQLite-backed event type registry for runtime event definitions."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._ensure_schema()

    def register(self, definition: EventTypeDefinition) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO event_runtime_types (
                        type_id, display_name, trigger_type, payload_schema_json,
                        prompt_template, allowed_tools_json, context_policy_json,
                        auth_policy_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _definition_row_values(definition),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"event type already registered: {definition.type_id}") from exc

    def get(self, type_id: str) -> EventTypeDefinition | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM event_runtime_types WHERE type_id = ?", (type_id,)).fetchone()
        return _row_to_definition(row) if row is not None else None

    def list(self) -> tuple[EventTypeDefinition, ...]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM event_runtime_types ORDER BY type_id").fetchall()
        return tuple(_row_to_definition(row) for row in rows)

    def _connect(self) -> sqlite.Connection:
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite.connect(str(self.db_path))
        conn.row_factory = sqlite.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS event_runtime_types (
                    type_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    payload_schema_json TEXT NOT NULL,
                    prompt_template TEXT NOT NULL DEFAULT '',
                    allowed_tools_json TEXT NOT NULL,
                    context_policy_json TEXT NOT NULL,
                    auth_policy_json TEXT NOT NULL
                )
                """
            )


def _event_row_values(event: EventInstance) -> tuple[Any, ...]:
    return (
        event.id,
        event.type_id,
        event.trigger_type.value if isinstance(event.trigger_type, EventTriggerType) else str(event.trigger_type),
        json.dumps(dict(event.payload), ensure_ascii=False, sort_keys=True, default=str),
        event.status.value if isinstance(event.status, EventStatus) else str(event.status),
        event.agent_id,
        event.workspace_id,
        event.context_hint,
        event.fire_at,
        event.created_at,
        event.updated_at,
    )


def _definition_row_values(definition: EventTypeDefinition) -> tuple[Any, ...]:
    return (
        definition.type_id,
        definition.display_name,
        definition.trigger_type.value
        if isinstance(definition.trigger_type, EventTriggerType)
        else str(definition.trigger_type),
        json.dumps(dict(definition.payload_schema), ensure_ascii=False, sort_keys=True, default=str),
        definition.prompt_template,
        json.dumps(list(definition.allowed_tools), ensure_ascii=False, sort_keys=True, default=str),
        json.dumps(dict(definition.context_policy), ensure_ascii=False, sort_keys=True, default=str),
        json.dumps(dict(definition.auth_policy), ensure_ascii=False, sort_keys=True, default=str),
    )


def _row_to_event(row: sqlite.Row) -> EventInstance:
    return EventInstance(
        id=row["id"],
        type_id=row["type_id"],
        trigger_type=EventTriggerType(row["trigger_type"]),
        payload=json.loads(row["payload_json"] or "{}"),
        status=EventStatus(row["status"]),
        agent_id=row["agent_id"],
        workspace_id=row["workspace_id"],
        context_hint=row["context_hint"] or "",
        fire_at=row["fire_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_definition(row: sqlite.Row) -> EventTypeDefinition:
    return EventTypeDefinition(
        type_id=row["type_id"],
        display_name=row["display_name"],
        trigger_type=EventTriggerType(row["trigger_type"]),
        payload_schema=json.loads(row["payload_schema_json"] or "{}"),
        prompt_template=row["prompt_template"] or "",
        allowed_tools=tuple(json.loads(row["allowed_tools_json"] or "[]")),
        context_policy=json.loads(row["context_policy_json"] or "{}"),
        auth_policy=json.loads(row["auth_policy_json"] or "{}"),
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

__all__ = [
    "EventQueue",
    "EventRegistry",
    "InMemoryEventQueue",
    "InMemoryEventRegistry",
    "SQLiteEventQueue",
    "SQLiteEventRegistry",
]
