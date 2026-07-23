"""MVP orchestration policies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecKitPolicyDecision:
    use_speckit: bool
    reason: str


class MvpOrchestrationPolicy:
    """Small deterministic policies used by the MVP planners."""

    def speckit_decision(
        self,
        *,
        missing_capabilities: list[str] | tuple[str, ...],
        estimated_task_count: int = 0,
        touched_modules: int = 0,
        requires_formal_artifacts: bool = False,
    ) -> SpecKitPolicyDecision:
        if requires_formal_artifacts:
            return SpecKitPolicyDecision(True, "formal_artifacts_required")
        if len(missing_capabilities) > 1:
            return SpecKitPolicyDecision(True, "multiple_capability_gaps")
        if touched_modules > 1:
            return SpecKitPolicyDecision(True, "multiple_modules")
        if estimated_task_count > 5:
            return SpecKitPolicyDecision(True, "large_task_count")
        return SpecKitPolicyDecision(False, "simple_capability_gap")


__all__ = ["MvpOrchestrationPolicy", "SpecKitPolicyDecision"]
