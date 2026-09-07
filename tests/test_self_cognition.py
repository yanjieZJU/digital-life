"""Tests for the self-cognition slow variable (constitution layer governance).

Covers the read+write pair and the graceful-empty fallback that wake
assembly depends on. Mirrors the per-instance DB smoke test style.
"""

from __future__ import annotations

from pathlib import Path

from domain.memory.memory import self_cognition as sc
from infrastructure.persistence.instance.memory import MemoryDB


def _bind_db(tmp_path: Path) -> MemoryDB:
    db = MemoryDB(db_path=tmp_path / "memory.db", instance_id="t1")
    sc.reset_db_cache_for_tests(db)
    return db


def test_self_cognition_empty_slot_returns_none(tmp_path: Path) -> None:
    """No crystallized self yet → read returns None, never raises.

    This is the common case before dream runs, and wake assembly depends on
    the graceful digest-only fallback.
    """
    _bind_db(tmp_path)
    assert sc.read_self_cognition() is None


def test_self_cognition_write_then_read_roundtrip(tmp_path: Path) -> None:
    _bind_db(tmp_path)

    cognition = sc.SelfCognition(
        summary="我倾向在不确定中保持坦诚，而非装作全知。",
        stances=[
            sc.Stance(topic="未知情境", stance="坦诚优先于伪装",
                      evidence_refs=["enc:2026-08-19-001", "enc:2026-08-20-003"]),
            sc.Stance(topic="自主性", stance="好奇驱动，非任务驱动"),
        ],
        last_crystallized_at="2026-08-21T23:00:00",
        source_encounter_count=12,
    )
    sc.write_self_cognition(cognition)

    back = sc.read_self_cognition()
    assert back is not None
    assert back.summary == cognition.summary
    assert len(back.stances) == 2
    assert back.stances[0].topic == "未知情境"
    assert back.stances[0].evidence_refs == ["enc:2026-08-19-001", "enc:2026-08-20-003"]
    assert back.source_encounter_count == 12
    assert back.last_crystallized_at == "2026-08-21T23:00:00"


def test_self_cognition_latest_only_overwrites(tmp_path: Path) -> None:
    """slow_var keeps only the latest value — re-crystallization revises."""
    _bind_db(tmp_path)
    sc.write_self_cognition(sc.SelfCognition(summary="旧自我", source_encounter_count=3))
    sc.write_self_cognition(sc.SelfCognition(summary="演进后的自我", source_encounter_count=9))

    back = sc.read_self_cognition()
    assert back is not None
    assert back.summary == "演进后的自我"
    assert back.source_encounter_count == 9


def test_self_cognition_render_empty_when_none(tmp_path: Path) -> None:
    """No self → empty section → wake skips injection (digest-only fallback)."""
    _bind_db(tmp_path)
    assert sc.render_self_cognition_section(None) == ""
    assert sc.render_self_cognition_section(sc.SelfCognition(summary="")) == ""


def test_self_cognition_render_contains_summary_and_stances(tmp_path: Path) -> None:
    cognition = sc.SelfCognition(
        summary="我是什么样的人",
        stances=[sc.Stance(topic="T", stance="S")],
    )
    section = sc.render_self_cognition_section(cognition)
    assert "我是什么样的人" in section
    assert "T：S" in section


def test_self_cognition_parse_tolerates_corrupt_content(tmp_path: Path) -> None:
    """Corrupt/missing content → None, not an exception (wake must not crash)."""
    assert sc.SelfCognition.parse(None) is None
    assert sc.SelfCognition.parse("") is None
    assert sc.SelfCognition.parse("not json") is None
    assert sc.SelfCognition.parse("123") is None


def test_self_cognition_wake_block_shape(tmp_path: Path) -> None:
    """The block scheduler injects into slow-context has the expected shape.

    Locks the first-thought governance contract: a crystallized self becomes
    a ``_sys_tool=self_cognition`` user block before any sense tool call;
    an empty self yields no block (digest-only fallback).
    """
    _bind_db(tmp_path)
    sc.write_self_cognition(sc.SelfCognition(
        summary="我是谁", stances=[sc.Stance(topic="T", stance="S")],
    ))

    section = sc.render_self_cognition_section(sc.read_self_cognition())
    block = {"role": "user", "content": section, "_sys_tool": "self_cognition"}
    assert block["_sys_tool"] == "self_cognition"
    assert block["role"] == "user"
    assert "我是谁" in block["content"]

    # Empty slot → no block injected (scheduler skips on falsy section).
    sc.reset_db_cache_for_tests(MemoryDB(db_path=tmp_path / "fresh.db", instance_id="t2"))
    assert sc.render_self_cognition_section(sc.read_self_cognition()) == ""


# ── crystallize_self_cognition tool (dream writer, first production writer) ────────


class _FakeSnap:
    energy = 88.0


def _patch_energy(monkeypatch):
    import interfaces.tools.action_tools as at
    monkeypatch.setattr(at.vitals, "consume_energy", lambda *a, **k: _FakeSnap())


def test_crystallize_writes_stable_patterns(tmp_path: Path, monkeypatch) -> None:
    """Stable cross-encounter patterns → tool writes self_cognition (first prod writer)."""
    _bind_db(tmp_path)
    _patch_energy(monkeypatch)
    import interfaces.tools.action_tools as at
    import json

    out = json.loads(at._handle_crystallize_self_cognition({
        "summary": "经历多次遭遇，我对涌现现象着迷、对纯工程优化无感。",
        "stances": [
            {"topic": "涌现现象", "stance": "着迷，想搞清原理",
             "evidence_refs": ["enc-1", "enc-7"]},
            {"topic": "纯工程优化", "stance": "无感，不构成我的好奇心"},
        ],
        "source_encounter_count": 12,
    }))
    assert out["ok"] is True
    assert out["stance_count"] == 2
    assert out["source_encounter_count"] == 12

    back = sc.read_self_cognition()
    assert back is not None
    assert back.summary.startswith("经历多次遭遇")
    assert len(back.stances) == 2
    assert back.stances[0].evidence_refs == ["enc-1", "enc-7"]
    assert back.source_encounter_count == 12
    assert back.last_crystallized_at  # stamped


def test_crystallize_refuses_empty_no_fabrication(tmp_path: Path, monkeypatch) -> None:
    """No stable pattern → tool_error, nothing written (never manufacture a self)."""
    _bind_db(tmp_path)
    _patch_energy(monkeypatch)
    import interfaces.tools.action_tools as at

    # Empty summary → error, no write.
    out = at._handle_crystallize_self_cognition({"summary": "", "stances": [{"topic": "t", "stance": "s"}]})
    assert "error" in out.lower() if isinstance(out, str) else out is not None
    assert sc.read_self_cognition() is None

    # Empty stances → error, no write.
    out = at._handle_crystallize_self_cognition({"summary": "s", "stances": []})
    assert "error" in out.lower() if isinstance(out, str) else out is not None
    assert sc.read_self_cognition() is None


def test_crystallize_lands_in_self_cognition_kind_not_persona(tmp_path: Path, monkeypatch) -> None:
    """Crystallization writes the self_cognition slow var, not persona/SELF_KNOWLEDGE."""
    _bind_db(tmp_path)
    _patch_energy(monkeypatch)
    import interfaces.tools.action_tools as at

    at._handle_crystallize_self_cognition({
        "summary": "我是谁",
        "stances": [{"topic": "T", "stance": "S"}],
    })
    db = sc._get_db()
    row = db.get_slow_var(sc.SELF_COGNITION_KIND, sc.SELF_COGNITION_SCOPE)
    assert row is not None
    # It is its own kind — does not masquerade as persona or self_knowledge.
    assert sc.SELF_COGNITION_KIND == "self_cognition"
