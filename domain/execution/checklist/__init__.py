"""Checklist items used to recover interrupted event execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class ExecutionStatus(str, Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass
class ExecutionItem:
    id: str
    event_id: str
    title: str
    status: ExecutionStatus = ExecutionStatus.TODO
    workspace_id: str | None = None
    notes: str = ""
    evidence: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionItem":
        return cls(
            id=str(data["id"]),
            event_id=str(data["event_id"]),
            title=str(data["title"]),
            status=ExecutionStatus(data.get("status", ExecutionStatus.TODO.value)),
            workspace_id=data.get("workspace_id"),
            notes=str(data.get("notes", "")),
            evidence=str(data.get("evidence", "")),
        )
