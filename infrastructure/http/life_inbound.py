"""Gateway inbound hook — feed human messages into the Digital Life pipeline.

挂载事件: agent:start

人类消息到达时设置 affair 上下文。实际的事件 emit 和 nurture 由 handler.py 完成。
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger("gateway.life-inbound")

_agent_root = str(Path(__file__).resolve().parents[2])
if _agent_root not in sys.path:
    sys.path.insert(0, _agent_root)


def _feed_life_pipeline(message: str, platform: str, user_id: str) -> None:
    """人类消息到达 → 设置 affair 上下文。"""
    try:
        try:
            from domain.orchestration.lifecycle_orchestration.bootstrap.runtime import _find_life_affair
            life_aid = _find_life_affair()
        except Exception:
            life_aid = None

        if not life_aid:
            return

        try:
            from domain.lifecycle.runtime_context import set_current_affair
            set_current_affair(life_aid)
        except Exception as e:
            logger.debug("set_current_affair failed: %s", e)

    except Exception as e:
        logger.warning("life-inbound hook failed (non-fatal): %s", e)


async def handle(event_type: str, context: dict) -> None:
    """agent:start handler."""
    if event_type != "agent:start":
        return

    message = context.get("message", "")
    platform = context.get("platform", "")
    user_id = context.get("user_id", "")

    if not message:
        return

    _feed_life_pipeline(message, platform, user_id)
