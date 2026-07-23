"""Task contract construction from extracted orchestration slots."""

from __future__ import annotations

from domain.core.ids import new_id

from ..types import TaskAction, TaskContract
from .models import Intent, SlotSet


class TaskContractBuilder:
    def build(
        self,
        *,
        request: object | None = None,
        intent: Intent,
        slots: SlotSet,
    ) -> TaskContract:
        values = slots.values
        employee_id = str(getattr(request, "employee_id", "") or "")
        message_event_id = str(getattr(request, "message_event_id", "") or "")
        task_type = str(values.get("task_type", "one_shot"))
        domain = str(values.get("domain", "general"))
        action_type = str(values.get("action_type", "respond"))
        action_channel = str(values.get("action_channel", "chat"))

        allowed_types = {"one_shot", "recurring_monitor", "reminder", "research"}
        return TaskContract(
            id=new_id("tc"),
            employee_id=employee_id,
            source_message_event_id=message_event_id,
            type=task_type if task_type in allowed_types else "one_shot",
            domain=domain,
            goal=str(values.get("goal", "")),
            target=self._prefixed_dict(values, "target_"),
            schedule=self._prefixed_dict(values, "schedule_"),
            condition=self._prefixed_dict(values, "condition_"),
            action=TaskAction(type=action_type, channel=action_channel),
            constraints=self._prefixed_dict(values, "constraint_"),
        )

    def generate(self, slots: dict[str, object]) -> TaskContract:
        intent = Intent(name=str(slots.get("task_type", "one_shot")), domain=str(slots.get("domain", "general")))
        return self.build(intent=intent, slots=SlotSet(values=slots))

    @staticmethod
    def _prefixed_dict(values: dict[str, object], prefix: str) -> dict[str, object]:
        return {key.removeprefix(prefix): value for key, value in values.items() if key.startswith(prefix)}


TaskContractGenerator = TaskContractBuilder


__all__ = ["TaskContractBuilder", "TaskContractGenerator"]
