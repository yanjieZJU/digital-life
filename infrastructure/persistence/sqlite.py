"""SQLite infrastructure facade.

Domain code imports this project-owned facade instead of importing ``sqlite3``
directly. A later step can replace this with repository/unit-of-work ports.
"""

from __future__ import annotations

import sqlite3 as _sqlite3

Connection = _sqlite3.Connection
Row = _sqlite3.Row


def connect(path: str) -> Connection:
    return _sqlite3.connect(path)


__all__ = ["Connection", "Row", "connect"]
