"""Canonical layer rules for the agent-first backend architecture."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class LayerName(str, Enum):
    FRONTEND = "frontend"
    INGRESS_INTERACTIONS = "ingress_interactions"
    INGRESS_CHECKS = "ingress_checks"
    APPLICATION_USE_CASE = "application_use_case"
    DOMAIN_MEMORY_CONTEXT = "domain_memory_context"
    DOMAIN_ORCHESTRATION = "domain_orchestration"
    DOMAIN_EXECUTION_SEMANTICS = "domain_execution_semantics"
    DOMAIN_FEEDBACK = "domain_feedback"
    DOMAIN_FLOW_EVENT_LOG = "domain_flow_event_log"
    RUNTIME_INTEGRATION_ADAPTER = "runtime_integration_adapter"
    INFRASTRUCTURE = "infrastructure"
    VENDOR_RUNTIME = "vendor_runtime"
    RUNTIME_DATA = "runtime_data"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class LayerRule:
    name: LayerName
    purpose: str
    owns: tuple[str, ...]
    does_not_own: tuple[str, ...]
    allowed_downstream_layers: tuple[LayerName, ...]
    example_paths: tuple[str, ...]


LAYER_RULES: dict[LayerName, LayerRule] = {
    LayerName.FRONTEND: LayerRule(
        name=LayerName.FRONTEND,
        purpose="User-facing screens and browser interaction.",
        owns=("presentation", "browser interaction", "static assets"),
        does_not_own=("backend request handling", "domain rules"),
        allowed_downstream_layers=(LayerName.INGRESS_INTERACTIONS,),
        example_paths=("interfaces/web/employee-console",),
    ),
    LayerName.INGRESS_INTERACTIONS: LayerRule(
        name=LayerName.INGRESS_INTERACTIONS,
        purpose="Normalize external channel entries into project-owned inputs.",
        owns=("channel entry normalization", "source identity mapping"),
        does_not_own=("digital-life business decisions", "raw platform SDK ownership"),
        allowed_downstream_layers=(LayerName.INGRESS_CHECKS, LayerName.APPLICATION_USE_CASE),
        example_paths=("application/ingress_interactions",),
    ),
    LayerName.INGRESS_CHECKS: LayerRule(
        name=LayerName.INGRESS_CHECKS,
        purpose="Block or sanitize deterministic invalid input before model-facing context assembly.",
        owns=("security checks", "deduplication", "rate limits", "sensitive-content screening"),
        does_not_own=("task planning", "memory selection", "execution strategy"),
        allowed_downstream_layers=(LayerName.APPLICATION_USE_CASE,),
        example_paths=("application/checks",),
    ),
    LayerName.APPLICATION_USE_CASE: LayerRule(
        name=LayerName.APPLICATION_USE_CASE,
        purpose="Coordinate accepted requests into system outcomes.",
        owns=("transactions", "idempotency", "permission outcome", "response assembly"),
        does_not_own=("domain rules", "prompt construction", "runtime calls"),
        allowed_downstream_layers=(
            LayerName.DOMAIN_MEMORY_CONTEXT,
            LayerName.DOMAIN_ORCHESTRATION,
            LayerName.DOMAIN_EXECUTION_SEMANTICS,
            LayerName.DOMAIN_FEEDBACK,
            LayerName.INFRASTRUCTURE,
        ),
        example_paths=("application",),
    ),
    LayerName.DOMAIN_MEMORY_CONTEXT: LayerRule(
        name=LayerName.DOMAIN_MEMORY_CONTEXT,
        purpose="Load context and produce structured Prompt Bundles.",
        owns=("persona", "memory selection", "skills", "token budget", "prompt bundle assembly"),
        does_not_own=("task execution", "external side effects"),
        allowed_downstream_layers=(LayerName.INFRASTRUCTURE,),
        example_paths=("domain/memory",),
    ),
    LayerName.DOMAIN_ORCHESTRATION: LayerRule(
        name=LayerName.DOMAIN_ORCHESTRATION,
        purpose="Decompose Prompt Bundles into executable Task Lists.",
        owns=("task decomposition", "capability requirements", "task-list structure"),
        does_not_own=("tool invocation", "Hermes runtime calls", "external side effects"),
        allowed_downstream_layers=(LayerName.DOMAIN_MEMORY_CONTEXT,),
        example_paths=("domain/orchestration",),
    ),
    LayerName.DOMAIN_EXECUTION_SEMANTICS: LayerRule(
        name=LayerName.DOMAIN_EXECUTION_SEMANTICS,
        purpose="Own L4 execution meaning, state, progress, interruption, recovery, and result interpretation.",
        owns=("execution state", "progress semantics", "interruption", "recovery", "completion meaning"),
        does_not_own=("vendor runtime internals", "raw MCP clients", "tool SDK objects"),
        allowed_downstream_layers=(LayerName.RUNTIME_INTEGRATION_ADAPTER, LayerName.INFRASTRUCTURE),
        example_paths=("domain/execution", "domain/lifecycle", "domain/vital"),
    ),
    LayerName.DOMAIN_FEEDBACK: LayerRule(
        name=LayerName.DOMAIN_FEEDBACK,
        purpose="Reserved post-execution feedback contract and quality-signal interpretation.",
        owns=("feedback contracts", "future quality-gate semantics"),
        does_not_own=("current Continue workflows", "current GitLab integrations", "ReAct loop observations"),
        allowed_downstream_layers=(LayerName.INFRASTRUCTURE,),
        example_paths=("domain/feedback",),
    ),
    LayerName.DOMAIN_FLOW_EVENT_LOG: LayerRule(
        name=LayerName.DOMAIN_FLOW_EVENT_LOG,
        purpose="Own cross-layer flow event semantics and run-level EventLog ordering.",
        owns=("flow event contract", "cross-layer run trace", "event ordering", "event validation"),
        does_not_own=("business object replacement", "runtime trigger queues", "storage implementation"),
        allowed_downstream_layers=(),
        example_paths=("domain/flow_event_log",),
    ),
    LayerName.RUNTIME_INTEGRATION_ADAPTER: LayerRule(
        name=LayerName.RUNTIME_INTEGRATION_ADAPTER,
        purpose="Translate project-owned intent to external runtime and integration providers.",
        owns=("Hermes adapters", "Feishu adapters", "LLM adapters", "MCP adapters", "tool adapters"),
        does_not_own=("digital-life business semantics", "lifecycle policy"),
        allowed_downstream_layers=(LayerName.INFRASTRUCTURE, LayerName.VENDOR_RUNTIME),
        example_paths=("adapters/feishu", "adapters/llm", "adapters/mcp", "adapters/tools"),
    ),
    LayerName.INFRASTRUCTURE: LayerRule(
        name=LayerName.INFRASTRUCTURE,
        purpose="Provide technical primitives through project-owned ports.",
        owns=("persistence", "queues", "cache", "filesystem", "scheduler primitives", "config", "observability"),
        does_not_own=("runtime engine behavior", "channel protocol interpretation", "digital-life semantics"),
        allowed_downstream_layers=(),
        example_paths=("infrastructure",),
    ),
}


def _norm(path: str | Path) -> str:
    return str(path).replace("\\", "/").strip("./")


def classify_path(path: str | Path) -> LayerName:
    normalized = _norm(path)
    if normalized.startswith("interfaces/web/"):
        return LayerName.FRONTEND
    if normalized.startswith("application/ingress_interactions/"):
        return LayerName.INGRESS_INTERACTIONS
    if normalized.startswith("application/checks/"):
        return LayerName.INGRESS_CHECKS
    if normalized.startswith("application/"):
        return LayerName.APPLICATION_USE_CASE
    if normalized.startswith(("domain/memory/", "domain/memory/")):
        return LayerName.DOMAIN_MEMORY_CONTEXT
    if normalized.startswith(("domain/orchestration/", "domain/orchestration/")):
        return LayerName.DOMAIN_ORCHESTRATION
    if normalized.startswith(("domain/execution/", "domain/lifecycle/", "domain/vital/")):
        return LayerName.DOMAIN_EXECUTION_SEMANTICS
    if normalized.startswith(("domain/feedback/", "domain/feedback/")):
        return LayerName.DOMAIN_FEEDBACK
    if normalized.startswith(("domain/flow_event_log/", "domain/flow_event_log/")):
        return LayerName.DOMAIN_FLOW_EVENT_LOG
    if normalized.startswith("adapters/"):
        return LayerName.RUNTIME_INTEGRATION_ADAPTER
    if normalized.startswith("infrastructure/"):
        return LayerName.INFRASTRUCTURE
    if normalized.startswith("vendor/hermes-agent/"):
        return LayerName.VENDOR_RUNTIME
    if normalized.startswith("runtime/"):
        return LayerName.RUNTIME_DATA
    return LayerName.UNKNOWN


def get_layer_rule(layer: LayerName) -> LayerRule | None:
    return LAYER_RULES.get(layer)


__all__ = ["LAYER_RULES", "LayerName", "LayerRule", "classify_path", "get_layer_rule"]
