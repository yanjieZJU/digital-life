"""会话中事件注入信号。

当 affair 为 RUNNING 状态时，cron tick 无法直接触发唤醒，
而是通过本模块将新事件注入到内存中，供正在运行的会话感知。

工作流程：
  1. cron_lifecycle._inject_events_to_running_session() → signal_new_events()
  2. sense_tools（sense_vitals/sense_time/sense_event_queue）→ consume_signalled_events() 读取并清除
  3. communication.check_before_send() → peek_signalled_events() 只读不清除，用于发送拦截

多实例隔离：
  事件按 instance_id 分桶存储（_pending_inject: dict[str, list[dict]]），
  防止实例 A 的事件被实例 B 消费。

与 DB 事件队列的关系：
  DB 事件队列（pop_due_events）是持久化的，跨进程存活。
  内存信号事件是瞬时的，只存在于 RUNNING 会话期间。
  communication.py 的 check_before_send 合并两路来源并去重。
"""
import threading

_lock = threading.Lock()
# Keyed by instance_id to isolate event pools between instances.
_pending_inject: dict[str, list[dict]] = {}


def _resolve_instance_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        from infrastructure.config import get_app_instance_id
        return get_app_instance_id()
    except Exception:
        import os as _os
        return _os.environ.get("DIGITAL_LIFE_INSTANCE_ID", "zero")


def signal_new_events(events: list[dict], *, instance_id: str | None = None) -> None:
    """批量写入新事件到内存队列，运行中会话的 sense 工具会拾取。"""
    _id = _resolve_instance_id(instance_id)
    with _lock:
        if _id not in _pending_inject:
            _pending_inject[_id] = []
        _pending_inject[_id].extend(events)


def consume_signalled_events_by_ids(event_ids: set[int], *, instance_id: str | None = None) -> list[dict]:
    """从内存队列中移除指定 event_id 的事件并返回它们。

    与 consume_signalled_events（清空全部）不同，此函数只移除指定 ID，
    其他事件保留在队列中不受影响。用于第 1 步拦截精确消费。
    """
    _id = _resolve_instance_id(instance_id)
    with _lock:
        remaining: list[dict] = []
        removed: list[dict] = []
        for ev in _pending_inject.get(_id, []):
            if ev.get("event_id") in event_ids:
                removed.append(ev)
            else:
                remaining.append(ev)
        _pending_inject[_id] = remaining
        return removed


def consume_signalled_events(*, instance_id: str | None = None) -> list[dict]:
    """读取并清空指定实例的信号事件（sense 工具调用）。"""
    _id = _resolve_instance_id(instance_id)
    with _lock:
        events = list(_pending_inject.get(_id, []))
        _pending_inject[_id] = []
        return events


def peek_signalled_events(*, instance_id: str | None = None) -> list[dict]:
    """只读信号事件（不清空），供 guard check 使用。"""
    _id = _resolve_instance_id(instance_id)
    with _lock:
        return list(_pending_inject.get(_id, []))
