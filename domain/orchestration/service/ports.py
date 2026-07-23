"""Ports used by the orchestration layer."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from ..capability import Capability


class LLMPlanningPort(Protocol):
    def complete(self, prompt: str, *, context: Mapping[str, Any] | None = None) -> str: ...


class CapabilityCatalogPort(Protocol):
    def list_capabilities(self) -> tuple[Capability, ...]: ...


class PromptTemplatePort(Protocol):
    def get_template(self, name: str) -> str: ...


class OrchestrationArtifactPort(Protocol):
    def write_artifact(self, path: str, content: str) -> str: ...


__all__ = [
    "CapabilityCatalogPort",
    "LLMPlanningPort",
    "OrchestrationArtifactPort",
    "PromptTemplatePort",
]
