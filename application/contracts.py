"""Application use-case contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class UseCaseRequest:
    use_case_id: str
    request_type: str
    actor: str
    payload: Mapping[str, object] = field(default_factory=dict)
    idempotency_key: str | None = None
    permission_outcome: str = "unknown"
    transaction_scope: str = "none"
    response_policy: str = "default"


@dataclass(frozen=True)
class UseCaseResponse:
    use_case_id: str
    status: str
    payload: Mapping[str, object] = field(default_factory=dict)
    message: str = ""


@dataclass(frozen=True)
class UseCaseResult:
    payload: Mapping[str, object] = field(default_factory=dict)
    status_code: int = 200


__all__ = ["UseCaseRequest", "UseCaseResponse", "UseCaseResult"]
