"""任务调度 — 事件发射、状态变更副作用、cron tick hook、停滞检测。

合并了原 scheduling.py（事件发射 + cron hook）和 momentum.py（停滞检测）。
共用 _build_task_hints() 构建提示文本，避免重复代码。
"""

from __future__ import annotations

import logging
import time

from ._infra import (
    get_db, tasks_dir, now_iso, parse_iso, now_dt,
    emit_event, cancel_alarms_by_filter, set_alarm, pop_due_events, consume_event,
    task_title_by_id, task_has_speckit,
)

logger = logging.getLogger("digital_life.domain.todos")

# ──────────────────────────────── 共用辅助 ────────────────────────────────


def _build_task_hints(task_id: str) -> dict:
    """构建任务提示信息（speckit / notes / 进度），被 schedule_task_wakeup 和 check_task_momentum 共用。"""
    _has_speckit = task_has_speckit(task_id)
    _has_notes = False
    _notes_short = ""
    _steps_summary = ""

    ws = tasks_dir() / task_id
    notes_file = ws / "NOTES.md"
    if notes_file.exists():
        _has_notes = True
        try:
            full_notes = notes_file.read_text(encoding="utf-8")
            _notes_short = full_notes[-100:].strip()
            if len(full_notes) > 100:
                _notes_short = "...(摘要)" + _notes_short
        except Exception:
            pass

    try:
        db = get_db()
        try:
            plan_rows = db.execute(
                "SELECT COUNT(*) as total, SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as done "
                "FROM todo_plans WHERE task_id=?",
                (task_id,),
            ).fetchone()
            if plan_rows and plan_rows["total"] > 0:
                _steps_summary = f"{plan_rows['done']}/{plan_rows['total']}步完成"
        finally:
            db.close()
    except Exception:
        pass

    return {
        "has_speckit": _has_speckit,
        "has_notes": _has_notes,
        "notes_short": _notes_short,
        "steps_summary": _steps_summary,
        "speckit_hint": "请先读取 spec.md 理解需求" if _has_speckit else "",
        "notes_hint": f"上次笔记：{_notes_short}" if _has_notes else "",
        "remaining_hint": f"还剩{_steps_summary}" if _steps_summary else "",
    }


# ──────────────────────────────── 事件发射 ────────────────────────────────


def schedule_plan_event(task_id: str, plan_id: int, content: str, deadline: str) -> None:
    """为计划步骤调度到期提醒闹钟。"""
    try:
        cancel_alarms_by_filter(kind="task_reminder", payload_filter={"task_id": task_id, "plan_id": plan_id})
        set_alarm(event_kind="task_reminder", fire_at=deadline,
                  payload={"task_id": task_id, "plan_id": plan_id, "content": content})
    except Exception as e:
        logger.warning("Failed to schedule plan event: %s", e)


def schedule_task_wakeup(
    task_id: str,
    *,
    title: str | None = None,
    status: str = "planned",
    force: bool = False,
) -> None:
    """已停用（2026-06-17）：task_reminder 事件移除。

    原设计：planned/in_progress 的待办定期自动提醒推进。但实际效果是
    每次 session 结束（尤其精力低做不了事时）→ on_session_end → force emit
    → 下一 cron tick 又 wake → 又做不了 → 又 emit → 死循环风暴。
    设计意图（用户确认）：待办长期未推进时的提醒应该后续重新实现为 BLOCKED
    状态下的周期提醒机制，不是绿每次 session 结束就立刻 emit。

    保留函数签名和所有调用方不动（避免大范围改动），但 body no-op。
    """
    return


# ──────────────────────────────── 状态变更副作用 ────────────────────────────────


def on_status_change(task_id: str, new_status: str) -> None:
    """已停用（2026-06-17）：task_reminder 事件移除，状态变更不再产生自动提醒。
    done/cancelled 的闹钟取消仍保留。
    """
    if new_status in ("done", "cancelled"):
        try:
            cancel_alarms_by_filter(kind="task_reminder", payload_filter={"task_id": task_id})
        except Exception:
            pass


# ──────────────────────────────── Cron Tick Hook ────────────────────────────────


def on_tick(*, consume: bool = True) -> list | None:
    """cron tick 时调用。返回 due 的 task_reminder 事件 payload 列表。"""
    try:
        due = pop_due_events(limit=20)
        reminders = [e for e in due if e["kind"] == "task_reminder"]
        if not reminders:
            return None

        payloads = []
        for ev in reminders:
            if consume:
                consume_event(ev["event_id"])
            payloads.append({
                "event_id": ev.get("event_id"),
                "kind": "task_reminder",
                "payload": ev.get("payload", {}),
                "created_at": ev.get("created_at"),
            })

        return payloads
    except Exception as e:
        logger.debug("on_tick failed: %s", e)
        return None


# ──────────────────────────────── 停滞检测 ────────────────────────────────

_momentum_last_fired: dict[str, float] = {}


def check_task_momentum() -> dict | None:
    """已停用（2026-06-17）：每 cron tick（60s）检测 in_progress 任务停滞 →
    emit task_momentum。但反弹效果是每分钟一条重复催促 + _momentum_last_fired
    在进程内存里重启就清 → 风暴。后续重设计后再启用。
    """
    return None
