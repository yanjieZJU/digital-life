"""Application workflow for normal external messages."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from application.contracts import UseCaseResult
from application.ingress_interactions import MessageEvent
from domain.flow_event_log import (
    ActionDispatchedEvent,
    ActionProposedEvent,
    CapabilityMatchedEvent,
    CapabilityMissingEvent,
    ClarificationRequiredEvent,
    ContextBudgetAppliedEvent,
    EventRecorder,
    ExecutionCompletedEvent,
    ExecutionFailedEvent,
    ExecutionRequestCreatedEvent,
    ExecutionStartedEvent,
    FlowEvent,
    FlowEventLog,
    IntentClassifiedEvent,
    MemoryContextRequestedEvent,
    MemoryRecallCompletedEvent,
    MessageNormalizedEvent,
    MessageReceivedEvent,
    ObservationReceivedEvent,
    OrchestrationCompletedEvent,
    OrchestrationStartedEvent,
    PlanCreatedEvent,
    RunResultEvaluatedEvent,
    SlotExtractedEvent,
    StateChangedEvent,
    ToolErrorEvent,
)
from domain.execution.semantics import (
    ActionEvent,
    AgentErrorEvent,
    EventLog,
    ExecutionRequest,
    MessageTraceEvent,
    ObservationEvent,
    RuntimeEnginePort,
    RuntimeExecutionResult,
    StateUpdateEvent,
)
from domain.orchestration import (
    Capability,
    CapabilityRegistry,
    OrchestrationPlan,
    OrchestrationRequest,
    OrchestrationResult,
    OrchestrationService,
    TaskNode,
)
from infrastructure.config import get_runtime_state_db_path
from infrastructure.persistence.repositories import SQLiteFlowEventLogRepository


DEFAULT_MESSAGE_CAPABILITIES = (
    Capability(id="agent.run", name="Default agent runtime"),
    Capability(id="notification.chat", name="Default chat notification"),
)


class AcceptedRuntimeEngine:
    """Minimal RuntimeEnginePort used when no external engine is injected."""

    engine_name = "application-default"

    def execute(self, request: ExecutionRequest) -> RuntimeExecutionResult:
        return RuntimeExecutionResult(
            execution_id=request.execution_id,
            status="accepted",
            output={
                "runtime_capability": request.runtime_capability,
                "task_node_id": request.task_node_id,
            },
        )


class MessageWorkflow:
    """Coordinate the common MessageEvent flow for all digital employees."""

    def __init__(
        self,
        *,
        orchestration_service: OrchestrationService | None = None,
        runtime_engine: RuntimeEnginePort | None = None,
        flow_event_recorder: EventRecorder | None = None,
    ) -> None:
        self._orchestration = orchestration_service or OrchestrationService(
            CapabilityRegistry(DEFAULT_MESSAGE_CAPABILITIES)
        )
        self._runtime = runtime_engine or AcceptedRuntimeEngine()
        self._flow_events = flow_event_recorder or EventRecorder(
            SQLiteFlowEventLogRepository(get_runtime_state_db_path())
        )

    def receive(self, event: MessageEvent) -> UseCaseResult:
        if event.type != "MessageEvent":
            return UseCaseResult({"error": f"unsupported event type: {event.type}"}, 400)
        if not event.content.strip():
            return UseCaseResult({"error": "message content required"}, 400)
        run_id = self._run_id(event)
        self._start_flow_log(event, run_id=run_id)
        self._record_flow(
            MessageReceivedEvent(
                **self._flow_base(event, run_id=run_id),
                timestamp=event.timestamp,
                payload=self._message_event_ref_payload(event),
                summary="MessageEvent received by application workflow.",
            )
        )
        self._record_flow(
            MessageNormalizedEvent(
                **self._flow_base(event, run_id=run_id),
                timestamp=event.timestamp,
                payload={
                    "message_event_id": event.id,
                    "role": event.llm_message.role,
                    "content_preview": event.content[:200],
                    "activated_skills": list(event.activated_skills),
                },
                summary="Ingress message normalized to MessageEvent.",
            )
        )
        self._record_memory_context_events(event, run_id=run_id)
        trace = self._trace_for_message(event, run_id=run_id)
        self._record_flow(
            OrchestrationStartedEvent(
                **self._flow_base(event, run_id=run_id),
                payload={"request": self._orchestration_request_ref_payload(event)},
                summary="Orchestration planning started.",
            )
        )
        outcome = self._orchestration.plan(self._orchestration_request(event))
        self._record_orchestration_events(event, outcome, run_id=run_id)
        trace = trace.append(
            StateUpdateEvent(
                source="application",
                run_id=run_id,
                state="running",
                reason="message_orchestration_completed",
                metadata={"orchestration_kind": outcome.kind},
            )
        )
        self._record_flow(
            ExecutionStartedEvent(
                **self._flow_base(event, run_id=run_id),
                payload={"orchestration_kind": outcome.kind, "plan_id": outcome.plan_id},
                summary="Runtime execution phase entered.",
            )
        )
        execution = self._execute_outcome(event, outcome, trace)
        self._record_flow(
            RunResultEvaluatedEvent(
                **self._flow_base(event, run_id=run_id),
                payload=self._execution_flow_summary(execution["payload"]),
                summary=f"Run result evaluated: {execution['payload'].get('status')}",
            )
        )
        self._flow_events.finish(
            run_id,
            status="failed" if execution["payload"].get("status") == "failed" else "completed",
        )
        flow_log = self._flow_events.get(run_id)
        return UseCaseResult({
            "ok": True,
            "event": self._event_payload(event),
            "orchestration": self._orchestration_payload(outcome),
            "execution": execution["payload"],
            "event_log": execution["event_log"].to_dict(),
            "flow_event_log": flow_log.to_dict() if flow_log else None,
        })

    @staticmethod
    def _event_payload(event: MessageEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "type": event.type,
            "source": event.source,
            "sender": event.sender,
            "llm_message": {
                "role": event.llm_message.role,
                "content": event.llm_message.content,
            },
            "activated_skills": list(event.activated_skills),
            "metadata": dict(event.metadata),
            "timestamp": event.timestamp,
        }

    @staticmethod
    def _run_id(event: MessageEvent) -> str:
        return event.correlation_id or event.id

    @staticmethod
    def _orchestration_request(event: MessageEvent) -> OrchestrationRequest:
        return OrchestrationRequest(
            employee_id=MessageWorkflow._employee_id(event) or "",
            message_event_id=event.id,
            source=event.source,
            text=event.content,
            sender_id=event.sender,
            occurred_at=MessageWorkflow._parse_time(event.timestamp),
            memory_context=event.metadata.get("memory_context", {}) if isinstance(event.metadata, dict) else {},
            metadata=dict(event.metadata),
        )

    @staticmethod
    def _parse_time(value: str) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(timezone.utc)

    @staticmethod
    def _orchestration_payload(outcome: OrchestrationResult) -> dict[str, Any]:
        if outcome.clarification is not None:
            payload = outcome.clarification.to_dict()
        elif outcome.plan is not None:
            payload = outcome.plan.to_dict()
        else:
            payload = {"output_type": outcome.kind, "blocked_reason": outcome.blocked_reason}
        payload["kind"] = outcome.kind
        payload["plan_id"] = outcome.plan_id
        return payload

    @staticmethod
    def _trace_for_message(event: MessageEvent, *, run_id: str) -> EventLog:
        trace_event = MessageTraceEvent(
            id=event.id,
            source=event.source,
            run_id=run_id,
            timestamp=event.timestamp,
            message_id=event.id,
            role=event.llm_message.role,
            content=event.llm_message.content,
            sender=event.sender,
            metadata=dict(event.metadata),
        )
        return EventLog(run_id=run_id, employee_id=MessageWorkflow._employee_id(event)).append(trace_event)

    def _execute_outcome(self, event: MessageEvent, outcome: OrchestrationResult, trace: EventLog) -> dict[str, Any]:
        run_id = self._run_id(event)
        if outcome.kind not in {"execution_ready", "capability_development_ready"} or outcome.plan is None:
            reason = outcome.clarification.output_type if outcome.clarification else outcome.kind
            self._record_flow(
                StateChangedEvent(
                    **self._flow_base(event, run_id=run_id),
                    payload={"state": "finished", "reason": f"orchestration_returned_{reason}"},
                    summary=f"Execution skipped because orchestration returned {reason}.",
                )
            )
            self._record_flow(
                ExecutionCompletedEvent(
                    **self._flow_base(event, run_id=run_id),
                    payload={"executed": False, "reason": reason},
                    summary="Execution completed without runtime dispatch.",
                )
            )
            trace = trace.append(
                StateUpdateEvent(
                    source="application",
                    run_id=run_id,
                    state="finished",
                    reason=f"orchestration_returned_{reason}",
                )
            )
            return {
                "payload": {
                    "executed": False,
                    "status": "not_executable",
                    "reason": reason,
                    "results": [],
                },
                "event_log": trace,
            }

        if outcome.plan.status != "ready_for_execution":
            self._record_flow(
                StateChangedEvent(
                    **self._flow_base(event, run_id=run_id),
                    payload={"state": "stuck", "reason": f"runtime_plan_status_{outcome.plan.status}"},
                    summary=f"Execution blocked by plan status {outcome.plan.status}.",
                    severity="warning",
                )
            )
            self._record_flow(
                ExecutionFailedEvent(
                    **self._flow_base(event, run_id=run_id),
                    payload={"executed": False, "reason": outcome.plan.status},
                    summary="Execution failed before runtime dispatch.",
                )
            )
            trace = trace.append(
                StateUpdateEvent(
                    source="application",
                    run_id=run_id,
                    state="stuck",
                    reason=f"runtime_plan_status_{outcome.plan.status}",
                )
            )
            return {
                "payload": {
                    "executed": False,
                    "status": "blocked",
                    "reason": outcome.plan.status,
                    "results": [],
                },
                "event_log": trace,
            }

        results: list[dict[str, Any]] = []
        requests_by_task = {request.task_node_id: request for request in outcome.execution_requests}
        for task in outcome.plan.tasks:
            request = requests_by_task.get(task.id) or self._execution_request(run_id=run_id, event=event, plan=outcome.plan, task=task)
            self._record_flow(
                ActionProposedEvent(
                    **self._flow_base(event, run_id=run_id),
                    payload={
                        "execution_request": self._execution_request_ref_payload(request),
                        "task_node": self._task_ref_payload(task),
                    },
                    summary=f"Runtime action proposed: {request.runtime_capability}",
                )
            )
            action = ActionEvent(
                source="application",
                run_id=run_id,
                tool_call_id=request.execution_id,
                tool_name=request.runtime_capability,
                summary=task.title,
                security_risk="UNKNOWN",
                action={
                    "execution_request": self._request_payload(request),
                    "task_node": task.to_dict(),
                },
            )
            trace = trace.append(action)
            try:
                self._record_flow(
                    ActionDispatchedEvent(
                        **self._flow_base(event, run_id=run_id),
                        causation_event_id=action.id,
                        payload={"execution_request": self._execution_request_ref_payload(request)},
                        summary=f"Runtime action dispatched: {request.runtime_capability}",
                    )
                )
                result = self._runtime.execute(request)
            except Exception as exc:
                self._record_flow(
                    ToolErrorEvent(
                        **self._flow_base(event, run_id=run_id),
                        causation_event_id=action.id,
                        payload={
                            "execution_id": request.execution_id,
                            "runtime_capability": request.runtime_capability,
                            "error": str(exc),
                        },
                        summary=f"Runtime action failed: {request.runtime_capability}",
                    )
                )
                trace = trace.append(
                    AgentErrorEvent(
                        source="runtime",
                        run_id=run_id,
                        error_kind="runtime",
                        message=str(exc),
                        tool_call_id=request.execution_id,
                        tool_name=request.runtime_capability,
                        recoverable=True,
                    )
                )
                results.append({
                    "execution_id": request.execution_id,
                    "task_node_id": task.id,
                    "runtime_capability": request.runtime_capability,
                    "status": "failed",
                    "error": str(exc),
                })
                continue

            self._record_flow(
                ObservationReceivedEvent(
                    **self._flow_base(event, run_id=run_id),
                    causation_event_id=action.id,
                    payload=self._result_ref_payload(result, task_node_id=task.id),
                    summary=f"Runtime observation received: {result.status}",
                    severity="error" if self._observation_status(result.status) == "failed" else "info",
                )
            )
            trace = trace.append(
                ObservationEvent(
                    source="runtime",
                    run_id=run_id,
                    action_id=action.id,
                    tool_call_id=request.execution_id,
                    tool_name=request.runtime_capability,
                    status=self._observation_status(result.status),
                    observation=self._result_payload(result),
                )
            )
            results.append(self._result_payload(result, task_node_id=task.id))

        failed = any(result.get("status") in {"failed", "error"} for result in results)
        self._record_flow(
            StateChangedEvent(
                **self._flow_base(event, run_id=run_id),
                payload={
                    "state": "failed" if failed else "finished",
                    "reason": "runtime_execution_failed" if failed else "runtime_execution_completed",
                },
                summary="Execution state updated after runtime results.",
                severity="error" if failed else "info",
            )
        )
        self._record_flow(
            (ExecutionFailedEvent if failed else ExecutionCompletedEvent)(
                **self._flow_base(event, run_id=run_id),
                payload=self._execution_flow_summary(
                    {
                        "executed": True,
                        "status": "failed" if failed else "completed",
                        "results": results,
                    }
                ),
                summary="Runtime execution failed." if failed else "Runtime execution completed.",
            )
        )
        trace = trace.append(
            StateUpdateEvent(
                source="application",
                run_id=run_id,
                state="failed" if failed else "finished",
                reason="runtime_execution_failed" if failed else "runtime_execution_completed",
            )
        )
        return {
            "payload": {
                "executed": True,
                "status": "failed" if failed else "completed",
                "results": results,
            },
            "event_log": trace,
        }

    @staticmethod
    def _execution_request(
        *,
        run_id: str,
        event: MessageEvent,
        plan: OrchestrationPlan,
        task: TaskNode,
    ) -> ExecutionRequest:
        capability = task.required_capability or task.type
        return ExecutionRequest(
            execution_id=f"{run_id}:{plan.plan_id}:{task.id}",
            task_node_id=task.id,
            runtime_capability=capability,
            execution_policy={
                "source": "message_workflow",
                "plan_id": plan.plan_id,
                "plan_type": plan.plan_type,
                "task_type": task.type,
                "depends_on": list(task.depends_on),
                "message_source": event.source,
            },
            context_refs=(event.id,),
            result_contract=task.output or "default",
        )

    @staticmethod
    def _request_payload(request: ExecutionRequest) -> dict[str, Any]:
        return {
            "execution_id": request.execution_id,
            "task_node_id": request.task_node_id,
            "runtime_capability": request.runtime_capability,
            "execution_policy": dict(request.execution_policy),
            "context_refs": list(request.context_refs),
            "interrupt_policy": request.interrupt_policy,
            "result_contract": request.result_contract,
        }

    @staticmethod
    def _result_payload(result: RuntimeExecutionResult, *, task_node_id: str | None = None) -> dict[str, Any]:
        payload = {
            "execution_id": result.execution_id,
            "status": result.status,
            "output": dict(result.output),
            "error": result.error,
        }
        if task_node_id:
            payload["task_node_id"] = task_node_id
        return payload

    @staticmethod
    def _message_event_ref_payload(event: MessageEvent) -> dict[str, Any]:
        return {
            "message_event_id": event.id,
            "type": event.type,
            "source": event.source,
            "sender": event.sender,
            "role": event.llm_message.role,
            "content_preview": event.content[:200],
            "activated_skill_count": len(event.activated_skills),
            "metadata_keys": sorted(str(key) for key in event.metadata.keys()),
            "timestamp": event.timestamp,
        }

    @staticmethod
    def _orchestration_request_ref_payload(event: MessageEvent) -> dict[str, Any]:
        memory_context = event.metadata.get("memory_context", {}) if isinstance(event.metadata, dict) else {}
        return {
            "employee_id": MessageWorkflow._employee_id(event),
            "message_event_id": event.id,
            "source": event.source,
            "sender_id": event.sender,
            "text_preview": event.content[:200],
            "memory_context_keys": sorted(memory_context.keys()) if isinstance(memory_context, dict) else [],
        }

    @staticmethod
    def _plan_ref_payload(plan: OrchestrationPlan) -> dict[str, Any]:
        return {
            "plan_id": plan.plan_id,
            "plan_type": plan.plan_type,
            "status": plan.status,
            "task_count": len(plan.tasks),
            "task_ids": [task.id for task in plan.tasks],
            "required_capabilities": sorted({
                str(task.required_capability or task.type) for task in plan.tasks
            }),
        }

    @staticmethod
    def _execution_request_ref_payload(request: ExecutionRequest) -> dict[str, Any]:
        return {
            "execution_id": request.execution_id,
            "task_node_id": request.task_node_id,
            "runtime_capability": request.runtime_capability,
            "context_refs": list(request.context_refs),
            "result_contract": request.result_contract,
        }

    @staticmethod
    def _task_ref_payload(task: TaskNode) -> dict[str, Any]:
        return {
            "task_node_id": task.id,
            "type": task.type,
            "title": task.title,
            "required_capability": task.required_capability,
        }

    @staticmethod
    def _result_ref_payload(result: RuntimeExecutionResult, *, task_node_id: str | None = None) -> dict[str, Any]:
        payload = {
            "execution_id": result.execution_id,
            "status": result.status,
            "output_keys": sorted(str(key) for key in result.output.keys()),
            "error": result.error,
        }
        if task_node_id:
            payload["task_node_id"] = task_node_id
        return payload

    @staticmethod
    def _execution_flow_summary(payload: dict[str, Any]) -> dict[str, Any]:
        results = payload.get("results", [])
        result_items = [item for item in results if isinstance(item, dict)] if isinstance(results, list) else []
        return {
            "executed": bool(payload.get("executed")),
            "status": payload.get("status"),
            "reason": payload.get("reason"),
            "result_count": len(result_items),
            "failed_count": sum(1 for item in result_items if item.get("status") in {"failed", "error"}),
            "execution_ids": [str(item.get("execution_id")) for item in result_items if item.get("execution_id")],
        }

    @staticmethod
    def _observation_status(runtime_status: str) -> str:
        normalized = (runtime_status or "").lower()
        if normalized in {"failed", "error", "rejected"}:
            return "failed"
        if normalized in {"partial", "blocked", "stuck"}:
            return "partial"
        return "succeeded"

    @staticmethod
    def _employee_id(event: MessageEvent) -> str | None:
        for key in ("employee_id", "digital_life_id", "life_id"):
            value = event.metadata.get(key)
            if value:
                return str(value)
        return None

    def _start_flow_log(self, event: MessageEvent, *, run_id: str) -> None:
        self._flow_events.start(
            FlowEventLog(
                run_id=run_id,
                employee_id=self._employee_id(event),
                message_event_id=event.id,
                metadata={
                    "source": event.source,
                    "sender": event.sender,
                    "message_event_id": event.id,
                },
            )
        )

    def _record_flow(self, event: FlowEvent) -> FlowEvent:
        return self._flow_events.record(event)

    def _flow_base(self, event: MessageEvent, *, run_id: str) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "source": "application.message_workflow",
            "employee_id": self._employee_id(event),
            "message_event_id": event.id,
            "correlation_id": event.correlation_id,
        }

    def _record_memory_context_events(self, event: MessageEvent, *, run_id: str) -> None:
        memory_context = event.metadata.get("memory_context", {}) if isinstance(event.metadata, dict) else {}
        context_keys = sorted(memory_context.keys()) if isinstance(memory_context, dict) else []
        self._record_flow(
            MemoryContextRequestedEvent(
                **self._flow_base(event, run_id=run_id),
                payload={"requested_for": event.id},
                summary="Memory context requested for orchestration.",
            )
        )
        self._record_flow(
            MemoryRecallCompletedEvent(
                **self._flow_base(event, run_id=run_id),
                payload={"context_keys": context_keys, "context_source": "message_event.metadata"},
                summary=f"Memory context loaded with {len(context_keys)} top-level keys.",
            )
        )
        self._record_flow(
            ContextBudgetAppliedEvent(
                **self._flow_base(event, run_id=run_id),
                payload={"context_keys": context_keys},
                summary="Context budget checkpoint applied before orchestration.",
            )
        )

    def _record_orchestration_events(self, event: MessageEvent, outcome: OrchestrationResult, *, run_id: str) -> None:
        debug = dict(outcome.debug or {})
        if isinstance(debug.get("intent"), dict):
            self._record_flow(
                IntentClassifiedEvent(
                    **self._flow_base(event, run_id=run_id),
                    payload=debug["intent"],
                    summary=f"Intent classified as {debug['intent'].get('name', 'unknown')}.",
                )
            )
        if isinstance(debug.get("slots"), dict):
            self._record_flow(
                SlotExtractedEvent(
                    **self._flow_base(event, run_id=run_id),
                    payload=debug["slots"],
                    summary="Slots extracted for orchestration.",
                )
            )
        match = debug.get("capability_match")
        if isinstance(match, dict):
            event_cls = CapabilityMatchedEvent if match.get("ok") else CapabilityMissingEvent
            self._record_flow(
                event_cls(
                    **self._flow_base(event, run_id=run_id),
                    payload={
                        "required_capabilities": debug.get("required_capabilities", []),
                        "capability_match": match,
                    },
                    summary="Capability requirements matched." if match.get("ok") else "Capability requirements missing.",
                )
            )
        if outcome.clarification is not None:
            self._record_flow(
                ClarificationRequiredEvent(
                    **self._flow_base(event, run_id=run_id),
                    payload=outcome.clarification.to_dict(),
                    summary="Orchestration requires clarification.",
                )
            )
        if outcome.plan is not None:
            self._record_flow(
                PlanCreatedEvent(
                    **self._flow_base(event, run_id=run_id),
                    payload=self._plan_ref_payload(outcome.plan),
                    summary=f"Orchestration plan created: {outcome.plan.plan_id}.",
                )
            )
        for request in outcome.execution_requests:
            self._record_flow(
                ExecutionRequestCreatedEvent(
                    **self._flow_base(event, run_id=run_id),
                    payload=self._execution_request_ref_payload(request),
                    summary=f"ExecutionRequest created: {request.execution_id}.",
                )
            )
        self._record_flow(
            OrchestrationCompletedEvent(
                **self._flow_base(event, run_id=run_id),
                payload={
                    "kind": outcome.kind,
                    "plan_id": outcome.plan_id,
                    "execution_request_count": len(outcome.execution_requests),
                },
                summary=f"Orchestration completed with kind {outcome.kind}.",
            )
        )


__all__ = ["AcceptedRuntimeEngine", "MessageWorkflow"]
