"""Global todos DB — 待办的单一真相(N_o matter instance / project)。

设计原则（用户 2026-06-14 确认）：
  - 待办是独立 entity。关联关系（关联了哪个项目、关联了谁）是它的属性，
    不是它的归属。
  - 一个待办挂哪个项目是它的属性(可选,空=纯个人)；assignee 是它的属性
    (可改=可转移)。
  - "我自己要做的" = `WHERE assignee_instance=me`，无论 todo 是从哪里
    产生的(自己手动建 / 被项目分了认领 / 临时派的)。

为什么是 global 不是 per-instance 或 per-project：
  - per-instance: 实例之间转移 todo 需要数据搬家（stale + race 风险）
  - per-project: 个人 todo（不挂项目）不知道存哪
  - 单点真相的 global 表 + 关联列（assignee_instance / project_id）天然解
    决「派给我就我的」「转给谁都行」「项目档案/实例分配」三种语义

历史包袱：
  - 老 apps/{id}/data/todos/todos.db.todos 表（内部 source='project:X'
    描述挂项目，但没有 assignee_instance 列）→ 迁移脚本吸收
  - 老 projects/{pid}/data/todos.db.project_todos 表（完全在项目 DB 里）→
    迁移脚本吸收

存储位置：<repo_root>/data/global_todos.db（跨实例，不能放 apps/*/ 里；
跨项目，不能放 projects/*/ 里）。
"""

from __future__ import annotations

import logging
from pathlib import Path

from infrastructure.persistence import sqlite

logger = logging.getLogger("digital_life.infrastructure.persistence")


def _repo_root() -> Path:
    """仓库根目录。本文件路径是 <root>/infrastructure/persistence/global_todos.py。"""
    return Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    d = _repo_root() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _db_path() -> Path:
    return _data_dir() / "global_todos.db"


_SCHEMA_SQL = """
        CREATE TABLE IF NOT EXISTS todos (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            acceptance_criteria TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'idea',
            priority TEXT DEFAULT 'medium',
            deadline TEXT,
            tags TEXT DEFAULT '[]',
            -- 关联关系（都可为空）
            project_id TEXT DEFAULT '',              -- 关联的项目 ID（personal = 空）
            assignee_instance TEXT DEFAULT '',       -- 分给哪个实例（转移 = 改这列）
            assignee_kind TEXT DEFAULT '',           -- instance / human / position
            parent_id TEXT DEFAULT '',               -- 拆解关系（子 todo 指向父 todo）
            linked_deliverable_id TEXT DEFAULT '',   -- 关联项目 deliverable
            type TEXT DEFAULT '',                    -- 类型（绑 Skill）
            has_workspace INTEGER DEFAULT 0,
            -- 老的 source 字段（'personal' 或 'project:X'），保留作为向后兼容，迁移时填
            source TEXT DEFAULT '',
            -- 来源实例（哪个实例创建的——便于 migration 跟踪）
            origin_instance TEXT DEFAULT '',
            -- 分配的岗位名(architect/developer/trader 等)——2026-06-24 deliverables 合并后引入。
            assignee_position TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

CREATE INDEX IF NOT EXISTS idx_todos_assignee ON todos(assignee_instance, status);
CREATE INDEX IF NOT EXISTS idx_todos_project ON todos(project_id, status);
CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status);
CREATE INDEX IF NOT EXISTS idx_todos_parent ON todos(parent_id);

CREATE TABLE IF NOT EXISTS todo_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    content TEXT NOT NULL,
    deadline TEXT,
    status TEXT DEFAULT 'pending',
    order_num INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (task_id) REFERENCES todos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS todo_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES todos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS todo_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    session_id TEXT,
    digest TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    FOREIGN KEY (task_id) REFERENCES todos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS todo_triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    assignee TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    trigger_type TEXT NOT NULL DEFAULT 'time',
    due_at TEXT,
    trigger_condition TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    assignee_text TEXT DEFAULT '',
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES todos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_todo_triggers_assignee ON todo_triggers(assignee, status);
CREATE INDEX IF NOT EXISTS idx_todo_triggers_task ON todo_triggers(task_id);
CREATE INDEX IF NOT EXISTS idx_todo_triggers_status ON todo_triggers(status, due_at);
CREATE INDEX IF NOT EXISTS idx_todo_plans_todo ON todo_plans(task_id);
CREATE INDEX IF NOT EXISTS idx_todo_notes_todo ON todo_notes(task_id);
CREATE INDEX IF NOT EXISTS idx_todo_sessions_todo ON todo_sessions(task_id);
"""


def get_global_todos_db() -> sqlite.Connection:
    """返回 global_todos.db 的连接。自动建库 + schema。

    幂等：多次调用不会重复建表。Schema 改了在这里改，旧库重启时 patch。
    """
    db = sqlite.connect(str(_db_path()))
    db.row_factory = sqlite.Row
    # durability: WAL + FULL synchronous 防 WAL 半写损坏。
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("PRAGMA foreign_keys=ON")
    # 幂等迁移：老库没有这些列 → 补一次。新库由 schema 自动建。
    try:
        db.execute("ALTER TABLE todos ADD COLUMN acceptance_criteria TEXT DEFAULT ''")
    except Exception:
        pass  # 列已存在
    try:
        # detail = 详情记忆(增删改)；rest 前编辑、sense_todos board 渲染时模型可见
        db.execute("ALTER TABLE todos ADD COLUMN detail TEXT DEFAULT ''")
    except Exception:
        pass  # 列已存在
    try:
        # assignee_position = 分配的岗位名(architect/developer/trader)。
        # 2026-06-24 Phase 4 deliverables 表合并后引入——deliverables 原有这列,
        # todos 表此前缺失,合并后补齐。create_deliverable thin wrapper 到 create_task 时用它。
        db.execute("ALTER TABLE todos ADD COLUMN assignee_position TEXT DEFAULT ''")
    except Exception:
        pass  # 列已存在
    db.executescript(_SCHEMA_SQL)
    db.commit()
    return db


def global_todos_db_path() -> Path:
    """暴露 DB 文件路径，便于 backup / 测试。"""
    return _db_path()


__all__ = [
    "get_global_todos_db",
    "global_todos_db_path",
]
