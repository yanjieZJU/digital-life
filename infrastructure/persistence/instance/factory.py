"""Per-instance persistence factory.

One entry point for callers that need the 4 persistence ports bound to a
specific instance. The factory memoizes one connection per (kind,
instance_id) pair; instance code should obtain ports via:

    from infrastructure.persistence.instance import get_audit, get_memory

or all four at once::

    bundle = get_instance_bundle(instance_id)
    bundle.audit.create_wake(...)
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any

from infrastructure.config import get_app_instance_id
from infrastructure.persistence.instance.memory import MemoryDB
from infrastructure.persistence.instance.runtime_log import RuntimeLogDB
from infrastructure.persistence.instance.vitals import VitalsDB
from infrastructure.persistence.instance.workflow import WorkflowDB


@dataclass(frozen=True)
class InstanceBundle:
    audit: RuntimeLogDB
    memory: MemoryDB
    vitals: VitalsDB
    workflow: WorkflowDB

    @property
    def instance_id(self) -> str:
        return self.audit.instance_id or self.memory.instance_id


_BUNDLE_CACHE: dict[str, InstanceBundle] = {}
_CACHE_LOCK = RLock()


def get_instance_bundle(instance_id: str | None = None) -> InstanceBundle:
    """Return the 4-port bundle for ``instance_id`` (memoized per instance).

    Falls back to the current infra ContextVar instance id when None.
    """
    iid = instance_id or get_app_instance_id() or "adhoc"
    with _CACHE_LOCK:
        cached = _BUNDLE_CACHE.get(iid)
        if cached:
            return cached
        bundle = InstanceBundle(
            audit=RuntimeLogDB(instance_id=iid),
            memory=MemoryDB(instance_id=iid),
            vitals=VitalsDB(instance_id=iid),
            workflow=WorkflowDB(instance_id=iid),
        )
        _BUNDLE_CACHE[iid] = bundle
        return bundle


def get_audit(instance_id: str | None = None) -> RuntimeLogDB:
    """Convenience: just the audit (runtime_log) port."""
    return get_instance_bundle(instance_id).audit


def get_memory(instance_id: str | None = None) -> MemoryDB:
    return get_instance_bundle(instance_id).memory


def get_vitals(instance_id: str | None = None) -> VitalsDB:
    return get_instance_bundle(instance_id).vitals


def get_workflow(instance_id: str | None = None) -> WorkflowDB:
    return get_instance_bundle(instance_id).workflow


def reset_cache() -> None:
    """Drop all cached bundles (mostly for tests)."""
    with _CACHE_LOCK:
        for bundle in _BUNDLE_CACHE.values():
            for db in (bundle.audit, bundle.memory, bundle.vitals, bundle.workflow):
                try:
                    db.close()
                except Exception:
                    pass
        _BUNDLE_CACHE.clear()


__all__: list[str] = [
    "InstanceBundle",
    "get_instance_bundle",
    "get_audit",
    "get_memory",
    "get_vitals",
    "get_workflow",
    "reset_cache",
]
