"""Employee console session workflow for the digital employee monitor."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from application.contracts import UseCaseResult
from infrastructure.config import get_runtime_memories_dir, get_runtime_state_db_path


class SessionConsoleWorkflow:
    """Read session lists/details and attach session memory summaries."""

    def __init__(self) -> None:
        pass

    @staticmethod
    def _state_db_path():
        path = get_runtime_state_db_path()
        return path if path.exists() else None

    def _db(self) -> sqlite3.Connection | None:
        try:
            path = self._state_db_path()
            if path is None:
                return None
            conn = sqlite3.connect(str(path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only = ON")
            return conn
        except Exception:
            return None

    @staticmethod
    def _memory_layers_db() -> sqlite3.Connection | None:
        try:
            path = get_runtime_memories_dir() / "memory_layers.db"
            if not path.exists():
                return None
            conn = sqlite3.connect(str(path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only = ON")
            return conn
        except Exception:
            return None

    @staticmethod
    def _has_sessions_table(db: sqlite3.Connection) -> bool:
        try:
            db.execute("SELECT 1 FROM sessions LIMIT 0")
            return True
        except sqlite3.OperationalError:
            return False

    def list_sessions(self, limit: int = 20) -> UseCaseResult:
        db = self._db()
        if not db:
            return UseCaseResult({"error": "state.db unavailable"}, 500)
        try:
            if not self._has_sessions_table(db):
                return UseCaseResult({"sessions": []})
            capped_limit = max(1, min(int(limit), 50))
            rows = db.execute(
                "SELECT s.id, s.source, s.started_at, s.ended_at, s.message_count, "
                "s.tool_call_count, s.input_tokens, s.output_tokens, s.end_reason, "
                "COALESCE(latest.latest_message_at, s.ended_at, s.started_at) AS latest_message_at "
                "FROM sessions s "
                "LEFT JOIN ("
                "  SELECT session_id, MAX(timestamp) AS latest_message_at "
                "  FROM messages WHERE role != 'session_meta' GROUP BY session_id"
                ") latest ON latest.session_id = s.id "
                "ORDER BY latest_message_at DESC LIMIT ?",
                (capped_limit,),
            ).fetchall()
            sessions = [dict(row) for row in rows]
            self._attach_session_summaries(sessions)
            self._attach_session_health(sessions)
            return UseCaseResult({"sessions": sessions})
        except Exception as exc:
            return UseCaseResult({"error": str(exc)}, 500)
        finally:
            db.close()

    def session_detail(self, session_id: str) -> UseCaseResult:
        db = self._db()
        if not db:
            return UseCaseResult({"error": "state.db unavailable"}, 500)
        try:
            if not self._has_sessions_table(db):
                return UseCaseResult({"error": "no sessions yet"}, 404)
            rows = db.execute(
                "SELECT role, content, reasoning, timestamp, tool_calls, tool_call_id, tool_name FROM messages "
                "WHERE session_id=? ORDER BY timestamp",
                (session_id,),
            ).fetchall()
            messages: list[dict[str, Any]] = []
            for row in rows:
                role = row["role"]
                raw_content = row["content"] or ""
                if role == "tool" and not raw_content.strip():
                    continue
                tool_calls = self._parse_tool_calls(row["tool_calls"])
                # reasoning 列对齐：上游 SELECT 已取，老 SQL 兼容用 try/key fallback
                reasoning = None
                try:
                    reasoning = row["reasoning"]
                except (IndexError, KeyError):
                    pass
                messages.append({
                    "role": role,
                    "content": raw_content,
                    "reasoning": reasoning or "",
                    "ts": row["timestamp"],
                    "tool_calls": tool_calls,
                    "tool_call_id": row["tool_call_id"],
                    "tool_name": row["tool_name"],
                })
            result: dict[str, Any] = {"session_id": session_id, "messages": messages}
            self._attach_session_summary(result, session_id)
            self._attach_consumed_events(db, result, session_id)
            return UseCaseResult(result)
        except Exception as exc:
            return UseCaseResult({"error": str(exc)}, 500)
        finally:
            db.close()

    @staticmethod
    def _parse_tool_calls(raw: str | None) -> list[dict[str, Any]]:
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except Exception:
            return []
        if not isinstance(parsed, list):
            return []
        return [item for item in parsed if isinstance(item, dict)]

    def _attach_session_summaries(self, sessions: list[dict[str, Any]]) -> None:
        db = self._memory_layers_db()
        if not db:
            return
        try:
            for session in sessions:
                row = db.execute(
                    "SELECT digest, tool_summary FROM memory_layers WHERE layer='session' AND period=?",
                    (session["id"],),
                ).fetchone()
                if row:
                    session["digest"] = (row["digest"] or "")[:200]
                    session["tool_summary"] = row["tool_summary"] or ""
        except Exception:
            return
        finally:
            db.close()

    @staticmethod
    def _attach_session_health(sessions: list[dict[str, Any]]) -> None:
        for session in sessions:
            message_count = int(session.get("message_count") or 0)
            tool_call_count = int(session.get("tool_call_count") or 0)
            source = str(session.get("source") or "")
            end_reason = str(session.get("end_reason") or "")
            if source == "l4_wake" and message_count <= 1 and tool_call_count == 0:
                session["health"] = "no_response"
                session["health_label"] = "未产生回复"
                if end_reason.startswith("error:"):
                    session["health_detail"] = f"执行异常：{end_reason[6:] or 'unknown'}"
                else:
                    session["health_detail"] = "该唤醒只写入了输入提示，没有助手回复或工具调用"
            elif end_reason.startswith("error:"):
                session["health"] = "error"
                session["health_label"] = "执行异常"
                session["health_detail"] = end_reason[6:] or "unknown"
            else:
                session["health"] = "ok"
                session["health_label"] = "正常"
                session["health_detail"] = ""

    @staticmethod
    def _attach_consumed_events(db: sqlite3.Connection, result: dict[str, Any], session_id: str) -> None:
        """Attach events consumed by this session, using the consumed_by_session_id column."""
        try:
            rows = db.execute(
                "SELECT event_id, kind, payload, created_at, consumed_at FROM events "
                "WHERE consumed_by_session_id = ? "
                "ORDER BY consumed_at ASC LIMIT 100",
                (session_id,),
            ).fetchall()
            if not rows:
                return
            from domain.lifecycle.event_registry import get_event_type
            events = []
            for row in rows:
                kind = row["kind"] or ""
                td = get_event_type(kind)
                try:
                    payload = json.loads(row["payload"]) if row["payload"] else {}
                except Exception:
                    payload = {}
                events.append({
                    "event_id": row["event_id"],
                    "kind": kind,
                    "display_name": td.display_name if td else kind,
                    "description": td.description if td else "",
                    "created_at": row["created_at"],
                    "consumed_at": row["consumed_at"],
                    "payload": payload,
                })
            result["consumed_events"] = events
        except Exception:
            return

    def _attach_session_summary(self, result: dict[str, Any], session_id: str) -> None:
        db = self._memory_layers_db()
        if not db:
            return
        try:
            row = db.execute(
                "SELECT digest, tool_summary FROM memory_layers WHERE layer='session' AND period=?",
                (session_id,),
            ).fetchone()
            if row:
                result["digest"] = row["digest"] or ""
                result["tool_summary"] = row["tool_summary"] or ""
        except Exception:
            return
        finally:
            db.close()


__all__ = ["SessionConsoleWorkflow"]
