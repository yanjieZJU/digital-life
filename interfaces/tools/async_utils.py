"""Async helpers used by project-owned tool integrations."""

from __future__ import annotations

import asyncio
from typing import Awaitable, TypeVar

T = TypeVar("T")


def run_async(awaitable: Awaitable[T]) -> T:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    future = asyncio.run_coroutine_threadsafe(awaitable, loop)
    return future.result()

