"""Task management domain module.

Provides task CRUD, plans, notes, session tracking, wake context,
momentum detection, scheduling, speckit integration, and tool registration.
"""

from ._infra import configure_runtime_hooks
from .core.constants import CN_PRIORITIES, VALID_PRIORITIES, VALID_STATUSES
from .core.models import Task, TaskNote, TaskPlan, find_similar_task, row_to_task, task_to_dict
from .crud import (
    create_task, list_tasks, get_task, update_task, search_tasks,
    create_plan, list_plans, complete_plan, skip_plan, update_plan,
    add_note, read_notes,
    create_todo, list_todos, get_todo, update_todo, delete_todo, cancel_todos_by_task,
    resolve_skill_for_task_type, resolve_skill_for_current_task,
)
from .session_tracking import (
    record_session_human_reply,
    record_session_execution_tool,
    session_has_execution_attempt,
    completion_ready,
    on_session_end,
)
from .wake_context import get_wake_context
from .scheduler import schedule_task_wakeup, schedule_plan_event, on_status_change, on_tick, check_task_momentum
from .speckit import attach_speckit_plan
from .board import render_my_board
from .tools import register_task_tools

__all__ = [
    "CN_PRIORITIES",
    "VALID_PRIORITIES",
    "VALID_STATUSES",
    "Task",
    "TaskNote",
    "TaskPlan",
    "attach_speckit_plan",
    "complete_plan",
    "completion_ready",
    "configure_runtime_hooks",
    "create_plan",
    "create_task",
    "create_todo",
    "cancel_todos_by_task",
    "delete_todo",
    "find_similar_task",
    "get_task",
    "get_todo",
    "get_wake_context",
    "list_plans",
    "list_tasks",
    "list_todos",
    "add_note",
    "read_notes",
    "on_session_end",
    "on_status_change",
    "on_tick",
    "record_session_execution_tool",
    "record_session_human_reply",
    "register_task_tools",
    "render_my_board",
    "row_to_task",
    "schedule_plan_event",
    "schedule_task_wakeup",
    "search_tasks",
    "session_has_execution_attempt",
    "skip_plan",
    "task_to_dict",
    "update_plan",
    "update_task",
    "update_todo",
    "resolve_skill_for_task_type",
    "resolve_skill_for_current_task",
    "check_task_momentum",
]
