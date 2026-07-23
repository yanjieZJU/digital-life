"""Storage provider placeholders owned by infrastructure."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass
class InMemoryRepository:
    """Small repository implementation used by boundary tests and local wiring."""

    values: dict[str, Mapping[str, Any]] = field(default_factory=dict)

    def get(self, key: str) -> Mapping[str, Any] | None:
        return self.values.get(key)

    def put(self, key: str, value: Mapping[str, Any]) -> None:
        self.values[key] = dict(value)


__all__ = ["InMemoryRepository"]

