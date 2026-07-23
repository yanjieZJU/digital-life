from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional, Sequence


@dataclass
class Task:
    id: str = ""
    title: str = ""
    description: str = ""
    acceptance_criteria: str = ""
    # 详情记忆：模型/真人在任意时刻可编辑（增删改，非 append-only）。
    # 跟 todo_notes 子表的"append-only 笔记"区别：detail 是当前最新版本,
    # 用于 rest 前"给未来自己留详情备注" / sense_todos 时模型直接看见的"上下文记忆"。
    # rest 工具调 todo(action='update', todo_id, detail='...') 写入；sense_todos board 渲染
    detail: str = ""
    status: str = "idea"
    priority: str = "medium"
    deadline: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    source: str = "personal"
    linked_deliverable_id: Optional[str] = None
    type: str = ""
    # 新维度（global_todos.db 重构后）
    project_id: str = ""
    assignee_instance: str = ""
    assignee_kind: str = ""
    parent_id: str = ""
    has_workspace: bool = False
    # Phase 4 (2026-06-24):岗位名 architect/developer/trader(从 deliverables 合并过来),
    # 跟 assignee_kind(instance/human/position) 不同语义。
    assignee_position: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class TaskPlan:
    id: int = 0
    task_id: str = ""
    content: str = ""
    deadline: Optional[str] = None
    status: str = "pending"
    order_num: int = 0
    created_at: str = ""
    completed_at: Optional[str] = None


@dataclass
class TaskNote:
    id: int = 0
    task_id: str = ""
    content: str = ""
    created_at: str = ""


def row_to_task(row) -> Task:
    tags = json.loads(row["tags"]) if row["tags"] else []
    keys = row.keys() if hasattr(row, "keys") else []
    source = row["source"] if "source" in keys else "personal"
    linked = row["linked_deliverable_id"] if "linked_deliverable_id" in keys else None
    type_ = row["type"] if "type" in keys else ""
    project_id = row["project_id"] if "project_id" in keys else (source.split(":", 1)[1] if source.startswith("project:") else "")
    assignee = row["assignee_instance"] if "assignee_instance" in keys else ""
    assignee_kind = row["assignee_kind"] if "assignee_kind" in keys else ""
    parent_id = row["parent_id"] if "parent_id" in keys else ""
    has_workspace = bool(row["has_workspace"]) if "has_workspace" in keys else False
    acceptance_criteria = row["acceptance_criteria"] if "acceptance_criteria" in keys else ""
    detail = row["detail"] if "detail" in keys else ""
    assignee_position = row["assignee_position"] if "assignee_position" in keys else ""
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        acceptance_criteria=acceptance_criteria or "",
        detail=detail or "",
        status=row["status"],
        priority=row["priority"],
        deadline=row["deadline"],
        tags=tags,
        source=source or "personal",
        linked_deliverable_id=linked,
        type=type_ or "",
        project_id=project_id or "",
        assignee_instance=assignee or "",
        assignee_kind=assignee_kind or "",
        parent_id=parent_id or "",
        has_workspace=has_workspace,
        assignee_position=assignee_position or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def task_to_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "acceptance_criteria": task.acceptance_criteria,
        "detail": task.detail,
        "status": task.status,
        "priority": task.priority,
        "deadline": task.deadline,
        "tags": task.tags,
        "source": task.source,
        "linked_deliverable_id": task.linked_deliverable_id,
        "type": task.type,
        # 新字段（前端能看到）
        "project_id": task.project_id,
        "assignee_instance": task.assignee_instance,
        "assignee_kind": task.assignee_kind,
        "assignee_position": task.assignee_position,
        "parent_id": task.parent_id,
        "has_workspace": task.has_workspace,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def find_similar_task(candidates: Sequence[Task], title: str) -> Optional[Task]:
    query = title.strip().lower()
    if len(query) < 2:
        return None

    for task in candidates:
        existing = task.title.lower()
        if query in existing or existing in query:
            return task

        query_chars = set(query)
        existing_chars = set(existing)
        if query_chars and existing_chars:
            overlap = len(query_chars & existing_chars) / max(len(query_chars), len(existing_chars))
            if overlap > 0.6:
                return task
    return None


__all__ = [
    "Task",
    "TaskNote",
    "TaskPlan",
    "find_similar_task",
    "row_to_task",
    "task_to_dict",
]
