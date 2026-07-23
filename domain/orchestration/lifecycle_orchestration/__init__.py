"""Lifecycle orchestration_layer migration manifest.

Owns wake decisions, event-to-work planning, task decomposition, and condition
selection extracted from Hermes lifecycle modules.
"""

from __future__ import annotations

from domain.core.models import LifecycleLayer, LifecycleSourceSlice
from domain.orchestration.lifecycle_orchestration.bootstrap import (
    LIFE_AFFAIR_GOAL,
    LIFE_AFFAIR_PRIORITY,
    find_life_affair_id,
    is_life_affair_meta,
    life_affair_metadata,
)
from domain.orchestration.lifecycle_orchestration.wakeup_policy import (
    choose_auto_rest_wake_time,
    next_retry_delay_minutes,
    retry_intent_meta,
)
from domain.orchestration.lifecycle_orchestration.plan_state import (
    PlanState,
    PlanStatePolicy,
    PlanStateSnapshot,
)
from domain.orchestration.lifecycle_orchestration.replan_policy import (
    ReplanDecision,
    ReplanPolicy,
)


LIFECYCLE_ORCHESTRATION_SLICES: tuple[LifecycleSourceSlice, ...] = (
    LifecycleSourceSlice(
        source_module="init_life",
        layer=LifecycleLayer.ORCHESTRATION,
        target_package="domain.orchestration.lifecycle_orchestration.bootstrap",
        responsibility="Create or locate a concrete digital-life instance before work can be planned.",
        adapter_boundary="Hermes startup asks domain orchestration for the active life instance id.",
    ),
    LifecycleSourceSlice(
        source_module="events",
        layer=LifecycleLayer.ORCHESTRATION,
        target_package="domain.orchestration.lifecycle_orchestration.events",
        responsibility="Turn queued lifecycle events into schedulable work candidates.",
        adapter_boundary="Hermes event table is accessed through adapters, not directly by orchestrators.",
    ),
    LifecycleSourceSlice(
        source_module="scheduler",
        layer=LifecycleLayer.ORCHESTRATION,
        target_package="domain.orchestration.lifecycle_orchestration.wakeup_policy",
        responsibility="Choose wake reason, priority, pending events, and next orchestration action.",
        adapter_boundary="Hermes cron delegates wake policy to domain orchestration before invoking runtime.",
    ),
    LifecycleSourceSlice(
        source_module="tasks",
        layer=LifecycleLayer.ORCHESTRATION,
        target_package="domain.orchestration.lifecycle_orchestration.task_planning",
        responsibility="Goal/task planning, milestones, daily plans, and due task selection.",
        adapter_boundary="Hermes tools call orchestration services for task planning decisions.",
    ),
    LifecycleSourceSlice(
        source_module="vitals",
        layer=LifecycleLayer.ORCHESTRATION,
        target_package="domain.orchestration.lifecycle_orchestration.vital_triggers",
        responsibility="Convert vital threshold predictions into triggerable orchestration events.",
        adapter_boundary="Vitals feedback is converted to events before Hermes runtime is invoked.",
    ),
    LifecycleSourceSlice(
        source_module="nurture",
        layer=LifecycleLayer.ORCHESTRATION,
        target_package="domain.orchestration.lifecycle_orchestration.message_intake",
        responsibility="Classify inbound human messages into task, nurture, or plain conversation intents.",
        adapter_boundary="Gateway adapters call package intake before L4 wake handoff.",
    ),
)


__all__ = [
    "LIFECYCLE_ORCHESTRATION_SLICES",
    "LIFE_AFFAIR_GOAL",
    "LIFE_AFFAIR_PRIORITY",
    "find_life_affair_id",
    "is_life_affair_meta",
    "life_affair_metadata",
    "choose_auto_rest_wake_time",
    "next_retry_delay_minutes",
    "retry_intent_meta",
    "PlanState",
    "PlanStatePolicy",
    "PlanStateSnapshot",
    "ReplanDecision",
    "ReplanPolicy",
]
