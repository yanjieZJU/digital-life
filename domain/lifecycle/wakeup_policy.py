"""唤醒决策规则:从一批 due 事件中选出本次 wake 的 reason。

历史位置:``infrastructure/scheduler/cron_lifecycle.py`` 内联了同名逻辑。
为了 emit→wake 和 cron tick 都走**同一份优先级判断**(产品语义"事件平权"
的落地),抽到这里。

设计依据(docs/design 第 5.1 节 "事件平权"修订版):
- 所有 due 事件**平权**排队,按 (priority desc, tiebreak asc, event_id asc)
  三层比较选 reason。
- tiebreak 表的同优先级顺序固定:routine > message/group_message >
  awaiting_reply > timer > initiative > 其它。

历史 BUG(说明 tiebreak 为什么存在):
  08:00 morning_plan(routine) + timer 同时到期,pop_due_events 按 event_id
  ASC 返回 → events=[routine, timer],严格 > 让 timer 赢 → wake reason=timer,
  build_wake_prompt 走 timer 模板而非 routine 的 prompt_template → morning_plan
  的 "skill_view daily_planner" 等深度思考 skill 永远不注入。
"""

from __future__ import annotations

from typing import Any


# 同优先级 ties 的 tie-break:值越小越优先。
# 顺序就是"同优先级时哪种应该赢"——内容类事件优先于定时类。
_REASON_TIEBREAK: dict[str, int] = {
    "routine": 0,
    "group_message": 1,
    "message": 2,
    "awaiting_reply": 3,
    "timer": 4,
    "initiative": 5,
}


def choose_reason(events: list[dict[str, Any]]) -> str:
    """从一批 due 事件中选出本次 wake 的 reason。

    优先级取自 event_registry;缺失的事件类型默认 priority=5。
    同优先级时按 ``_REASON_TIEBREAK`` 表的顺序选(内容类 > 定时类)。

    Args:
        events: pop_due_events 的返回值,列表里每项至少有 ``kind`` 字段。

    Returns:
        本轮 wake 的 reason(事件 kind 字符串)。空列表 → "unknown"(理论上不会
        发生,调用方应当先过滤空集)。
    """
    if not events:
        return "unknown"

    # lazy import:避免 wakeup_policy ↔ event_registry ↔ events 之间的导入环
    try:
        from domain.lifecycle.event_registry import get_event_type
    except Exception:
        get_event_type = None  # type: ignore[assignment]

    reason = "unknown"
    top_priority = -1
    top_tiebreak = 10 ** 9

    for ev in events:
        kind = ev.get("kind", "") or ""
        try:
            td = get_event_type(kind) if get_event_type else None
            pri = td.priority if td else 5
        except Exception:
            pri = 5
        tb = _REASON_TIEBREAK.get(kind, 100)
        if pri > top_priority or (pri == top_priority and tb < top_tiebreak):
            top_priority = pri
            top_tiebreak = tb
            reason = kind

    return reason


__all__ = ["choose_reason"]
