"""Intake models for the orchestration MVP."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Callable, Literal

from ..types import ClarificationRequest, TaskAction, TaskContract


@dataclass(frozen=True)
class Intent:
    name: str
    domain: str
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IntentRule:
    intent: str
    domain: str = "general"
    confidence: float = 0.8
    include_any: tuple[str, ...] = ()
    include_all: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()

    def matches(self, text: str) -> bool:
        if self.include_any and not any(token in text for token in self.include_any):
            return False
        if self.include_all and not all(token in text for token in self.include_all):
            return False
        if self.patterns and not any(re.search(pattern, text) for pattern in self.patterns):
            return False
        return bool(self.include_any or self.include_all or self.patterns)


@dataclass(frozen=True)
class SlotSet:
    values: dict[str, Any] = field(default_factory=dict)
    missing_required: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SlotParser = Callable[[str], Any]
SlotValueType = Literal["string", "float", "int"]


@dataclass(frozen=True)
class SlotRule:
    name: str
    pattern: str
    group: str | int = 1
    value_type: SlotValueType = "string"
    parser: SlotParser | None = None

    def extract(self, text: str) -> Any:
        match = re.search(self.pattern, text)
        if match is None:
            return None
        raw = match.group(self.group)
        if self.parser is not None:
            return self.parser(raw)
        if self.value_type == "float":
            return float(raw)
        if self.value_type == "int":
            return int(raw)
        return str(raw).strip()


__all__ = [
    "ClarificationRequest",
    "Intent",
    "IntentRule",
    "SlotRule",
    "SlotSet",
    "TaskAction",
    "TaskContract",
]
