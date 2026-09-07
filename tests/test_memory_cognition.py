"""碎片认知生命周期测试——记忆衰减 + 认知更新（cognition.py / entity_index 扩展）。

覆盖：
1. 衰减纯函数：分层半衰期 / 瞬态 tag 覆盖 / 损坏时间戳放行
2. 召回门控 + 只读锁定：低于地板线碎片出局，召回前后文件字节相等
3. 信号跃迁：falsify×2 → challenged（降权仍可见）；verify 复位 + 计数
4. supersede 链：旧碎片翻转 / 新碎片 derived_from / 追链 / 幂等 / 防环
5. 副本同步：认知字段按 memory_id 全副本演进
6. 写时查重：同 key 同值拦截 / 同 key 异值建链 / 跨 type 共存 / 无 key 旧行为
7. 批量归档：只碰低于地板线的 active，幂等，restore 后衰减门仍生效
8. 老数据兼容：缺新字段的最小碎片过全部新读路径不抛异常
9. 工具 handler：update_memory_cognition 五分支 + record_thought cog_key 校验
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.memory.memory.consciousness import cognition as cog
from domain.memory.memory.consciousness import entity_index as ei

_NOW = datetime(2026, 9, 7, 12, 0, 0, tzinfo=cog._LOCAL_TZ)


def _ts(days_ago: float) -> str:
    """_NOW 起 days_ago 天前的 ISO 时间戳。"""
    return (_NOW - timedelta(days=days_ago)).isoformat()


def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """隔离的 entity_index：读写都指向 tmp_path/memories/entity_index.json。"""
    mem_dir = tmp_path / "memories"
    mem_dir.mkdir()
    monkeypatch.setattr(ei, "_get_runtime_home", lambda: tmp_path)
    return tmp_path / "memories" / "entity_index.json"


def _frag(
    mid: str,
    mtype: str,
    snippet: str,
    *,
    days_ago: float = 0.0,
    entity: str = "华能蒙电",
    **extra,
) -> dict:
    """最小碎片 dict（老格式兼容：新字段按需经 extra 传入）。"""
    mem = {
        "memory_type": mtype,
        "memory_id": mid,
        "snippet": snippet,
        "timestamp": _ts(days_ago),
        "linked_entities": [entity],
        "verification_count": 0,
        "last_accessed": None,
    }
    mem.update(extra)
    return mem


def _seed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *fragments: dict) -> Path:
    """把碎片按 entity 字段挂进隔离 index（同 entity 多条共用槽位）。"""
    isolated = _isolate(monkeypatch, tmp_path)
    entities: dict[str, dict] = {}
    for f in fragments:
        name = f.get("linked_entities") or ["华能蒙电"]
        for e in name:
            entities.setdefault(e, {"aliases": [], "type": None, "memories": []})
            entities[e]["memories"].append(dict(f))
    ei.save_entity_index({"version": 1, "entities": entities})
    return isolated


def _all_fragments() -> dict[str, dict]:
    """全索引碎片平铺 {memory_id: fragment}（取每 id 第一份副本）。"""
    out: dict[str, dict] = {}
    for entity in ei.load_entity_index().get("entities", {}).values():
        for m in entity.get("memories", []):
            out.setdefault(str(m.get("memory_id", "")), m)
    return out


# ─────────────────────────────────────────────────────────────────────
# 1. 衰减纯函数
# ─────────────────────────────────────────────────────────────────────


def test_freshness_half_life_consciousness():
    """consciousness 0/14/28 天 → 1.0/0.5/0.25；61 天跌破地板线。"""
    assert cog.fragment_freshness(_frag("c1", "consciousness", "x", days_ago=0), now=_NOW) == 1.0
    assert cog.fragment_freshness(_frag("c2", "consciousness", "x", days_ago=14), now=_NOW) == pytest.approx(0.5)
    assert cog.fragment_freshness(_frag("c3", "consciousness", "x", days_ago=28), now=_NOW) == pytest.approx(0.25)
    assert cog.fragment_freshness(_frag("c4", "consciousness", "x", days_ago=61), now=_NOW) < cog.ARCHIVE_FRESHNESS_FLOOR


def test_freshness_permanent_types_never_decay():
    """rule / lesson 永不时间衰减（10 年后仍 1.0）。"""
    assert cog.fragment_freshness(_frag("r1", "rule", "x", days_ago=3650), now=_NOW) == 1.0
    assert cog.fragment_freshness(_frag("l1", "lesson", "x", days_ago=3650), now=_NOW) == 1.0


def test_freshness_insight_and_low_tag():
    """insight 30d 半衰期（200 天出局）；consciousness+瞬态 tag 覆盖为 3d（14 天出局）。"""
    assert cog.fragment_freshness(_frag("i1", "insight", "x", days_ago=30), now=_NOW) == pytest.approx(0.5)
    assert cog.fragment_freshness(_frag("i2", "insight", "x", days_ago=200), now=_NOW) < cog.ARCHIVE_FRESHNESS_FLOOR
    transient = _frag("t1", "consciousness", "x", days_ago=14, tag="trading_wait")
    assert cog.fragment_freshness(transient, now=_NOW) < cog.ARCHIVE_FRESHNESS_FLOOR
    assert cog.half_life_days(transient) == cog.HALF_LIFE_LOW_TAG_DAYS


def test_freshness_unparseable_timestamp_passes():
    """timestamp 不可解析 → freshness 1.0（门控对损坏时间戳放行，宁漏勿杀）。"""
    bad = _frag("b1", "consciousness", "x")
    bad["timestamp"] = "not-a-date"
    assert cog.fragment_freshness(bad, now=_NOW) == 1.0
    assert cog.passes_recall_gate(bad, now=_NOW)


def test_cog_key_validation():
    """subject:predicate 校验：全角冒号归一化合法；缺分隔符/单侧空非法。"""
    assert cog.is_valid_cog_key("华能蒙电:止损线=5.53")
    assert cog.is_valid_cog_key("华能蒙电：止损线")  # 全角冒号
    assert not cog.is_valid_cog_key("华能蒙电")      # 无分隔符
    assert not cog.is_valid_cog_key("华能蒙电:")     # predicate 空
    assert not cog.is_valid_cog_key(":止损")         # subject 空
    assert not cog.is_valid_cog_key("")
    assert cog.normalize_cog_key(" A ： B ") == "a:b"


def test_bigram_jaccard_empty_side_zero():
    """任一侧空串 → 0.0（空 snippet 不参与查重命中）。"""
    assert cog.bigram_jaccard("", "任何文本") == 0.0
    assert cog.bigram_jaccard("任何文本", "") == 0.0
    assert cog.bigram_jaccard("止损线设在五点五三", "止损线设在五点五三") == 1.0


# ─────────────────────────────────────────────────────────────────────
# 2. 召回门控 + 只读锁定
# ─────────────────────────────────────────────────────────────────────


def test_recall_gate_filters_decayed_but_not_permanent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """61 天前的 consciousness 出局；同龄 rule / insight / 新 consciousness 仍在。"""
    idx_path = _seed(
        monkeypatch, tmp_path,
        _frag("old_c", "consciousness", "两个月前的意识流碎片", days_ago=61),
        _frag("old_rule", "rule", "两个月前的规则仍然有效", days_ago=61),
        _frag("old_insight", "insight", "两个月前的闪念", days_ago=61),  # 0.245 > 0.05
        _frag("new_c", "consciousness", "上周的意识流碎片", days_ago=7),
    )
    before = idx_path.read_text(encoding="utf-8")

    results = ei.query_entities_ranked(["华能蒙电"], limit=10)
    ids = {m.get("memory_id") for m in results}

    assert "old_c" not in ids, "61 天前的 consciousness 应被衰减门过滤"
    assert {"old_rule", "old_insight", "new_c"} <= ids

    after = idx_path.read_text(encoding="utf-8")
    assert before == after, "召回门控是纯函数，不得回写 entity_index.json"


def test_recall_gate_superseded_excluded_unless_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """superseded 默认出局；include_superseded=True 放开（主动查历史场景）。"""
    _seed(
        monkeypatch, tmp_path,
        _frag("old", "lesson", "旧结论", status=cog.COG_SUPERSEDED),
        _frag("new", "lesson", "新结论"),
    )
    default_ids = {m.get("memory_id") for m in ei.query_entities_ranked(["华能蒙电"], limit=10)}
    assert "old" not in default_ids and "new" in default_ids

    wide_ids = {m.get("memory_id") for m in ei.query_entities_ranked(
        ["华能蒙电"], limit=10, include_superseded=True)}
    assert {"old", "new"} <= wide_ids


# ─────────────────────────────────────────────────────────────────────
# 3. 信号跃迁
# ─────────────────────────────────────────────────────────────────────


def test_falsify_twice_reaches_challenged_then_verify_restores(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """falsify×1 仍 active；×2 → challenged（authority 减半）；verify → active + vc+1。"""
    _seed(monkeypatch, tmp_path, _frag("l1", "lesson", "华能蒙电止损线 5.53"))

    r1 = ei.apply_cognition_signal("l1", "falsified", note="盘中未触发")
    assert r1["ok"] and r1["status"] == cog.COG_ACTIVE

    r2 = ei.apply_cognition_signal("l1", "falsified", note="再次未触发")
    assert r2["status"] == cog.COG_CHALLENGED

    frag = _all_fragments()["l1"]
    assert frag["challenge_count"] == 2 and frag["status_note"] == "再次未触发"
    assert ei._compute_authority(frag) == pytest.approx(0.8 * cog.CHALLENGED_AUTHORITY_FACTOR)

    r3 = ei.apply_cognition_signal("l1", "verified", note="回测复核成立")
    assert r3["status"] == cog.COG_ACTIVE
    frag = _all_fragments()["l1"]
    assert frag["verification_count"] == 1  # seed 时 vc=0，verify +1
    assert frag["challenge_count"] == 2     # 历史保留


def test_cognition_signal_unknown_inputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """未知信号 / 不存在的 memory_id 返回 ok=False，不写盘。"""
    _isolate(monkeypatch, tmp_path)
    assert not ei.apply_cognition_signal("l1", "maybe")["ok"]
    assert not ei.apply_cognition_signal("no-such-id", "verified")["ok"]


# ─────────────────────────────────────────────────────────────────────
# 4. supersede 链
# ─────────────────────────────────────────────────────────────────────


def test_apply_supersede_builds_chain_and_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """旧→superseded+superseded_by；新→derived_from；ranked 不含旧；重复执行幂等。"""
    _seed(
        monkeypatch, tmp_path,
        _frag("old", "lesson", "看多华能蒙电，止损 5.53"),
        _frag("new", "lesson", "华能蒙电已清仓，看多结论作废"),
    )

    r = ei.apply_supersede("old", "new", note="清仓事实推翻")
    assert r["ok"] and r["old_hits"] == 1 and r["new_hits"] == 1

    frags = _all_fragments()
    assert frags["old"]["status"] == cog.COG_SUPERSEDED
    assert frags["old"]["superseded_by"] == "new"
    assert "old" in frags["new"]["derived_from"]

    ranked_ids = {m.get("memory_id") for m in ei.query_entities_ranked(["华能蒙电"], limit=10)}
    assert "old" not in ranked_ids and "new" in ranked_ids

    # 幂等：重复 supersede 不产生重复 derived_from / 不报错
    ei.apply_supersede("old", "new")
    assert _all_fragments()["new"]["derived_from"].count("old") == 1

    # 自环 / 缺参拒绝
    assert not ei.apply_supersede("old", "old")["ok"]
    assert not ei.apply_supersede("", "new")["ok"]


def test_get_supersede_chain_follows_and_stops_on_cycle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """追链到最新；手工构造的环（A→B→A）不无限循环。"""
    _seed(
        monkeypatch, tmp_path,
        _frag("a", "lesson", "结论A", status=cog.COG_SUPERSEDED, superseded_by="b"),
        _frag("b", "lesson", "结论B", status=cog.COG_SUPERSEDED, superseded_by="c"),
        _frag("c", "lesson", "结论C"),
    )
    chain = ei.get_supersede_chain("a")
    assert [step["memory_id"] for step in chain] == ["a", "b", "c"]
    assert chain[-1]["superseded_by"] == ""

    # 环：b→c，c→b——visited 集合保证终止
    ei.save_entity_index({
        "version": 1,
        "entities": {"华能蒙电": {"aliases": [], "type": None, "memories": [
            _frag("b", "lesson", "结论B", status=cog.COG_SUPERSEDED, superseded_by="c"),
            _frag("c", "lesson", "结论C", status=cog.COG_SUPERSEDED, superseded_by="b"),
        ]}},
    })
    cyclic = ei.get_supersede_chain("b")
    assert len(cyclic) == 2, "环链应在 visited 处截断"


# ─────────────────────────────────────────────────────────────────────
# 5. 副本同步（同 memory_id 挂多实体）
# ─────────────────────────────────────────────────────────────────────


def _seed_two_copies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mid: str) -> dict:
    """同一 memory_id 挂两个实体的最小 index（模拟共享碎片）。"""
    _isolate(monkeypatch, tmp_path)
    frag = _frag(mid, "lesson", "跨实体共享的结论", entity="甲")
    frag["linked_entities"] = ["甲", "乙"]
    ei.save_entity_index({"version": 1, "entities": {
        "甲": {"aliases": [], "type": None, "memories": [dict(frag)]},
        "乙": {"aliases": [], "type": None, "memories": [dict(frag)]},
    }})
    return frag


def _copies(mid: str) -> list[dict]:
    out = []
    for entity in ei.load_entity_index().get("entities", {}).values():
        for m in entity.get("memories", []):
            if m.get("memory_id") == mid:
                out.append(m)
    return out


def test_cognition_fields_sync_across_copies(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """supersede / falsify / archive 后，两份副本的认知字段一致。"""
    _isolate(monkeypatch, tmp_path)
    shared = _frag("shared", "lesson", "跨实体共享的结论", entity="甲")
    shared["linked_entities"] = ["甲", "乙"]
    ei.save_entity_index({"version": 1, "entities": {
        "甲": {"aliases": [], "type": None, "memories": [dict(shared)]},
        "乙": {"aliases": [], "type": None, "memories": [
            dict(shared),
            _frag("other", "lesson", "乙实体的独立碎片", entity="乙"),
        ]},
    }})

    ei.apply_supersede("shared", "other")
    ei.apply_cognition_signal("shared", "falsified", note="证伪一次")
    ei.set_fragment_status("shared", cog.COG_ARCHIVED, note="归档")

    copies = _copies("shared")
    assert len(copies) == 2
    for c in copies:
        assert c["status"] == cog.COG_ARCHIVED  # set_fragment_status 覆盖了前两步的 status
        assert c["superseded_by"] == "other"    # supersede 的链注记保留（restore 后仍可溯源）
        assert c["challenge_count"] == 1
        assert c["status_note"] == "归档"


def test_bump_verification_syncs_all_copies(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """bump_verification 修复后全副本 +1（历史上只改第一份副本）。"""
    _seed_two_copies(monkeypatch, tmp_path, "shared")
    ei.bump_verification("shared")
    assert all(c["verification_count"] == 1 for c in _copies("shared"))


# ─────────────────────────────────────────────────────────────────────
# 6. 写时查重（cog_key）
# ─────────────────────────────────────────────────────────────────────


def test_write_time_dedup_same_key_same_value_bumps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """同 key 同 type 且内容几乎相同 → 拦截写入，旧碎片 vc+1。"""
    _isolate(monkeypatch, tmp_path)
    key = "华能蒙电:止损线"
    text = "华能蒙电止损线设在5.53元，破位必须离场"

    r1 = ei.update_entity_index(["华能蒙电"], memory_type="lesson",
                                memory_id="lesson:1", snippet=text, cog_key=key)
    assert r1["action"] == "insert"

    r2 = ei.update_entity_index(["华能蒙电"], memory_type="lesson",
                                memory_id="lesson:2", snippet=text + "。", cog_key=key)
    assert r2["action"] == "skip_bumped"
    assert r2["memory_id"] == "lesson:1"

    frags = _all_fragments()
    assert "lesson:2" not in frags, "同值重复不应写入新碎片"
    assert frags["lesson:1"]["verification_count"] == 1


def test_write_time_dedup_same_key_new_value_supersedes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """同 key 同 type 但结论变了 → 写新碎片并自动 supersede 旧碎片。"""
    _isolate(monkeypatch, tmp_path)
    key = "华能蒙电:方向判断"

    ei.update_entity_index(["华能蒙电"], memory_type="lesson", memory_id="lesson:1",
                           snippet="看多华能蒙电，回调即买点", cog_key=key)
    r2 = ei.update_entity_index(["华能蒙电"], memory_type="lesson", memory_id="lesson:2",
                                snippet="华能蒙电基本面恶化，已清仓不再看多", cog_key=key)
    assert r2["action"] == "superseded"
    assert r2["superseded"] == ["lesson:1"]

    frags = _all_fragments()
    assert frags["lesson:1"]["status"] == cog.COG_SUPERSEDED
    assert frags["lesson:1"]["superseded_by"] == "lesson:2"
    assert frags["lesson:2"]["derived_from"] == ["lesson:1"]

    # 旧碎片出局后，同 key 再写异值只对 active 查重——不会链到 superseded 上
    r3 = ei.update_entity_index(["华能蒙电"], memory_type="lesson", memory_id="lesson:3",
                                snippet="重新建仓华能蒙电，基本面修复确认", cog_key=key)
    assert r3["action"] == "superseded"
    assert r3["superseded"] == ["lesson:2"]
    assert _all_fragments()["lesson:1"]["superseded_by"] == "lesson:2"  # 链不被改写


def test_write_time_dedup_cross_type_coexists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """同 key 跨 memory_type 共存（record_thought 双写 consciousness+insight 场景）。"""
    _isolate(monkeypatch, tmp_path)
    key = "回测框架:结论"

    r1 = ei.update_entity_index(["回测框架"], memory_type="consciousness",
                                memory_id="c:1", snippet="回测显示策略A年化超额20%", cog_key=key)
    r2 = ei.update_entity_index(["回测框架"], memory_type="insight",
                                memory_id="i:1", snippet="回测显示策略A年化超额20%", cog_key=key)
    assert r1["action"] == "insert" and r2["action"] == "insert"

    frags = _all_fragments()
    assert frags["c:1"].get("status", cog.COG_ACTIVE) == cog.COG_ACTIVE
    assert frags["i:1"].get("status", cog.COG_ACTIVE) == cog.COG_ACTIVE


def test_write_without_cog_key_keeps_legacy_behavior(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """无 cog_key → 不查重不建链，两次写入两条碎片（旧行为零变化）。"""
    _isolate(monkeypatch, tmp_path)
    ei.update_entity_index(["华能蒙电"], memory_type="lesson",
                           memory_id="lesson:1", snippet="同一段文本")
    r2 = ei.update_entity_index(["华能蒙电"], memory_type="lesson",
                                memory_id="lesson:2", snippet="同一段文本")
    assert r2["action"] == "insert"
    frags = _all_fragments()
    assert "lesson:1" in frags and "lesson:2" in frags
    assert frags["lesson:1"].get("status", cog.COG_ACTIVE) == cog.COG_ACTIVE
    assert frags["lesson:1"].get("verification_count", 0) == 0


def test_write_invalid_cog_key_dropped_defensively(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """非法 cog_key（缺分隔符）防御性丢弃：走普通写入，不抛异常。"""
    _isolate(monkeypatch, tmp_path)
    r = ei.update_entity_index(["华能蒙电"], memory_type="lesson",
                               memory_id="lesson:1", snippet="x", cog_key="没有冒号")
    assert r["action"] == "insert"
    assert "cog_key" not in _all_fragments()["lesson:1"]


# ─────────────────────────────────────────────────────────────────────
# 7. 批量归档
# ─────────────────────────────────────────────────────────────────────


def test_archive_decayed_only_marks_below_floor_active(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """只归档低于地板线的 active；superseded 不动；幂等；restore 后衰减门仍生效。"""
    _seed(
        monkeypatch, tmp_path,
        _frag("stale_c", "consciousness", "61 天前的意识流", days_ago=61),
        _frag("fresh_c", "consciousness", "上周的意识流", days_ago=7),
        _frag("old_rule", "rule", "61 天前的规则", days_ago=61),  # 永不衰减
        _frag("sup", "lesson", "已推翻的旧结论", status=cog.COG_SUPERSEDED, superseded_by="x"),
    )

    r1 = ei.archive_decayed_fragments()
    assert r1["archived"] == 1
    assert r1["by_type"] == {"consciousness": 1}

    frags = _all_fragments()
    assert frags["stale_c"]["status"] == cog.COG_ARCHIVED
    assert "archived_at" in frags["stale_c"]
    assert frags["fresh_c"].get("status", cog.COG_ACTIVE) == cog.COG_ACTIVE
    assert frags["old_rule"].get("status", cog.COG_ACTIVE) == cog.COG_ACTIVE
    assert frags["sup"]["status"] == cog.COG_SUPERSEDED  # 已翻转的不重复处理

    # 幂等
    assert ei.archive_decayed_fragments()["archived"] == 0

    # restore 后状态回 active，但衰减门按时间仍然过滤（时间才是裁判）
    ei.set_fragment_status("stale_c", cog.COG_ACTIVE, note="周度纠错找回")
    ranked_ids = {m.get("memory_id") for m in ei.query_entities_ranked(["华能蒙电"], limit=10)}
    assert "stale_c" not in ranked_ids


def test_cognition_backlog_reports_three_lists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """backlog 三张清单：challenged / to_archive / recent_supersede + 全量计数。"""
    _seed(
        monkeypatch, tmp_path,
        _frag("ch1", "lesson", "待决断的结论", status=cog.COG_CHALLENGED, challenge_count=2),
        _frag("stale", "consciousness", "61 天前的意识流", days_ago=61),
        _frag("sup1", "lesson", "被推翻的结论", status=cog.COG_SUPERSEDED,
              superseded_by="sup2", superseded_at=_ts(1)),
        _frag("sup2", "lesson", "推翻后的新结论"),
    )
    backlog = ei.cognition_backlog()
    assert backlog["challenged_count"] == 1
    assert backlog["to_archive_count"] == 1
    assert backlog["superseded_count"] == 1
    assert backlog["challenged"][0]["memory_id"] == "ch1"
    assert backlog["to_archive"][0]["memory_id"] == "stale"
    assert backlog["recent_supersede"][0]["memory_id"] == "sup1"


# ─────────────────────────────────────────────────────────────────────
# 8. 老数据兼容
# ─────────────────────────────────────────────────────────────────────


def test_legacy_minimal_fragment_passes_all_new_read_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """缺 cog_key/status/challenge_count 的最小老格式碎片过全部新读路径不抛异常。"""
    isolated = _isolate(monkeypatch, tmp_path)
    ei.save_entity_index({"version": 1, "entities": {
        "老实体": {"aliases": [], "type": None, "memories": [
            # 生产老数据的真实形态：无任何认知新字段
            {"memory_type": "consciousness", "memory_id": "legacy:1",
             "snippet": "2026 年 7 月的碎片", "timestamp": _ts(20),
             "linked_entities": ["老实体"]},
        ]}},
    })

    assert cog.passes_recall_gate(
        {"memory_type": "consciousness", "timestamp": _ts(20)}) is True
    assert ei.query_entities_ranked(["老实体"], limit=5), "老碎片默认 active 应可召回"
    ei.cognition_backlog()
    ei.get_supersede_chain("legacy:1")
    ei.archive_decayed_fragments()
    assert ei.get_fragment_by_id("legacy:1")["fragment"]["memory_id"] == "legacy:1"

    # 召回仍然只读
    before = isolated.read_text(encoding="utf-8")
    ei.query_entities_ranked(["老实体"], limit=5)
    assert isolated.read_text(encoding="utf-8") == before


# ─────────────────────────────────────────────────────────────────────
# 9. 工具 handler
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def tool_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """隔离 index + 注册表环境，返回 action_tools 模块。"""
    from interfaces.tools import action_tools as at

    _isolate(monkeypatch, tmp_path)
    return at


def _dispatch_cognition(at, **args) -> dict:
    import json as _json
    return _json.loads(at._handle_update_memory_cognition(args))


def test_tool_update_memory_cognition_validation(tool_env):
    at = tool_env
    bad = at._handle_update_memory_cognition({"action": "explode"})
    assert "action 必须是" in bad

    no_id = at._handle_update_memory_cognition({"action": "archive"})
    assert "memory_id 必填" in no_id

    missing = _dispatch_cognition(at, action="verify", memory_id="ghost")
    assert missing["ok"] is False


def test_tool_update_memory_cognition_verify_falsify_flow(tool_env):
    at = tool_env
    ei.update_entity_index(["华能蒙电"], memory_type="lesson",
                           memory_id="lesson:1", snippet="止损结论")

    r1 = _dispatch_cognition(at, action="falsify", memory_id="lesson:1", note="未触发")
    assert r1["ok"] and r1["status"] == cog.COG_ACTIVE
    r2 = _dispatch_cognition(at, action="falsify", memory_id="lesson:1", note="再次未触发")
    assert r2["status"] == cog.COG_CHALLENGED
    assert "challenged" in r2["note"]

    r3 = _dispatch_cognition(at, action="verify", memory_id="lesson:1", note="复核成立")
    assert r3["status"] == cog.COG_ACTIVE


def test_tool_update_memory_cognition_supersede(tool_env):
    at = tool_env
    ei.update_entity_index(
        ["华能蒙电"], memory_type="lesson", memory_id="lesson:1",
        snippet="看多华能蒙电，回调即买点", cog_key="华能蒙电:方向判断",
    )

    r = _dispatch_cognition(
        at, action="supersede", memory_id="lesson:1",
        new_text="华能蒙电基本面恶化，已清仓不再看多",
        new_type="lesson", note="清仓事实推翻",
    )
    assert r["ok"] and r["action"] == "superseded"

    frags = _all_fragments()
    old, new_id = frags["lesson:1"], r["new_memory_id"]
    assert old["status"] == cog.COG_SUPERSEDED and old["superseded_by"] == new_id
    assert frags[new_id]["derived_from"] == ["lesson:1"]
    assert frags[new_id]["cog_key"] == "华能蒙电:方向判断"  # 继承旧 key

    # 同 key 同值 supersede → 写时查重拦截（skip_bumped），不新建碎片
    r2 = _dispatch_cognition(
        at, action="supersede", memory_id=new_id,
        new_text="华能蒙电基本面恶化，已清仓不再看多",
    )
    assert r2["ok"] and r2["action"] == "skip_bumped"

    # 缺 new_text 报错
    assert "new_text" in at._handle_update_memory_cognition(
        {"action": "supersede", "memory_id": new_id})


def test_tool_supersede_twice_in_same_second_no_id_collision(tool_env):
    """同一秒内连续两次 supersede：new_id 必须互异，两条新结论都不丢。

    回归：new_id 曾用秒级 now_iso——批量 tool_calls 同秒派发时第二次的
    new_text 被 existing_ids 去重静默丢弃，旧碎片错指向第一次的新文本。
    """
    at = tool_env
    ei.update_entity_index(["甲"], memory_type="lesson",
                           memory_id="lesson:a", snippet="甲的旧结论", cog_key="甲:结论")
    ei.update_entity_index(["乙"], memory_type="lesson",
                           memory_id="lesson:b", snippet="乙的旧结论", cog_key="乙:结论")

    r1 = _dispatch_cognition(at, action="supersede", memory_id="lesson:a", new_text="甲的新结论")
    r2 = _dispatch_cognition(at, action="supersede", memory_id="lesson:b", new_text="乙的新结论")
    assert r1["new_memory_id"] != r2["new_memory_id"]

    frags = _all_fragments()
    assert frags["lesson:a"]["superseded_by"] == r1["new_memory_id"]
    assert frags["lesson:b"]["superseded_by"] == r2["new_memory_id"]
    assert "甲的新结论" in frags[r1["new_memory_id"]]["snippet"]
    assert "乙的新结论" in frags[r2["new_memory_id"]]["snippet"]


def test_tool_update_memory_cognition_archive_restore(tool_env):
    at = tool_env
    ei.update_entity_index(["华能蒙电"], memory_type="lesson",
                           memory_id="lesson:1", snippet="某结论")

    r1 = _dispatch_cognition(at, action="archive", memory_id="lesson:1", note="没用了")
    assert r1["ok"] and r1["status"] == cog.COG_ARCHIVED
    assert "lesson:1" not in {
        m.get("memory_id") for m in ei.query_entities_ranked(["华能蒙电"], limit=10)}

    r2 = _dispatch_cognition(at, action="restore", memory_id="lesson:1")
    assert r2["ok"] and r2["status"] == cog.COG_ACTIVE
    assert "lesson:1" in {
        m.get("memory_id") for m in ei.query_entities_ranked(["华能蒙电"], limit=10)}


def test_tool_update_memory_cognition_archive_decayed_scope(tool_env):
    """archive + scope=decayed → 批量归档，memory_id 可空（dream 认知体检路径）。"""
    at = tool_env
    ei.update_entity_index(["华能蒙电"], memory_type="consciousness",
                           memory_id="c:1", snippet="结论")
    data = ei.load_entity_index()
    data["entities"]["华能蒙电"]["memories"][0]["timestamp"] = _ts(61)
    ei.save_entity_index(data)

    r = _dispatch_cognition(at, action="archive", scope="decayed")
    assert r["archived"] == 1
    assert _all_fragments()["c:1"]["status"] == cog.COG_ARCHIVED


def test_tool_record_thought_cog_key_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
):
    """record_thought 的 cog_key 格式校验：非法报错引导重传；合法透传 _record。"""
    from interfaces.tools import action_tools as at

    _isolate(monkeypatch, tmp_path)
    # 隔离精力引擎与写入：cog_key 校验失败时不该消耗真实精力/写记忆
    stub = SimpleNamespace(
        consume_energy=lambda *_a, **_k: SimpleNamespace(energy=80.0),
        get_current_vitals=lambda: SimpleNamespace(energy=80.0),
    )
    monkeypatch.setattr(at, "vitals", stub)
    recorded: list[dict] = []
    monkeypatch.setattr(at, "_record", lambda text, **kw: recorded.append({"text": text, **kw}))

    bad = at._handle_record_thought({"text": "止损结论", "cog_key": "没有冒号"})
    assert "cog_key 格式应为" in bad
    assert not recorded

    ok = at._handle_record_thought({"text": "止损结论", "cog_key": "华能蒙电:止损线"})
    assert '"ok": true' in ok
    assert recorded and recorded[0]["cog_key"] == "华能蒙电:止损线"
