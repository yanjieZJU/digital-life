"""会话已查看通道账本。

记录「某个 session 在本次唤醒生命周期中实际查看过哪些通道（chat_id）的历史」。
express_to_human 发送消息前会查这本账：目标通道若未查看，先拦截并补历史。

信息来源（任一发生即登记）：
  1. scheduler 注入 chat_stream —— wake 入口系统自动给模型看的近 N 条流水
  2. sense_conversation 工具 —— 模型主动调「查看对话历史」
  3. check_before_send 拦截补历史 —— 发送被拦后系统补的近期流水

存储：
  纯内存，按 session_id 分桶（dict[str, set[str]]）+ threading.Lock。
  与 session_events.py 同构，重启即丢——「本次 session 看过」本就是短命信息，
  每轮 wake 系统会重新注入 chat_stream 自动刷新标记，无需持久化。

续接语义：
  session 续接（15 min 内连续唤醒）会复用同一 session_id，故 viewed 集合自然继承；
  新 session_id 的桶由首次 mark 创建，老 session 的桶残留无害（重启清空）。
"""
from __future__ import annotations

import threading

_lock = threading.Lock()
# Keyed by session_id: 每个 session 看过哪些通道（chat_id 去重）。
_viewed_channels: dict[str, set[str]] = {}


def _resolve_session_id(explicit: str | None) -> str:
    """解析当前 session_id：显式传入优先，否则回退到 contextvar。"""
    if explicit:
        return explicit
    try:
        from infrastructure.config import get_current_session_id
        return get_current_session_id() or ""
    except Exception:
        return ""


def mark_channel_viewed(chat_id: str, *, session_id: str = "") -> None:
    """登记「本 session 查看过通道 chat_id 的历史」。

    幂等：重复 mark 同一 (session_id, chat_id) 无副作用（set 去重）。
    chat_id 为空或 session_id 解析为空时跳过（无意义）。
    """
    if not chat_id:
        return
    sid = _resolve_session_id(session_id)
    if not sid:
        return
    with _lock:
        bucket = _viewed_channels.setdefault(sid, set())
        bucket.add(chat_id)


def has_viewed_channel(chat_id: str, *, session_id: str = "") -> bool:
    """查账：本 session 是否查看过通道 chat_id 的历史。

    chat_id 或 session_id 解析为空时返回 True（放行）——
    无法判定目标时不应阻塞发送（空目标另有 express_to_human 的拒绝逻辑兜底）。
    """
    if not chat_id:
        return True
    sid = _resolve_session_id(session_id)
    if not sid:
        return True
    with _lock:
        return chat_id in _viewed_channels.get(sid, set())


def reset_for_session(session_id: str) -> None:
    """清空某 session 的已查看记录（正常路径不需要主动调用，保留备用）。"""
    if not session_id:
        return
    with _lock:
        _viewed_channels.pop(session_id, None)
