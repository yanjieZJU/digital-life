"""Ingress check contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping


@dataclass(frozen=True)
class CheckDecision:
    decision_id: str
    input_id: str
    status: str
    reasons: tuple[str, ...] = ()
    sanitized_payload: Mapping[str, object] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def accepted(self) -> bool:
        return self.status in {"accepted", "sanitized"}


__all__ = ["CheckDecision"]
