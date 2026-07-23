"""Capability matching against a catalog."""

from __future__ import annotations

from ..types import CapabilityCheckResult
from .capability_models import CapabilityRegistry


class CapabilityMatcher:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    def match(self, required: list[str] | tuple[str, ...]) -> CapabilityCheckResult:
        return self._registry.check(required)

    def check(self, required: list[str] | tuple[str, ...]) -> CapabilityCheckResult:
        return self.match(required)


CapabilityChecker = CapabilityMatcher


__all__ = ["CapabilityChecker", "CapabilityMatcher"]
