"""Event runtime foundation for L4.

This package owns event type packages, type registration, queues, and trigger
coordination. Message payload normalization belongs in `backend.ingress_interactions`.
"""

from .event_packages import EventPackage, discover_event_packages, load_simple_manifest
from .consumers import EventConsumer, EventConsumptionResult
from .queue import InMemoryEventQueue, SQLiteEventQueue
from .registry import InMemoryEventRegistry, SQLiteEventRegistry
from .security import EventSecurityDecision, EventSecurityPolicy, sanitize_payload
from .service import EventService
from .triggers import EventTriggerRouter
from domain.lifecycle.event_bus import LegacyEventBus

__all__ = [
    "EventConsumer",
    "EventConsumptionResult",
    "EventPackage",
    "EventSecurityDecision",
    "EventSecurityPolicy",
    "EventService",
    "EventTriggerRouter",
    "InMemoryEventQueue",
    "InMemoryEventRegistry",
    "LegacyEventBus",
    "SQLiteEventQueue",
    "SQLiteEventRegistry",
    "discover_event_packages",
    "load_simple_manifest",
    "sanitize_payload",
]
