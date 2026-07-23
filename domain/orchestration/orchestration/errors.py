"""Orchestration-layer domain errors."""

from __future__ import annotations


class OrchestrationError(Exception):
    """Base error for orchestration planning failures."""


class PlanningBlockedError(OrchestrationError):
    """Raised when policy allows no executable or clarifying next step."""


__all__ = ["OrchestrationError", "PlanningBlockedError"]
