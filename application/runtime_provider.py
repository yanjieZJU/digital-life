"""Runtime provider bootstrap for application workflows."""

from __future__ import annotations

import importlib
import os
from functools import lru_cache
from typing import Any


DEFAULT_RUNTIME_PROVIDER = "l4"

_PROVIDER_MODULES = {
    "l4": "infrastructure.ai.task_runtime",
}

_CONSOLE_PROVIDER_MODULES = {
    "l4": "infrastructure.console.adapter",
}


@lru_cache(maxsize=1)
def configure_runtime_provider() -> str:
    """Configure domain runtime hooks for the selected agent provider."""
    provider = (
        os.getenv("DIGITAL_LIFE_RUNTIME_PROVIDER")
        or os.getenv("DIGITAL_LIFE_AGENT_PROVIDER")
        or DEFAULT_RUNTIME_PROVIDER
    ).strip().lower()
    module_name = _PROVIDER_MODULES.get(provider)
    if not module_name:
        raise RuntimeError(f"Unsupported digital life runtime provider: {provider}")
    module = importlib.import_module(module_name)
    configure = getattr(module, "configure_task_runtime", None)
    if callable(configure):
        configure()
    return provider


def runtime_provider_name() -> str:
    return (
        os.getenv("DIGITAL_LIFE_RUNTIME_PROVIDER")
        or os.getenv("DIGITAL_LIFE_AGENT_PROVIDER")
        or DEFAULT_RUNTIME_PROVIDER
    ).strip().lower()


@lru_cache(maxsize=1)
def console_runtime_adapter() -> Any:
    provider = runtime_provider_name()
    module_name = _CONSOLE_PROVIDER_MODULES.get(provider)
    if not module_name:
        raise RuntimeError(f"Unsupported digital life console provider: {provider}")
    return importlib.import_module(module_name)


__all__ = [
    "DEFAULT_RUNTIME_PROVIDER",
    "configure_runtime_provider",
    "console_runtime_adapter",
    "runtime_provider_name",
]
