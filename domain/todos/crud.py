"""Task CRUD operations."""

from __future__ import annotations

import json
import uuid
from typing import List, Optional

from ._infra import get_db, tasks_dir, now_iso, task_has_speckit
from .core.constants import VALID_STATUSES, VALID_PRIORITIES
from .core.models import Task, row_to_task, task_to_dict, find_similar_task
from .scheduler import schedule_task_wakeup

TASK_UPDATE_COLUMNS = {
    "title",
    "description",
    "acceptance_criteria",
    "detail",  # 详情记忆(增删改,非 append-only)。rest 前编辑、sense_todos 渲染
    "priority",
    "deadline",
    "status",
    "tags",
    "source",
    "linked_deliverable_id",
    "type",
    "parent_id",
    "has_workspace",
    "assignee_position",  # 2026-06-24 Phase 4:岗位名 architect/developer/trader
}
PLAN_UPDATE_COLUMNS = {"content", "deadline"}
TODO_UPDATE_COLUMNS = {"content", "due_at", "trigger_condition", "status", "note"}


def _row_to_task(r) -> Task:
    return row_to_task(r)


def _task_to_dict(task: Task) -> dict:
    return task_to_dict(task)


def create_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    deadline: Optional[str] = None,
    tags: Optional[List[str]] = None,
    status: str = "planned",
    source: str = "personal",
    linked_deliverable_id: Optional[str] = None,
    type: str = "",
    assignee_instance: Optional[str] = None,
    project_id: Optional[str] = None,
    acceptance_criteria: str = "",
    detail: str = "",
    assignee_position: str = "",
) -> dict:
    """创建一条 todo。

    新参数（2026-06-14 重构后）：
      assignee_instance: 分给哪个实例。如果 None，默认为当前 context 实例。
      project_id: 关联项目（空=纯个人 todo）。None=不挂项目。
      source: 旧字段，向后兼容。若同时给了 project_id，project_id 优先。
      acceptance_criteria: 完成标准（什么样算 done）。明文写下做完什么样才能 close。
      detail: 详情记忆 —— 增删改（非 append-only）。模型 rest 前可写，
              sense_todos 时模型直接看见这个 todo 的"上下文记忆"。
              与 todo_notes 子表的 append-only 笔记区别：detail 是"当前最新版"。
      assignee_position: 分配的岗位名(architect/developer/trader)。
              2026-06-24 Phase 4 引入 — 创建 deliverable 的 thin wrapper 时透传。

    schema 已经迁移到 global_todos.db.todos，列：
      - project_id（拆自旧 source='project:X'）
      - assignee_instance（新增 — 旧表没这列因为"实例即拥有的"假设）
      - acceptance_criteria（新增 — 强制每个 todo 写"什么算 done"）
      - detail（新增 — 详情记忆；ALTER TABLE 兜底加列，老库容错)
      - assignee_position(2026-06-24 Phase 4 — deliverables 表合并后引入;
        岗位名跟 assignee_kind 不同语义:kind 是 instance/human/position,
        position 才是 architect/developer 这种)
    """
    if status not in VALID_STATUSES:
        return {"ok": False, "reason": f"无效状态 {status}"}
    if priority not in VALID_PRIORITIES:
        return {"ok": False, "reason": f"无效优先级 {priority}"}

    # 2026-06-23 防御:source vs project_id 冲突时,project_id 优先。
    # 历史 BUG:caller 传 source='personal' + project_id='shangcheng' 时,
    # source='personal' 被原样写入 → 前端按 source 分组把项目待办错误归到"个人"段。
    # 规则:只要给了 project_id,source 自动设为 'project:<project_id>'。
    if project_id:
        source = f"project:{project_id}"

    dup = _find_similar_task(title, description)
    if dup:
        return {"ok": False, "reason": f"已有相似任务「{dup.title}」(id={dup.id}, 状态={dup.status})，建议复用",
                "similar_task": _task_to_dict(dup)}

    tid = uuid.uuid4().hex[:8]
    now = now_iso()
    tags = tags or []
    # source 兼容：旧 caller 传 source='project:X'，转成 project_id
    if project_id is None and source.startswith("project:"):
        project_id = source.split(":", 1)[1]
    if not project_id:
        project_id = ""
    # assignee 默认当前实例
    if assignee_instance is None:
        try:
            from infrastructure.config import get_app_instance_id
            assignee_instance = get_app_instance_id() or ""
        except Exception:
            assignee_instance = ""
    # workspace 懒创建：只有项目来源或有明确 type 才建目录
    _needs_workspace = bool(project_id) or bool(type)
    assignee_kind = "instance" if assignee_instance else ""
    db = get_db()
    try:
        # 先确保 detail 列存在(老库 ALTER TABLE 兜底;global_todos.get_global_todos_db 自动建,但防御性)
        try:
            db.execute("ALTER TABLE todos ADD COLUMN detail TEXT DEFAULT ''")
        except Exception:
            pass
        db.execute(
            "INSERT INTO todos (id, title, description, acceptance_criteria, detail, status, priority, "
            "deadline, tags, project_id, assignee_instance, assignee_kind, assignee_position, parent_id, "
            "linked_deliverable_id, type, has_workspace, source, origin_instance, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?, ?, ?)",
            (tid, title, description, acceptance_criteria, (detail or ""), status, priority, deadline,
             json.dumps(tags, ensure_ascii=False),
             project_id, assignee_instance, assignee_kind, assignee_position,
             linked_deliverable_id, type, 1 if _needs_workspace else 0,
             source, assignee_instance, now, now),
        )
        db.commit()
    finally:
        db.close()

    if _needs_workspace:
        ws = tasks_dir() / tid
        ws.mkdir(parents=True, exist_ok=True)
        (ws / "NOTES.md").write_text(f"# {title}\n\n{description}\n", encoding="utf-8")

    task = Task(id=tid, title=title, description=description,
                acceptance_criteria=acceptance_criteria,
                detail=(detail or ""),
                priority=priority, status=status, deadline=deadline, tags=tags,
                source=source, linked_deliverable_id=linked_deliverable_id, type=type,
                project_id=project_id, assignee_instance=assignee_instance,
                assignee_kind=assignee_kind,
                created_at=now, updated_at=now)
    if status in ("planned", "in_progress"):
        schedule_task_wakeup(task.id, title=task.title, status=status)
    return {"ok": True, "task": _task_to_dict(task)}


def list_tasks(
    status_filter: Optional[str] = None,
    source: Optional[str] = None,
    project_id: Optional[str] = None,
    linked_deliverable_id: Optional[str] = None,
    *,
    assignee_instance: Optional[str] = None,
    include_unassigned: bool = False,
) -> List[dict]:
    """列任务。

    可选过滤（多重 AND）：
      status_filter: planned / in_progress / done / cancelled / paused / idea
      source: 'personal' 或 'project:{pid}'（向后兼容，等价于 project_id）
      project_id: 关联的项目 ID
      linked_deliverable_id: 关联 deliverable 的 id
      assignee_instance: 分给某个实例（'我自己要做的'，传当前 instance_id 即可）
      include_unassigned: 配合 assignee_instance，True 时也包含未指派的 todo

    新语义（global_todos.db 重构后）：
      source 字段仍可用，但等价于 project_id（'project:X' → project_id='X'）
      assignee_instance 是新维度（解决"派给我就我的"的产品需求）
    """
    where_parts: list[str] = []
    params: list = []
    if status_filter and status_filter in VALID_STATUSES:
        where_parts.append("status=?")
        params.append(status_filter)

    # project_id / source 同维：旧 caller 传 source='project:X' 仍能 work
    if project_id:
        where_parts.append("project_id=?")
        params.append(project_id)
    elif source:
        if source.startswith("project:"):
            where_parts.append("project_id=?")
            params.append(source.split(":", 1)[1])
        elif source == "personal":
            # 老 'personal' 表示"不挂项目"
            where_parts.append("project_id=''")

    if linked_deliverable_id:
        where_parts.append("linked_deliverable_id=?")
        params.append(linked_deliverable_id)

    if assignee_instance is not None:
        if include_unassigned:
            where_parts.append("(assignee_instance=? OR assignee_instance='')")
            params.append(assignee_instance)
        else:
            where_parts.append("assignee_instance=?")
            params.append(assignee_instance)

    db = get_db()
    try:
        # 优先用新表 todos（global_todos.db.todos 已含 project_id/assignee_instance 列）
        sql = "SELECT * FROM todos"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        sql += " ORDER BY status IN ('in_progress','planned','idea','paused') DESC, updated_at DESC"
        rows = db.execute(sql, params).fetchall()
    finally:
        db.close()
    return [_task_to_dict(_row_to_task(r)) for r in rows]


def get_task(task_id: str) -> Optional[dict]:
    db = get_db()
    try:
        row = db.execute("SELECT * FROM todos WHERE id=?", (task_id,)).fetchone()
        if not row:
            return None
        task = _row_to_task(row)

        ws = tasks_dir() / task_id
        notes_file = ws / "NOTES.md"
        workspace_notes = notes_file.read_text(encoding="utf-8") if notes_file.exists() else ""

        note_rows = db.execute(
            "SELECT content, created_at FROM todo_notes WHERE task_id=? ORDER BY created_at DESC LIMIT 5",
            (task_id,),
        ).fetchall()
        recent_notes = [{"content": r["content"], "created_at": r["created_at"]} for r in note_rows]

        plan_rows = db.execute(
            "SELECT * FROM todo_plans WHERE task_id=? ORDER BY order_num, id",
            (task_id,),
        ).fetchall()
        plans = [dict(r) for r in plan_rows]

        speckit = None
        speckit_dir = ws / "speckit"
        if speckit_dir.exists():
            try:
                speckit = {}
                for filename in ("spec.md", "plan.md", "tasks.md", "tasks.json"):
                    fpath = speckit_dir / filename
                    if fpath.exists():
                        content = fpath.read_text(encoding="utf-8")
                        if len(content) > 3000:
                            content = content[:3000] + "\n\n...[truncated]"
                        speckit[filename] = content
            except Exception:
                pass

        session_rows = db.execute(
            "SELECT digest, started_at, ended_at FROM todo_sessions WHERE task_id=? ORDER BY started_at DESC LIMIT 3",
            (task_id,),
        ).fetchall()
        sessions = [dict(r) for r in session_rows]

        task_dict = _task_to_dict(task)

        from .execution_context import build_execution_context
        execution = build_execution_context(
            task=task_dict, speckit=speckit, plans=plans, notes=recent_notes,
            workspace_path=str(ws.relative_to(ws.parent.parent)),
            sessions=sessions,
        )

        return {
            "task": _task_to_dict(task),
            "workspace": {
                "path": str(ws.relative_to(ws.parent.parent)),
                "notes_summary": workspace_notes[-1000:] if len(workspace_notes) > 1000 else workspace_notes,
                "notes": recent_notes,
            },
            "execution": execution,
            "context": {
                "speckit": speckit,
                "past_sessions": sessions,
                "plans": plans,
            },
        }
    finally:
        db.close()


def update_task(task_id: str, **kwargs) -> dict:
    updates = {k: v for k, v in kwargs.items() if k in TASK_UPDATE_COLUMNS and v is not None}
    if not updates:
        return {"ok": False, "reason": "没有可更新的字段"}

    if "status" in updates and updates["status"] not in VALID_STATUSES:
        return {"ok": False, "reason": f"无效状态 {updates['status']}"}
    if "priority" in updates and updates["priority"] not in VALID_PRIORITIES:
        return {"ok": False, "reason": f"无效优先级 {updates['priority']}"}

    updates["updated_at"] = now_iso()

    if "tags" in updates and isinstance(updates["tags"], list):
        updates["tags"] = json.dumps(updates["tags"], ensure_ascii=False)

    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [task_id]

    db = get_db()
    try:
        sql = "UPDATE todos SET " + set_clause + " WHERE id=?"
        cur = db.execute(sql, values)
        db.commit()
        if cur.rowcount == 0:
            return {"ok": False, "reason": f"任务 {task_id} 不存在"}
    finally:
        db.close()

    if "status" in updates:
        from .scheduler import on_status_change
        on_status_change(task_id, updates["status"])

        # task cancelled → 联动取消所有 todos（含撤销时间型闹钟）
        if updates["status"] == "cancelled":
            try:
                cancel_todos_by_task(task_id)
            except Exception:
                pass

        # 项目 deliverable 状态联动（双向对称）：
        #   task done/cancelled → deliverable 同步到 done/planned
        #   task in_progress → deliverable 同步到 in_progress（让规划者看见进度）
        try:
            new_status = updates["status"]
            if new_status in ("done", "cancelled", "in_progress"):
                db2 = get_db()
                try:
                    row = db2.execute(
                        "SELECT source, linked_deliverable_id FROM todos WHERE id=?", (task_id,)
                    ).fetchone()
                finally:
                    db2.close()
                if row and row["source"] and row["source"].startswith("project:") and row["linked_deliverable_id"]:
                    pid = row["source"].split(":", 1)[1]
                    did = row["linked_deliverable_id"]
                    if new_status == "done":
                        dstatus = "done"
                    elif new_status == "cancelled":
                        dstatus = "planned"
                    elif new_status == "in_progress":
                        dstatus = "in_progress"
                    try:
                        from domain.project._infra import get_project_db
                        from domain.project.crud import update_deliverable
                        pdb = get_project_db(pid)
                        try:
                            # 这里 task 状态变更驱动 deliverable 同步，
                            # 显式不触发反向（避免循环：反向 sync 又改 task 状态）
                            update_deliverable(pdb, did, status=dstatus, project_id=None)
                        finally:
                            pdb.close()
                    except Exception:
                        pass
        except Exception:
            pass

    return {"ok": True, "task_id": task_id}


def attach_workspace(task_id: str) -> dict:
    """给一个已有待办懒创建工作空间目录（空间维度）。

    大部分待办不需要 workspace；只有当模型/系统明确需要时才调。
    幂等：已创建则直接返回。
    """
    task = get_task(task_id)
    if not task:
        return {"ok": False, "reason": f"待办 {task_id} 不存在"}
    ws = tasks_dir() / task_id
    if ws.exists() and (ws / "NOTES.md").exists():
        return {"ok": True, "task_id": task_id, "workspace": str(ws), "already_existed": True}
    ws.mkdir(parents=True, exist_ok=True)
    title = (task.get("task") or {}).get("title", task_id)
    desc = (task.get("task") or {}).get("description", "")
    (ws / "NOTES.md").write_text(f"# {title}\n\n{desc}\n", encoding="utf-8")
    update_task(task_id, has_workspace=1)
    return {"ok": True, "task_id": task_id, "workspace": str(ws), "already_existed": False}


def search_tasks(query: str) -> List[dict]:
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM todos WHERE title LIKE ? OR description LIKE ?",
                          (f"%{query}%", f"%{query}%")).fetchall()
    finally:
        db.close()
    return [_task_to_dict(_row_to_task(r)) for r in rows]


def _find_similar_task(title: str, description: str) -> Optional[Task]:
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM todos WHERE status NOT IN ('done', 'cancelled')"
        ).fetchall()
    finally:
        db.close()
    return find_similar_task([_row_to_task(r) for r in rows], title)


# ──────────────────────────────── Task Plans ────────────────────────────────


def create_plan(task_id: str, content: str, deadline: Optional[str] = None) -> dict:
    """创建任务计划步骤。有 deadline 时自动调度闹钟提醒。"""
    db = get_db()
    try:
        now = now_iso()
        row = db.execute("SELECT MAX(order_num) as m FROM todo_plans WHERE task_id=?", (task_id,)).fetchone()
        order = (row["m"] or 0) + 1
        cur = db.execute(
            "INSERT INTO todo_plans (task_id, content, deadline, status, order_num, created_at) VALUES (?, ?, ?, 'pending', ?, ?)",
            (task_id, content, deadline, order, now),
        )
        db.commit()
        plan_id = cur.lastrowid
    finally:
        db.close()

    if deadline:
        from .scheduler import schedule_plan_event
        schedule_plan_event(task_id, plan_id, content, deadline)

    return {"ok": True, "plan_id": plan_id}


def list_plans(task_id: str) -> List[dict]:
    """列出任务的所有计划步骤。"""
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM todo_plans WHERE task_id=? ORDER BY order_num, id", (task_id,)).fetchall()
    finally:
        db.close()
    return [dict(r) for r in rows]


def complete_plan(plan_id: int) -> dict:
    """标记计划步骤为已完成。"""
    db = get_db()
    try:
        now = now_iso()
        cur = db.execute("UPDATE todo_plans SET status='done', completed_at=? WHERE id=?", (now, plan_id))
        db.commit()
        if cur.rowcount == 0:
            return {"ok": False, "reason": f"计划 {plan_id} 不存在"}
    finally:
        db.close()
    return {"ok": True, "plan_id": plan_id}


def skip_plan(plan_id: int) -> dict:
    """标记计划步骤为已跳过。"""
    db = get_db()
    try:
        now = now_iso()
        cur = db.execute("UPDATE todo_plans SET status='skipped', completed_at=? WHERE id=?", (now, plan_id))
        db.commit()
        if cur.rowcount == 0:
            return {"ok": False, "reason": f"计划 {plan_id} 不存在"}
    finally:
        db.close()
    return {"ok": True, "plan_id": plan_id}


def update_plan(plan_id: int, content: Optional[str] = None, deadline: Optional[str] = None) -> dict:
    """更新计划步骤内容或截止日期。deadline 变更时重新调度闹钟。"""
    updates = {}
    if content:
        updates["content"] = content
    if deadline:
        updates["deadline"] = deadline
    if not updates:
        return {"ok": False, "reason": "没有可更新的字段"}

    updates = {k: v for k, v in updates.items() if k in PLAN_UPDATE_COLUMNS}
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [plan_id]

    db = get_db()
    try:
        sql = "UPDATE todo_plans SET " + set_clause + " WHERE id=?"
        cur = db.execute(sql, values)
        db.commit()
        if cur.rowcount == 0:
            return {"ok": False, "reason": f"计划 {plan_id} 不存在"}
    finally:
        db.close()

    if deadline:
        row = db.execute("SELECT task_id, content FROM todo_plans WHERE id=?", (plan_id,)).fetchone()
        if row:
            from .scheduler import schedule_plan_event
            schedule_plan_event(row["task_id"], plan_id, row["content"], deadline)

    return {"ok": True, "plan_id": plan_id}


# ──────────────────────────────── Task Notes ────────────────────────────────


def add_note(task_id: str, content: str) -> dict:
    """添加任务笔记（DB + 文件系统双写）。"""
    db = get_db()
    try:
        now = now_iso()
        cur = db.execute(
            "INSERT INTO todo_notes (task_id, content, created_at) VALUES (?, ?, ?)",
            (task_id, content, now),
        )
        db.commit()
        note_id = cur.lastrowid
    finally:
        db.close()

    ws = tasks_dir() / task_id
    notes_file = ws / "NOTES.md"
    if notes_file.exists():
        text = notes_file.read_text(encoding="utf-8")
        text += f"\n\n## {now}\n\n{content}\n"
        notes_file.write_text(text, encoding="utf-8")

    return {"ok": True, "note_id": note_id}


def read_notes(task_id: str, limit: int = 20) -> List[dict]:
    """读取任务最近笔记。"""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, content, created_at FROM todo_notes WHERE task_id=? ORDER BY created_at DESC LIMIT ?",
            (task_id, limit),
        ).fetchall()
    finally:
        db.close()
    return [dict(r) for r in rows]


# ──────────────────────────────── 待办 (todo_triggers) ────────────────────────────────
# v5 设计：待办是任务的执行计划。三种触发：time / condition / ongoing
# 时间型 create 时自动注册闹钟；delete/cancel 时自动撤销闹钟
# 不主动处理条件型，由 scheduler 注入 todos 给承担者自己判断

VALID_TODO_STATUSES = ("pending", "active", "done", "cancelled")
VALID_TODO_TRIGGERS = ("time", "condition", "ongoing")


def create_todo(
    task_id: str,
    assignee: str,
    content: str,
    trigger_type: str = "time",
    due_at: Optional[str] = None,
    condition: Optional[str] = None,
) -> dict:
    """创建待办。

    时间型：due_at 必填，会自动注册闹钟 event_kind='task_todo_due'
    条件型：condition 必填（自然语言描述）
    持续型：永远 active，不注册闹钟

    assignee 可以是自己，也可以是别人（规划者给执行者定待办）
    """
    if trigger_type not in VALID_TODO_TRIGGERS:
        return {"ok": False, "reason": f"无效 trigger_type {trigger_type}"}
    if not content.strip():
        return {"ok": False, "reason": "content 必填"}
    if trigger_type == "time" and not due_at:
        return {"ok": False, "reason": "time 型待办 due_at 必填"}
    if trigger_type == "condition" and not condition:
        return {"ok": False, "reason": "condition 型待办 condition 必填"}

    now = now_iso()

    # Cross-instance dispatch: if the assignee is another instance, write this
    # todo into that instance's tasks DB so its own cron / scheduler picks it
    # up. Otherwise it'd land in the dispatcher's DB and never fire on the
    # assignee's wake. We switch ContextVar temporarily and restore afterwards.
    target_ctx_token = None
    current_iid = ""
    try:
        from infrastructure.config import get_app_instance_id, set_current_instance_id, reset_current_instance_id
        current_iid = get_app_instance_id() or ""
    except Exception:
        pass
    if assignee and current_iid and assignee != current_iid:
        try:
            target_ctx_token = set_current_instance_id(assignee)
        except Exception:
            target_ctx_token = None

    try:
        db = get_db()
        try:
            cur = db.execute(
                "INSERT INTO todo_triggers (task_id, assignee, content, trigger_type, due_at, "
                "trigger_condition, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
                (task_id, assignee, content, trigger_type,
                 due_at if trigger_type == "time" else None,
                 condition if trigger_type == "condition" else "",
                 now, now),
            )
            todo_id = cur.lastrowid
            db.commit()
        finally:
            db.close()

        # 时间型 → 注册闹钟（emit event_kind='task_todo_due'）。
        # 必须放在 cross-instance dispatch 的 ContextVar 切换范围内，否则 alarm
        # 会落到 dispatcher 的 DB 而非 assignee 的 DB。
        if trigger_type == "time":
            try:
                from domain.lifecycle.alarms import set_alarm
                set_alarm(
                    event_kind="task_todo_due",
                    fire_at=due_at,
                    payload={
                        "todo_id": todo_id,
                        "task_id": task_id,
                        "assignee": assignee,
                        "content": content,
                    },
                )
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "create_todo: 注册闹钟失败 todo_id=%s: %s", todo_id, exc,
                )
    finally:
        if target_ctx_token is not None:
            try:
                reset_current_instance_id(target_ctx_token)
            except Exception:
                pass

    return {"ok": True, "todo_id": todo_id}


def list_todos(
    assignee: Optional[str] = None,
    status: Optional[str] = None,
    task_id: Optional[str] = None,
    trigger_type: Optional[str] = None,
) -> List[dict]:
    """列待办，支持多维过滤。

    默认不限制 assignee（任何人都能查任何人——规划者给执行者定待办前查冲突）
    """
    where_parts: list[str] = []
    params: list = []
    if status:
        if status not in VALID_TODO_STATUSES:
            return []
        where_parts.append("status=?")
        params.append(status)
    if assignee:
        where_parts.append("assignee=?")
        params.append(assignee)
    if task_id:
        where_parts.append("task_id=?")
        params.append(task_id)
    if trigger_type:
        where_parts.append("trigger_type=?")
        params.append(trigger_type)

    order = (
        "ORDER BY "
        "CASE trigger_type WHEN 'time' THEN 0 WHEN 'condition' THEN 1 WHEN 'ongoing' THEN 2 ELSE 3 END, "
        "due_at ASC NULLS LAST, "
        "updated_at DESC"
    )

    db = get_db()
    try:
        sql = "SELECT * FROM todo_triggers"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        sql += " " + order
        rows = db.execute(sql, params).fetchall()
    finally:
        db.close()
    return [dict(r) for r in rows]


def get_todo(todo_id: int) -> Optional[dict]:
    db = get_db()
    try:
        row = db.execute("SELECT * FROM todo_triggers WHERE id=?", (todo_id,)).fetchone()
    finally:
        db.close()
    return dict(row) if row else None


def update_todo(todo_id: int, **kwargs) -> dict:
    """更新待办。

    支持字段：状态、内容、due_at、condition。
    状态变 done / cancelled 或时间型 due_at 改了 → 撤销/重新注册闹钟
    """
    updates = {k: v for k, v in kwargs.items() if k in TODO_UPDATE_COLUMNS and v is not None}
    if not updates:
        return {"ok": False, "reason": "没有可更新的字段"}

    if "status" in updates and updates["status"] not in VALID_TODO_STATUSES:
        return {"ok": False, "reason": f"无效状态 {updates['status']}"}

    new_status = updates.get("status")
    new_due = updates.get("due_at")

    # 先查原 todo 拿 trigger_type + assignee
    db = get_db()
    try:
        orig = db.execute("SELECT * FROM todo_triggers WHERE id=?", (todo_id,)).fetchone()
        if not orig:
            return {"ok": False, "reason": f"待办 {todo_id} 不存在"}
        orig = dict(orig)
    finally:
        db.close()

    updates["updated_at"] = now_iso()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [todo_id]

    db = get_db()
    try:
        sql = "UPDATE todo_triggers SET " + set_clause + " WHERE id=?"
        db.execute(sql, vals)
        db.commit()
    finally:
        db.close()

    # 闹钟联动
    is_time = orig["trigger_type"] == "time"
    if is_time:
        try:
            from domain.lifecycle.alarms import cancel_alarms_by_filter
            # 撤销该 todo 的所有 pending 闹钟
            cancel_alarms_by_filter(
                kind="task_todo_due",
                payload_filter={"todo_id": str(todo_id)},
            )
        except Exception:
            pass
        # 如果状态是非最终 + 新 due_at 还在，重新注册
        if (new_status in (None, "pending", "active")):
            due_to_use = new_due or orig["due_at"]
            if due_to_use:
                try:
                    from domain.lifecycle.alarms import set_alarm
                    set_alarm(
                        event_kind="task_todo_due",
                        fire_at=due_to_use,
                        payload={
                            "todo_id": todo_id,
                            "task_id": orig["task_id"],
                            "assignee": orig["assignee"],
                            "content": updates.get("content", orig["content"]),
                        },
                    )
                except Exception:
                    pass

    return {"ok": True, "todo_id": todo_id}


def delete_todo(todo_id: int) -> dict:
    """删除待办（同步撤销关联闹钟）。"""
    db = get_db()
    try:
        row = db.execute("SELECT trigger_type FROM todo_triggers WHERE id=?", (todo_id,)).fetchone()
        if not row:
            return {"ok": False, "reason": f"待办 {todo_id} 不存在"}
        db.execute("DELETE FROM todo_triggers WHERE id=?", (todo_id,))
        db.commit()
    finally:
        db.close()

    # 撤销闹钟
    if row["trigger_type"] == "time":
        try:
            from domain.lifecycle.alarms import cancel_alarms_by_filter
            cancel_alarms_by_filter(
                kind="task_todo_due",
                payload_filter={"todo_id": str(todo_id)},
            )
        except Exception:
            pass

    return {"ok": True, "todo_id": todo_id}


def cancel_todos_by_task(task_id: str) -> int:
    """取消某任务下所有未完成的待办（含撤销闹钟）。

    用于父任务被取消 / 成果被关闭时的联动。
    Returns: 取消的数量
    """
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, trigger_type FROM todo_triggers WHERE task_id=? AND status IN ('pending','active')",
            (task_id,),
        ).fetchall()
        if not rows:
            return 0
        for r in rows:
            db.execute(
                "UPDATE todo_triggers SET status='cancelled', updated_at=? WHERE id=?",
                (now_iso(), r["id"]),
            )
        db.commit()
    finally:
        db.close()

    # 撤销所有时间型闹钟
    todo_ids = [str(r["id"]) for r in rows if r["trigger_type"] == "time"]
    if todo_ids:
        try:
            from domain.lifecycle.alarms import cancel_alarms_by_filter
            for tid in todo_ids:
                cancel_alarms_by_filter(
                    kind="task_todo_due",
                    payload_filter={"todo_id": tid},
                )
        except Exception:
            pass

    return len(rows)


def resolve_skill_for_task_type(task_type: str) -> str:
    """根据待办的 type 字段查 task_types.yaml → skill name → 读 skill SKILL.md 返回文本。

    如果 type 为空 → 兜底注入 todo_execution（通用执行方法论）。
    如果 yaml 映射的 skill 文件不存在 → 返回空。

    设计：P2 仅支持"读 SKILL.md"，不跑 skill 的推理链。注入纯文本到 prompt。
    """
    import yaml as _yaml
    from infrastructure.config import get_project_root

    # type 为空 → 兜底通用执行方法论
    if not task_type:
        task_type = "default"

    # 1. 查 yaml 配置
    yaml_path = get_project_root() / "config" / "task_types.yaml"
    if not yaml_path.exists():
        return ""
    try:
        data = _yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return ""

    mapping = data.get("task_types") or {}
    entry = mapping.get(task_type)
    if not entry or not isinstance(entry, dict):
        return ""
    skill_name = (entry.get("skill") or "").strip()
    if not skill_name:
        return ""
    # 带 note 标记的（如 "skill 文件待写，暂不注入"）→ 跳过
    note = (entry.get("note") or "").strip().lower()
    if "暂不注入" in note or "pending" in note or "待写" in note:
        return ""

    # 2. 读 skill 文件
    skill_path = get_project_root() / "interfaces" / "skills" / skill_name / "SKILL.md"
    if not skill_path.exists():
        return ""

    try:
        content = skill_path.read_text(encoding="utf-8").strip()
        # 去掉 frontmatter（--- 之间的部分）
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                content = content[end + 3:].strip()
        return content
    except Exception:
        return ""


def resolve_skill_for_current_task() -> str:
    """查当前正在执行的 task 的 type → 返回对应 skill 文本。

    用于 scheduler 拼 prompt 时自动注入。
    优先级：session 当前绑定的 task > 最近 in_progress 的 task。
    """
    try:
        from infrastructure.config import get_current_session_id
        # 暂不做 session-task 绑定（P3 时加），先找最近的 in_progress
        tasks = list_tasks(status_filter="in_progress")
        if not tasks:
            return ""
        task = tasks[0]
        task_type = task.get("type") or ""
        return resolve_skill_for_task_type(task_type)
    except Exception:
        return ""
