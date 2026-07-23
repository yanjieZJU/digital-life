"""Map task contracts to required runtime capabilities."""

from __future__ import annotations

from ..types import TaskContract


class CapabilityMapper:
    """Map a task contract into required capabilities.

    The default mapping is intentionally domain-neutral. Scenario-specific
    mappings should be injected by application/config adapters.
    """

    DEFAULT_MAPPINGS: dict[tuple[str, str], tuple[str, ...]] = {
        ("recurring_monitor", "*"): (
            "scheduler.recurring",
            "target.observe",
            "condition.evaluate",
            "notification.chat",
        ),
        ("reminder", "*"): ("scheduler.once", "notification.chat"),
        ("research", "*"): ("context.recall", "tool.search", "notification.chat"),
        ("one_shot", "*"): ("agent.run", "notification.chat"),
    }

    def __init__(self, mappings: dict[tuple[str, str], tuple[str, ...]] | None = None) -> None:
        self._mappings = dict(self.DEFAULT_MAPPINGS)
        if mappings:
            self._mappings.update(mappings)

    def map(self, contract: TaskContract) -> list[str]:
        key = (contract.type, contract.domain)
        fallback_key = (contract.type, "*")
        capabilities = self._mappings.get(key) or self._mappings.get(fallback_key)
        if capabilities:
            return list(capabilities)
        return ["agent.run", "notification.chat"]


__all__ = ["CapabilityMapper"]
