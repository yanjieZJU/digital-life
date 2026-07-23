"""Self-registered tool/skill capability system.

Public API — callers (interfaces/tools/capability_tools.py, scheduler,
frontend) interact through this package, not the internal modules.

Layers:
  paths.py   — scope → directory resolution (pure, no IO)
  store.py   — manifest.json CRD (metadata only, no business logic)
  lifecycle.py — full registration lifecycle (safety → write → store → hot-load)
"""

from domain.capability.lifecycle import register_tool, register_skill, RESERVED_TOOL_PREFIXES
from domain.capability.paths import resolve_tool_path, resolve_skill_path, project_root
from domain.capability.store import (
    list_all_tools,
    list_all_skills,
    list_my_tools_and_skills,
)

__all__ = [
    "register_tool",
    "register_skill",
    "RESERVED_TOOL_PREFIXES",
    "resolve_tool_path",
    "resolve_skill_path",
    "project_root",
    "list_all_tools",
    "list_all_skills",
    "list_my_tools_and_skills",
]
