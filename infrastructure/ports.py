"""Infrastructure port contracts."""

from __future__ import annotations

from typing import Any, Mapping, Protocol


class RepositoryPort(Protocol):
    def get(self, key: str) -> Mapping[str, Any] | None: ...

    def put(self, key: str, value: Mapping[str, Any]) -> None: ...


class UnitOfWorkPort(Protocol):
    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class QueuePort(Protocol):
    def publish(self, topic: str, payload: Mapping[str, Any]) -> None: ...


class CachePort(Protocol):
    def get(self, key: str) -> Any: ...

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None: ...


class ConfigPort(Protocol):
    def get(self, name: str, default: str | None = None) -> str | None: ...


__all__ = ["CachePort", "ConfigPort", "QueuePort", "RepositoryPort", "UnitOfWorkPort"]

