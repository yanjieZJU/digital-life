"""Affair / WaitIntent 数据模型 + SQLite 持久化。

所有 L4 持久状态落在实例的 state.db（apps/{uuid}/data/state.db），
与 Hermes 现有 session/messages 共用一个库。

新增表（L4 核心持久化）：
  affairs      — 长程事务元数据（状态机：BLOCKED ↔ RUNNING → DONE）
  wait_intents — 事务当前等待意图（1:1 于 affair，BLOCKED 时有值）
  events       — 事件总线队列（gateway/webhook 写入，scheduler 消费）
  heartbeats   — 心跳审计记录
  vitals       — 精力状态（能量值 + 更新时间）
  wallet       — 钱包余额 + 持仓
  nurture_log  — 养育动作日志
  timers       — 定时器

关键设计：
  - configure_runtime_hooks() 注入 db_path / now_iso 等运行时依赖
  - _conn() 上下文管理器提供 SQLite 连接（busy_timeout=5000 避免锁竞争）
  - init_db() 幂等建表（CREATE TABLE IF NOT EXISTS）
  - CRUD 函数操作 affairs / wait_intents / events / heartbeats
  - vitals 读取包含时间衰减计算（elapsed_h × DECAY 系数）
"""

from __future__ import annotations

import json
import sqlite3 as _real_sqlite3
from contextlib import contextmanager
from infrastructure.persistence import sqlite
from pathlib import Path
from typing import Optional, List, Dict, Any, Generator

from . import (  # noqa: E402
    Affair,
    WaitIntent,
    normalize_affair_update_fields,
)
from ..clock import now_dt as _default_now_dt
from ..clock import now_iso as _default_now_iso
from ..clock import parse_iso as _default_parse_iso
from ..state_machine import AffairStatus, WaitType

def _resolve_default_state_db() -> str:
    """解析默认 state.db 路径：优先走 infrastructure 配置兜底到 apps/zero/data/state.db。"""
    try:
        from infrastructure.config import get_runtime_state_db_path
        return str(get_runtime_state_db_path())
    except Exception:
        # 不再 fallback 到 apps/zero/data/state.db。
        # fresh clone 没有 zero 实例时这里写出来的是脏路径——抛错让根因可见。
        raise RuntimeError(
            "state.db 路径未配置：调 get_runtime_state_db_path 失败。"
            "确认 DIGITAL_LIFE_INSTANCE_ID 已设、对应实例已经 digital-life init 初始化。"
        )


_db_path_hook = lambda: Path(_resolve_default_state_db())
_now_iso_hook = _default_now_iso
_now_dt_hook = _default_now_dt
_parse_iso_hook = _default_parse_iso
AFFAIR_UPDATE_COLUMNS = {
    "goal",
    "status",
    "priority",
    "deadline",
    "session_id",
    "mental_context",
    "history_digest",
    "updated_at",
    "completed_at",
    "meta_json",
}


def configure_runtime_hooks(
    *,
    db_path: Any | None = None,
    now_iso: Any | None = None,
    now_dt: Any | None = None,
    parse_iso: Any | None = None,
) -> None:
    """注入适配器/Hermes 提供的运行时服务（db_path / now_iso / now_dt / parse_iso）。"""
    global _db_path_hook, _now_iso_hook, _now_dt_hook, _parse_iso_hook
    if db_path is not None:
        _db_path_hook = db_path if callable(db_path) else lambda: Path(db_path)
    if now_iso is not None:
        _now_iso_hook = now_iso
    if now_dt is not None:
        _now_dt_hook = now_dt
    if parse_iso is not None:
        _parse_iso_hook = parse_iso


def now_iso() -> str:
    """返回当前 UTC 时间（ISO8601），委托给注入的 _now_iso_hook。"""
    return _now_iso_hook()


def _get_db_path() -> Path:
    """返回当前实例的 state.db 路径，委托给注入的 _db_path_hook。"""
    return Path(_db_path_hook())


SCHEMA = """
CREATE TABLE IF NOT EXISTS affairs (
    affair_id        TEXT PRIMARY KEY,
    goal             TEXT NOT NULL,
    status           TEXT NOT NULL,
    priority         INTEGER NOT NULL DEFAULT 0,
    deadline         TEXT,
    session_id       TEXT,
    mental_context   TEXT,
    history_digest   TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    completed_at     TEXT,
    meta_json        TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_affairs_status   ON affairs(status);
CREATE INDEX IF NOT EXISTS idx_affairs_priority ON affairs(priority DESC);

CREATE TABLE IF NOT EXISTS wait_intents (
    affair_id        TEXT PRIMARY KEY REFERENCES affairs(affair_id) ON DELETE CASCADE,
    wait_type        TEXT NOT NULL,          -- until | event | condition
    resume_when      TEXT NOT NULL,          -- ISO8601 | channel expr | check_skill
    interval_seconds INTEGER,                -- 仅 condition 用
    max_wait_until   TEXT,                   -- 兜底绝对截止时间
    reason           TEXT,                   -- agent 说明为何 block
    resume_action    TEXT,                   -- 唤醒后第一步做啥
    blocked_at       TEXT NOT NULL,
    meta_json        TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS events (
    event_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    channel          TEXT NOT NULL,
    payload          TEXT NOT NULL,          -- JSON
    created_at       TEXT NOT NULL,
    fire_at          TEXT,                   -- 预定触发时间(可为 NULL)
    kind             TEXT,                   -- 事件类型
    consumed_at      TEXT,                   -- NULL 未消费
    target_affair_id TEXT                    -- 投递后填
);

CREATE INDEX IF NOT EXISTS idx_events_unconsumed ON events(consumed_at, channel);

CREATE TABLE IF NOT EXISTS heartbeats (
    hb_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    fired_at         TEXT NOT NULL,
    woke_affair_id   TEXT,
    reflect          INTEGER NOT NULL DEFAULT 0,   -- 0/1 是否触发了 reflection
    notes            TEXT
);

-- ═══════════════════════════════════════════════════════════════
-- 生命状态（合并后，不再用 simulation.db）
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS vitals (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    energy           REAL NOT NULL DEFAULT 70.0,
    updated_at       TEXT NOT NULL,
    last_nurture     TEXT
);

CREATE TABLE IF NOT EXISTS wallet (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    balance          REAL NOT NULL DEFAULT 100.0,
    positions_json   TEXT NOT NULL DEFAULT '{}'  -- {"AAPL": {"shares": 10, "avg_cost": 150.0}}
);

CREATE TABLE IF NOT EXISTS nurture_log (
    log_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    at               TEXT NOT NULL,
    kind             TEXT NOT NULL,       -- feed/pet/groom/play/scold/chat/transfer_in
    deltas_json      TEXT NOT NULL,       -- {"satiety": +15, "mood": +3}
    raw_text         TEXT,                -- 触发这次养育的人类消息原文
    source           TEXT                 -- lark/cli/webhook
);

CREATE INDEX IF NOT EXISTS idx_nurture_at ON nurture_log(at DESC);

CREATE TABLE IF NOT EXISTS timers (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    event_kind       TEXT NOT NULL,
    fire_at          TEXT NOT NULL,
    payload_json     TEXT NOT NULL DEFAULT '{}',
    created_at       TEXT NOT NULL,
    fired_at         TEXT
);

CREATE INDEX IF NOT EXISTS idx_timers_due ON timers(fired_at, fire_at);
"""


def init_db(db_path: Optional[Path] = None) -> Path:
    """幂等初始化所有 L4 表（建表 + 历史字段清理迁移）。"""
    path = db_path or _get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _real_sqlite3.connect(str(path))
    # durability：ALL/FULL synchronous 让 schema 初始化时也走 fsync，跟 _conn() 对齐。
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA busy_timeout = 5000;")
    try:
        conn.executescript(SCHEMA)
        # Migration: drop pre-energy-only dimension columns
        for col in ("satiety", "mood", "hygiene", "bond"):
            try:
                sql = "ALTER TABLE vitals DROP COLUMN " + col
                conn.execute(sql)
            except Exception:
                pass
        conn.commit()
    finally:
        conn.close()
    return path


@contextmanager
def _conn() -> Generator[sqlite.Connection, None, None]:
    """SQLite 连接上下文管理器——自动设置 row_factory、foreign_keys、busy_timeout。"""
    c = _real_sqlite3.connect(str(_get_db_path()), timeout=10, isolation_level=None)
    c.row_factory = sqlite.Row
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA synchronous=FULL;")
    c.execute("PRAGMA foreign_keys = ON;")
    c.execute("PRAGMA busy_timeout = 5000;")
    try:
        yield c
    finally:
        c.close()


# ---------------- CRUD ----------------

def create_affair(goal: str, priority: int = 0, deadline: Optional[str] = None,
                  meta: Optional[Dict[str, Any]] = None) -> Affair:
    """创建新事务（初始状态 BLOCKED），写入 affairs 表。"""
    init_db()
    a = Affair(
        affair_id=Affair.new_id(),
        goal=goal,
        status=AffairStatus.BLOCKED,
        priority=priority,
        deadline=deadline,
        meta=meta or {},
    )
    row = a.to_row()
    with _conn() as c:
        c.execute(
            """INSERT INTO affairs
               (affair_id, goal, status, priority, deadline, session_id, mental_context,
                history_digest, created_at, updated_at, completed_at, meta_json)
               VALUES (:affair_id, :goal, :status, :priority, :deadline, :session_id,
                       :mental_context, :history_digest, :created_at, :updated_at,
                       :completed_at, :meta_json)""",
            row,
        )
    return a


def get_affair(affair_id: str) -> Optional[Affair]:
    """按 affair_id 读取单个事务，不存在返回 None。"""
    with _conn() as c:
        row = c.execute("SELECT * FROM affairs WHERE affair_id = ?", (affair_id,)).fetchone()
        return Affair.from_row(row) if row else None


def list_affairs(status: Optional[AffairStatus] = None) -> List[Affair]:
    """列出事务（可按状态过滤），按优先级降序 + 创建时间升序排列。"""
    init_db()
    q = "SELECT * FROM affairs"
    params: tuple = ()
    if status is not None:
        q += " WHERE status = ?"
        params = (status.value,)
    q += " ORDER BY priority DESC, created_at ASC"
    with _conn() as c:
        return [Affair.from_row(r) for r in c.execute(q, params).fetchall()]


def update_affair(affair_id: str, **fields) -> None:
    """部分更新 affair 字段（只更新传入的字段），自动追加 updated_at。"""
    if not fields:
        return
    fields = normalize_affair_update_fields(fields, now_iso())
    fields = {key: value for key, value in fields.items() if key in AFFAIR_UPDATE_COLUMNS}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    fields["affair_id"] = affair_id
    with _conn() as c:
        sql = "UPDATE affairs SET " + set_clause + " WHERE affair_id = :affair_id"
        c.execute(sql, fields)


def set_wait_intent(affair_id: str, intent: WaitIntent) -> None:
    """保存事务的等待意图，并把事务状态置 BLOCKED。"""
    row = intent.to_row(affair_id)
    with _conn() as c:
        c.execute(
            """INSERT INTO wait_intents
               (affair_id, wait_type, resume_when, interval_seconds, max_wait_until,
                reason, resume_action, blocked_at, meta_json)
               VALUES (:affair_id, :wait_type, :resume_when, :interval_seconds,
                       :max_wait_until, :reason, :resume_action, :blocked_at, :meta_json)
               ON CONFLICT(affair_id) DO UPDATE SET
                 wait_type=excluded.wait_type,
                 resume_when=excluded.resume_when,
                 interval_seconds=excluded.interval_seconds,
                 max_wait_until=excluded.max_wait_until,
                 reason=excluded.reason,
                 resume_action=excluded.resume_action,
                 blocked_at=excluded.blocked_at,
                 meta_json=excluded.meta_json
            """,
            row,
        )
        c.execute(
            "UPDATE affairs SET status = ?, updated_at = ? WHERE affair_id = ?",
            (AffairStatus.BLOCKED.value, now_iso(), affair_id),
        )


def get_wait_intent(affair_id: str) -> Optional[WaitIntent]:
    """获取事务当前的等待意图，无则返回 None。"""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM wait_intents WHERE affair_id = ?", (affair_id,)
        ).fetchone()
        return WaitIntent.from_row(row) if row else None


def clear_wait_intent(affair_id: str) -> None:
    """删除事务的等待意图（退出 BLOCKED 状态时调用）。"""
    with _conn() as c:
        c.execute("DELETE FROM wait_intents WHERE affair_id = ?", (affair_id,))


def enqueue_event(channel: str, payload: Dict[str, Any]) -> int:
    """写入一个事件到 events 表（网关/webhook 调用），返回 event_id。"""
    init_db()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO events (channel, payload, created_at) VALUES (?, ?, ?)",
            (channel, json.dumps(payload, ensure_ascii=False), now_iso()),
        )
        return cur.lastrowid


def list_unconsumed_events(channel_like: Optional[str] = None) -> List[sqlite.Row]:
    """列出未消费事件（按 channel 前缀过滤），按 event_id ASC 排序。"""
    q = "SELECT * FROM events WHERE consumed_at IS NULL"
    params: tuple = ()
    if channel_like:
        q += " AND channel LIKE ?"
        params = (channel_like,)
    q += " ORDER BY event_id ASC"
    with _conn() as c:
        return c.execute(q, params).fetchall()


def record_heartbeat(woke_affair_id: Optional[str], reflect: bool, notes: str = "") -> int:
    """记录一次心跳到 heartbeats 表，返回 hb_id。"""
    init_db()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO heartbeats (fired_at, woke_affair_id, reflect, notes) VALUES (?, ?, ?, ?)",
            (now_iso(), woke_affair_id, 1 if reflect else 0, notes),
        )
        return cur.lastrowid


def count_recent_heartbeats(since_iso: str) -> int:
    """统计最近 heartbeat 次数。"""
    with _conn() as c:
        row = c.execute(
            "SELECT COUNT(*) AS n FROM heartbeats WHERE fired_at >= ?", (since_iso,)
        ).fetchone()
        return int(row["n"]) if row else 0


# ─────────────────────────────────────────────────────────────────────────────
# 生命状态（vitals）— 合并后走 state.db
# ─────────────────────────────────────────────────────────────────────────────

def get_vitals() -> Dict[str, float]:
    """读取 vitals（含时间衰减计算）。"""
    init_db()
    with _conn() as c:
        row = c.execute("SELECT * FROM vitals WHERE id = 1").fetchone()
    if not row:
        return {"energy": 70.0}

    updated_at = _parse_iso_hook(row["updated_at"])
    elapsed_h = max(0.0, (_now_dt_hook() - updated_at).total_seconds() / 3600.0)

    DECAY = {"energy": -40.0}
    return {
        dim: max(0, min(100, row[dim] - DECAY[dim] * elapsed_h))
        for dim in ("energy",)
    }


def save_vitals(vitals: Dict[str, float]) -> None:
    """保存 vitals 到 DB（updated_at 设为当前）。"""
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO vitals (id, energy, updated_at) "
            "VALUES (1, :energy, :updated_at)",
            {**vitals, "updated_at": now_iso()},
        )


def log_nurture(kind: str, deltas: Dict[str, float], raw_text: str = "", source: str = "") -> None:
    """记录一次养育动作。"""
    init_db()
    with _conn() as c:
        c.execute(
            "INSERT INTO nurture_log (at, kind, deltas_json, raw_text, source) VALUES (?, ?, ?, ?, ?)",
            (now_iso(), kind, json.dumps(deltas, ensure_ascii=False), raw_text, source),
        )


def get_nurture_log(hours: int = 24) -> List[Dict]:
    """获取最近 N 小时的养育记录。"""
    init_db()
    from datetime import timedelta
    since = (_now_dt_hook() - timedelta(hours=hours)).isoformat(timespec="seconds")
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM nurture_log WHERE at >= ? ORDER BY at DESC", (since,)
        ).fetchall()
    return [
        {
            "at": r["at"], "kind": r["kind"],
            "deltas": json.loads(r["deltas_json"]),
            "raw_text": r["raw_text"] or "",
            "source": r["source"] or "",
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 钱包（wallet）— 合并后走 state.db
# ─────────────────────────────────────────────────────────────────────────────

def get_wallet() -> Dict:
    """读取钱包（含持仓）。"""
    init_db()
    with _conn() as c:
        row = c.execute("SELECT * FROM wallet WHERE id = 1").fetchone()
    if not row:
        return {"balance": 100.0, "positions": {}}
    positions = json.loads(row["positions_json"] or "{}")
    return {"balance": row["balance"], "positions": positions}


def save_wallet(balance: float, positions: Dict) -> None:
    """保存钱包到 DB。"""
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO wallet (id, balance, positions_json) VALUES (1, ?, ?)",
            (balance, json.dumps(positions, ensure_ascii=False)),
        )
