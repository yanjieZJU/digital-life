"""Event package loading primitives."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from domain.core.models import EventTriggerType, EventTypeDefinition


@dataclass(frozen=True)
class EventPackage:
    root: Path
    definition: EventTypeDefinition


def load_simple_manifest(root: Path) -> EventPackage:
    """Load the minimal line-based manifest used by the first event packages.

    This intentionally avoids a YAML dependency during the architecture phase.
    It supports `key: value` lines and ignores comments/blank lines.
    """
    manifest = root / "manifest.yaml"
    values: dict[str, str] = {}
    for raw_line in manifest.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')

    definition = EventTypeDefinition(
        type_id=values["type_id"],
        display_name=values.get("display_name", values["type_id"]),
        trigger_type=EventTriggerType(values.get("trigger_type", "external")),
        prompt_template=(root / values.get("prompt", "prompt.md")).read_text(encoding="utf-8"),
        allowed_tools=_csv_tuple(values.get("allowed_tools", "")),
        context_policy=_kv_policy(values.get("context_policy", "")),
        auth_policy=_kv_policy(values.get("auth_policy", "")),
    )
    return EventPackage(root=root, definition=definition)


def discover_event_packages(root: Path) -> tuple[EventPackage, ...]:
    """Discover event packages under a directory."""
    packages: list[EventPackage] = []
    if not root.exists():
        return ()
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "manifest.yaml").exists():
            continue
        packages.append(load_simple_manifest(child))
    return tuple(packages)


def definitions(packages: Iterable[EventPackage]) -> tuple[EventTypeDefinition, ...]:
    return tuple(package.definition for package in packages)


def _csv_tuple(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _kv_policy(value: str) -> dict[str, str]:
    """Parse a small `a=b,c=d` policy string.

    Event packages can move to real YAML later; this keeps bootstrapping
    dependency-free.
    """
    policy: dict[str, str] = {}
    for item in value.split(","):
        if "=" not in item:
            continue
        key, raw_value = item.split("=", 1)
        policy[key.strip()] = raw_value.strip()
    return policy
