"""Build typed message display views for the employee console."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MessageDisplayBlock:
    id: str
    kind: str
    title: str
    render_as: str
    content: Any
    display_scope: str
    collapsed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "render_as": self.render_as,
            "content": self.content,
            "display_scope": self.display_scope,
            "collapsed": self.collapsed,
        }


def _tool_call_name(call: dict[str, Any]) -> str:
    """Check if this message involves express_to_human."""
    if tool_name == "express_to_human":
        return True
    for call in tool_calls:
        name = _tool_call_name(call)
        if name == "express_to_human":
            return True
    return False


def _is_express_to_human(tool_calls: list[dict[str, Any]], tool_name: str | None) -> bool:
    """Check if this message involves express_to_human."""
    if tool_name == "express_to_human":
        return True
    for call in tool_calls:
        name = _tool_call_name(call)
        if name == "express_to_human":
            return True
    return False


@dataclass(frozen=True)
class MessageEventDisplayView:
    message_id: str
    role: str
    timestamp: str
    raw_content: str
    layout_side: str
    source: str = ""
    sender: str = ""
    channel: str = ""
    correlation_id: str = ""
    current_message: str = ""
    system_context: dict[str, Any] = field(default_factory=dict)
    waiting_state: str = ""
    recent_messages: list[str] = field(default_factory=list)
    recent_experiences: list[str] = field(default_factory=list)
    associative_memory: list[str] = field(default_factory=list)
    blocks: list[MessageDisplayBlock] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "role": self.role,
            "layout_side": self.layout_side,
            "timestamp": self.timestamp,
            "source": self.source,
            "sender": self.sender,
            "channel": self.channel,
            "correlation_id": self.correlation_id,
            "current_message": self.current_message,
            "system_context": self.system_context,
            "waiting_state": self.waiting_state,
            "recent_messages": self.recent_messages,
            "recent_experiences": self.recent_experiences,
            "associative_memory": self.associative_memory,
            "blocks": [block.to_dict() for block in self.blocks],
            "raw_content": self.raw_content,
        }


class MessageDisplayViewBuilder:
    """Convert persisted session rows into stable console display views."""

    def build(
        self,
        *,
        message_id: str,
        role: str,
        content: str,
        timestamp: str,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        tool_name: str | None = None,
    ) -> MessageEventDisplayView:
        raw = content or ""
        source = _source_for_role(role)
        layout_side = _layout_side(role)
        parsed = self._parse_user_message(raw) if role == "user" else {"current_message": raw}
        blocks = self._blocks_for_message(role, parsed, raw, tool_calls or [], tool_call_id, tool_name)
        return MessageEventDisplayView(
            message_id=message_id,
            role=role,
            timestamp=timestamp,
            raw_content=raw,
            layout_side=layout_side,
            source=source,
            current_message=str(parsed.get("current_message") or raw),
            system_context=dict(parsed.get("system_context") or {}),
            waiting_state=str(parsed.get("waiting_state") or ""),
            recent_messages=list(parsed.get("recent_messages") or []),
            recent_experiences=list(parsed.get("recent_experiences") or []),
            associative_memory=list(parsed.get("associative_memory") or []),
            blocks=blocks,
        )

    def _blocks_for_message(
        self,
        role: str,
        parsed: dict[str, Any],
        raw: str,
        tool_calls: list[dict[str, Any]],
        tool_call_id: str | None,
        tool_name: str | None,
    ) -> list[MessageDisplayBlock]:
        blocks: list[MessageDisplayBlock] = []

        # ── system prompt ──
        if role == "system":
            if raw.strip():
                blocks.append(MessageDisplayBlock(
                    "system_prompt", "system_prompt", "系统提示词",
                    "markdown", raw, "conversation",
                ))
            return blocks

        # ── user message (context fed to the model) ──
        if role == "user":
            if raw.strip():
                blocks.append(MessageDisplayBlock(
                    "user_input", "message", "用户输入 / 上下文",
                    "markdown", raw, "conversation",
                ))
            return blocks

        # ── assistant message ──
        if role == "assistant":
            visible = str(parsed.get("current_message") or raw).strip()
            if visible:
                blocks.append(MessageDisplayBlock(
                    "visible", "assistant_message", "模型输出",
                    "markdown", visible, "conversation",
                ))
            for index, call in enumerate(tool_calls):
                name = _tool_call_name(call)
                kind = "sent_message" if name == "express_to_human" else "tool_call"
                blocks.append(MessageDisplayBlock(
                    f"tool_call_{index}", kind,
                    f"{'发送消息' if kind == 'sent_message' else '工具调用'}: {name}",
                    "json", call, "conversation",
                ))
            if not visible and not tool_calls and raw.strip():
                blocks.append(MessageDisplayBlock(
                    "raw", "assistant_message", "模型输出",
                    "markdown", raw, "conversation",
                ))
            return blocks

        # ── tool result ──
        if role == "tool":
            name = tool_name or tool_call_id or "tool"
            kind = "sent_message" if _is_express_to_human([], tool_name) else "tool_result"
            blocks.append(MessageDisplayBlock(
                "tool_result", kind,
                f"{'发送消息' if kind == 'sent_message' else '工具结果'}: {name}",
                "markdown" if kind == "sent_message" else "plain",
                raw, "conversation",
            ))
            return blocks

        # ── fallback ──
        if raw.strip():
            blocks.append(MessageDisplayBlock(
                "raw", "system_prompt", "系统消息",
                "markdown", raw, "conversation",
            ))
        return blocks

    def _parse_user_message(self, content: str) -> dict[str, Any]:
        lines = content.replace("\r\n", "\n").split("\n")
        section = "current"
        # Suppress lines from current_message for sections that go into structured fields.
        # Avoids duplicate: content appears in both visible message and system_context fields.
        suppress_from_current = False
        current: list[str] = []
        system_context: dict[str, Any] = {
            "nurture_commands": {"description": [], "effects": {}, "response_rules": []},
            "notices": [],
            "follow_up_actions": [],
            "duplicate_rules": [],
        }
        recent_messages: list[str] = []
        recent_experiences: list[str] = []
        associative_memory: list[str] = []
        waiting_state = ""
        structured = False
        timestamp = ""

        for raw_line in lines:
            line = raw_line.strip()
            if line.lower() == "user":
                structured = True
                continue
            if line.startswith("[") and line.endswith("]") and "T" in line:
                timestamp = line.strip("[]")
                structured = True
                continue
            if line.startswith("## "):
                title = line[3:].strip().rstrip("：:")
                structured = True
                section, suppress_from_current = self._section_for_heading(title)
                continue
            if line.startswith("养育命令："):
                section = "nurture"
                suppress_from_current = True
                structured = True
                _push(system_context["nurture_commands"]["description"], line.replace("养育命令：", "").strip())
                continue
            if line.startswith("注意："):
                section = "notice"
                suppress_from_current = True
                structured = True
                _push(system_context["notices"], line.replace("注意：", "").strip())
                continue
            if line.startswith("感知消息"):
                section = "workflow"
                suppress_from_current = True
                structured = True
                _push(system_context["follow_up_actions"], line)
                continue
            if line.startswith("waiting for reply"):
                waiting_state = line
                section = "waiting"
                suppress_from_current = True
                structured = True
                continue
            if line.startswith("最近发送的消息："):
                section = "recent_messages"
                suppress_from_current = True
                structured = True
                continue
            if line.startswith("你最近的经历："):
                section = "recent_experiences"
                suppress_from_current = True
                structured = True
                continue
            if line.startswith("[联想记忆"):
                section = "associative_memory"
                suppress_from_current = True
                structured = True
                _push(associative_memory, line.strip("[]"))
                continue
            if line.startswith("[/联想记忆"):
                continue
            self._append_line(
                section,
                raw_line,
                system_context,
                current,
                recent_messages,
                recent_experiences,
                associative_memory,
                suppress_from_current,
            )
        current = _trim_blank(current)
        if not structured:
            current = [content]
        return {
            "timestamp": timestamp,
            "current_message": "\n".join(current).strip(),
            "system_context": _clean(system_context),
            "waiting_state": waiting_state,
            "recent_messages": _trim_blank(recent_messages),
            "recent_experiences": _trim_blank(recent_experiences),
            "associative_memory": _trim_blank(associative_memory),
        }

    @staticmethod
    def _section_for_heading(title: str) -> tuple[str, bool]:
        """Return (section_name, suppress_from_current).

        When suppress_from_current is True, subsequent lines are routed
        to a structured field and excluded from the visible current_message,
        preventing duplication.
        """
        if title in {"当前消息", "唤醒事件", "用户原话"}:
            return "current", False
        if title in {"执行要求", "后续动作", "行动流程"}:
            return "workflow", True
        if title in {"养育命令", "养育规则"}:
            return "nurture", True
        if title in {"注意", "注意事项"}:
            return "notice", True
        if title in {"当前等待状态", "等待状态"}:
            return "waiting", True
        if title in {"最近发送的消息", "最近发送"}:
            return "recent_messages", True
        if title in {"最近经历", "你最近的经历"}:
            return "recent_experiences", True
        if title in {"联想记忆", "Associative Memory"}:
            return "associative_memory", True
        if title in {"主动汇报策略", "主动汇报", "强制规则", "交互边界"}:
            return "workflow", True
        if title in {"待处理事件"}:
            return "workflow", True
        return "current", False

    def _append_line(
        self,
        section: str,
        raw_line: str,
        system_context: dict[str, Any],
        current: list[str],
        recent_messages: list[str],
        recent_experiences: list[str],
        associative_memory: list[str],
        suppress_from_current: bool = False,
    ) -> None:
        line = raw_line.strip()
        if section == "nurture":
            if line.startswith("「") and "」→" in line:
                left, right = line.split("」→", 1)
                system_context["nurture_commands"]["effects"][left.strip("「")] = right.strip()
            else:
                _push(system_context["nurture_commands"]["response_rules"], line)
            return
        if section == "notice":
            _push(system_context["notices"], line)
            return
        if section == "workflow":
            _push(system_context["follow_up_actions"], line)
            return
        if section == "recent_messages":
            if "|" in line and line[:4].isdigit():
                _push(recent_messages, line)
            else:
                _push(system_context["duplicate_rules"], line)
            return
        if section == "recent_experiences":
            recent_experiences.append(raw_line)
            return
        if section == "associative_memory":
            associative_memory.append(raw_line)
            return
        if section != "waiting" and not suppress_from_current:
            current.append(raw_line)


class MessageInspectorViewBuilder:
    """Build a stable read model for the right-side message inspector."""

    def build(
        self,
        *,
        message: dict[str, Any],
        display_view: MessageEventDisplayView | dict[str, Any],
        raw_content: str,
        original_length: int | None = None,
        truncated: bool = False,
    ) -> dict[str, Any]:
        display_payload = display_view.to_dict() if hasattr(display_view, "to_dict") else dict(display_view)
        role = str(message.get("role") or display_payload.get("role") or "")
        tool_calls = message.get("tool_calls") if isinstance(message.get("tool_calls"), list) else []
        blocks = display_payload.get("blocks") if isinstance(display_payload.get("blocks"), list) else []
        primary_text = self._primary_text(role, display_payload, raw_content, message)
        content_chars = len(primary_text)
        raw_length = original_length if original_length is not None else len(raw_content or "")
        tool_name = message.get("tool_name")
        tool_call_id = message.get("tool_call_id")
        kind = self._kind(role, tool_calls, tool_name, tool_call_id)

        return {
            "schema_version": 1,
            "summary": {
                "title": self._title(role, tool_name),
                "role": role,
                "time": message.get("ts") or display_payload.get("timestamp") or "",
                "kind": kind,
                "source": display_payload.get("source") or _source_for_role(role),
                "status": "ok",
            },
            "content": {
                "primary_text": primary_text,
                "content_preview": _preview(primary_text, 320),
                "truncated": bool(truncated),
                "raw_length": raw_length,
            },
            "metrics": {
                "blocks": len(blocks),
                "tool_calls": len(tool_calls),
                "content_chars": content_chars,
                "raw_chars": raw_length,
            },
            "tooling": {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "tool_calls": tool_calls,
                "tool_call_names": [_tool_call_name(call) for call in tool_calls],
            },
            "display": {
                "layout_side": display_payload.get("layout_side", ""),
                "blocks": self._block_summaries(blocks),
            },
            "raw": {
                "message": self._message_snapshot(message),
                "display_view": display_payload,
            },
        }

    @staticmethod
    def _primary_text(
        role: str,
        display_payload: dict[str, Any],
        raw_content: str,
        message: dict[str, Any],
    ) -> str:
        current = str(display_payload.get("current_message") or "").strip()
        if current:
            return current
        if role == "tool":
            name = message.get("tool_name") or message.get("tool_call_id") or "tool"
            text = str(raw_content or message.get("content") or "").strip()
            return f"{name}\n{text}" if text else str(name)
        return str(raw_content or message.get("content") or "").strip()

    @staticmethod
    def _title(role: str, tool_name: Any) -> str:
        if role == "assistant":
            return "员工回复"
        if role == "user":
            return "用户 / 系统上下文"
        if role == "tool":
            return f"工具结果 · {tool_name or 'tool'}"
        if role == "system":
            return "系统消息"
        return role or "消息"

    @staticmethod
    def _kind(role: str, tool_calls: list[dict[str, Any]], tool_name: Any, tool_call_id: Any) -> str:
        if role == "tool":
            return "tool_result"
        if tool_calls:
            return "assistant_with_tool_calls" if role == "assistant" else "message_with_tool_calls"
        if tool_name or tool_call_id:
            return "tool_related_message"
        return f"{role}_message" if role else "message"

    @staticmethod
    def _block_summaries(blocks: list[Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            content = block.get("content")
            result.append({
                "id": block.get("id", ""),
                "kind": block.get("kind", ""),
                "title": block.get("title", ""),
                "render_as": block.get("render_as", ""),
                "display_scope": block.get("display_scope", ""),
                "collapsed": bool(block.get("collapsed")),
                "preview": _preview(content, 180),
            })
        return result

    @staticmethod
    def _message_snapshot(message: dict[str, Any]) -> dict[str, Any]:
        return {
            key: message.get(key)
            for key in (
                "role",
                "content",
                "ts",
                "tool_calls",
                "tool_call_id",
                "tool_name",
            )
            if key in message
        }


def _layout_side(role: str) -> str:
    if role == "assistant":
        return "right"
    if role == "user":
        return "left"
    return "full_width"


def _source_for_role(role: str) -> str:
    if role == "assistant":
        return "agent"
    if role == "tool":
        return "tool_runtime"
    if role == "system":
        return "system"
    return "human"


def _tool_call_name(call: dict[str, Any]) -> str:
    function = call.get("function") if isinstance(call.get("function"), dict) else {}
    return str(function.get("name") or call.get("name") or call.get("tool_name") or call.get("type") or "tool")


def _push(target: list[str], value: str) -> None:
    text = str(value or "").strip()
    if text:
        target.append(text)


def _trim_blank(lines: list[str]) -> list[str]:
    copy = list(lines)
    while copy and not copy[0].strip():
        copy.pop(0)
    while copy and not copy[-1].strip():
        copy.pop()
    return copy


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            cleaned = _clean(item)
            if cleaned not in ({}, [], ""):
                result[key] = cleaned
        return result
    if isinstance(value, list):
        return [item for item in value if str(item).strip()]
    return value


def _preview(value: Any, limit: int) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        import json

        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


__all__ = [
    "MessageDisplayBlock",
    "MessageDisplayViewBuilder",
    "MessageEventDisplayView",
    "MessageInspectorViewBuilder",
]
