"""Execution traces for event processing."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from domain.core.ids import new_id
from infrastructure.persistence.paths import RuntimePaths

from ..checklist import ExecutionItem, ExecutionStatus


@dataclass
class ExecutionTrace:
    id: str
    event_id: str
    agent_id: str
    status: ExecutionStatus = ExecutionStatus.DOING
    workspace_id: str | None = None
    summary: str = ""
    checklist: tuple[ExecutionItem, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def start(
        cls,
        event_id: str,
        agent_id: str,
        *,
        workspace_id: str | None = None,
        checklist: tuple[ExecutionItem, ...] = (),
    ) -> "ExecutionTrace":
        return cls(
            id=new_id("trace"),
            event_id=event_id,
            agent_id=agent_id,
            workspace_id=workspace_id,
            checklist=checklist,
        )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        data["checklist"] = [item.to_dict() for item in self.checklist]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionTrace":
        return cls(
            id=str(data["id"]),
            event_id=str(data["event_id"]),
            agent_id=str(data["agent_id"]),
            status=ExecutionStatus(data.get("status", ExecutionStatus.DOING.value)),
            workspace_id=data.get("workspace_id"),
            summary=str(data.get("summary", "")),
            checklist=tuple(ExecutionItem.from_dict(item) for item in data.get("checklist", [])),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )


class ExecutionRepository(Protocol):
    def save(self, trace: ExecutionTrace) -> None: ...

    def get(self, trace_id: str) -> ExecutionTrace | None: ...

    def list_open(self, agent_id: str | None = None) -> tuple[ExecutionTrace, ...]: ...


class FileExecutionRepository:
    """JSON-file execution repository.

    This is intentionally boring storage for the extraction phase. It makes
    interrupted work visible without committing to a final DB schema.
    """

    def __init__(self, root: Path | None = None) -> None:
        paths = RuntimePaths.from_env()
        self.root = root or (paths.events / "execution")
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, trace: ExecutionTrace) -> None:
        trace.updated_at = datetime.now(timezone.utc).isoformat()
        path = self._path(trace.id)
        path.write_text(json.dumps(trace.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, trace_id: str) -> ExecutionTrace | None:
        path = self._path(trace_id)
        if not path.exists():
            return None
        return ExecutionTrace.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_open(self, agent_id: str | None = None) -> tuple[ExecutionTrace, ...]:
        traces: list[ExecutionTrace] = []
        for path in sorted(self.root.glob("*.json")):
            trace = ExecutionTrace.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if trace.status in {ExecutionStatus.DONE, ExecutionStatus.SKIPPED}:
                continue
            if agent_id is not None and trace.agent_id != agent_id:
                continue
            traces.append(trace)
        return tuple(traces)

    def _path(self, trace_id: str) -> Path:
        return self.root / f"{trace_id}.json"


__all__ = ["ExecutionRepository", "ExecutionTrace", "FileExecutionRepository"]
