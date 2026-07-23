"""Ingress interactions layer: normalize external stimuli into project-owned input."""

from .contracts import (
    BaseEvent,
    InteractionInput,
    InteractionMessage,
    LLMMessage,
    MessageEvent,
)
from .cli import CliIngress
from .feedback import FeedbackIngress
from .normalizer import InteractionNormalizer
from .scheduler import SchedulerIngress
from .webhook import WebhookIngress

# FeishuMessageIngress moved here from the removed feishu/ subpackage
import json as _json
from typing import Any as _Any
from uuid import uuid4 as _uuid4


class FeishuMessageIngress:
    """Convert Feishu gateway message events into InteractionMessage."""

    def __init__(self, bot_app_id: str | None = None) -> None:
        self._bot_app_id = (bot_app_id or "").strip()

    def normalize(self, event: _Any) -> InteractionMessage:
        lark_msg = getattr(getattr(event, "event", None), "message", None)
        if lark_msg is not None:
            return self._normalize_lark_v2(event)
        return self._normalize_legacy(event)

    def _normalize_lark_v2(self, event: _Any) -> InteractionMessage:
        msg = event.event.message
        sender = event.event.sender

        chat_id = getattr(msg, "chat_id", "") or ""
        chat_type = getattr(msg, "chat_type", "p2p") or "p2p"
        message_id = getattr(msg, "message_id", "") or f"in_{_uuid4().hex}"

        raw_content = getattr(msg, "content", "") or ""
        text = raw_content
        if raw_content.startswith("{"):
            try:
                text = _json.loads(raw_content).get("text", raw_content)
            except (_json.JSONDecodeError, TypeError):
                pass

        sender_open_id = ""
        sender_obj = getattr(sender, "sender_id", None)
        if sender_obj:
            sender_open_id = getattr(sender_obj, "open_id", "") or ""
            if not sender_open_id:
                sender_open_id = getattr(sender_obj, "user_id", "") or ""

        metadata = {
            "external_channel": "feishu",
            "message_id": message_id,
            "chat_id": chat_id,
            "chat_name": "",
            "chat_type": chat_type,
            "is_group": chat_type == "group",
            "sender_id": sender_open_id,
            "sender_name": "",
            "mentions_bot": False,
        }
        if self._bot_app_id:
            metadata["bot_app_id"] = self._bot_app_id
        return InteractionMessage(
            message_id=message_id,
            actor_id=sender_open_id or chat_id,
            content=text,
            metadata=metadata,
            correlation_id=chat_id or None,
        )

    def _normalize_legacy(self, event: _Any) -> InteractionMessage:
        source = getattr(event, "source", None)
        raw_message = getattr(event, "raw_message", None)
        mentions_bot = False
        if raw_message:
            raw_content = getattr(raw_message, "content", "") or ""
            if "@_all" in raw_content:
                mentions_bot = True
            else:
                for mention in getattr(raw_message, "mentions", []) or []:
                    mention_id = getattr(mention, "id", None)
                    open_id = getattr(mention_id, "open_id", "") if mention_id else ""
                    if open_id:
                        mentions_bot = True
                        break

        chat_id = getattr(source, "chat_id", "") or "" if source else ""
        user_id = getattr(source, "user_id", "") or "" if source else ""
        message_id = getattr(event, "message_id", None) or f"in_{_uuid4().hex}"
        text = getattr(event, "text", "") or ""
        metadata = {
            "external_channel": "feishu",
            "message_id": message_id,
            "chat_id": chat_id,
            "chat_name": getattr(source, "chat_name", "") or "" if source else "",
            "chat_type": getattr(source, "chat_type", "dm") if source else "dm",
            "is_group": (getattr(source, "chat_type", "dm") == "group") if source else False,
            "sender_id": user_id,
            "sender_name": getattr(source, "user_name", "") or "" if source else "",
            "mentions_bot": mentions_bot,
        }
        if self._bot_app_id:
            metadata["bot_app_id"] = self._bot_app_id
        return InteractionMessage(
            message_id=message_id or "",
            actor_id=user_id or chat_id,
            content=text,
            metadata=metadata,
            correlation_id=chat_id or None,
        )

__all__ = [
    "CliIngress",
    "BaseEvent",
    "FeedbackIngress",
    "FeishuMessageIngress",
    "InteractionInput",
    "InteractionMessage",
    "InteractionNormalizer",
    "LLMMessage",
    "MessageEvent",
    "SchedulerIngress",
    "WebhookIngress",
]
