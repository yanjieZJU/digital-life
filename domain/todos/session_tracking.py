"""Session-to-task association and evidence tracking."""

from __future__ import annotations

from ._infra import get_db, now_iso, parse_iso, pop_due_events, session_evidence_store
from .crud import get_task, read_notes


def record_session_human_reply(
    session_id: str | None,
    *,
    sent: bool,
    text: str = "",
    channel: str = "",
    error: str | None = None,
) -> None:
    store = session_evidence_store()
    if hasattr(store, "record_human_reply"):
        store.record_human_reply(
            session_id,
            sent=sent,
            text=text,
            channel=channel,
            error=error,
        )


def record_session_execution_tool(
    session_id: str | None,
    *,
    tool_name: str,
    success: bool,
    summary: str = "",
) -> None:
    store = session_evidence_store()
    if hasattr(store, "record_execution_tool"):
        store.record_execution_tool(
            session_id,
            tool_name=tool_name,
            success=success,
            summary=summary,
        )


def session_has_execution_attempt(session_id: str | None) -> bool:
    return session_evidence_store().has_execution_attempt(session_id)


def _session_has_sent_human_reply(session_id: str | None) -> bool:
    return session_evidence_store().has_sent_human_reply(session_id)


def _session_has_successful_execution_tool(session_id: str | None) -> bool:
    return session_evidence_store().has_successful_execution_tool(session_id)


def completion_ready(
    task_id: str,
    *,
    session_id: str | None = None,
) -> tuple[bool, str]:
    """判断待办是否可以标记完成。

    产品语义（设计文档 6.6 重写）：待办只有一道硬门禁——**必须写过笔记**，
    写明结果 / 阻塞原因 / 验收说明。仅此一条。

    为什么不再有「session 内必须调过 terminal」或「session 内必须向人汇报」
    这类硬性证据门禁：

      1. **任务经常跨多 session 完成**。拆解→执行→收尾可能分布在不同 wakeup
         里。强制"标 done 的那一轮 session 必须调过 terminal"是反现实的。
      2. **很多待办本来就不需要执行类工具**。决策类、等待类、整理类任务，
         笔记已能完整描述结果，逼着模型去 terminal 找证据既无意义也无效。
      3. **形似门禁、实则虚设**。原规则只检查"调没调"，不检查"调用有没有
         意义"，模型可以瞎调 `terminal pwd` 就过——这既苛刻又防不了自评自夸。
      4. **会导致死循环**。case: 2026-06-13 alpha 盯盘任务实质完成、notes 已写，
         但 todo done 工具反复被门禁拒（"必须先调 terminal"，可是已经调过了，
         fallback reader 在生产里根本没注入）→ 任务永远 in_progress →
         task_momentum 持续催 → 反复唤醒浪费配额 → 死循环。

    防自评自夸真正靠的是 **task_note 内容本身**——笔记是模型的自我陈述，
    reviewer（人或自身复盘）看得到、可以追溯。把"动作检查"当成门禁的思路
    在实践中反而创造了卡死，把硬性规则收回"必须有笔记"一条，更符合
    "事件即一次性消费、待办是计划性的自我陈述"的产品哲学。

    Args:
        task_id: 待办 ID
        session_id: 保留（兼容现有调用方）；当前不使用。

    Returns:
        (True, "") 可标完成
        (False, reason) 不可完成 + 人类可读原因
    """
    detail = get_task(task_id)
    if not detail:
        return False, f"任务 {task_id} 不存在"
    notes = read_notes(task_id, limit=1)
    if not notes:
        return False, "完成任务前必须先用 task_note 写入结果、阻塞原因或验收说明"
    return True, ""


def on_session_end(session_id: str, digest: str) -> None:
    """session 结束时关联到当前 in_progress 的 todo。

    作用：todo_sessions 表记录每次 session 跑了哪个 todo + digest 摘要。
    被完成门禁（completion_ready）和 momentum 检测（已停用）依赖。
    """
    db = get_db()
    try:
        # 取当前 in_progress 最新 todo 关联到本次 session
        row = db.execute(
            "SELECT id FROM todos WHERE status='in_progress' ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        task_id = row["id"] if row else None

        if not task_id:
            return

        now = now_iso()
        db.execute(
            "INSERT INTO todo_sessions (task_id, session_id, digest, started_at, ended_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, session_id, digest, now, now),
        )
        db.commit()
        # task_reminder re-arm 已停用（2026-06-17）：每次 session 结束
        # 如果没调过执行工具就 force emit → 死循环风暴（6-14 实测 1h emit
        # 20 条 task_reminder）。task_reminder 事件本身也停用了。
        # 待办提醒的后续实现待设计文档重新定义后再加回。
    except Exception as e:
        import logging
        logging.getLogger("digital_life.domain.todos").debug("on_session_end failed: %s", e)
    finally:
        db.close()
