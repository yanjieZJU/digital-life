"""Thin application use-case coordinator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import UseCaseRequest, UseCaseResponse


class UseCaseHandler(Protocol):
    def handle(self, request: UseCaseRequest) -> UseCaseResponse: ...


@dataclass
class UseCaseCoordinator:
    """Routes accepted requests to registered use-case handlers without owning domain rules."""

    handlers: dict[str, UseCaseHandler]

    def handle(self, request: UseCaseRequest) -> UseCaseResponse:
        handler = self.handlers.get(request.request_type)
        if handler is None:
            return UseCaseResponse(
                use_case_id=request.use_case_id,
                status="unsupported",
                message=f"unsupported use case: {request.request_type}",
            )
        return handler.handle(request)


__all__ = ["UseCaseCoordinator", "UseCaseHandler"]

