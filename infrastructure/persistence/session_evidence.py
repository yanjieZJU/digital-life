"""Hermes-backed implementation of the generic session evidence port."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from infrastructure.persistence import sqlite

from domain.runtime.session_evidence import (
    DEFAULT_EXECUTION_TOOL_NAMES,
    SessionEvidenceReader,
    collect_tool_call_ids,
    session_has_tool_attempt,
    tool_result_sent,
    tool_result_success,
)


class HermesSessionEvidenceReader(SessionEvidenceReader):
    def __init__(self, *, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path else None

    def has_sent_human_reply(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        rows = self._session_message_rows(str(session_id))
        express_call_ids = collect_tool_call_ids(rows, {"express_to_human"})
        if not express_call_ids:
            return False
        for row in rows:
            if _row_get(row, "role") != "tool":
                continue
            if str(_row_get(row, "tool_call_id") or "") not in express_call_ids:
                continue
            if tool_result_sent(_row_get(row, "content")):
                return True
        return False

    def has_successful_execution_tool(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        rows = self._session_message_rows(str(session_id))
        if not rows:
            return False
        execution_call_ids = collect_tool_call_ids(rows, set(DEFAULT_EXECUTION_TOOL_NAMES))
        if not execution_call_ids:
            return False
        for row in rows:
            if _row_get(row, "role") != "tool":
                continue
            if str(_row_get(row, "tool_call_id") or "") not in execution_call_ids:
                continue
            if tool_result_success(_row_get(row, "content")):
                return True
        return False

    def has_execution_attempt(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        return session_has_tool_attempt(
            self._session_message_rows(str(session_id)),
            set(DEFAULT_EXECUTION_TOOL_NAMES),
        )

    def _runtime_db_path(self) -> Path | None:
        if self._db_path is not None:
            return self._db_path
        try:
            from infrastructure.config import get_runtime_state_db_path
        except Exception:
            return None
        return get_runtime_state_db_path()

    def _session_message_rows(self, session_id: str) -> list[Any]:
        db_path = self._runtime_db_path()
        if not db_path or not db_path.exists():
            return []
        conn = None
        try:
            conn = sqlite.connect(str(db_path))
            conn.row_factory = sqlite.Row
            return conn.execute(
                "SELECT role, content, tool_call_id, tool_calls FROM messages "
                "WHERE session_id=? ORDER BY timestamp, id",
                (session_id,),
            ).fetchall()
        except Exception:
            return []
        finally:
            if conn is not None:
                conn.close()


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return getattr(row, key, default)


__all__ = ["HermesSessionEvidenceReader"]
