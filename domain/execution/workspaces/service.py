"""Workspace service contracts and small helpers."""

from __future__ import annotations

from typing import Protocol

from domain.core.models import Workspace, WorkspaceDetail


class WorkspaceRepository(Protocol):
    def list(self, status: str | None = None) -> tuple[Workspace, ...]: ...

    def get(self, workspace_id: str) -> WorkspaceDetail | None: ...

    def create(
        self,
        title: str,
        goal: str = "",
        priority: str = "medium",
        deadline: str | None = None,
    ) -> Workspace: ...

    def wake_context(self) -> str: ...


class WorkspaceService:
    """Thin business facade over a workspace repository."""

    def __init__(self, repository: WorkspaceRepository) -> None:
        self._repository = repository

    def list_active(self) -> tuple[Workspace, ...]:
        workspaces = self._repository.list()
        return tuple(ws for ws in workspaces if ws.status in {"active", "planned", "in_progress"})

    def get(self, workspace_id: str) -> WorkspaceDetail | None:
        return self._repository.get(workspace_id)

    def wake_context(self) -> str:
        return self._repository.wake_context()
