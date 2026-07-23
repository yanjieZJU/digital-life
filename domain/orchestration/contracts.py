"""Orchestration contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class TaskNode:
    node_id: str
    goal: str
    dependencies: tuple[str, ...] = ()
    required_capability: str | None = None
    input_context: Mapping[str, object] = field(default_factory=dict)
    expected_output: str = ""
    completion_criteria: str = ""
    priority: str = "normal"


@dataclass(frozen=True)
class TaskList:
    task_list_id: str
    origin_bundle_id: str
    intent_summary: str
    nodes: tuple[TaskNode, ...]
    created_at: str = ""


__all__ = ["TaskList", "TaskNode"]

