"""Project infrastructure: 物理目录 + (legacy) DB 入口。

Phase 4 (2026-06-24) 之后,**todos 不再写在项目 DB 里**。所有 todo 全在
`data/global_todos.db.todos`,本项目依次通过 `linked_deliverable_id != ''`
和 `project_id` 字段反向定位。

`get_project_db(project_id)` 保留为 thin wrapper 转发到
`global_todos.get_global_todos_db()`,让 老 caller 拿到一个能用的连接
- 它读 `todos` 表(不是项目本地表)。老 caller 内部的 SQL(查 deliverables/
project_todos)会抛 `no such table`,这是预期 — 让 caller 修。但拿连接本身不报错。

物理文件目录 `deliverables_dir` (projects/<pid>/deliverables/) 是真实交付物
文件存放,跟 todos 无关,保留。
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("digital_life.domain.project")


def _project_dir(project_id: str) -> Path:
    return Path(__file__).resolve().parents[2] / "projects" / project_id


def _db_path(project_id: str) -> Path:
    """旧项目 db 路径——Phase 4 后不再使用,保留作迁移历史查询。"""
    return _project_dir(project_id) / "data" / "todos.db"


def get_project_db(project_id: str):
    """⚠ Phase 4:转发到 global_todos.db。

    旧 caller 期望拿到一个 connection 操作 'deliverables' / 'project_todos' 表,
    Phase 4 后这些表都不存在了——global `todos` 表才是单一真相。

    返回 global_todos.db 的连接,callers 应当迁移到 `crud.list_deliverables`
    / `list_tasks(project_id=...)` 等 thin wrapper(它们已封装 global_db 路径)。
    """
    from infrastructure.persistence.global_todos import get_global_todos_db
    return get_global_todos_db()


def project_dir(project_id: str) -> Path:
    """项目目录 projects/<pid>/。"""
    return _project_dir(project_id)


def deliverables_dir(project_id: str) -> Path:
    """物理交付物文件目录 projects/<pid>/deliverables/。

    注意:这是**文件目录**,不是 todos 数据表。project_deliver 工具存
    HTML / pdf / 报告等物理交付物用。Phase 4 不动这部分。
    """
    p = _project_dir(project_id) / "deliverables"
    p.mkdir(parents=True, exist_ok=True)
    return p
