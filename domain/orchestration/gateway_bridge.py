"""Gateway-facing helpers for the orchestration MVP."""

from __future__ import annotations

from dataclasses import dataclass

from .service import OrchestrationService


@dataclass(frozen=True)
class GatewayOrchestrationReply:
    """A reply that can be sent directly by a gateway adapter."""

    output_type: str
    text: str


def plan_gateway_reply(user_text: str, service: OrchestrationService | None = None) -> GatewayOrchestrationReply | None:
    """Return an immediate gateway reply when orchestration needs clarification.

    The MVP should not execute tasks from the messaging adapter.  For now the
    gateway only short-circuits when the task contract is incomplete and the
    user needs to answer slot-filling questions.
    """

    text = (user_text or "").strip()
    if not text:
        return None

    outcome = (service or OrchestrationService()).plan(text)
    if outcome.output_type != "clarification_request":
        return None

    questions = getattr(outcome, "questions", []) or []
    if not questions:
        return None

    body = "\n".join(f"{index}. {question}" for index, question in enumerate(questions, start=1))
    return GatewayOrchestrationReply(
        output_type=outcome.output_type,
        text="这个任务还缺几个关键信息，我先确认一下：\n" + body,
    )


__all__ = ["GatewayOrchestrationReply", "plan_gateway_reply"]
