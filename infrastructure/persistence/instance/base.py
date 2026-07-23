"""Base SQLite connection + schema bootstrap for per-instance .db files."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any


class InstanceDB:
    """Owns one SQLite file for one instance.

    Subclasses define ``SCHEMA_SQL`` (a list of CREATE statements executed
    on open) and helper read/write methods. Reads use ``row_factory=Row``
    so callers get dict-like rows. All access is serialized through one
    re-entrant lock per instance — same model as the legacy ``SessionDB``.
    """

    SCHEMA_SQL: tuple[str, ...] = ()

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(db_path), check_same_thread=False, timeout=5.0
        )
        self._conn.row_factory = sqlite3.Row
        # durability: WAL + FULL synchronous 让 commit 强制 fsync，避免系统睡眠/异常
        # 退出时 WAL 半写导致主库 b-tree 损坏（曾反复发生 rowid out of order 故障）。
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._apply_schema()

    def _apply_schema(self) -> None:
        if not self.SCHEMA_SQL:
            return
        with self._lock:
            cur = self._conn.executescript("\n\n".join(self.SCHEMA_SQL))
            self._conn.commit()
            return cur

    def execute(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, tuple(params))

    def executemany(self, sql: str, params_list: list[tuple[Any, ...]]) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.executemany(sql, params_list)

    def fetchone(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(sql, tuple(params)).fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def commit(self) -> None:
        with self._lock:
            self._conn.commit()

    def rollback(self) -> None:
        with self._lock:
            self._conn.rollback()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "InstanceDB":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
