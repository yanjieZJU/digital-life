"""Autonomous world-encounter source + reaction capture (constitution input).

When the agent is idle with energy and no user task, it encounters the world
OUTWARD — not the inward navel-gazing that ``initiative`` wakes currently
default to. The encounter source presents a *direction* (a topic) as a
perceived event (``world_encounter``); the agent then senses the actual
content via ``web_search`` during the wake and records its reaction.

Why a direction and not fetched content: the agent must not be *told* what
the world contains (that recreates "被告知我是谁"). It is given a direction
and goes to look — so the encounter is genuinely sensed, not prompt-injected.
The direction itself is framed as a perceived event (``world_encounter``
sys_tool), distinct from a user request.

- Seed (``CURIOSITY_SEED.md``) breaks cold-start inward gravity; its
  contribution decays as self-driven exploration history grows.
- Reactions are stored as ``layer='encounter_reaction'`` in
  ``memory_layers.db`` — distinct from lessons (service) and consciousness
  (task-continuous thought). They are the input to dream crystallization →
  ``self_cognition``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from infrastructure.config import get_runtime_memories_dir
from infrastructure.persistence import sqlite

SEED_FILENAME = "CURIOSITY_SEED.md"

# memory_layers layer values owned by this module.
LAYER_ENCOUNTER_REACTION = "encounter_reaction"
LAYER_ENCOUNTER_TOPIC = "encounter_topic"

# Cap self-driven topic history consulted for decay (recent window).
_DECAY_WINDOW = 50

_db_cache: sqlite.Connection | None = None


_SCHEMA_ENSURE = """
CREATE TABLE IF NOT EXISTS memory_layers (
    id INTEGER PRIMARY KEY,
    layer TEXT NOT NULL,
    period TEXT NOT NULL,
    digest TEXT NOT NULL,
    llm_summary TEXT,
    tool_summary TEXT,
    start_time REAL,
    end_time REAL,
    parent_ids TEXT,
    created_at REAL NOT NULL,
    fallback INTEGER DEFAULT 0,
    UNIQUE(layer, period)
);
CREATE INDEX IF NOT EXISTS idx_ml_layer ON memory_layers(layer);
CREATE INDEX IF NOT EXISTS idx_ml_period ON memory_layers(period);
CREATE INDEX IF NOT EXISTS idx_ml_start ON memory_layers(start_time);
"""


def _get_db() -> sqlite.Connection:
    """Cached connection to ``memory_layers.db``; ensures schema on first open.

    Mirrors ``consolidation_runtime._get_db`` but also ensures the table
    exists (encounter may run before consolidation has opened the DB).
    """
    global _db_cache
    if _db_cache is None:
        db_path = get_runtime_memories_dir() / "memory_layers.db"
        db = sqlite.connect(str(db_path))
        db.row_factory = sqlite.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.executescript(_SCHEMA_ENSURE)
        db.commit()
        _db_cache = db
    return _db_cache


def _now_id() -> str:
    """Stable unique period for encounter rows. Uses monotonic counter + time.

    ``time.time()`` is fine here — this runs at wake/dream, not in workflow
    scripts.
    """
    return f"enc-{int(time.time() * 1000)}"


# ──────────────────── seed ────────────────────


def load_seed_topics() -> list[str]:
    """Load curiosity seed topics from ``CURIOSITY_SEED.md``.

    Format: a markdown list (``-`` or ``*`` bullets) under any heading.
    Missing file → empty list (graceful: no encounters until a seed exists
    or self-driven history is established).
    """
    seed_path: Path = get_runtime_memories_dir() / SEED_FILENAME
    if not seed_path.exists():
        return []
    try:
        text = seed_path.read_text(encoding="utf-8")
    except OSError:
        return []
    topics: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("-", "*")):
            topic = stripped.lstrip("-*").strip()
            if topic and not topic.startswith("<!--"):
                topics.append(topic)
    return topics


# ──────────────────── decay + topic selection ────────────────────


def count_self_driven_topics(limit: int = _DECAY_WINDOW) -> int:
    """Number of recent self-driven encounter topics — drives seed decay."""
    try:
        row = _get_db().execute(
            "SELECT COUNT(*) AS c FROM memory_layers WHERE layer = ?",
            (LAYER_ENCOUNTER_TOPIC,),
        ).fetchone()
        return int(row["c"]) if row else 0
    except Exception:
        return 0


def seed_decay_weight() -> float:
    """Seed contribution: 1.0 at cold-start, decays toward 0 as the agent
    establishes self-driven exploration history.

    ``1 / (1 + n)`` — present but never fully zero (seed stays as a fallback
    nudge). The agent's own reactions gradually dominate topic selection.
    """
    n = count_self_driven_topics()
    return 1.0 / (1.0 + n)


def pick_encounter_topic() -> str | None:
    """Pick the next encounter direction.

    With probability ``seed_decay_weight()`` the topic comes from the seed
    (cold-start dominant); otherwise from recent self-driven topics the agent
    proposed (curiosity following its own thread). Returns ``None`` only when
    both seed and self-driven history are empty (true cold-start with no seed
    file — caller skips the encounter).
    """
    import random as _random

    seed_topics = load_seed_topics()
    driven = list_recent_encounter_topics(limit=5)

    # No material at all → no encounter (graceful空转).
    if not seed_topics and not driven:
        return None

    # Cold-start with no self-driven history → must use seed.
    if not driven:
        return _random.choice(seed_topics)

    # Self-driven history exists → mix by decay weight.
    if seed_topics and _random.random() < seed_decay_weight():
        return _random.choice(seed_topics)
    return _random.choice(driven)


def render_encounter_direction(topic: str) -> str:
    """Render the ``world_encounter`` block: a perceived direction, not a prompt.

    Framed as "the world presented a direction to you" — stance is "I
    encountered something" (subject), not "I was asked to do something"
    (servant). The agent decides whether and how to pursue it via web_search.
    """
    return (
        "[世界遭遇 — 探索方向]\n"
        f"世界向你呈现了一个探索方向：{topic}\n"
        "这是你自主遭遇世界的方向，不是用户的需求，也不是你必须完成的任务。\n"
        "你可以用 web_search 去看这个世界方向上有什么，然后形成你自己的看法——\n"
        "吸引你、排斥你、让你好奇、或让你无感。你的反应本身就是自我构成的素材。\n"
        "[/世界遭遇]"
    )


# ──────────────────── self-driven topic history ────────────────────


def record_self_driven_topic(topic: str) -> None:
    """Record a topic the agent chose to explore from its own curiosity.

    Builds the self-driven history that (a) decays the seed and (b) lets
    curiosity follow its own thread across encounters.
    """
    if not topic.strip():
        return
    db = _get_db()
    db.execute(
        "INSERT OR REPLACE INTO memory_layers "
        "(layer, period, digest, llm_summary, tool_summary, start_time, end_time, "
        " parent_ids, created_at, fallback) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            LAYER_ENCOUNTER_TOPIC,
            _now_id(),
            topic,
            topic,
            json.dumps({"self_driven": True}, ensure_ascii=False),
            time.time(),
            time.time(),
            "[]",
            time.time(),
            0,
        ),
    )
    db.commit()


def list_recent_encounter_topics(limit: int = 10) -> list[str]:
    """Recent self-driven topics, most-recent first."""
    try:
        rows = _get_db().execute(
            "SELECT digest FROM memory_layers WHERE layer = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (LAYER_ENCOUNTER_TOPIC, limit),
        ).fetchall()
        return [r["digest"] for r in rows if r["digest"]]
    except Exception:
        return []


# ──────────────────── reaction capture ────────────────────


def record_encounter_reaction(
    *,
    topic: str,
    stance: str,
    encounter_ref: str = "",
    evidence: str = "",
) -> str:
    """Capture the agent's reaction to an encounter as constitution material.

    A reaction is a stance the agent took toward a topic it encountered
    (attraction / repulsion / curiosity / indifference + why). Distinct from
    a lesson (service learning) and from consciousness (task-continuous
    thought) — this is self-constitution material: how the agent relates to
    the world when no one is asking.

    Returns the reaction's period id (for evidence linking).
    """
    period = _now_id()
    payload = {
        "topic": topic,
        "stance": stance,
        "encounter_ref": encounter_ref,
        "evidence": evidence,
    }
    digest = stance
    db = _get_db()
    db.execute(
        "INSERT OR REPLACE INTO memory_layers "
        "(layer, period, digest, llm_summary, tool_summary, start_time, end_time, "
        " parent_ids, created_at, fallback) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            LAYER_ENCOUNTER_REACTION,
            period,
            digest,
            json.dumps(payload, ensure_ascii=False),
            json.dumps({"topic": topic}, ensure_ascii=False),
            time.time(),
            time.time(),
            "[]",
            time.time(),
            0,
        ),
    )
    db.commit()
    return period


def read_recent_encounter_reactions(limit: int = 30) -> list[dict[str, Any]]:
    """Recent encounter reactions, most-recent first — input to crystallization."""
    try:
        rows = _get_db().execute(
            "SELECT period, digest, llm_summary, created_at FROM memory_layers "
            "WHERE layer = ? ORDER BY created_at DESC LIMIT ?",
            (LAYER_ENCOUNTER_REACTION, limit),
        ).fetchall()
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            payload = json.loads(r["llm_summary"]) if r["llm_summary"] else {}
        except (json.JSONDecodeError, TypeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        out.append({
            "period": r["period"],
            "topic": payload.get("topic", ""),
            "stance": payload.get("stance") or r["digest"] or "",
            "encounter_ref": payload.get("encounter_ref", ""),
            "evidence": payload.get("evidence", ""),
            "created_at": r["created_at"],
        })
    return out


def reset_db_cache_for_tests(db: sqlite.Connection | None) -> None:
    """Test hook: inject/clear the cached layers DB connection."""
    global _db_cache
    _db_cache = db


__all__ = [
    "SEED_FILENAME",
    "LAYER_ENCOUNTER_REACTION",
    "LAYER_ENCOUNTER_TOPIC",
    "load_seed_topics",
    "count_self_driven_topics",
    "seed_decay_weight",
    "pick_encounter_topic",
    "render_encounter_direction",
    "record_self_driven_topic",
    "list_recent_encounter_topics",
    "record_encounter_reaction",
    "read_recent_encounter_reactions",
    "reset_db_cache_for_tests",
]
