"""HTTP 路由: 接收 peer 实例的广播消息。

仅在 master 进程的 HTTP server 上注册。worker 通过 HTTP POST 调用。
"""
from __future__ import annotations

import logging
from typing import Any

from aiohttp import web

logger = logging.getLogger(__name__)


async def _handle_broadcast(request: web.Request) -> web.Response:
    """POST /internal/message-broadcast

    Body(JSON):
        from_instance_id: 发送方实例 UUID
        from_display_name: 发送方 display_name(如 "zero")
        chat_id: 群/私聊 ID
        text: 消息文本
        msg_ref: 平台 msg_id(去重 key)
        source_platform: 源平台("lark"/"wechat"/...)

    不需要鉴权(仅内网 / 同机实例间调用)。
    """
    try:
        payload = await request.json()
    except Exception as exc:
        logger.warning("broadcast endpoint: bad json from %s: %s",
                       request.remote, exc)
        return web.json_response({"ok": False, "reason": f"bad json: {exc}"},
                                 status=400)
    try:
        from domain.messages.broadcast import receive_broadcast
        result = receive_broadcast(payload)
        # 访问日志——历史盲区: master log 全天没任何 broadcast 入站记录,
        # 因为只 INFO 了"注册成功",没记录每次 POST 调用。下面这行让 broadcast
        # 健康度可视化(成功/失败/送达数)
        from_short = (payload.get("from_instance_id") or "")[:8]
        chat_short = (payload.get("chat_id") or "")[:16]
        delivered = result.get("delivered", 0) if isinstance(result, dict) else "?"
        logger.info("broadcast in: from=%s chat=%s delivered=%s",
                    from_short, chat_short, delivered)
        return web.json_response(result,
                                 status=200 if result.get("ok") else 400)
    except Exception as exc:
        logger.exception("broadcast endpoint error: %s", exc)
        return web.json_response({"ok": False, "reason": str(exc)}, status=500)


def add_broadcast_routes(app: web.Application) -> None:
    """注册广播 endpoint 路由到 aiohttp app。"""
    app.router.add_post("/internal/message-broadcast", _handle_broadcast)
    logger.info("Broadcast endpoint registered: POST /internal/message-broadcast")
