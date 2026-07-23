"""Affair and wait-intent lifecycle contracts.

These are pure execution_layer models. Hermes keeps the SQLite repository shell
until the persistence adapter is fully extracted.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from ..clock import now_iso
from ..state_machine import AffairStatus, WaitType


@dataclass
class WaitIntent:
    wait_type: WaitType
    resume_when: str
    reason: str = ""
    resume_action: str = ""
    interval_seconds: Optional[int] = None
    max_wait_until: Optional[str] = None
    blocked_at: str = field(default_factory=now_iso)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_row(self, affair_id: str) -> Dict[str, Any]:
        return {
            "affair_id": affair_id,
            "wait_type": self.wait_type.value if isinstance(self.wait_type, WaitType) else str(self.wait_type),
            "resume_when": self.resume_when,
            "interval_seconds": self.interval_seconds,
            "max_wait_until": self.max_wait_until,
            "reason": self.reason,
            "resume_action": self.resume_action,
            "blocked_at": self.blocked_at,
            "meta_json": json.dumps(self.meta, ensure_ascii=False),
        }

    @classmethod
    def from_row(cls, row) -> "WaitIntent":
        return cls(
            wait_type=WaitType(row["wait_type"]),
            resume_when=row["resume_when"],
            reason=row["reason"] or "",
            resume_action=row["resume_action"] or "",
            interval_seconds=row["interval_seconds"],
            max_wait_until=row["max_wait_until"],
            blocked_at=row["blocked_at"],
            meta=json.loads(row["meta_json"] or "{}"),
        )


@dataclass
class Affair:
    affair_id: str
    goal: str
    status: AffairStatus = AffairStatus.PENDING
    priority: int = 0
    deadline: Optional[str] = None
    session_id: Optional[str] = None
    mental_context: str = ""
    history_digest: str = ""
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    completed_at: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:12]

    def to_row(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value if isinstance(self.status, AffairStatus) else str(self.status)
        data["meta_json"] = json.dumps(data.pop("meta"), ensure_ascii=False)
        return data

    @classmethod
    def from_row(cls, row) -> "Affair":
        return cls(
            affair_id=row["affair_id"],
            goal=row["goal"],
            status=AffairStatus(row["status"]),
            priority=row["priority"],
            deadline=row["deadline"],
            session_id=row["session_id"],
            mental_context=row["mental_context"] or "",
            history_digest=row["history_digest"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
            meta=json.loads(row["meta_json"] or "{}"),
        )


def normalize_affair_update_fields(fields: Dict[str, Any], updated_at: str) -> Dict[str, Any]:
    """Normalize caller fields for the legacy affairs table update."""
    normalized = dict(fields)
    normalized["updated_at"] = updated_at
    if "status" in normalized and isinstance(normalized["status"], AffairStatus):
        normalized["status"] = normalized["status"].value
    if "meta" in normalized:
        normalized["meta_json"] = json.dumps(normalized.pop("meta"), ensure_ascii=False)
    return normalized


__all__ = ["Affair", "WaitIntent", "normalize_affair_update_fields"]
