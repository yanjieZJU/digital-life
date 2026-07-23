"""Tool registry."""

from __future__ import annotations

from domain.core.models import ToolDefinition


class InMemoryToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def list_allowed(self, names: tuple[str, ...]) -> tuple[ToolDefinition, ...]:
        if not names:
            return ()
        if "*" in names:
            return self.list_all()
        allowed: list[ToolDefinition] = []
        for name in names:
            if name.endswith(".*"):
                prefix = name[:-2]
                allowed.extend(tool for tool in self._tools.values() if tool.toolset == prefix)
                continue
            tool = self._tools.get(name)
            if tool:
                allowed.append(tool)
        return tuple(allowed)

    def list_all(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tools.values())
