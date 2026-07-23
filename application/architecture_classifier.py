"""Small classifier used by migration tests and architecture review tooling."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .architecture_layers import LayerName, classify_path, get_layer_rule


@dataclass(frozen=True)
class ClassificationResult:
    path: str
    primary_layer: LayerName
    rationale: str
    allowed_downstream_layers: tuple[LayerName, ...] = field(default_factory=tuple)
    violations: tuple[str, ...] = field(default_factory=tuple)


class ArchitectureClassifier:
    """Classify planned files or changes into the target architecture."""

    def classify(self, path: str | Path, description: str = "") -> ClassificationResult:
        layer = classify_path(path)
        rule = get_layer_rule(layer)
        violations: list[str] = []
        text = description.lower()

        if layer == LayerName.UNKNOWN:
            violations.append("unknown_layer")
        if layer == LayerName.INGRESS_INTERACTIONS and any(
            token in text for token in ("plan task", "task planning", "memory selection", "lifecycle policy")
        ):
            violations.append("ingress_contains_domain_decision")
        if layer == LayerName.INGRESS_CHECKS and any(
            token in text for token in ("clarify task", "decompose", "execute", "memory recall")
        ):
            violations.append("ingress_checks_contains_domain_reasoning")
        if layer == LayerName.DOMAIN_ORCHESTRATION and any(
            token in text for token in ("call hermes", "invoke tool", "write file", "send message")
        ):
            violations.append("orchestration_contains_execution")
        if layer == LayerName.DOMAIN_EXECUTION_SEMANTICS and any(
            token in text for token in ("vendor/hermes-agent", "from agent.", "import agent.")
        ):
            violations.append("execution_imports_vendor_runtime")

        rationale = rule.purpose if rule else "No target layer rule matched this path."
        return ClassificationResult(
            path=str(path),
            primary_layer=layer,
            rationale=rationale,
            allowed_downstream_layers=rule.allowed_downstream_layers if rule else (),
            violations=tuple(violations),
        )


__all__ = ["ArchitectureClassifier", "ClassificationResult"]
