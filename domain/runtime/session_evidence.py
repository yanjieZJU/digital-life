"""Adapter-neutral session evidence helpers.

Task completion logic needs to know whether an agent actually executed work and
sent a user-facing reply. The domain should not know how a concrete adapter
stores chat messages, tool calls, or delivery receipts, so this module exposes a
small evidence reader protocol plus an in-memory receipt store.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable, Protocol


DEFAULT_EXECUTION_TOOL_NAMES = {
    "terminal",
    "web_search",
    "web_extract",
    "execute_code",
    "browser_navigate",
    "browser_click",
    "browser_type",
    "browser_snapshot",
}


class SessionEvidenceReader(Protocol):
    def has_sent_human_reply(self, session_id: str | None) -> bool:
        """Return true when the session delivered a user-facing response."""

    def has_successful_execution_tool(self, session_id: str | None) -> bool:
        """Return true when the session successfully used an execution tool."""

    def has_execution_attempt(self, session_id: str | None) -> bool:
        """Return true when the session attempted an execution tool."""


class NullSessionEvidenceReader:
    def has_sent_human_reply(self, session_id: str | None) -> bool:
        return False

    def has_successful_execution_tool(self, session_id: str | None) -> bool:
        return False

    def has_execution_attempt(self, session_id: str | None) -> bool:
        return False


class InMemorySessionEvidenceStore:
    def __init__(
        self,
        *,
        now_iso: Callable[[], str],
        execution_tool_names: Iterable[str] = DEFAULT_EXECUTION_TOOL_NAMES,
        fallback: SessionEvidenceReader | None = None,
    ) -> None:
        self._now_iso = now_iso
        self._execution_tool_names = set(execution_tool_names)
        self._fallback: SessionEvidenceReader = fallback or NullSessionEvidenceReader()
        self._reply_receipts: dict[str, dict[str, Any]] = {}
        self._execution_receipts: dict[str, list[dict[str, Any]]] = {}

    def set_fallback(self, fallback: SessionEvidenceReader) -> None:
        self._fallback = fallback

    def record_human_reply(
        self,
        session_id: str | None,
        *,
        sent: bool,
        text: str = "",
        channel: str = "",
        error: str | None = None,
    ) -> None:
        if not session_id:
            return
        self._reply_receipts[str(session_id)] = {
            "sent": bool(sent),
            "text": str(text or "")[:500],
            "channel": str(channel or ""),
            "error": str(error or "") if error else "",
            "recorded_at": self._now_iso(),
        }

    def record_execution_tool(
        self,
        session_id: str | None,
        *,
        tool_name: str,
        success: bool,
        summary: str = "",
    ) -> None:
        if not session_id or tool_name not in self._execution_tool_names:
            return
        self._execution_receipts.setdefault(str(session_id), []).append(
            {
                "tool_name": tool_name,
                "success": bool(success),
                "summary": str(summary or "")[:500],
                "recorded_at": self._now_iso(),
            }
        )

    def has_sent_human_reply(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        receipt = self._reply_receipts.get(str(session_id))
        if receipt and receipt.get("sent"):
            return True
        return self._fallback.has_sent_human_reply(str(session_id))

    def has_successful_execution_tool(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        receipts = self._execution_receipts.get(str(session_id)) or []
        if any(item.get("success") for item in receipts):
            return True
        return self._fallback.has_successful_execution_tool(str(session_id))

    def has_execution_attempt(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        if self._execution_receipts.get(str(session_id)):
            return True
        return self._fallback.has_execution_attempt(str(session_id))


def parse_tool_calls(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return []
    if isinstance(raw, list):
        calls = raw
    else:
        try:
            calls = json.loads(str(raw))
        except Exception:
            return []
    if not isinstance(calls, list):
        return []
    return [call for call in calls if isinstance(call, dict)]


def collect_tool_call_ids(rows: Iterable[Any], tool_names: set[str]) -> set[str]:
    call_ids: set[str] = set()
    for row in rows:
        if _row_get(row, "role") != "assistant":
            continue
        for call in parse_tool_calls(_row_get(row, "tool_calls")):
            function = call.get("function") or {}
            if function.get("name") in tool_names and call.get("id"):
                call_ids.add(str(call["id"]))
    return call_ids


def session_has_tool_attempt(rows: Iterable[Any], tool_names: set[str]) -> bool:
    for row in rows:
        if _row_get(row, "role") != "assistant":
            continue
        for call in parse_tool_calls(_row_get(row, "tool_calls")):
            function = call.get("function") or {}
            if function.get("name") in tool_names:
                return True
    return False


def tool_result_sent(content: Any) -> bool:
    text = _jsonish_text(content)
    if not text:
        return False
    try:
        payload = json.loads(text)
    except Exception:
        return '"sent": true' in text.lower()
    return isinstance(payload, dict) and payload.get("sent") is True


def tool_result_success(content: Any) -> bool:
    text = _jsonish_text(content)
    if not text:
        return False
    try:
        payload = json.loads(text)
    except Exception:
        lowered = text.lower()
        return "error" not in lowered and "traceback" not in lowered
    if isinstance(payload, dict):
        if payload.get("error"):
            return False
        if payload.get("ok") is False:
            return False
        if payload.get("success") is False:
            return False
    return True


def _jsonish_text(content: Any) -> str:
    text = str(content or "").strip()
    first_json = text.find("{")
    if first_json > 0:
        text = text[first_json:]
    return text


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return getattr(row, key, default)
