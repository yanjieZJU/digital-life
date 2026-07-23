"""Project deliverables —— thin wrapper 到 domain.todos.crud (global_todos.db).

Phase 4 (2026-06-24) 之后:本模块不再有独立的 deliverables 表。
原 `projects/<pid>/data/todos.db.deliverables` 表已合并到
`data/global_todos.db.todos`,通过 `linked_deliverable_id != ''` + `project_id`
两个字段反向定位。

原函数签名(create_deliverable/list_deliverables/get_deliverable/update_deliverable)
保留作为兼容入口,内部全部转发到 `domain.todos.crud.{create,list,get,update}_task`,
让 legacy caller 不用改。
"""

from __future__ import annotations

import logging

logger = logging.getLogger("digital_life.domain.project")


def _new_id() -> str:
    """新 id 生成 — create_task 内部用 uuid4,这里只保留给少量老调用方。"""
    import uuid
    return uuid.uuid4().hex[:8]


def _now_iso() -> str:
    try:
        from domain.lifecycle.clock import now_iso
        return now_iso()
    except Exception:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


# ──────────────────────────── deliverables 接口(thin wrappers) ────────────────────────────


def create_deliverable(
    db,  # 兼容老 caller 传的 project_db,现在 ignore
    title: str,
    description: str = "",
    priority: str = "medium",
    assignee_instance: str = "",
    assignee_position: str = "",
    *,
    project_id: str = "",
    acceptance_criteria: str = "",
) -> str:
    """创建 deliverable = 创建一条 todo(linked_deliverable_id 指自己)。

    Phase 4 后:不再写 projects/<pid>/data/todos.db.deliverables 表。
    内部直接调 global todos.create_task。

    db 参数保留只是为了让 legacy caller 不报错,内部 ignored。
    """
    from domain.todos.crud import create_task

    # deliverable 用 todo.id 作为自身 id;create_task 内部用 uuid4[:8]
    # 所以先调,然后从结果里取 id 当返回。这也保证 deliverable.id == todo.id。
    result = create_task(
        title=title,
        description=description,
        priority=priority,
        status="planned",  # deliverable 默认 planned
        source=f"project:{project_id}" if project_id else "personal",
        linked_deliverable_id=None,  # 关键:留空,因为 create_task 返回的 id 就是 deliverable.id
        assignee_instance=assignee_instance or None,
        project_id=project_id or None,
        acceptance_criteria=acceptance_criteria,
        assignee_position=assignee_position,
    )

    if not result.get("ok"):
        # create 失败(去重等) — log + 抛,让上层处理
        logger.warning("create_deliverable failed: %s", result.get("reason"))
        # 返回空字符串让上层 fallback;不抛异常兼容老 caller
        return ""

    tid = result["task"]["id"]

    # 回写 linked_deliverable_id 等于自身 id,这样 `WHERE linked_deliverable_id != ''`
    # 才能筛出 deliverable-类 todo。
    if project_id and tid:
        from domain.todos.crud import update_task
        try:
            update_task(tid, linked_deliverable_id=tid)
        except Exception as exc:
            logger.warning("create_deliverable: 失败回写 linked_deliverable_id=%s: %s", tid, exc)

    logger.info(
        "create_deliverable → todo %s (title=%s project=%s assignee=%s position=%s)",
        tid, title[:30], project_id, (assignee_instance or "")[:8], assignee_position,
    )
    return tid


def list_deliverables(db, project_id: str = "") -> list[dict]:
    """列项目 deliverable。返回全字段。

    Phase 4 改造:从 todos 表 WHERE project_id=pid AND linked_deliverable_id != ''。
    """
    from domain.todos.crud import list_tasks

    if not project_id:
        return []
    # linked_deliverable_id IS NOT NULL AND != '' 过滤出 deliverable-类 todo
    tasks = list_tasks(project_id=project_id)
    return [
        t for t in tasks
        if t.get("linked_deliverable_id")
    ]


def get_deliverable(db, deliverable_id: str) -> dict | None:
    """取单个 deliverable。"""
    from domain.todos.crud import list_tasks

    tasks = list_tasks(linked_deliverable_id=deliverable_id)
    return tasks[0] if tasks else None


def update_deliverable(
    db,
    deliverable_id: str,
    project_id: str = "",
    **updates,
) -> bool:
    """更新 deliverable = 更新对应 todo。

    Phase 4:内部调 update_task。assignee_position 等所有 deliverables 表字段
    都映射到 todos 列。
    """
    from domain.todos.crud import update_task

    # 限定可更新字段(白名单),避免 caller 传奇怪字段
    allowed = {
        "title", "description", "status", "priority",
        "assignee_instance", "assignee_position",
        "acceptance_criteria", "detail", "deadline",
    }
    safe_updates = {k: v for k, v in updates.items() if k in allowed}

    try:
        update_task(deliverable_id, **safe_updates)
        return True
    except Exception as exc:
        logger.warning("update_deliverable %s failed: %s", deliverable_id, exc)
        return False


__all__ = [
    "create_deliverable",
    "list_deliverables",
    "get_deliverable",
    "update_deliverable",
]
