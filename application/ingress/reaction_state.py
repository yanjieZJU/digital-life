"""Reaction 表情收条状态机 — 跨两个调用点传递 msg_id ↔ reaction_id。

两态收条（2026-07 简化：去掉入站即刻的 ✅）:
  入站收到 → 仅登记 msg_id（不加表情）
  wake 启动 LLM → 给所有已登记 msg_id 加 🤔 (THINKING)
  express_to_human 发送后 → 撤全部 🤔

历史背景：原为三态（入站 ✅ → 处理中 🤔 → 撤回）。但 ✅ 与 🤔 间隔过短
（emit 到 wake 通常 <1s），用户视觉上是个无意义的闪烁。去掉第一个 ✅，
只在真正开始处理时才出现 🤔，更清晰。

batch 多条消息:register/mark/clear 全部对 batch 内所有 msg_id 操作。
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time

logger = logging.getLogger(__name__)

# msg_id → {reaction_id, emoji, ts}
_REACTIONS: dict[str, dict] = {}
_EXPIRY_S = 3600
_ADAPTER = None


def register_adapter(adapter) -> None:
    global _ADAPTER
    _ADAPTER = adapter


def _gc() -> None:
    now = time.time()
    expired = [k for k, v in _REACTIONS.items() if now - v.get("ts", 0) > _EXPIRY_S]
    for k in expired:
        _REACTIONS.pop(k, None)


async def register_received(msg_id: str, adapter) -> None:
    """入站收到消息 → 仅登记 msg_id（不再加 ✅ 表情）。

    登记的 msg_id 供后续 `mark_all_processing` 加 🤔 用。adapter 参数保留
    向后兼容（历史调用方仍传），但本函数不再使用它。
    """
    if not msg_id:
        return
    _gc()
    if msg_id in _REACTIONS:
        return
    # 登记 msg_id，emoji 留空——尚未加任何表情
    _REACTIONS[msg_id] = {"reaction_id": "", "emoji": "", "ts": time.time()}
    logger.debug("msg_id %s registered (no emoji)", msg_id[:16])


async def mark_all_processing(adapter=None) -> None:
    """给所有已登记的 msg_id 加 🤔 (THINKING)。在 wake 真正启动 LLM 时调。

    2026-07 简化：去掉「先撤 ✅」步骤（入站已不再加 ✅）。这里直接给登记过
    的 msg_id 加 THINKING。若已加过 THINKING 则跳过（幂等）。
    """
    ad = adapter or _ADAPTER
    if ad is None or not hasattr(ad, "add_reaction"):
        return
    _gc()
    for msg_id, info in list(_REACTIONS.items()):
        # 已经加过 THINKING 的不重复加；空 emoji 或其它状态才加
        if info.get("emoji") == "THINKING":
            continue
        try:
            new_rid = await ad.add_reaction(msg_id, "THINKING")
            if new_rid:
                _REACTIONS[msg_id] = {"reaction_id": new_rid, "emoji": "THINKING", "ts": time.time()}
                logger.debug("🤔 set on %s", msg_id[:16])
        except Exception as exc:
            logger.debug("mark_processing on %s failed: %s", msg_id[:16], exc)


async def clear_all_reactions(adapter=None) -> None:
    """撤掉所有活跃表情(✅ 或 🤔)。express_to_human 发送成功后调。"""
    ad = adapter or _ADAPTER
    if ad is None or not hasattr(ad, "remove_reaction"):
        return
    for msg_id in list(_REACTIONS.keys()):
        info = _REACTIONS.pop(msg_id, None)
        if info and info.get("reaction_id"):
            try:
                await ad.remove_reaction(msg_id, info["reaction_id"])
                logger.debug("cleared %s on %s", info.get("emoji"), msg_id[:16])
            except Exception as exc:
                logger.debug("clear on %s failed: %s", msg_id[:16], exc)


# ── sync wrappers ──

def mark_all_processing_sync() -> None:
    if _ADAPTER is None:
        return
    def _run():
        try:
            asyncio.run(mark_all_processing())
        except Exception as exc:
            logger.debug("mark_all_processing_sync failed: %s", exc)
    threading.Thread(target=_run, daemon=True, name="reaction-mark").start()


def clear_all_reactions_sync() -> None:
    def _run():
        try:
            asyncio.run(clear_all_reactions())
        except Exception as exc:
            logger.debug("clear_all_reactions_sync failed: %s", exc)
    threading.Thread(target=_run, daemon=True, name="reaction-clear").start()
