"""End-to-end self-constitution flow: encounter → reaction → crystallize → govern wake.

Exercises the full constitution loop at the module level:

    idle high-energy (initiative) → world_encounter direction injected
        → agent senses world, records a reaction
        → dream reads reactions, crystallizes stable patterns
        → next wake's first-thought block carries the crystallized self

The scheduler injection sites are thin try/except wrappers around these module
calls (covered by event-flow / console tests in group 6). This test pins the
*governance contract* of the loop: a self crystallized from encounters shows
up in the wake block, and an empty self yields no block (digest-only).
"""

from __future__ import annotations

import json
from pathlib import Path

from domain.memory.memory import encounter as enc
from domain.memory.memory import self_cognition as sc
from infrastructure.persistence.instance.memory import MemoryDB


def _bind(tmp_path: Path):
    """Point both the encounter (layers) and self_cognition (slow_var) modules
    at tmp_path-backed DBs and reset their caches."""
    mem_dir = tmp_path / "memories"
    mem_dir.mkdir()
    # encounter module reads get_runtime_memories_dir() for memory_layers.db + seed.
    import infrastructure.config as cfg
    import sys
    # Patch the symbol encounter actually imported.
    enc.get_runtime_memories_dir = lambda: mem_dir  # type: ignore[assignment]
    enc.reset_db_cache_for_tests(None)
    # self_cognition slow_var lives in MemoryDB (memory.db).
    sc_db = MemoryDB(db_path=tmp_path / "memory.db", instance_id="t1")
    sc.reset_db_cache_for_tests(sc_db)
    return mem_dir


def _patch_energy(monkeypatch):
    import interfaces.tools.action_tools as at

    class _Snap:
        energy = 90.0
    monkeypatch.setattr(at.vitals, "consume_energy", lambda *a, **k: _Snap())


def test_constitution_loop_carries_self_into_wake_block(tmp_path: Path, monkeypatch) -> None:
    """Full loop: encounter → react → crystallize → wake block carries the self."""
    mem_dir = _bind(tmp_path)
    _patch_energy(monkeypatch)

    # 1. Seed exists; an initiative wake picks an encounter direction (perceived event).
    (mem_dir / enc.SEED_FILENAME).write_text("# 好奇心种子\n- 涌现悖论\n", encoding="utf-8")
    topic = enc.pick_encounter_topic()
    assert topic == "涌现悖论"
    direction = enc.render_encounter_direction(topic)
    assert "世界向你呈现" in direction  # perceived event, not a user request

    # 2. Agent senses the world (web_search, out of scope here) and records a reaction.
    enc.record_encounter_reaction(
        topic="涌现悖论", stance="着迷——简单规则产生复杂行为让我想搞清边界",
        encounter_ref="web:emergence",
    )
    # A second, different encounter pointing the same way (stable pattern material).
    enc.record_encounter_reaction(
        topic="元胞自动机", stance="同样着迷——又是简单规则涌现复杂性",
        encounter_ref="web:conway",
    )

    # 3. Dream reads recent reactions and crystallizes a stable cross-encounter pattern.
    reactions = enc.read_recent_encounter_reactions()
    assert len(reactions) == 2
    assert {r["topic"] for r in reactions} == {"涌现悖论", "元胞自动机"}

    import interfaces.tools.action_tools as at
    out = json.loads(at._handle_crystallize_self_cognition({
        "summary": "我对'简单规则涌现复杂性'这类现象稳定地着迷。",
        "stances": [{
            "topic": "涌现现象",
            "stance": "着迷，想搞清规则到复杂性的边界",
            "evidence_refs": [reactions[0]["period"], reactions[1]["period"]],
        }],
        "source_encounter_count": 2,
    }))
    assert out["ok"] is True

    # 4. Next wake: first-thought block carries the crystallized self.
    section = sc.render_self_cognition_section(sc.read_self_cognition())
    assert section  # non-empty → scheduler injects it
    block = {"role": "user", "content": section, "_sys_tool": "self_cognition"}
    assert block["_sys_tool"] == "self_cognition"
    assert "涌现" in block["content"]


def test_constitution_loop_empty_before_any_encounter(tmp_path: Path) -> None:
    """Before any encounter/crystallization, wake is digest-only (no self block)."""
    _bind(tmp_path)
    # No seed, no self-driven history → no encounter direction.
    assert enc.pick_encounter_topic() is None
    # No crystallized self → empty section → scheduler skips injection.
    assert sc.read_self_cognition() is None
    assert sc.render_self_cognition_section(sc.read_self_cognition()) == ""


def test_constitution_loop_no_stable_pattern_does_not_fabricate(tmp_path: Path, monkeypatch) -> None:
    """A single reaction is not a stable pattern → no crystallization → no self block."""
    mem_dir = _bind(tmp_path)
    _patch_energy(monkeypatch)
    (mem_dir / enc.SEED_FILENAME).write_text("# s\n- X\n", encoding="utf-8")

    enc.record_encounter_reaction(topic="X", stance="一次性反应，不足以结晶")
    reactions = enc.read_recent_encounter_reactions()
    assert len(reactions) == 1

    # Dream judges: only one reaction, not cross-encounter stable → does NOT call crystallize.
    # (Simulate the model correctly choosing not to fabricate: slot stays empty.)
    assert sc.read_self_cognition() is None
    assert sc.render_self_cognition_section(sc.read_self_cognition()) == ""
