"""Lifecycle migration split model.

This file describes how the old Hermes lifecycle extension modules are split
into L4's layer-first architecture during the migration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LifecycleLayer(str, Enum):
    MEMORY = "memory_layer"
    ORCHESTRATION = "orchestration_layer"
    EXECUTION = "execution_layer"
    FEEDBACK = "feedback_layer"


@dataclass(frozen=True)
class LifecycleSourceSlice:
    source_module: str
    layer: LifecycleLayer
    target_package: str
    responsibility: str
    adapter_boundary: str


__all__ = ["LifecycleLayer", "LifecycleSourceSlice"]
