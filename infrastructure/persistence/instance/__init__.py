"""Per-instance DB layer.

Splits each instance's persistence into 4 .db files by purpose:
vitals / memory / runtime_log / workflow. Old single-file
``apps/<id>/data/state.db`` keeps running until callers migrate.

Modules in this package create and own SQLite connections for one
instance. Domain code should depend on per-area ports (in
``domain/persistence``) and not on the concrete SQLite classes here.
"""

from infrastructure.persistence.instance.base import InstanceDB
from infrastructure.persistence.instance.factory import (
    InstanceBundle,
    get_audit,
    get_instance_bundle,
    get_memory,
    get_vitals,
    get_workflow,
    reset_cache,
)

__all__ = [
    "InstanceDB",
    "InstanceBundle",
    "get_audit",
    "get_instance_bundle",
    "get_memory",
    "get_vitals",
    "get_workflow",
    "reset_cache",
]

