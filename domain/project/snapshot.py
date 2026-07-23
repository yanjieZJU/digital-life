"""Project portfolio snapshot — gives the model a complete view of
"who I am across all my projects", at wake time.

Aggregates per-instance data:
  - All active projects the instance is assigned to
  - Per project: position + responsibilities + goal/KPI/thesis/deadline
  - Per project: assignee's todos (personal tasks) + deliverables (project-level)
  - Per project: siblings (other instances) and their roles
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from domain.lifecycle.clock import parse_iso


def build_my_portfolio(instance_id: str | None = None) -> List[Dict[str, Any]]:
    """Return a list of project dicts the instance is part of, with full context.

    Each dict has shape:
      {
        "project_id": ...,
        "name": ...,
        "status": ...,
        "is_manager": bool,
        "my_position": "策略师" | ...,
        "responsibilities": [...],
        "goal": {...},
        "thesis": [...],
        "kpis": [...],
        "deadline": ...,
        "deadline_remaining_days": int | None,
        "personal_todos": [...],     # from instance's tasks.db WHERE source=project_id
        "project_deliverables": [...],# Phase 4:from global_todos.db WHERE project_id=pid AND linked_deliverable_id != ''
        "siblings": [...]            # other instances in this project
      }
    """
    from domain.project.loader import load_all_projects
    from infrastructure.config import get_app_instance_id

    iid = instance_id or get_app_instance_id() or ""
    if not iid:
        return []

    out: list[dict] = []
    projects = load_all_projects() or {}
    for pid, cfg in projects.items():
        if cfg.status != "active":
            continue
        pos = cfg.get_position_for_instance(iid)
        if not pos:
            # 不在这个项目里——略过（portfolio 只含我参与的项目）
            continue

        # 拉个人 todos（tasks 表里 source=project_id 的）
        personal_todos = _load_personal_todos(iid, pid)

        # 拉项目级 deliverables assignee 是我 或 unassigned
        project_deliverables = _load_project_deliverables(pid, iid)

        # siblings：同项目其他实例
        siblings: list[dict] = []
        for ap in cfg.positions:
            for a in ap.assignees:
                if a != iid and a and not a.startswith("human:"):
                    siblings.append({
                        "instance_id": a,
                        "position": ap.name,
                        "responsibilities": list(ap.responsibilities or []),
                    })

        # deadline remaining
        deadline_remaining = None
        if cfg.goal.get("deadline"):
            try:
                dl = parse_iso(cfg.goal["deadline"])
                deadline_remaining = (dl - datetime.now(timezone.utc)).days
            except Exception:
                pass

        out.append({
            "project_id": pid,
            "name": cfg.name,
            "description": cfg.description,
            "status": cfg.status,
            "is_manager": cfg.manager == iid,
            "my_position": pos.name,
            "responsibilities": list(pos.responsibilities or []),
            "goal": dict(cfg.goal or {}),
            "thesis": list(cfg.thesis or []),
            "review_schedule": dict(cfg.review_schedule or {}),
            "kpis": list(cfg.kpis or []),
            "deadline": cfg.goal.get("deadline", ""),
            "deadline_remaining_days": deadline_remaining,
            "personal_todos": personal_todos,
            "project_deliverables": project_deliverables,
            "siblings": siblings,
        })

    return out


def _load_personal_todos(instance_id: str, project_id: str) -> list[dict]:
    """Phase 4:读 global_todos.db.assignee_instance=instance_id 且 project_id=pid 的 todo。"""
    try:
        from domain.todos.crud import list_tasks
        tasks = list_tasks(project_id=project_id, assignee_instance=instance_id)
        # 取关键字段
        return [
            {
                "id": t.get("id", ""),
                "title": t.get("title", ""),
                "status": t.get("status", ""),
                "priority": t.get("priority", ""),
                "deadline": t.get("deadline"),
                "description": t.get("description", ""),
                "updated_at": t.get("updated_at", ""),
            }
            for t in tasks[:20]
        ]
    except Exception:
        return []


def _load_project_deliverables(project_id: str, instance_id: str | None = None) -> list[dict]:
    """Phase 4:读 global_todos.db 的 deliverable 类 todo WHERE project_id=pid
    AND linked_deliverable_id != ''。

    deliverable 是一种特殊 todo(用 linked_deliverable_id 标识),不必走第二个表。
    """
    try:
        from domain.todos.crud import list_tasks
        tasks = list_tasks(project_id=project_id)
        # 只取 deliverable 类(linked_deliverable_id 非空)
        delivs = [t for t in tasks if t.get("linked_deliverable_id")]
        # 按 instance 过滤:我相关的(分给我或无主)
        if instance_id:
            delivs = [
                t for t in delivs
                if (t.get("assignee_instance") or "") in (instance_id, "", None)
            ]
        # 排序:in_progress > planned > 其它
        status_order = {"in_progress": 0, "planned": 1}
        delivs.sort(key=lambda t: (status_order.get(t.get("status", ""), 2), t.get("updated_at", "")))
        delivs = delivs[:25]
        # 给前端加 mine 标记
        out = []
        for t in delivs:
            d = dict(t)
            d["mine"] = bool((d.get("assignee_instance") or "") == (instance_id or ""))
            out.append(d)
        return out
    except Exception:
        return []
