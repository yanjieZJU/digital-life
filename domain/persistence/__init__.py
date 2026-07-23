"""Per-instance persistence ports.

Domain lattice for who-talks-to-which-DB inside wakes and lifecycle hooks.
Defines the contracts ``scheduler`` / ``agent`` / lifecycle modules depend
on; concrete SQLite implementations live in
``infrastructure/persistence/instance/``.

The hour ports intentionally accept primitive types (dict / int / str),
not dataclasses — the persisted shape is itself a dict, and callers
should not have to wrap/unwrap on every insert.
"""

from __future__ import annotations

from typing import Any, Protocol


class AuditPort(Protocol):
    """Wake / turn / injection writer used by scheduler + agent.

    The audit DB is the only place that records "what the LLM actually
    saw and did". Reading from memory happens in memory_port.
    """

    instance_id: str

    def next_wake_seq(self) -> int: ...
    def create_wake(self, *, meta: dict[str, Any] | None = None) -> int: ...
    def end_wake(
        self,
        wake_id: int,
        *,
        meta_updates: dict[str, Any] | None = None,
    ) -> None: ...
    def get_wake(self, wake_id: int) -> dict[str, Any] | None: ...
    def list_wakes(
        self,
        *,
        chat_id: str | None = None,
        trigger_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...

    def append_turn(
        self,
        *,
        wake_id: int,
        wake_seq: int,
        llm_call_seq: int,
        role: str,
        content: str | None = None,
        position_in_call: int = 0,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        reasoning: str | None = None,
        finish_reason: str | None = None,
        token_count: int | None = None,
        chat_id: str | None = None,
        error: str | None = None,
    ) -> int: ...
    def list_turns(self, wake_id: int) -> list[dict[str, Any]]: ...

    def inject(
        self,
        *,
        wake_id: int,
        wake_seq: int,
        sys_tool: str,
        content: str,
        scope_id: str = "*",
        injected_before_call: int = 0,
        memory_refs: list[int] | dict[str, Any] | None = None,
    ) -> int: ...
    def list_injections(
        self,
        wake_id: int,
        *,
        before_call: int | None = None,
    ) -> list[dict[str, Any]]: ...

    def render_input_for_call(
        self,
        wake_id: int,
        call_seq: int,
        *,
        persona_loader: Any | None = None,
    ) -> list[dict[str, Any]]: ...


class MemoryPort(Protocol):
    """Slow-var current value + segment digest + chat facts + contacts."""

    instance_id: str

    # seg_digest
    def upsert_seg_digest(self, **fields: Any) -> int: ...
    def list_recent_seg_digests(
        self, *, layer: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]: ...

    # slow_var
    def set_slow_var(self, *, kind: str, content: str, scope_id: str = "*") -> int: ...
    def get_slow_var(self, kind: str, scope_id: str = "*") -> dict[str, Any] | None: ...
    def list_slow_vars(self, *, kind: str | None = None) -> list[dict[str, Any]]: ...

    # chat_fact
    def append_chat_fact(
        self,
        *,
        chat_id: str,
        speaker: str,
        text: str | None = None,
        speaker_name: str | None = None,
        payload: dict[str, Any] | None = None,
        said_at: float | None = None,
        source_ref: str | None = None,
    ) -> int: ...
    def list_chat_facts(
        self,
        chat_id: str,
        *,
        limit: int = 50,
        speaker: str | None = None,
    ) -> list[dict[str, Any]]: ...

    # contact
    def upsert_contact(
        self,
        contact_id: str,
        *,
        name: str | None = None,
        kind: str = "human",
        notes: str | None = None,
        blocked: bool | None = None,
        block_reason: str | None = None,
    ) -> str: ...
    def get_contact(self, contact_id: str) -> dict[str, Any] | None: ...
    def find_by_platform(self, platform: str, platform_id: str) -> dict[str, Any] | None: ...
    def link_platform(self, contact_id: str, platform: str, platform_id: str) -> None: ...
    def list_contacts(self, *, kind: str | None = None) -> list[dict[str, Any]]: ...

    # nurture_log
    def log_nurture(
        self,
        *,
        kind: str,
        deltas: dict[str, float] | None = None,
        raw_text: str | None = None,
        source: str | None = None,
    ) -> int: ...
    def list_nurture(self, limit: int = 50) -> list[dict[str, Any]]: ...


class VitalsPort(Protocol):
    """Energy state machine; single row per instance."""

    instance_id: str

    def snapshot(self) -> dict[str, Any]: ...
    def adjust_energy(
        self,
        delta: float,
        *,
        reason: str | None = None,
        source_ref: str | None = None,
    ) -> float: ...
    def set_energy(self, value: float, *, reason: str | None = None) -> float: ...
    def set_last_nurture(self, note: str) -> None: ...
    def list_log(self, limit: int = 50) -> list[dict[str, Any]]: ...


class WorkflowPort(Protocol):
    """Engine plumbing: events / timers / affairs / flow logs."""

    instance_id: str

    def enqueue_event(
        self,
        channel: str,
        payload: dict[str, Any],
        *,
        kind: str | None = None,
        fire_at: str | None = None,
    ) -> int: ...
    def claim_next_event(self, channel: str) -> dict[str, Any] | None: ...

    def arm_timer(
        self,
        event_kind: str,
        fire_at: str,
        payload: dict[str, Any] | None = None,
    ) -> int: ...
    def fire_due_timers(self, *, now_iso: str | None = None) -> list[dict[str, Any]]: ...

    def upsert_affair(self, **fields: Any) -> str: ...
    def list_affairs(self, *, status: str | None = None) -> list[dict[str, Any]]: ...


__all__ = [
    "AuditPort",
    "MemoryPort",
    "VitalsPort",
    "WorkflowPort",
]
