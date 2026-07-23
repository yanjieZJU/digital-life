"""Generic runtime contracts.

Domain services depend on these small protocols instead of importing a concrete
agent adapter such as Hermes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class AgentRunRequest:
    session_id: str
    prompt: str
    trigger: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentRunResult:
    session_id: str
    final_response: str = ""
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.error


class AgentRunnerPort(Protocol):
    def run_session(self, request: AgentRunRequest) -> AgentRunResult:
        """Run one agent session and return the final adapter-neutral result."""


class MessageChannelPort(Protocol):
    def send_message(
        self,
        *,
        text: str,
        channel: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Send a user-facing message through the active channel adapter."""


class SessionStorePort(Protocol):
    def recent_sessions(self, *, limit: int = 20) -> Sequence[Mapping[str, Any]]:
        """Return recent runtime sessions in adapter-neutral shape."""
