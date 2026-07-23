"""Employee console task workflow for the digital employee monitor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import sqlite3
from typing import Any

from application.contracts import UseCaseResult
from application.runtime_provider import configure_runtime_provider
from domain.orchestration import AssignedTaskSpeckitBuilder, TaskComplexityClassifier
from infrastructure.config import get_runtime_home, get_runtime_state_db_path

_LEGACY_VITAL_TERMS = ("饱腹", "心情", "清洁", "联结", "LQ=", "生命状态")


class TaskConsoleWorkflow:
    """Coordinate task CRUD and plan actions through the existing task backend."""

    def list_tasks(self,
                   status: str | None = None,
                   source: str | None = None,
                   project_id: str | None = None,
                   linked_deliverable_id: str | None = None) -> UseCaseResult:
        try:
            task_runtime = _task_runtime()

            return UseCaseResult({"tasks": self._enrich_tasks(
                task_runtime.list_tasks(status_filter=status,
                                        source=source,
                                        project_id=project_id,
                                        linked_deliverable_id=linked_deliverable_id)
            )})
        except Exception as exc:
            return UseCaseResult({"error": str(exc)}, 500)

    def task_detail(self, task_id: str) -> UseCaseResult:
        try:
            task_runtime = _task_runtime()

            task = task_runtime.get_task(task_id)
            if not task:
                return UseCaseResult({"error": "not found"}, 404)
            if isinstance(task.get("task"), dict):
                task["task"] = self._enrich_tasks([task["task"]])[0]
            return UseCaseResult(task)
        except Exception as exc:
            return UseCaseResult({"error": str(exc)}, 500)

    def create_task(self, body: dict[str, Any]) -> UseCaseResult:
        try:
            task_runtime = _task_runtime()

            title = str(body.get("title", "")).strip()
            if not title:
                return UseCaseResult({"error": "title required"}, 400)
            description = str(body.get("description", "") or "")
            priority = str(body.get("priority", "medium") or "medium")
            complexity = TaskComplexityClassifier().classify(title, description, priority)
            result = task_runtime.create_task(
                title=title,
                description=description,
                priority=priority,
                deadline=body.get("deadline"),
                tags=body.get("tags"),
                status=body.get("status") or "planned",
                source=body.get("source") or "personal",
                linked_deliverable_id=body.get("linked_deliverable_id") or None,
            )
            if result.get("ok") and complexity.complex and isinstance(result.get("task"), dict):
                task_id = str(result["task"]["id"])
                speckit = AssignedTaskSpeckitBuilder().build(
                    task_id=task_id,
                    title=title,
                    description=description,
                    priority=priority,
                    employee_id=str(body.get("employee_id", "") or ""),
                    decision=complexity,
                )
                attached = task_runtime.attach_speckit_plan(task_id, speckit)
                if attached.get("ok"):
                    result["speckit"] = attached.get("speckit")
                    result["orchestration"] = {
                        "use_speckit": True,
                        "complexity": {"complex": complexity.complex, "reason": complexity.reason},
                    }
                else:
                    result["speckit_error"] = attached.get("reason") or "failed to attach speckit plan"
            elif result.get("ok"):
                result["orchestration"] = {
                    "use_speckit": False,
                    "complexity": {"complex": complexity.complex, "reason": complexity.reason},
                }
            if result.get("ok") and isinstance(result.get("task"), dict):
                result["task"] = self._enrich_tasks([result["task"]])[0]
            return UseCaseResult(result, 200 if result.get("ok") else 409)
        except Exception as exc:
            return UseCaseResult({"error": str(exc)}, 500)

    def update_task(self, task_id: str, body: dict[str, Any]) -> UseCaseResult:
        try:
            task_runtime = _task_runtime()

            result = task_runtime.update_task(task_id, **body)
            if result.get("ok"):
                task = task_runtime.get_task(task_id)
                if task and isinstance(task.get("task"), dict):
                    result["task"] = self._enrich_tasks([task["task"]])[0]
            return UseCaseResult(result)
        except Exception as exc:
            return UseCaseResult({"error": str(exc)}, 500)

    def task_plans(self, task_id: str) -> UseCaseResult:
        try:
            task_runtime = _task_runtime()

            return UseCaseResult({"plans": task_runtime.list_plans(task_id)})
        except Exception as exc:
            return UseCaseResult({"error": str(exc)}, 500)

    def create_plan(self, task_id: str, body: dict[str, Any]) -> UseCaseResult:
        try:
            task_runtime = _task_runtime()

            content = str(body.get("content", "")).strip()
            if not content:
                return UseCaseResult({"error": "content required"}, 400)
            return UseCaseResult(task_runtime.create_plan(task_id, content, deadline=body.get("deadline")))
        except Exception as exc:
            return UseCaseResult({"error": str(exc)}, 500)

    def update_plan(self, plan_id: int, body: dict[str, Any]) -> UseCaseResult:
        try:
            task_runtime = _task_runtime()

            action = body.get("action", "")
            if action == "complete":
                result = task_runtime.complete_plan(plan_id)
            elif action == "skip":
                result = task_runtime.skip_plan(plan_id)
            elif action == "update":
                result = task_runtime.update_plan(plan_id, content=body.get("content"), deadline=body.get("deadline"))
            else:
                return UseCaseResult({"error": "action must be complete/skip/update"}, 400)
            return UseCaseResult(result)
        except Exception as exc:
            return UseCaseResult({"error": str(exc)}, 500)

    def task_notes(self, task_id: str) -> UseCaseResult:
        try:
            task_runtime = _task_runtime()

            return UseCaseResult({"notes": task_runtime.read_notes(task_id)})
        except Exception as exc:
            return UseCaseResult({"error": str(exc)}, 500)

    def _enrich_tasks(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not tasks:
            return []
        task_ids = [str(task.get("id")) for task in tasks if task.get("id")]
        events_by_task = _task_events(task_ids)
        sessions_by_task = _task_sessions(task_ids)
        _append_event_sessions(sessions_by_task, events_by_task)
        message_logs = _session_message_logs(sessions_by_task)
        return [
            _enrich_task(
                task,
                events_by_task.get(str(task.get("id")), []),
                sessions_by_task.get(str(task.get("id")), []),
                message_logs.get(str(task.get("id")), []),
            )
            for task in tasks
        ]


def _task_runtime():
    configure_runtime_provider()
    from domain import todos as task_runtime

    return task_runtime


def _task_events(task_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    wanted = set(task_ids)
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(get_runtime_state_db_path()))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT event_id, payload, fire_at, created_at, consumed_at, kind "
            "FROM events WHERE kind='task_reminder' "
            "ORDER BY event_id DESC LIMIT 300"
        ).fetchall()
    except Exception:
        return {}
    finally:
        if conn is not None:
            conn.close()

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        event = dict(row)
        try:
            payload = json.loads(event.get("payload") or "{}")
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            continue
        task_id = str(payload.get("task_id") or "")
        if not task_id or task_id not in wanted:
            continue
        event["payload"] = payload
        grouped.setdefault(task_id, []).append(event)
    return grouped


def _task_sessions(task_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not task_ids:
        return {}
    db_path = get_runtime_home() / "tasks" / "tasks.db"
    if not db_path.exists():
        return {}
    placeholders = ",".join("?" * len(task_ids))
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT task_id, session_id, digest, started_at, ended_at "
            f"FROM task_sessions WHERE task_id IN ({placeholders}) "
            "ORDER BY COALESCE(ended_at, started_at) DESC",
            task_ids,
        ).fetchall()
    except Exception:
        return {}
    finally:
        if conn is not None:
            conn.close()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        item = dict(row)
        grouped.setdefault(str(item.get("task_id")), []).append(item)
    return grouped


def _append_event_sessions(
    sessions_by_task: dict[str, list[dict[str, Any]]],
    events_by_task: dict[str, list[dict[str, Any]]],
) -> None:
    consumed_events: list[tuple[str, int, float]] = []
    for task_id, events in events_by_task.items():
        for event in events:
            consumed_at = event.get("consumed_at")
            event_ts = _iso_to_epoch_seconds(str(consumed_at)) if consumed_at else None
            if event_ts is None:
                continue
            consumed_events.append((task_id, int(event.get("event_id") or 0), event_ts))
    if not consumed_events:
        return

    started_min = min(item[2] for item in consumed_events) - 60
    started_max = max(item[2] for item in consumed_events) + 300
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(get_runtime_state_db_path()))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT s.id, s.started_at, s.ended_at, s.end_reason, s.message_count, s.tool_call_count, "
            "latest.latest_message_at "
            "FROM sessions s "
            "LEFT JOIN ("
            "  SELECT session_id, MAX(timestamp) AS latest_message_at "
            "  FROM messages WHERE role != 'session_meta' GROUP BY session_id"
            ") latest ON latest.session_id = s.id "
            "WHERE s.source='l4_wake' AND s.id LIKE 'tx_task_reminder_%' "
            "AND s.started_at BETWEEN ? AND ? ORDER BY s.started_at DESC",
            (started_min, started_max),
        ).fetchall()
    except Exception:
        return
    finally:
        if conn is not None:
            conn.close()

    existing_session_ids = {
        str(session.get("session_id"))
        for sessions in sessions_by_task.values()
        for session in sessions
        if session.get("session_id")
    }
    now_ts = datetime.now(timezone(timedelta(hours=8))).timestamp()
    session_summaries = _session_summaries([str(row["id"]) for row in rows])
    for row in rows:
        session = dict(row)
        session_id = str(session.get("id") or "")
        if not session_id or session_id in existing_session_ids:
            continue
        started_at = float(session.get("started_at") or 0)
        task_id, event_id, event_ts = min(consumed_events, key=lambda item: abs(item[2] - started_at))
        if abs(event_ts - started_at) > 180:
            continue
        ended_at = session.get("ended_at")
        summary = session_summaries.get(session_id)
        latest_message_at = session.get("latest_message_at")
        if ended_at is None and summary:
            ended_at = latest_message_at or session.get("started_at")
        if ended_at is None and latest_message_at and now_ts - float(latest_message_at) > 60:
            ended_at = latest_message_at
            summary = summary or "任务提醒会话已结束，未见任务执行证据"
        if ended_at is None and now_ts - started_at > 30 * 60:
            continue
        digest = summary or ("任务提醒会话运行中" if ended_at is None else "任务提醒会话已触发")
        sessions_by_task.setdefault(task_id, []).append({
            "task_id": task_id,
            "session_id": session_id,
            "digest": digest if summary else f"{digest} (event #{event_id})",
            "started_at": _epoch_seconds_to_iso(started_at),
            "ended_at": _epoch_seconds_to_iso(float(ended_at)) if ended_at is not None else None,
        })
        existing_session_ids.add(session_id)


def _session_message_logs(sessions_by_task: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    session_to_task: dict[str, str] = {}
    for task_id, sessions in sessions_by_task.items():
        for session in sessions:
            session_id = str(session.get("session_id") or "")
            if session_id:
                session_to_task[session_id] = task_id
    if not session_to_task:
        return {}
    placeholders = ",".join("?" * len(session_to_task))
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(get_runtime_state_db_path()))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT session_id, role, content, timestamp, tool_name, tool_calls "
            f"FROM messages WHERE session_id IN ({placeholders}) "
            "ORDER BY timestamp DESC LIMIT 80",
            list(session_to_task),
        ).fetchall()
    except Exception:
        return {}
    finally:
        if conn is not None:
            conn.close()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        item = dict(row)
        task_id = session_to_task.get(str(item.get("session_id")))
        if not task_id:
            continue
        grouped.setdefault(task_id, []).append(item)
    return grouped


def _session_summaries(session_ids: list[str]) -> dict[str, str]:
    if not session_ids:
        return {}
    db_path = get_runtime_home() / "memories" / "memory_layers.db"
    if not db_path.exists():
        return {}
    placeholders = ",".join("?" * len(session_ids))
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT period, digest FROM memory_layers WHERE layer='session' "
            f"AND period IN ({placeholders})",
            session_ids,
        ).fetchall()
    except Exception:
        return {}
    finally:
        if conn is not None:
            conn.close()
    return {
        str(row["period"]): _drop_legacy_runtime_lines(row["digest"])
        for row in rows
        if row["digest"]
    }


def _enrich_task(
    task: dict[str, Any],
    events: list[dict[str, Any]],
    sessions: list[dict[str, Any]] | None = None,
    messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result = dict(task)
    state = _task_runtime_state(task, events, sessions or [], messages or [])
    result.update(state)
    return result


def _task_runtime_state(
    task: dict[str, Any],
    events: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    status = str(task.get("status") or "")
    # now_iso 用于和 events.fire_at（UTC ISO 存储）做字典序比较，必须用 UTC。
    from domain.lifecycle import clock as _clock
    now_iso = _clock.now_iso()
    pending_events = [event for event in events if not event.get("consumed_at")]
    consumed_events = [event for event in events if event.get("consumed_at")]
    due_events = [event for event in pending_events if not event.get("fire_at") or str(event.get("fire_at")) <= now_iso]
    next_fire_at = next((event.get("fire_at") for event in pending_events if event.get("fire_at")), None)
    execution_logs = _execution_logs(events, sessions, messages)
    task_evidence_count = _task_evidence_count(task, messages)
    running_sessions = [session for session in sessions if not session.get("ended_at")]

    if sessions and task_evidence_count:
        state = "executed"
        label = "已有任务执行证据"
    elif due_events:
        state = "waiting_execution"
        label = "等待执行"
    elif running_sessions:
        state = "running"
        label = "执行会话运行中"
    elif status == "in_progress" and consumed_events:
        state = "triggered"
        label = "已触发，等待执行日志"
    elif sessions:
        state = "triggered"
        label = "有唤醒会话，未见任务执行证据"
    elif status == "in_progress":
        state = "in_progress"
        label = "执行中，暂无日志"
    elif due_events:
        state = "waiting_execution"
        label = "等待执行"
    elif pending_events:
        state = "scheduled"
        label = "已排期"
    elif status == "planned":
        state = "planned"
        label = "已规划，未排队"
    elif status == "idea":
        state = "draft"
        label = "仅登记"
    elif status == "done":
        state = "done"
        label = "已完成"
    elif status == "cancelled":
        state = "cancelled"
        label = "已取消"
    else:
        state = status or "unknown"
        label = state

    return {
        "runtime_state": state,
        "runtime_state_label": label,
        "pending_event_count": len(pending_events),
        "triggered_event_count": len(consumed_events),
        "due_event_count": len(due_events),
        "session_count": len(sessions),
        "running_session_count": len(running_sessions),
        "task_evidence_count": task_evidence_count,
        "next_fire_at": next_fire_at,
        "execution_logs": execution_logs[:8],
    }


def _execution_logs(
    events: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    for event in events:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        consumed_at = event.get("consumed_at")
        logs.append({
            "kind": "task_event",
            "status": "triggered" if consumed_at else "queued",
            "label": "任务提醒已触发" if consumed_at else "任务提醒排队中",
            "at": consumed_at or event.get("fire_at") or event.get("created_at"),
            "event_id": event.get("event_id"),
            "summary": payload.get("content") or payload.get("task_title") or "task_reminder",
        })
    for session in sessions:
        logs.append({
            "kind": "session",
            "status": "completed" if session.get("ended_at") else "running",
            "label": "执行会话",
            "at": session.get("ended_at") or session.get("started_at"),
            "session_id": session.get("session_id"),
            "summary": _drop_legacy_runtime_lines(session.get("digest")) or session.get("session_id") or "session",
        })
    for message in messages[:8]:
        role = str(message.get("role") or "message")
        tool_name = message.get("tool_name")
        logs.append({
            "kind": "message",
            "status": role,
            "label": f"消息 · {tool_name}" if tool_name else f"消息 · {role}",
            "at": message.get("timestamp"),
            "session_id": message.get("session_id"),
            "summary": _compact_text(_drop_legacy_runtime_lines(message.get("content"))),
        })
    return sorted(logs, key=lambda item: str(item.get("at") or ""), reverse=True)


def _iso_to_epoch_seconds(value: str) -> float | None:
    try:
        return datetime.fromisoformat(value).timestamp()
    except Exception:
        return None


def _epoch_seconds_to_iso(value: float) -> str:
    # 显示层：epoch 转 ISO 时维持原 +08:00 行为（前端 new Date 会换成本地时区）。
    from domain.lifecycle import clock as _clock
    return datetime.fromtimestamp(value, tz=_clock.BEIJING).isoformat(timespec="seconds")


def _compact_text(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[:limit] + "..."


def _drop_legacy_runtime_lines(value: Any) -> str:
    lines = []
    for line in str(value or "").splitlines():
        if any(term in line for term in _LEGACY_VITAL_TERMS):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _task_evidence_count(task: dict[str, Any], messages: list[dict[str, Any]]) -> int:
    evidence = 0
    for message in messages:
        role = str(message.get("role") or "")
        if role == "user":
            continue
        tool_names = set(_message_tool_names(message))
        if "todo_note" in tool_names:
            evidence += 1
        if "todo_plan" in tool_names:
            evidence += 1
    return evidence


def _message_tool_names(message: dict[str, Any]) -> list[str]:
    names: list[str] = []
    tool_name = str(message.get("tool_name") or "")
    if tool_name:
        names.append(tool_name)
    raw_tool_calls = message.get("tool_calls")
    if not raw_tool_calls:
        return names
    try:
        tool_calls = json.loads(str(raw_tool_calls))
    except Exception:
        return names
    if not isinstance(tool_calls, list):
        return names
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        function = tool_call.get("function")
        if isinstance(function, dict) and function.get("name"):
            names.append(str(function["name"]))
    return names


__all__ = ["TaskConsoleWorkflow"]
