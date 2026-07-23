"""Central runtime path resolver — instance-scoped."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    root: Path

    @classmethod
    def from_env(cls) -> "RuntimePaths":
        root = Path(os.environ.get("L4_HOME", Path.cwd())).expanduser().resolve()
        return cls(root=root)

    @property
    def data(self) -> Path:
        """apps/{id}/data/ — canonical runtime data root."""
        return self.root / "apps" / _instance_id() / "data"

    @property
    def db(self) -> Path:
        return self.data / "db"

    @property
    def events(self) -> Path:
        return self.data / "events"

    @property
    def memories(self) -> Path:
        return self.data / "memories"

    @property
    def workspaces(self) -> Path:
        return self.data / "workspaces"

    # Legacy compatibility properties
    @property
    def runtime(self) -> Path:
        return self.data


def _instance_id() -> str:
    return (
        os.environ.get("DIGITAL_LIFE_INSTANCE_ID")
        or os.environ.get("L4_AGENT_ID")
        or os.environ.get("DIGITAL_LIFE_EMPLOYEE_ID")
        or "zero"
    ).strip("/") or "zero"

