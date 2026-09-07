"""Self-cognition slow variable — the crystallized self that governs wake.

This is the constitution layer's governance slot. Stable stances distilled
from autonomous world-encounter reactions during dream are written to the
``slow_var`` table (kind=``self_cognition``) and injected into the wake
slow-context, so the agent's first-thought carries "who I am" — not just
"what I did" (session digest) or "what I'm asked to do" (user events).

Read and write are paired here on purpose. Both callers — wake assembly
(read) and dream crystallization (write) — share this module, so the slot
is never written without a reader. This avoids the write-only-field
redundancy cleaned up in commit b88f624 (``last_accessed`` was written on
every recall but read by no path).

The ``slow_var`` table + ``MemoryPort.set_slow_var``/``get_slow_var`` port
already existed but had no production caller (only a smoke test). This
module is the first production reader/writer.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from infrastructure.persistence.instance.memory import MemoryDB

# The slow_var ``kind`` for the crystallized self. Coexists with other
# slow vars (consciousness residue, social relationships, task board).
SELF_COGNITION_KIND = "self_cognition"
SELF_COGNITION_SCOPE = "*"

_db_cache: MemoryDB | None = None


@dataclass
class Stance:
    """One crystallized stance — a stable way the agent relates to a topic.

    A stance is *earned*: it emerges only after multiple encounter-reactions
    point the same way (see dream crystallization). It is not a declared
    opinion or a compliance rule.
    """

    topic: str
    stance: str
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class SelfCognition:
    """The crystallized self — what the agent has become through experience.

    Distinct from persona (assigned initial params) and from
    ``SELF_KNOWLEDGE.md`` (observational self-description). This is the
    self-as-subject that governs future action.
    """

    summary: str
    stances: list[Stance] = field(default_factory=list)
    last_crystallized_at: str = ""
    source_encounter_count: int = 0

    def serialize(self) -> str:
        """Serialize to the JSON string stored in ``slow_var.content``."""
        data = asdict(self)
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def parse(cls, content: str | None) -> SelfCognition | None:
        """Parse ``slow_var.content`` back into a ``SelfCognition``.

        Returns ``None`` for empty/missing/unparseable content rather than
        raising — wake assembly must degrade gracefully when no self has
        crystallized yet (the common case before dream runs).
        """
        if not content:
            return None
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        stances = [
            Stance(
                topic=str(s.get("topic", "")),
                stance=str(s.get("stance", "")),
                evidence_refs=list(s.get("evidence_refs", []) or []),
            )
            for s in (data.get("stances") or [])
            if isinstance(s, dict)
        ]
        return cls(
            summary=str(data.get("summary", "")),
            stances=stances,
            last_crystallized_at=str(data.get("last_crystallized_at", "")),
            source_encounter_count=int(data.get("source_encounter_count", 0) or 0),
        )


def _get_db() -> MemoryDB:
    """Lazily build and cache the per-instance ``MemoryDB``.

    ``MemoryDB.__init__`` applies the ``slow_var`` schema (idempotent
    ``CREATE TABLE IF NOT EXISTS``) and opens a WAL connection. Cached so
    repeated wake reads don't reopen the file.
    """
    global _db_cache
    if _db_cache is None:
        _db_cache = MemoryDB()
    return _db_cache


def read_self_cognition() -> SelfCognition | None:
    """Read the crystallized self, or ``None`` if nothing has crystallized.

    Shared by wake assembly (governance injection) and by dream (to compare
    against the existing self before deciding whether to revise). Never
    raises on a missing/empty slot — callers depend on the graceful
    fallback (digest-only wake).
    """
    try:
        row = _get_db().get_slow_var(SELF_COGNITION_KIND, SELF_COGNITION_SCOPE)
    except Exception:
        return None
    if not row:
        return None
    return SelfCognition.parse(row.get("content"))


def write_self_cognition(cognition: SelfCognition) -> None:
    """Persist the crystallized self to the ``self_cognition`` slow var.

    Called by dream crystallization only when a stable pattern was found —
    never to manufacture a self from nothing (see spec: "无稳定模式不结晶").
    """
    _get_db().set_slow_var(
        kind=SELF_COGNITION_KIND,
        content=cognition.serialize(),
        scope_id=SELF_COGNITION_SCOPE,
    )


def render_self_cognition_section(cognition: SelfCognition | None) -> str:
    """Render the crystallized self as a prompt section, or '' if none.

    Wake assembly appends this as a ``_sys_tool=self_cognition`` block.
    Empty string means "no self has crystallized yet" — caller skips
    injection entirely (graceful digest-only fallback).
    """
    if not cognition or not cognition.summary:
        return ""
    lines = ["[我的自我认知 — 经验结晶]\n", cognition.summary]
    if cognition.stances:
        lines.append("")
        for s in cognition.stances:
            lines.append(f"· {s.topic}：{s.stance}")
    lines.append("[/我的自我认知]")
    return "\n".join(lines)


def reset_db_cache_for_tests(db: MemoryDB | None) -> None:
    """Test hook: inject/clear the cached MemoryDB so tests control state."""
    global _db_cache
    _db_cache = db


__all__ = [
    "SELF_COGNITION_KIND",
    "SELF_COGNITION_SCOPE",
    "Stance",
    "SelfCognition",
    "read_self_cognition",
    "write_self_cognition",
    "render_self_cognition_section",
    "reset_db_cache_for_tests",
]
