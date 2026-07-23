"""Employee console/debug HTTP request normalization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class EmployeeConsoleHttpInput:
    method: str
    path_params: Mapping[str, str] = field(default_factory=dict)
    query: Mapping[str, str] = field(default_factory=dict)
    body: Mapping[str, Any] = field(default_factory=dict)


class EmployeeConsoleHttpIngress:
    """Convert aiohttp requests into project-owned employee console workflow input."""

    async def normalize(self, request: Any) -> EmployeeConsoleHttpInput:
        body: Mapping[str, Any] = {}
        if request.can_read_body:
            try:
                parsed = await request.json()
                if isinstance(parsed, Mapping):
                    body = dict(parsed)
            except Exception:
                body = {}
        return EmployeeConsoleHttpInput(
            method=str(getattr(request, "method", "")),
            path_params=dict(getattr(request, "match_info", {}) or {}),
            query=dict(getattr(request, "query", {}) or {}),
            body=body,
        )


__all__ = ["EmployeeConsoleHttpIngress", "EmployeeConsoleHttpInput"]
