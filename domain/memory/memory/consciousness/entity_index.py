"""Entity index — inverted index mapping entities to associated memories.

Stored as entity_index.json in runtime/memories/.
Provides:
- String-match entity extraction (fast, for mid-session recall)
- Multi-dimensional ranked query (recency + authority + context_overlap +
  verification)
- Entity lifecycle: merge, heatmap, verification tracking
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from domain.memory.memory.consciousness.cognition import (
    ARCHIVE_FRESHNESS_FLOOR,
    CHALLENGED_AUTHORITY_FACTOR,
    COG_ACTIVE,
    COG_ARCHIVED,
    COG_AUTO_SUPERSEDE,
    COG_CHALLENGED,
    COG_DUP_JACCARD,
    COG_SUPERSEDED,
    FALSIFY_TO_CHALLENGED,
    bigram_jaccard,
    fragment_age_days,
    fragment_freshness,
    is_valid_cog_key,
    normalize_cog_key,
)

logger = logging.getLogger(__name__)

_LOCAL_TZ = datetime.now().astimezone().tzinfo

_AUTHORITY_MAP: dict[str, float] = {
    "rule": 1.0,
    "lesson": 0.8,
    "todo": 0.5,
    "consciousness": 0.6,
    "scratchpad": 0.2,
}
_LOW_AUTHORITY_TAGS: tuple[str, ...] = ("trading_wait", "system_wait", "monitor", "final_status")


def _get_runtime_home() -> Path:
    try:
        from infrastructure.config import get_runtime_home
        return get_runtime_home()
    except Exception:
        # Fallback is **last resort**——不应在 fresh clone 触发。
        # 旧实现默认走 apps/zero/data：在 zero 实例未创建时会写到错误路径。
        # 这里改成抛错让 module load 失败、错误更明显。
        raise RuntimeError(
            "runtime_home 未配置：调 get_runtime_home 失败且无 fallback。"
            "请先 digital-life init 创建实例并设置 DIGITAL_LIFE_INSTANCE_ID。"
        )


def _entity_index_path() -> Path:
    return _get_runtime_home() / "memories" / "entity_index.json"


def load_entity_index() -> dict[str, Any]:
    """Load the full entity index, returning empty dict if not found or corrupt."""
    path = _entity_index_path()
    if not path.exists():
        return {"version": 1, "entities": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "entities" not in data:
            return {"version": 1, "entities": {}}
        return data
    except Exception:
        logger.debug("Failed to load entity_index.json", exc_info=True)
        return {"version": 1, "entities": {}}


def save_entity_index(data: dict[str, Any]) -> None:
    path = _entity_index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(_LOCAL_TZ).isoformat()


def _apply_to_memory_copies(
    data: dict[str, Any],
    memory_id: str,
    mutator: Callable[[dict[str, Any]], None],
) -> int:
    """对同一 memory_id 的【所有】实体副本应用 mutator，返回命中副本数。

    认知字段（status/cog_key/challenge_count 等）按 memory_id 全局演进：
    同一 memory_id 挂 N 个实体 = 同一条逻辑记忆，副本是"实体↔记忆链接"
    不是独立记忆——分叉演进会让 query_entities 的全局去重（只返回先扫到
    的那份副本）读到哪个状态取决于 dict 遍历顺序，是不确定性行为。

    只改内存 dict，不落盘——调用方负责单次 load → 变更 → save。
    """
    if not memory_id:
        return 0
    hits = 0
    for entity in data.get("entities", {}).values():
        for mem in entity.get("memories", []):
            if mem.get("memory_id") == memory_id:
                mutator(mem)
                hits += 1
    return hits


def update_entity_index(
    entities: list[str],
    *,
    memory_type: str,
    memory_id: str,
    snippet: str = "",
    linked_entities: list[str] | None = None,
    tag: str = "",
    replace_existing: bool = False,
    cog_key: str = "",
) -> dict[str, Any]:
    """Associate a memory with one or more entities in the index.

    Creates new entity entries as needed.

    When replace_existing=True, removes old entries of the same memory_type
    for each entity before adding the new one. Used for state-report
    consciousness entries that should only have one current snapshot.

    cog_key（可选，"subject:predicate" 结构化认知主键）触发写时查重
    （域=同 memory_type + active + 同 key）：
      - snippet bigram jaccard ≥ COG_DUP_JACCARD → 同一结论重复提出：
        不写新碎片，旧碎片全副本 verification_count +1，返回 skip_bumped。
      - jaccard < 阈值 → 结论变了：写新碎片并自动 supersede 旧碎片
        （旧→superseded+superseded_by，新→derived_from），返回 superseded。
        COG_AUTO_SUPERSEDE=False 时只在新碎片记 conflict_with 不执行翻转。
    非法格式（缺分隔符/单侧为空）按防御性处理：丢弃 cog_key 走普通写入
    （格式校验的模型引导在工具层做）。

    返回 {"action": "insert"|"skip_bumped"|"superseded", ...}；旧行为调用方
    忽略返回值不受影响。
    """
    if not entities:
        return {"action": "insert", "memory_id": memory_id, "hits": 0}

    key = normalize_cog_key(cog_key) if cog_key else ""
    if cog_key and not is_valid_cog_key(cog_key):
        logger.warning("update_entity_index: 非法 cog_key %r 已丢弃（应为 subject:predicate）", cog_key[:40])
        key = ""

    data = load_entity_index()
    entities_dict: dict[str, dict[str, Any]] = data.setdefault("entities", {})

    # ── cog_key 写时查重（拷贝循环之前，全索引范围）────────────────────────
    superseded_ids: list[str] = []
    bump_ids: list[str] = []
    if key:
        same_key_actives = _find_active_by_cog_key(data, key, memory_type)
        if same_key_actives:
            latest = same_key_actives[0]  # _find_active_by_cog_key 已按时间降序
            if bigram_jaccard(snippet, str(latest.get("snippet", ""))) >= COG_DUP_JACCARD:
                bump_ids = [str(latest.get("memory_id", ""))]
            else:
                # 结论变了：同 key 的全部 active 旧碎片都应让位（正常只有
                # 一条；多条是历史异常，一并翻转恢复不变量）
                superseded_ids = [str(m.get("memory_id", "")) for m in same_key_actives]

    if bump_ids:
        # 同一结论重复提出 → 视为再次验证，不新增碎片
        for old_id in bump_ids:
            _apply_to_memory_copies(
                data, old_id,
                lambda m: m.__setitem__(
                    "verification_count", int(m.get("verification_count", 0)) + 1),
            )
        save_entity_index(data)
        return {"action": "skip_bumped", "memory_id": bump_ids[0], "hits": len(entities)}

    memory_entry: dict[str, Any] = {
        "memory_type": memory_type,
        "memory_id": memory_id,
        "snippet": snippet[:200] if snippet else "",
        "timestamp": _now_iso(),
        "linked_entities": linked_entities or [],
        "verification_count": 0,
        "last_accessed": None,
    }
    if tag:
        memory_entry["tag"] = tag
    if key:
        memory_entry["cog_key"] = key
    if superseded_ids:
        if COG_AUTO_SUPERSEDE:
            memory_entry["derived_from"] = list(superseded_ids)
        else:
            memory_entry["conflict_with"] = list(superseded_ids)

    for entity_name in entities:
        if not entity_name or not entity_name.strip():
            continue
        name = entity_name.strip()
        if name not in entities_dict:
            entities_dict[name] = {"aliases": [], "type": None, "memories": []}
        entity = entities_dict[name]

        # State-report replacement: remove old entries of same type so only
        # the current snapshot remains.
        if replace_existing:
            entity["memories"] = [
                m for m in entity["memories"]
                if m.get("memory_type") != memory_type
            ]

        # Avoid inserting duplicate memory entries (same memory_id).
        # Deep-copy memory_entry so each entity gets its own dict — prevents
        # shared-reference bugs when bump_verification modifies one entity's copy.
        existing_ids = {m.get("memory_id") for m in entity["memories"]}
        if memory_id not in existing_ids:
            entity["memories"].append(dict(memory_entry))

    # ── 自动 supersede：同 key 异值的旧碎片让位（按 memory_id 全副本同步）──
    if superseded_ids and COG_AUTO_SUPERSEDE:
        now_iso = _now_iso()
        for old_id in superseded_ids:
            def _mark_old(m: dict[str, Any], _old=old_id) -> None:
                m["status"] = COG_SUPERSEDED
                m["superseded_by"] = memory_id
                m["superseded_at"] = now_iso
            _apply_to_memory_copies(data, old_id, _mark_old)

    save_entity_index(data)
    return {
        "action": "superseded" if superseded_ids and COG_AUTO_SUPERSEDE else "insert",
        "memory_id": memory_id,
        "superseded": superseded_ids if COG_AUTO_SUPERSEDE else [],
        "hits": len(entities),
    }


def _find_active_by_cog_key(
    data: dict[str, Any], cog_key: str, memory_type: str,
) -> list[dict[str, Any]]:
    """全索引中同 memory_type + active + 同 cog_key 的碎片，按 timestamp 降序。

    查重域限定同 memory_type：record_thought 对同一文本双写 consciousness
    +insight 两条碎片且共用同一 cog_key——跨类型共存是合法形态，不互查。
    返回的是索引内真实 dict 引用（供写路径直接变更）。
    """
    found: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for entity in data.get("entities", {}).values():
        for mem in entity.get("memories", []):
            mid = str(mem.get("memory_id", ""))
            if mid in seen_ids:
                continue
            if str(mem.get("memory_type", "")) != memory_type:
                continue
            if str(mem.get("status") or "") not in ("", COG_ACTIVE):
                continue
            if str(mem.get("cog_key", "")) != cog_key:
                continue
            seen_ids.add(mid)
            found.append(mem)
    found.sort(key=lambda m: str(m.get("timestamp", "")), reverse=True)
    return found


def query_entities(entity_names: list[str]) -> list[dict[str, Any]]:
    """Return all memories associated with any of the given entity names.

    Results are sorted by timestamp descending.
    """
    if not entity_names:
        return []

    data = load_entity_index()
    entities_dict = data.get("entities", {})

    seen_ids: set[str] = set()
    results: list[dict[str, Any]] = []

    for name in entity_names:
        entity = entities_dict.get(name)
        if not entity:
            continue
        for memory in entity.get("memories", []):
            mid = memory.get("memory_id", "")
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                results.append(dict(memory, _matched_entity=name))

    results.sort(key=lambda m: str(m.get("timestamp", "")), reverse=True)
    return results


def _compute_authority(memory: dict[str, Any]) -> float:
    mtype = str(memory.get("memory_type", "")).lower()
    tag = str(memory.get("tag", "")).lower()

    base = 0.4
    if mtype == "rule":
        base = _AUTHORITY_MAP["rule"]
    elif mtype == "lesson":
        base = _AUTHORITY_MAP["lesson"]
    elif mtype == "scratchpad":
        base = _AUTHORITY_MAP["scratchpad"]
    elif mtype == "consciousness":
        base = 0.3
        for low_tag in _LOW_AUTHORITY_TAGS:
            if low_tag in tag:
                break
        else:
            base = _AUTHORITY_MAP["consciousness"]
    # 被证伪待决断的碎片降权（不除名——challenged 仍参与召回，等 dream 决断）
    if str(memory.get("status") or "") == COG_CHALLENGED:
        return base * CHALLENGED_AUTHORITY_FACTOR
    return base


def _compute_recency(timestamp: str | None) -> float:
    if not timestamp:
        return 0.0
    try:
        ts = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        now = datetime.now(_LOCAL_TZ)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=_LOCAL_TZ)
        days = (now - ts).total_seconds() / 86400.0
        return max(0.0, 1.0 - days / 30.0)
    except Exception:
        return 0.0


def _compute_context_overlap(memory: dict[str, Any], current_entities: set[str]) -> float:
    linked = set(memory.get("linked_entities", []))
    if not current_entities or not linked:
        return 0.0
    return len(current_entities & linked) / max(len(current_entities), 1)


def _compute_verification_bonus(memory: dict[str, Any]) -> float:
    count = int(memory.get("verification_count", 0))
    return min(count / 5.0, 1.0)


def query_entities_ranked(
    entity_names: list[str],
    *,
    current_context: str = "",
    exclude_ids: set[str] | None = None,
    limit: int = 3,
    include_superseded: bool = False,
) -> list[dict[str, Any]]:
    """Multi-dimensional ranked query for entity memories.

    Ranking formula: recency * 0.35 + authority * 0.25 +
                     context_overlap * 0.25 + verification * 0.15

    返回结构设计(2026): **profile 为主,碎片为辅**。
    每个命中实体若有 profile→先返回一张「概念卡」(memory_type="profile",
    snippet = summary + facts 合成);碎片仍按排名返回作补充细节。
    这样联想时模型读到的是「对实体的理解」而非散乱碎片——与 memory_hygiene
    的「消化碎片成 profile」步骤配套。没 profile 的实体退回纯碎片(不破坏旧行为)。

    ⚠ 重要:有 profile 但碎片已清空的实体(消化机制铺开后常态)不能被
    query_entities 的 "无碎片即空" 短路掉——profile 卡生成必须独立于碎片存在。
    """
    results = query_entities(entity_names)

    exclude = exclude_ids or set()
    # Use both passed entity_names AND entities extracted from the full context
    # text. In mid-session recall, entity_names may only contain NEW entities
    # (after dedup), but the context text spans the full session conversation
    # which includes entities injected earlier. Merging both gives the most
    # accurate context_overlap score.
    context_entities: set[str] = set()
    if current_context:
        context_entities = set(extract_entities_from_context(current_context))
    current_entities = set(entity_names) | context_entities

    scored: list[tuple[float, dict[str, Any]]] = []
    for mem in results:
        mid = str(mem.get("memory_id", ""))
        if mid and mid in exclude:
            continue

        # 认知生命周期门（纯函数，绝不写盘——"召回不回写"由
        # tests/test_memory_redundancy_cuts.py 字节级锁定）：
        #   - 状态门：superseded/archived 出局（被推翻/已归档不进被动注入）；
        #     include_superseded=True 放开（主动查询历史场景）
        #   - 衰减门：freshness < 地板线出局（分层半衰期，rule/lesson 永不衰减），恒开
        status = str(mem.get("status") or "") or COG_ACTIVE
        if status in (COG_SUPERSEDED, COG_ARCHIVED) and not include_superseded:
            continue
        if fragment_freshness(mem) < ARCHIVE_FRESHNESS_FLOOR:
            continue

        score = (
            _compute_recency(mem.get("timestamp")) * 0.35
            + _compute_authority(mem) * 0.25
            + _compute_context_overlap(mem, current_entities) * 0.25
            + _compute_verification_bonus(mem) * 0.15
        )
        scored.append((score, mem))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]
    top_mems = [mem for _, mem in top]

    # Profile-first: 为每个有 profile 的命中实体生成一张概念卡,排在碎片前面。
    # 必须独立于碎片结果——碎片可能是空的(消化机制铺开后 profile 实体常已清碎片)。
    profile_cards = _build_profile_cards(entity_names)
    if profile_cards:
        # 把 limit 拆分:profile 卡占一部分,碎片占余下。
        profile_quota = max(1, limit // 3)
        used_profile = profile_cards[:profile_quota]
        keep_fragments = max(0, limit - len(used_profile))
        top_mems = used_profile + top_mems[:keep_fragments]

    # last_accessed 历史上由 touch_last_accessed 在每次召回时回写，但该字段从未被
    # 任何打分/读取路径消费（_compute_recency 用的是 timestamp）。回写只会触发
    # 整份 entity_index.json 的读改写——每次召回 N 条命中 = N 次全文件 IO。
    # 已移除该写路径；memory_entry 里的 last_accessed 字段保留为 None 不再更新。
    return top_mems


def _build_profile_cards(entity_names: list[str]) -> list[dict[str, Any]]:
    """为命中的实体生成「概念卡」(memory_type=profile),用于联想注入时优先展示。

    无 profile 的实体跳过(调用方回退到纯碎片)。
    """
    if not entity_names:
        return []
    data = load_entity_index()
    entities_dict = data.get("entities", {})
    cards: list[dict[str, Any]] = []
    for name in entity_names:
        entity = entities_dict.get(name)
        if not entity:
            continue
        profile = entity.get("profile")
        if not profile:
            continue
        summary = str(profile.get("summary", "")).strip()
        facts = profile.get("facts") or []
        if not summary and not facts:
            continue
        parts = []
        if summary:
            parts.append(summary)
        if facts:
            joined = "; ".join(str(f) for f in facts if str(f).strip())
            if joined:
                parts.append(f"已知: {joined}")
        snippet = " | ".join(parts) if parts else summary
        cards.append({
            "memory_type": "profile",
            "memory_id": f"profile:{name}",
            "snippet": snippet,
            "timestamp": profile.get("last_updated"),
            "linked_entities": [],
            "verification_count": 0,
            "_matched_entity": name,
            "_entity_kind": entity.get("type"),
        })
    return cards


def extract_entities_from_context(text: str) -> list[str]:
    """Fast string-match extraction of known entities from a text.

    Matches entity names and aliases against the text. O(entities * text_len)
    which is fine for hundreds of entities and thousands of chars (<5ms).

    Returns entity names in order of first appearance in the text.
    """
    if not text or not text.strip():
        return []

    data = load_entity_index()
    entities_dict = data.get("entities", {})
    if not entities_dict:
        return []

    text_lower = text.lower()
    hits: list[tuple[int, str]] = []  # (position, entity_name)

    for entity_name, entity_data in entities_dict.items():
        patterns = [entity_name] + list(entity_data.get("aliases", []))
        for pattern in patterns:
            if not pattern:
                continue
            pos = text_lower.find(pattern.lower())
            if pos >= 0:
                hits.append((pos, entity_name))
                break  # One match is enough for this entity

    # Sort by position, remove duplicates while preserving order
    hits.sort(key=lambda x: x[0])
    seen: set[str] = set()
    result: list[str] = []
    for _, name in hits:
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def merge_entities(primary: str, alias: str) -> dict[str, Any]:
    """Merge an aliased entity into the primary one.

    Moves all memories from alias to primary, adds alias to primary's
    aliases list, removes the alias entity. Returns the updated primary
    entity dict.
    """
    data = load_entity_index()
    entities = data.setdefault("entities", {})

    primary_entity = entities.get(primary)
    alias_entity = entities.get(alias)

    if not alias_entity:
        return primary_entity or {}

    if not primary_entity:
        primary_entity = {"aliases": [], "type": None, "memories": []}
        entities[primary] = primary_entity

    # Move memories (dedup by memory_id)
    existing_ids = {m.get("memory_id") for m in primary_entity["memories"]}
    for mem in alias_entity.get("memories", []):
        if mem.get("memory_id") not in existing_ids:
            primary_entity["memories"].append(mem)
            existing_ids.add(mem.get("memory_id"))

    # Merge aliases
    for a in alias_entity.get("aliases", []):
        if a not in primary_entity["aliases"] and a != primary:
            primary_entity["aliases"].append(a)
    if alias not in primary_entity["aliases"]:
        primary_entity["aliases"].append(alias)

    # Merge type if primary doesn't have one
    if not primary_entity.get("type") and alias_entity.get("type"):
        primary_entity["type"] = alias_entity["type"]

    # Remove alias entity
    del entities[alias]
    save_entity_index(data)

    return primary_entity


def get_entity_heatmap(days_back: int = 1) -> dict[str, int]:
    """Count memory entries per entity in the last N days. Returns {entity_name: count}."""
    data = load_entity_index()
    entities = data.get("entities", {})

    cutoff = datetime.now(_LOCAL_TZ) - timedelta(days=days_back)
    result: dict[str, int] = {}

    for entity_name, entity_data in entities.items():
        count = 0
        for mem in entity_data.get("memories", []):
            ts_str = str(mem.get("timestamp", ""))
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=_LOCAL_TZ)
                if ts >= cutoff:
                    count += 1
            except Exception:
                pass
        if count > 0:
            result[entity_name] = count

    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


def bump_verification_for_entities(entity_names: list[str], memory_type: str) -> None:
    """Bump verification_count for the most recent memory of given type across entities.

    Used by add_lesson merge path — when a lesson is "confirmed again",
    the entity index verification_count should reflect that without creating
    a duplicate entry.
    """
    if not entity_names:
        return
    data = load_entity_index()
    for name in entity_names:
        entity = data.get("entities", {}).get(name)
        if not entity:
            continue
        best = None
        best_ts = ""
        for mem in entity.get("memories", []):
            if mem.get("memory_type") == memory_type:
                ts = str(mem.get("timestamp", ""))
                if ts > best_ts:
                    best_ts = ts
                    best = mem
        if best is not None:
            best["verification_count"] = int(best.get("verification_count", 0)) + 1
    save_entity_index(data)


def bump_verification(memory_id: str) -> None:
    """Increment verification_count for a memory entry.

    按记忆惯例本应只 bump 第一份副本——现改走 _apply_to_memory_copies
    同步全部副本（认知计数是记忆的属性，不是链接的属性；副本分叉
    会让召回读到不确定的状态）。全仓此前无调用方，行为变更零风险。
    """
    if not memory_id:
        return
    data = load_entity_index()
    hits = _apply_to_memory_copies(
        data, memory_id,
        lambda m: m.__setitem__(
            "verification_count", int(m.get("verification_count", 0)) + 1),
    )
    if hits:
        save_entity_index(data)


def get_entity_summary(entity_name: str) -> dict[str, Any] | None:
    """Get summary of an entity including its memories and metadata."""
    data = load_entity_index()
    return data.get("entities", {}).get(entity_name)


def get_fragment_by_id(memory_id: str) -> dict[str, Any] | None:
    """按 memory_id 全索引查找碎片（副本内容一致，取第一份）。

    返回 {"fragment": {...}, "entities": [挂载实体名...]}；不存在返回 None。
    update_memory_cognition 工具用它在 supersede 时继承旧碎片的
    cog_key / linked_entities。
    """
    if not memory_id:
        return None
    data = load_entity_index()
    fragment: dict[str, Any] | None = None
    owners: list[str] = []
    for name, entity in data.get("entities", {}).items():
        for mem in entity.get("memories", []):
            if mem.get("memory_id") == memory_id:
                if fragment is None:
                    fragment = mem
                owners.append(name)
    if fragment is None:
        return None
    return {"fragment": fragment, "entities": owners}


def list_entity_names() -> list[str]:
    """Return all entity names sorted alphabetically."""
    data = load_entity_index()
    return sorted(data.get("entities", {}).keys())


# ─────────────────────────────────────────────────────────────────────────
# Concept memory (profile + facts)
# ─────────────────────────────────────────────────────────────────────────
# A "concept memory" is the conceptual distillation of an entity — its
# profile. Distinct from fragment memories (consciousness / lesson snippets),
# a profile is a synthesized statement of "what we know about X" extracted
# from the fragments. Model writes these manually via the curate_entity tool,
# or writes via set_entity_profile. Frontend human can also edit.

# Concept-related entity types: these deserve a structured profile.
# Other entities (verbs / runtime strings) stay as pure association indices.
_CONCEPTUAL_TYPES: set[str] = {
    "person", "instance", "human",
    "project", "thesis", "strategy", "decision",
    "stock", "asset", "instrument",
    "concept", "skill", "tool",
    "todo",
}


def set_entity_profile(
    name: str,
    *,
    kind: str | None = None,
    aliases: list[str] | None = None,
    summary: str = "",
    facts: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Set or replace the structured profile of an entity.

    The profile is the conceptual distillation:
      - summary: 1-2 sentence "what is this thing" description
      - facts: list of bullet-form factual statements
      - extra: project-y specific fields (stop_loss / current_position etc.)

    Idempotent: re-running replaces prior profile field for the entity,
    fragments (memories) are unchanged.
    """
    if not name:
        return {"ok": False, "reason": "name required"}
    data = load_entity_index()
    entities_dict = data.setdefault("entities", {})
    entity = entities_dict.setdefault(name, {"aliases": [], "type": None, "memories": []})

    if kind:
        entity["type"] = kind
    if aliases is not None:
        entity["aliases"] = list(aliases)

    profile = entity.setdefault("profile", {})
    profile["summary"] = summary
    profile["facts"] = list(facts) if facts is not None else profile.get("facts", [])
    if extra:
        profile.setdefault("extra", {}).update(extra)
    profile["last_updated"] = _now_iso()

    save_entity_index(data)
    return {"ok": True, "entity": name, "profile": profile}


def get_entity_profile(name: str) -> dict[str, Any] | None:
    """Read profile field of an entity (without loading fragments)."""
    entity = get_entity_summary(name)
    if not entity:
        return None
    return entity.get("profile")


def index_health_check() -> dict[str, Any]:
    """Audit report on entity index health: missing profile/type/aliases.

    Returns:
      {
        "total_entities": N,
        "with_profile": [...],
        "missing_profile_high_value": [...],  # entities with many memories
                                              # but no profile (low signal)
        "missing_aliases": [...],             # entities with no aliases
                                              # (dedup candidates)
        "missing_type": [...],
        "suggested_merges": [                 # detected by common snippet prefix
          {"primary": X, "alias": Y, "shared_memory_count": N},
        ],
      }
    """
    data = load_entity_index()
    entities = data.get("entities", {})
    report = {
        "total_entities": len(entities),
        "with_profile": [],
        "missing_profile_high_value": [],
        "missing_aliases": [],
        "missing_type": [],
        "suggested_merges": [],
    }
    # Build snippet prefix map for merge detection
    snippet_index: dict[str, list[str]] = {}
    for name, info in entities.items():
        mems = info.get("memories", [])
        has_profile = bool(info.get("profile"))
        has_aliases = bool(info.get("aliases"))
        has_type = info.get("type")
        if has_profile:
            report["with_profile"].append(name)
        elif len(mems) >= 5:
            report["missing_profile_high_value"].append({
                "name": name,
                "fragment_count": len(mems),
                "kind": has_type,
            })
        if not has_aliases and len(mems) >= 3 and name.isdigit():
            # All-numeric names are likely codes/IDs — probably aliased elsewhere
            report["missing_aliases"].append(name)
        if not has_type and len(mems) >= 3:
            report["missing_type"].append(name)
        # Track snippet prefixes for dedup detection
        for m in mems:
            snip = (m.get("snippet") or "")[:80]
            if snip:
                snippet_index.setdefault(snip, []).append(name)
    # Cross-entity shared snippets ≥1 mean those entities point at SAME memory
    # → likely alias candidates.
    seen: set[tuple[str, str]] = set()
    for snip, names in snippet_index.items():
        unique_names = set(names)
        if len(unique_names) >= 2:
            primary = sorted(unique_names)[0]
            for alias in unique_names - {primary}:
                pair = tuple(sorted((primary, alias)))
                if pair in seen:
                    continue
                seen.add(pair)
                report["suggested_merges"].append({
                    "primary": primary,
                    "alias": alias,
                    "shared_memory_count": len(snippet_index[snip]),
                })
    return report


def prune_fragments_for_entity(name: str, keep: int = 5) -> dict[str, Any]:
    """Trim an entity's fragment memories to the most recent `keep` items.

    Use after ``set_entity_profile`` extracts the conceptual truth — keeping
    100+ consciousness fragments provides no signal at that point. Profile +
    a small tail of recent fragments is enough.
    """
    data = load_entity_index()
    entities = data.get("entities", {})
    if name not in entities:
        return {"ok": False, "reason": f"entity {name} not found"}
    mems = entities[name].get("memories", [])
    if len(mems) <= keep:
        return {"ok": True, "removed": 0, "kept": len(mems)}
    mems.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
    kept = mems[:keep]
    removed = len(mems) - keep
    entities[name]["memories"] = kept
    save_entity_index(data)
    return {"ok": True, "removed": removed, "kept": len(kept)}


def sync_entity_from_source(
    name: str,
    *,
    entity_type: str = "",
    summary: str = "",
    extra: dict[str, Any] | None = None,
    aliases: list[str] | None = None,
) -> None:
    """源系统变更时调用——自动创建或更新 entity。

    与 set_entity_profile 的区别：
      - set_entity_profile 是模型主动调（完整覆盖 profile.summary/facts）
      - sync_entity_from_source 是 contacts/projects/skills 等源系统自动调
      - **不覆盖模型已写的 profile.summary**——只在 entity 不存在或 summary 为空时写
      - **追加 extra 字段**（merge，不覆盖已有 extra 的 key 如果新值和旧值同）
      - 更新 type 和 aliases（只在 entity 还没 type 或 type 为空时设）

    设计意图：保持"模型写的 > 系统生成的"优先级。系统只负责"注册身份"，
    不影响模型对实体的深度理解。
    """
    if not name or not name.strip():
        return
    name = name.strip()
    try:
        data = load_entity_index()
        entities_dict = data.setdefault("entities", {})
        entity = entities_dict.setdefault(name, {"aliases": [], "type": None, "memories": []})

        # type：只在空时设（模型可能已手动设了更精确的 type）
        if entity_type and not entity.get("type"):
            entity["type"] = entity_type

        # aliases：追加新 alias（不覆盖已有的）
        if aliases:
            existing_aliases = set(entity.get("aliases", []))
            for a in aliases:
                a = a.strip()
                if a and a != name and a not in existing_aliases:
                    entity.setdefault("aliases", []).append(a)
                    existing_aliases.add(a)

        # profile：摘要只在空时写，extra 追加合并
        profile = entity.setdefault("profile", {})
        if summary and not profile.get("summary"):
            profile["summary"] = summary
        if extra:
            pe = profile.setdefault("extra", {})
            for k, v in extra.items():
                if k not in pe:  # 不覆盖已有 key
                    pe[k] = v
        profile["last_updated"] = _now_iso()
        profile["last_source_sync"] = _now_iso()

        save_entity_index(data)
    except Exception as exc:
        logger.warning("sync_entity_from_source failed for '%s': %s", name[:20], exc)


def mark_entity_status(name: str, **flags: Any) -> None:
    """在 entity profile.extra 里标记状态标志（deleted/archived/blocked 等）。

    不删除实体、不删碎片——只标记。entity_recall 打分时可以读取这些标志
    做降权（比如 archived 的项目碎片 recency 权重可以降低）。
    """
    if not name or not name.strip():
        return
    name = name.strip()
    try:
        data = load_entity_index()
        entities_dict = data.setdefault("entities", {})
        entity = entities_dict.setdefault(name, {"aliases": [], "type": None, "memories": []})
        profile = entity.setdefault("profile", {})
        extra = profile.setdefault("extra", {})
        extra.update(flags)
        extra["last_status_update"] = _now_iso()
        save_entity_index(data)
    except Exception as exc:
        logger.warning("mark_entity_status failed for '%s': %s", name[:20], exc)


# ─────────────────────────────────────────────────────────────────────────
# 碎片认知生命周期（cognition）
# ─────────────────────────────────────────────────────────────────────────
# 写路径 API：全部经 _apply_to_memory_copies 按 memory_id 全副本同步，
# 单次 load → 变更 → save。读路径门控见 query_entities_ranked。

_COG_VALID_STATUSES = frozenset({COG_ACTIVE, COG_CHALLENGED, COG_SUPERSEDED, COG_ARCHIVED})


def apply_cognition_signal(memory_id: str, signal: str, note: str = "") -> dict[str, Any]:
    """对碎片施加 verify / falsify 信号（上游 verified/falsified delta 本地化）。

    - verified：verification_count +1（打分公式的 verification_bonus×0.15
      天然承担"反复验证提升权威"，不另存浮点 authority）；若当前
      challenged → 恢复 active（复证可撤销质疑，challenge_count 保留作历史）。
    - falsified：challenge_count +1；当 challenge_count ≥ FALSIFY_TO_CHALLENGED
      且当前 active → challenged（被证伪待决断，召回中降权但可见，等 dream 决断）。

    note（一句话理由）落 status_note。返回 {"ok", "hits", "status"}；
    hits=0 表示 memory_id 不存在（ok=False）。
    """
    if signal not in ("verified", "falsified"):
        return {"ok": False, "reason": f"未知信号 {signal!r}（应为 verified/falsified）"}
    data = load_entity_index()

    final_status: dict[str, str] = {}

    def _mutate(mem: dict[str, Any]) -> None:
        if signal == "verified":
            mem["verification_count"] = int(mem.get("verification_count", 0)) + 1
            if str(mem.get("status") or "") == COG_CHALLENGED:
                mem["status"] = COG_ACTIVE
        else:
            cc = int(mem.get("challenge_count", 0)) + 1
            mem["challenge_count"] = cc
            if cc >= FALSIFY_TO_CHALLENGED and str(mem.get("status") or "") in ("", COG_ACTIVE):
                mem["status"] = COG_CHALLENGED
        if note:
            mem["status_note"] = note
        final_status["value"] = str(mem.get("status") or "") or COG_ACTIVE

    hits = _apply_to_memory_copies(data, memory_id, _mutate)
    if not hits:
        return {"ok": False, "hits": 0, "reason": f"memory_id {memory_id!r} 不存在"}
    save_entity_index(data)
    return {"ok": True, "hits": hits, "signal": signal,
            "status": final_status.get("value", COG_ACTIVE)}


def apply_supersede(old_memory_id: str, new_memory_id: str, *, note: str = "") -> dict[str, Any]:
    """新结论推翻旧结论：旧→superseded+superseded_by，新→derived_from 追加。

    幂等（旧已是 superseded 重复执行结果一致）；自环拒绝（old==new）。
    旧碎片从 ranked 召回出局（状态门），但 recall_entity 主动查询可见
    并带链注记——"知道自己改过主意"的认知价值放在主动深挖路径。
    """
    if not old_memory_id or not new_memory_id:
        return {"ok": False, "reason": "old/new memory_id 均必填"}
    if old_memory_id == new_memory_id:
        return {"ok": False, "reason": "不能 supersede 自身"}
    data = load_entity_index()
    now_iso = _now_iso()

    def _mark_old(mem: dict[str, Any]) -> None:
        mem["status"] = COG_SUPERSEDED
        mem["superseded_by"] = new_memory_id
        mem["superseded_at"] = now_iso
        if note:
            mem["status_note"] = note

    def _mark_new(mem: dict[str, Any]) -> None:
        derived = list(mem.get("derived_from", []))
        if old_memory_id not in derived:
            derived.append(old_memory_id)
        mem["derived_from"] = derived

    old_hits = _apply_to_memory_copies(data, old_memory_id, _mark_old)
    new_hits = _apply_to_memory_copies(data, new_memory_id, _mark_new)
    if not old_hits and not new_hits:
        return {"ok": False, "reason": f"两个 memory_id 都不存在: {old_memory_id!r}/{new_memory_id!r}"}
    save_entity_index(data)
    return {"ok": True, "old_hits": old_hits, "new_hits": new_hits,
            "old": old_memory_id, "new": new_memory_id}


def set_fragment_status(memory_id: str, status: str, *, note: str = "") -> dict[str, Any]:
    """显式设置碎片状态（archive / restore 的通用底座）。

    restore 用 status="active"：恢复参与召回；superseded_by 等链路注记
    保留作历史（门控只看 status）。note 落 status_note。
    """
    if status not in _COG_VALID_STATUSES:
        return {"ok": False, "reason": f"未知状态 {status!r}（应为 {'/'.join(sorted(_COG_VALID_STATUSES))}）"}
    data = load_entity_index()

    def _mutate(mem: dict[str, Any]) -> None:
        mem["status"] = status
        if note:
            mem["status_note"] = note

    hits = _apply_to_memory_copies(data, memory_id, _mutate)
    if not hits:
        return {"ok": False, "hits": 0, "reason": f"memory_id {memory_id!r} 不存在"}
    save_entity_index(data)
    return {"ok": True, "hits": hits, "status": status}


def archive_decayed_fragments(*, max_count: int = 200) -> dict[str, Any]:
    """dream 认知体检专用批量归档：freshness < 地板线且 active → archived。

    归档不删除（可 restore）；幂等（已 archived 的不再计）。这是衰减的
    唯一写回路径——读时门控是纯函数不落盘，本函数把"事实上已被时间
    淘汰"落成可见状态位，让 backlog 报告可审计。

    max_count 防单次写盘过大（按 timestamp 从旧到新归档）。
    """
    data = load_entity_index()
    candidates: list[tuple[str, dict[str, Any]]] = []  # (timestamp, mem)
    for entity in data.get("entities", {}).values():
        for mem in entity.get("memories", []):
            if str(mem.get("status") or "") not in ("", COG_ACTIVE):
                continue
            if fragment_freshness(mem) < ARCHIVE_FRESHNESS_FLOOR:
                candidates.append((str(mem.get("timestamp", "")), mem))
    candidates.sort(key=lambda x: x[0])  # 旧的先归档

    now_iso = _now_iso()
    by_type: dict[str, int] = {}
    sample_ids: list[str] = []
    archived = 0
    for _, mem in candidates:
        if archived >= max_count:
            break
        mtype = str(mem.get("memory_type", "?"))
        mem["status"] = COG_ARCHIVED
        mem["archived_at"] = now_iso
        by_type[mtype] = by_type.get(mtype, 0) + 1
        if len(sample_ids) < 10:
            sample_ids.append(str(mem.get("memory_id", "")))
        archived += 1

    if archived:
        save_entity_index(data)
    return {"archived": archived, "by_type": by_type, "sample_ids": sample_ids}


def get_supersede_chain(memory_id: str) -> list[dict[str, Any]]:
    """沿 superseded_by 向新追链（旧→新），防环。

    返回 [{memory_id, memory_type, snippet, status, superseded_by, timestamp}]，
    首元素是查询的碎片自身。供 recall_entity / cognition_backlog 展示
    "这个结论被什么推翻了、推翻后又经历了什么"。
    """
    data = load_entity_index()
    by_id: dict[str, dict[str, Any]] = {}
    for entity in data.get("entities", {}).values():
        for mem in entity.get("memories", []):
            by_id.setdefault(str(mem.get("memory_id", "")), mem)

    chain: list[dict[str, Any]] = []
    visited: set[str] = set()
    current = memory_id
    while current and current in by_id and current not in visited:
        visited.add(current)
        mem = by_id[current]
        chain.append({
            "memory_id": current,
            "memory_type": str(mem.get("memory_type", "")),
            "snippet": str(mem.get("snippet", ""))[:80],
            "status": str(mem.get("status") or "") or COG_ACTIVE,
            "superseded_by": str(mem.get("superseded_by", "") or ""),
            "timestamp": str(mem.get("timestamp", "")),
        })
        current = str(mem.get("superseded_by", "") or "")
    return chain


def cognition_backlog(*, list_cap: int = 20) -> dict[str, Any]:
    """认知积压三张清单（纯读，sense_cognition_backlog 工具与体检面板共用）。

    - challenged：被证伪待 dream 决断（supersede 或 verify），不带过夜
    - to_archive：freshness 已低于地板线、尚未写回 archived 的 active 碎片
    - recent_supersede：最近的推翻链头（按 superseded_at 降序）

    列表按 list_cap 截断，counts 是全量计数。
    """
    data = load_entity_index()
    challenged: list[dict[str, Any]] = []
    to_archive: list[dict[str, Any]] = []
    superseded: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for entity_name, entity in data.get("entities", {}).items():
        for mem in entity.get("memories", []):
            mid = str(mem.get("memory_id", ""))
            if not mid or mid in seen_ids:
                continue
            seen_ids.add(mid)
            status = str(mem.get("status") or "") or COG_ACTIVE
            base = {
                "memory_id": mid,
                "entity": entity_name,
                "memory_type": str(mem.get("memory_type", "")),
                "snippet": str(mem.get("snippet", ""))[:80],
                "timestamp": str(mem.get("timestamp", "")),
            }
            if status == COG_CHALLENGED:
                item = dict(base, challenge_count=int(mem.get("challenge_count", 0)),
                            status_note=str(mem.get("status_note", "")))
                challenged.append(item)
            elif status == COG_SUPERSEDED:
                superseded.append(dict(
                    base,
                    superseded_by=str(mem.get("superseded_by", "") or ""),
                    superseded_at=str(mem.get("superseded_at", "") or ""),
                ))
            elif status == COG_ACTIVE and fragment_freshness(mem) < ARCHIVE_FRESHNESS_FLOOR:
                to_archive.append(dict(
                    base,
                    age_days=round(fragment_age_days(mem) or 0.0, 1),
                    freshness=round(fragment_freshness(mem), 4),
                ))

    superseded.sort(key=lambda x: x.get("superseded_at", ""), reverse=True)
    return {
        "challenged_count": len(challenged),
        "to_archive_count": len(to_archive),
        "superseded_count": len(superseded),
        "challenged": challenged[:list_cap],
        "to_archive": to_archive[:list_cap],
        "recent_supersede": superseded[:list_cap],
    }


__all__ = [
    "load_entity_index",
    "save_entity_index",
    "update_entity_index",
    "query_entities",
    "query_entities_ranked",
    "extract_entities_from_context",
    "merge_entities",
    "get_entity_heatmap",
    "bump_verification",
    "bump_verification_for_entities",
    "get_entity_summary",
    "get_fragment_by_id",
    # Concept memory API:
    "set_entity_profile",
    "get_entity_profile",
    "index_health_check",
    "prune_fragments_for_entity",
    "list_entity_names",
    # Auto-sync API:
    "sync_entity_from_source",
    "mark_entity_status",
    # 碎片认知生命周期 API:
    "apply_cognition_signal",
    "apply_supersede",
    "set_fragment_status",
    "archive_decayed_fragments",
    "get_supersede_chain",
    "cognition_backlog",
]
