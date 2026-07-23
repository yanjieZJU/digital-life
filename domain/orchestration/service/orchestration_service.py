"""High-level orchestration service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import overload

from ..capability import CapabilityGapPlanner, CapabilityMapper, CapabilityMatcher, CapabilityRegistry
from ..intake import ClarificationPlanner, IntentClassifier, SlotExtractor, TaskContractBuilder
from ..planning import (
    CapabilityDevelopmentPlanner,
    DevelopmentComplexityPolicy,
    ExecutionRequestBuilder,
    RuntimeTaskPlanner,
    SpecKitPlanner,
)
from ..types import OrchestrationOutcome, OrchestrationPlan
from .contracts import OrchestrationRequest, OrchestrationResult


class OrchestrationService:
    """Plan user tasks without executing them."""

    def __init__(
        self,
        capability_registry: CapabilityRegistry | None = None,
        *,
        intent_classifier: IntentClassifier | None = None,
        slot_extractor: SlotExtractor | None = None,
        clarification_generator: ClarificationPlanner | None = None,
        task_contract_generator: TaskContractBuilder | None = None,
        capability_mapper: CapabilityMapper | None = None,
        runtime_task_planner: RuntimeTaskPlanner | None = None,
        capability_development_planner: CapabilityDevelopmentPlanner | None = None,
        speckit_planner: SpecKitPlanner | None = None,
        development_complexity: DevelopmentComplexityPolicy | None = None,
        execution_request_builder: ExecutionRequestBuilder | None = None,
    ) -> None:
        self._registry = capability_registry or CapabilityRegistry()
        self._intent_classifier = intent_classifier or IntentClassifier()
        self._slot_extractor = slot_extractor or SlotExtractor()
        self._clarification_planner = clarification_generator or ClarificationPlanner()
        self._task_contract_builder = task_contract_generator or TaskContractBuilder()
        self._capability_mapper = capability_mapper or CapabilityMapper()
        self._capability_matcher = CapabilityMatcher(self._registry)
        self._gap_planner = CapabilityGapPlanner()
        self._runtime_task_planner = runtime_task_planner or RuntimeTaskPlanner()
        self._capability_development_planner = capability_development_planner or CapabilityDevelopmentPlanner()
        self._speckit_planner = speckit_planner or SpecKitPlanner()
        self._development_complexity = development_complexity or DevelopmentComplexityPolicy()
        self._execution_request_builder = execution_request_builder or ExecutionRequestBuilder()
        self._last_debug = {}

    @overload
    def plan(self, request: OrchestrationRequest) -> OrchestrationResult: ...

    @overload
    def plan(self, request: str) -> OrchestrationOutcome: ...

    def plan(self, request: OrchestrationRequest | str) -> OrchestrationResult | OrchestrationOutcome:
        if isinstance(request, str):
            return self._plan_outcome(self._request_from_text(request))
        return self._plan_result(request)

    def _plan_result(self, request: OrchestrationRequest) -> OrchestrationResult:
        outcome = self._plan_outcome(request)
        if not isinstance(outcome, OrchestrationPlan):
            return OrchestrationResult.clarification_required(
                clarification=outcome,
                debug={"message_event_id": request.message_event_id},
            )

        execution_requests = self._execution_request_builder.from_task_list(
            employee_id=request.employee_id,
            source_message_event_id=request.message_event_id,
            task_contract=self._last_contract,
            task_list=outcome,
        )
        if outcome.output_type == "runtime_task_list":
            return OrchestrationResult.execution_ready(
                plan=outcome,
                task_contract=self._last_contract,
                execution_requests=execution_requests,
                debug=self._last_debug,
            )
        return OrchestrationResult.capability_development_ready(
            plan=outcome,
            task_contract=self._last_contract,
            execution_requests=execution_requests,
            debug=self._last_debug,
        )

    def _plan_outcome(self, request: OrchestrationRequest) -> OrchestrationOutcome:
        intent = self._intent_classifier.classify(request.text, context=request.memory_context)
        slots = self._slot_extractor.extract(request.text, intent, context=request.memory_context)
        if slots.missing_required:
            return self._clarification_planner.plan(intent, slots)

        contract = self._task_contract_builder.build(request=request, intent=intent, slots=slots)
        required = self._capability_mapper.map(contract)
        match = self._capability_matcher.match(required)
        self._last_contract = contract
        self._last_debug = {
            "intent": intent.to_dict(),
            "slots": slots.to_dict(),
            "required_capabilities": required,
            "capability_match": match.to_dict(),
        }
        if match.ok:
            return self._runtime_task_planner.build(contract, required)

        gap = self._gap_planner.plan(contract=contract, required_capabilities=required, match=match)
        complexity = self._development_complexity.evaluate([gap])
        if complexity.use_speckit or self._speckit_planner.should_use(match.missing):
            speckit = self._speckit_planner.plan(contract, gap, missing_capabilities=match.missing)
            self._last_debug = {
                **self._last_debug,
                "capability_gap": gap.to_dict(),
                "speckit": {
                    "spec_path": speckit.spec_path,
                    "plan_path": speckit.plan_path,
                    "tasks_path": speckit.tasks_path,
                    "tasks_json_path": speckit.tasks_json_path,
                },
            }
            return speckit.task_list
        return self._capability_development_planner.build(contract, gap)

    @staticmethod
    def _request_from_text(text: str) -> OrchestrationRequest:
        return OrchestrationRequest(
            employee_id="",
            message_event_id="",
            source="direct",
            text=text,
            sender_id=None,
            occurred_at=datetime.now(timezone.utc),
        )


__all__ = ["OrchestrationService"]
