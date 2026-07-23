"""Development complexity policy for capability gaps."""

from __future__ import annotations

from dataclasses import dataclass

from ..types import CapabilityGap


@dataclass(frozen=True)
class DevelopmentComplexity:
    use_speckit: bool
    reason: str = ""


class DevelopmentComplexityPolicy:
    def evaluate(self, gaps: list[CapabilityGap]) -> DevelopmentComplexity:
        if len(gaps) > 1:
            return DevelopmentComplexity(use_speckit=True, reason="multiple_capability_gaps")
        return DevelopmentComplexity(use_speckit=False, reason="single_capability_gap")


__all__ = ["DevelopmentComplexity", "DevelopmentComplexityPolicy"]
