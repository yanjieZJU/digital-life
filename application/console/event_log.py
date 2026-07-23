"""Read-model workflow for employee console flow event logs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any

from application.contracts import UseCaseResult
from domain.flow_event_log import (
    ActionDispatchedEvent,
    ActionProposedEvent,
    FlowEventLog,
    MessageReceivedEvent,
    ObservationReceivedEvent,
    RunResultEvaluatedEvent,
    StateChangedEvent,
)
from infrastructure.config import get_runtime_state_db_path
from infrastructure.persistence.repositories import SQLiteFlowEventLogRepository


class EventLogConsoleWorkflow:
    """Build FlowEventLog views for the employee console."""

    def __init__(self) -> None:
        self.repository = SQLiteFlowEventLogRepository(get_runtime_state_db_path())

    def _db(self) -> sqlite3.Connection | None:
        try:
            conn = sqlite3.connect(str(get_runtime_state_db_path()))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only = ON")
            return conn
        except Exception:
            return None

    def run_event_log(self, run_id: str, *, employee_id: str | None = None) -> UseCaseResult:
        stored = self.repository.get(run_id)
        if stored and stored.events:
            return UseCaseResult(_event_log_payload(stored.to_dict()))
        return self._legacy_session_event_log(run_id, employee_id=employee_id)

    def _legacy_session_event_log(self, run_id: str, *, employee_id: str | None = None) -> UseCaseResult:
        db = self._db()
        if not db:
            return UseCaseResult({"error": "state.db unavailable"}, 500)
        try:
            rows = db.execute(
                "SELECT id, role, content, reasoning, timestamp, tool_calls, tool_call_id, tool_name FROM messages "
                "WHERE session_id=? ORDER BY timestamp",
                (run_id,),
            ).fetchall()
            if not rows:
                return UseCaseResult({"error": "run not found"}, 404)
            log = FlowEventLog(
                run_id=run_id,
                employee_id=employee_id,
                status="legacy_reconstructed",
                metadata={"source": "legacy_session_messages"},
            )
            for row in rows:
                role = row["role"]
                timestamp = _timestamp_iso(row["timestamp"])
                if role == "session_meta":
                    log = log.append(
                        StateChangedEvent(
                            run_id=run_id,
                            source="application.console.legacy_session",
                            timestamp=timestamp,
                            employee_id=employee_id,
                            payload={"message_row_id": row["id"], "role": role},
                            summary="Legacy session metadata observed.",
                        )
                    )
                    continue
                if role == "user":
                    log = log.append(
                        MessageReceivedEvent(
                            run_id=run_id,
                            source="application.console.legacy_session",
                            timestamp=timestamp,
                            employee_id=employee_id,
                            payload=_message_payload(row),
                            summary="Legacy user message reconstructed from session storage.",
                        )
                    )
                    continue
                if role == "tool":
                    log = log.append(
                        ObservationReceivedEvent(
                            run_id=run_id,
                            source="application.console.legacy_session",
                            timestamp=timestamp,
                            employee_id=employee_id,
                            payload=_message_payload(row),
                            summary=f"Legacy tool observation reconstructed: {row['tool_name'] or 'tool'}.",
                        )
                    )
                    continue
                log = log.append(
                    ObservationReceivedEvent(
                        run_id=run_id,
                        source="application.console.legacy_session",
                        timestamp=timestamp,
                        employee_id=employee_id,
                        payload=_message_payload(row),
                        summary=f"Legacy {role} message reconstructed from session storage.",
                    )
                )
                for call in self._parse_tool_calls(row["tool_calls"]):
                    action = ActionProposedEvent(
                        run_id=run_id,
                        source="application.console.legacy_session",
                        timestamp=timestamp,
                        employee_id=employee_id,
                        payload=call,
                        summary=f"Legacy tool call proposed: {_tool_call_name(call)}.",
                    )
                    log = log.append(action)
                    log = log.append(
                        ActionDispatchedEvent(
                            run_id=run_id,
                            source="application.console.legacy_session",
                            timestamp=timestamp,
                            employee_id=employee_id,
                            causation_event_id=action.id,
                            payload=call,
                            summary=f"Legacy tool call dispatched: {_tool_call_name(call)}.",
                        )
                    )
            log = log.append(
                RunResultEvaluatedEvent(
                    run_id=run_id,
                    source="application.console.legacy_session",
                    employee_id=employee_id,
                    payload={"source": "legacy_session_messages", "message_rows": len(rows)},
                    summary="Legacy run result reconstructed from available session storage.",
                )
            )
            return UseCaseResult(_event_log_payload(log.to_dict()))
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
        return [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []


def _message_payload(row: sqlite3.Row) -> dict[str, Any]:
    # 列对齐：上游 SELECT 必须含 reasoning 列（messages 表已建，retry 兼容老查询的弱处理）
    reasoning = None
    try:
        reasoning = row["reasoning"]
    except (IndexError, KeyError):
        pass
    return {
        "message_row_id": row["id"],
        "role": row["role"],
        "content": row["content"] or "",
        "reasoning": reasoning or "",
        "tool_call_id": row["tool_call_id"],
        "tool_name": row["tool_name"],
    }


def _timestamp_iso(value: object) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
    text = str(value or "").strip()
    if text.replace(".", "", 1).isdigit():
        return datetime.fromtimestamp(float(text), timezone.utc).isoformat()
    try:
        return datetime.fromisoformat(text).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def _tool_call_name(call: dict[str, Any]) -> str:
    function = call.get("function") if isinstance(call.get("function"), dict) else {}
    return str(function.get("name") or call.get("name") or call.get("tool_name") or call.get("type") or "tool")


def _event_log_payload(payload: dict[str, Any]) -> dict[str, Any]:
    events = payload.get("events")
    if not isinstance(events, list):
        return payload
    result = dict(payload)
    result["events"] = [_enrich_event(event) for event in events if isinstance(event, dict)]
    return result


def _enrich_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    kind = str(event.get("kind") or _event_kind(event, payload))
    result = {
        **event,
        "kind": kind,
        "kind_label": _event_kind_label(kind),
    }
    tool_name = _payload_value(payload, "tool_name") or _payload_value(payload, "runtime_capability")
    status = event.get("status") or _payload_value(payload, "status") or _payload_value(payload, "state")
    if tool_name:
        result["tool_name"] = str(tool_name)
    if status:
        result["status"] = str(status)
    return result


def _event_kind(event: dict[str, Any], payload: dict[str, Any]) -> str:
    event_type = str(event.get("type") or "")
    payload_type = str(payload.get("type") or "")
    layer = str(event.get("layer") or "")
    severity = str(event.get("severity") or "")
    type_key = payload_type or event_type

    if severity == "error" or event_type in {"ToolErrorEvent", "ExecutionFailedEvent"}:
        return "error"
    if event_type in {"ActionProposedEvent", "ActionDispatchedEvent"} or payload_type == "ActionEvent":
        return "tool_call"
    if event_type == "ObservationReceivedEvent" and (
        payload_type == "ObservationEvent" or _payload_value(payload, "tool_name") or _payload_value(payload, "tool_call_id")
    ):
        return "tool_result"
    if event_type in {"StateChangedEvent"} or payload_type in {"StateUpdateEvent", "RejectionEvent"}:
        return "state"
    if event_type in {"AgentStepStartedEvent", "AgentStepCompletedEvent"}:
        return "agent_step"
    if event_type in {"ExecutionStartedEvent", "ExecutionCompletedEvent"}:
        return "task"
    if "Message" in type_key:
        return "message"
    if "Memory" in type_key or event_type in {"PersonaLoadedEvent", "SkillContextLoadedEvent", "ContextBudgetAppliedEvent"}:
        return "memory"
    if event_type in {"ExecutionRequestCreatedEvent", "PlanCreatedEvent"}:
        return "task"
    if layer == "orchestration":
        return "orchestration"
    if layer == "feedback" or event_type in {"RunResultEvaluatedEvent", "HumanReplySentEvent"}:
        return "feedback"
    if event_type.startswith("Ingress"):
        return "system"
    return "system"


def _event_kind_label(kind: str) -> str:
    return {
        "agent_step": "Agent Step",
        "error": "异常",
        "feedback": "反馈",
        "memory": "记忆",
        "message": "消息",
        "orchestration": "编排",
        "state": "状态",
        "system": "系统",
        "task": "任务",
        "tool_call": "工具调用",
        "tool_result": "工具结果",
    }.get(kind, kind or "未知")


def _payload_value(payload: dict[str, Any], key: str) -> Any:
    if key in payload:
        return payload[key]
    nested = payload.get("execution_request")
    if isinstance(nested, dict) and key in nested:
        return nested[key]
    return None


__all__ = ["EventLogConsoleWorkflow"]
