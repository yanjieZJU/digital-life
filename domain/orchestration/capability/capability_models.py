"""Capability models and registry for orchestration planning."""

from __future__ import annotations

from ..types import Capability, CapabilityCheckResult, CapabilityGap, CapabilityMatchResult


class CapabilityRegistry:
    """In-memory capability registry for the orchestration MVP."""

    def __init__(self, capabilities: list[Capability] | tuple[Capability, ...] = ()) -> None:
        self._capabilities: dict[str, Capability] = {}
        for capability in capabilities:
            self.register(capability)

    def register(self, capability: Capability) -> None:
        self._capabilities[capability.id] = capability

    def get(self, capability_id: str) -> Capability | None:
        return self._capabilities.get(capability_id)

    def list(self) -> tuple[Capability, ...]:
        return tuple(self._capabilities.values())

    def check(self, required: list[str] | tuple[str, ...]) -> CapabilityCheckResult:
        available: list[str] = []
        missing: list[str] = []
        partial: list[str] = []
        for capability_id in required:
            capability = self.get(capability_id)
            if capability is None or capability.status in {"missing", "disabled"}:
                missing.append(capability_id)
            elif capability.status == "partial":
                partial.append(capability_id)
                missing.append(capability_id)
            else:
                available.append(capability_id)
        return CapabilityCheckResult(ok=not missing, available=available, missing=missing, partial=partial)


__all__ = [
    "Capability",
    "CapabilityCheckResult",
    "CapabilityGap",
    "CapabilityMatchResult",
    "CapabilityRegistry",
]
