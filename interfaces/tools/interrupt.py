"""Interrupt state for local runtime tool calls."""

from __future__ import annotations

_interrupted = False


def interrupt() -> None:
    global _interrupted
    _interrupted = True


def clear_interrupt() -> None:
    global _interrupted
    _interrupted = False


def is_interrupted() -> bool:
    return _interrupted

