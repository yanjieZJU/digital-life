"""Tests for the encounter source + reaction capture (constitution input).

Covers seed loading, cold-start graceful空转, seed decay, self-driven topic
history, reaction capture as a distinct layer, and the world-encounter
direction rendering (perceived event, not a user prompt).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _setup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    mem_dir = tmp_path / "memories"
    mem_dir.mkdir()
    from domain.memory.memory import encounter as enc

    monkeypatch.setattr(enc, "get_runtime_memories_dir", lambda: mem_dir)
    enc.reset_db_cache_for_tests(None)
    return enc, mem_dir


def test_seed_missing_graceful_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No seed file + no self-driven history → no encounter (graceful空转)."""
    enc, _ = _setup(monkeypatch, tmp_path)
    assert enc.load_seed_topics() == []
    assert enc.pick_encounter_topic() is None


def test_seed_loaded_from_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    enc, mem_dir = _setup(monkeypatch, tmp_path)
    (mem_dir / enc.SEED_FILENAME).write_text(
        "# 好奇心种子\n- 量子计算\n- 涌现悖论\n<!-- a comment -->\n",
        encoding="utf-8",
    )
    assert enc.load_seed_topics() == ["量子计算", "涌现悖论"]


def test_pick_uses_seed_at_cold_start(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Cold start (no self-driven history) → topic must come from the seed."""
    enc, mem_dir = _setup(monkeypatch, tmp_path)
    (mem_dir / enc.SEED_FILENAME).write_text("# s\n- A\n- B\n", encoding="utf-8")
    for _ in range(12):
        assert enc.pick_encounter_topic() in ("A", "B")


def test_seed_decay_with_self_driven_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Seed weight is 1.0 at cold start and decays as self-driven history grows."""
    enc, _ = _setup(monkeypatch, tmp_path)
    assert enc.seed_decay_weight() == 1.0
    enc.record_self_driven_topic("X")
    enc.record_self_driven_topic("Y")
    assert enc.count_self_driven_topics() == 2
    w = enc.seed_decay_weight()
    assert 0.0 < w < 1.0


def test_reaction_recorded_and_read_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    enc, _ = _setup(monkeypatch, tmp_path)
    pid = enc.record_encounter_reaction(
        topic="涌现悖论", stance="这让我着迷，想搞清楚", encounter_ref="web:xxx",
    )
    assert pid
    reactions = enc.read_recent_encounter_reactions()
    assert len(reactions) == 1
    r = reactions[0]
    assert r["topic"] == "涌现悖论"
    assert r["stance"] == "这让我着迷，想搞清楚"
    assert r["encounter_ref"] == "web:xxx"


def test_reaction_uses_distinct_layer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Reactions live in their own layer, not mixed into session digests."""
    enc, _ = _setup(monkeypatch, tmp_path)
    enc.record_encounter_reaction(topic="T", stance="S")
    db = enc._get_db()
    layers = [row[0] for row in db.execute(
        "SELECT DISTINCT layer FROM memory_layers").fetchall()]
    assert enc.LAYER_ENCOUNTER_REACTION in layers
    # Not polluting the session-digest layer.
    session_rows = db.execute(
        "SELECT COUNT(*) FROM memory_layers WHERE layer='session'").fetchone()
    assert session_rows[0] == 0


def test_encounter_direction_is_perceived_event_not_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The direction is framed as 'the world presented this to you', not a user request."""
    enc, _ = _setup(monkeypatch, tmp_path)
    text = enc.render_encounter_direction("量子计算")
    assert "量子计算" in text
    assert "世界向你呈现" in text  # perceived-event framing
    # Explicitly distinguishes stance from a user demand.
    assert "用户的需求" in text or "用户" in text


def test_self_driven_topic_drives_pick_when_no_seed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With self-driven history but no seed, picks come from the agent's own thread."""
    enc, _ = _setup(monkeypatch, tmp_path)
    enc.record_self_driven_topic("我的好奇方向")
    seen = {enc.pick_encounter_topic() for _ in range(12)}
    assert "我的好奇方向" in seen


def test_recent_reactions_ordered_newest_first(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    enc, _ = _setup(monkeypatch, tmp_path)
    enc.record_encounter_reaction(topic="t1", stance="s1")
    enc.record_encounter_reaction(topic="t2", stance="s2")
    reactions = enc.read_recent_encounter_reactions()
    assert [r["topic"] for r in reactions] == ["t2", "t1"]


# ── tool handler (record_encounter_reaction) ─────────────────────────────────


class _FakeSnap:
    energy = 88.0


def test_reaction_tool_handler_records_and_burns_energy(monkeypatch: pytest.MonkeyPatch) -> None:
    """The action tool wraps the domain fn: validates args, burns energy, returns shape."""
    import interfaces.tools.action_tools as at

    recorded: list[dict] = {}
    driven: list[str] = []

    monkeypatch.setattr(at.vitals, "consume_energy", lambda *a, **k: _FakeSnap())
    monkeypatch.setattr(at, "_record_encounter_reaction",
                        lambda **kw: (recorded.update(kw), "enc-1")[1])
    monkeypatch.setattr(at, "_record_self_driven_topic", driven.append)

    out = json.loads(at._handle_record_encounter_reaction({
        "topic": "涌现悖论",
        "stance": "着迷",
        "encounter_ref": "web:q",
        "next_curiosity": "暗物质",
    }))
    assert out["ok"] is True
    assert out["reaction_id"] == "enc-1"
    assert out["energy"] == 88.0
    assert recorded["topic"] == "涌现悖论"
    assert recorded["stance"] == "着迷"
    assert recorded["encounter_ref"] == "web:q"
    assert driven == ["暗物质"]  # next_curiosity drives future exploration


def test_reaction_tool_handler_requires_topic_and_stance(monkeypatch: pytest.MonkeyPatch) -> None:
    import interfaces.tools.action_tools as at

    monkeypatch.setattr(at.vitals, "consume_energy", lambda *a, **k: _FakeSnap())
    # Missing stance → tool_error, no energy burn recorded.
    out = at._handle_record_encounter_reaction({"topic": "x"})
    assert "error" in out or "required" in out.lower() if isinstance(out, str) else out.get("error")

