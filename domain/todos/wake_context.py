"""wake_context — 向后兼容 shim。

历史用途：sense_todos / sense_work / heartbeat 各自通过 get_wake_context()
获取任务看板渲染。这套渲染在 2026-06-14 重构时被 domain/todos/board.py::render_my_board
取代（它直接基于 global_todos.todos 实体，包括 description / acceptance_criteria
/ notes / plans，且单一渲染入口）。

这里保留 get_wake_context 名字，但内部透传给 render_my_board，避免破坏现有
调用方（heartbeat.py / tools.py / sense_tools.py / 测试）。
"""

from __future__ import annotations

from typing import Any


def get_wake_context() -> str:
    """渲染当前实例的待办面板。

    旧名字 → 现在 = render_my_board() 的等价入口。
    保持无参（旧调用方不传 iid/now_dt）。内部自己取当前实例 + 当前时间。
    """
    try:
        from domain.lifecycle import clock
        from infrastructure.config import get_app_instance_id
        from domain.todos.board import render_my_board
        iid = get_app_instance_id() or ""
        return render_my_board(iid, clock.now_dt()) if iid else ""
    except Exception as e:
        import logging
        logging.getLogger("digital_life.domain.todos").debug(
            "get_wake_context render failed: %s", e
        )
        return ""


__all__ = ["get_wake_context"]
