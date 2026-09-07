"""碎片认知生命周期 —— 纯函数层（无 IO）。

本模块是 entity_index 碎片生命周期的单一常量源 + 纯计算层：
- 衰减：分层半衰期（freshness = 0.5 ** (age_days / half_life)），
  低于地板线的碎片从召回中过滤（资格过滤），与打分公式里的
  recency×0.35（排序惩罚）职责分离，避免双重惩罚。
- 认知状态：4 态 active / challenged / superseded / archived
  （裁剪自上游 8 态状态机——nascent/reinforced 的"证据强度"语义
  已由 verification_count 在打分公式中承担，不重复表达）。
- cog_key：结构化认知主键 "subject:predicate"，写入方显式传入
  （绝不自动生成），写时查重（bigram jaccard）在 entity_index.py。

设计约束：所有函数纯读 memory dict（防御性 .get()，老数据缺字段
天然合法、默认 active），不触碰文件系统——"召回不回写"由
tests/test_memory_redundancy_cuts.py 字节级锁定。

半衰期校准依据（生产 entity_index.json 实证 2026-09）：
全部 1366 碎片年龄 ≤60 天（>60d = 0 条），consciousness 14 天半衰期
→ 60.5 天落穿地板线 → 上线日过滤 0 条、随年龄渐进生效，天然灰度。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# 与 entity_index._LOCAL_TZ 同款惯用法：模块内自建本地时区，保持
# cognition ← entity_index 单向依赖（entity_index 要 import 本模块的
# 门控函数，反向引用会成环）。
_LOCAL_TZ = datetime.now().astimezone().tzinfo

# ── 认知状态（4 态；status 字段不存在 = active，零迁移）─────────────────────
COG_ACTIVE = "active"        # 缺省态：正常参与召回
COG_CHALLENGED = "challenged"  # 被证伪待决断（challenge_count ≥ 2 进入），降权仍可见
COG_SUPERSEDED = "superseded"  # 被新结论推翻（superseded_by 指向新碎片），召回出局
COG_ARCHIVED = "archived"      # 时间淘汰 / 显式归档（归档不删除），召回出局

_COG_RECALL_BLOCKED = frozenset({COG_SUPERSEDED, COG_ARCHIVED})

# ── 衰减半衰期（天）。None = 永不时间衰减（上游 permanence=1.0 豁免名单）────
# freshness = 0.5 ** (age_days / half_life)；公式与上游 exp(−Δh×(1−p)×0.005)
# 同族，但半衰期单参数可推理、可向模型解释。
#
# 与上游的关键分歧——insight 上游永不衰减，本地衰减（30d ≈130d 归档）：
# 本地 insight 是"未验证的闪念寄存室"（memory_hygiene：「idea 已采纳→删该
# insight，升级完不再原位存」），不是上游的结晶知识；且 record_thought 对
# 同一文本双写 consciousness+insight 两条碎片，insight 若免衰减则 consciousness
# 的衰减门形同虚设。md 文件（一等公民）不受影响，self_review 照读。
HALF_LIFE_DAYS: dict[str, float | None] = {
    "rule": None,           # 行为规则，永不过期
    "lesson": None,         # 已验证教训（LESSONS.md 同源），永不过期
    "insight": 30.0,        # 未验证闪念：≈130 天落穿地板线
    "consciousness": 14.0,  # 过程性意识流：≈60.5 天落穿地板线
    "todo": 3.0,
    "scratchpad": 1.0,
}
# consciousness + 瞬态 tag（trading_wait/system_wait/...）覆盖为更快衰减
# （≈13 天出局）——运行时状态快照本就是瞬态。与 entity_index 的
# _LOW_AUTHORITY_TAGS 保持同一取值来源（复制而非 import，避免模块间
# 私有常量耦合；两处若改动需同步）。
LOW_AUTHORITY_TAGS: tuple[str, ...] = ("trading_wait", "system_wait", "monitor", "final_status")
HALF_LIFE_LOW_TAG_DAYS: float = 3.0
HALF_LIFE_DEFAULT_DAYS: float = 30.0   # 未知类型兜底，对齐既有 recency 30 天线
ARCHIVE_FRESHNESS_FLOOR: float = 0.05  # freshness < 此值 → 召回过滤 / dream 归档

# ── 信号阈值（上游 verified/falsified delta 本地化）─────────────────────────
FALSIFY_TO_CHALLENGED: int = 2           # challenge_count ≥ 2 → challenged（防单次误证伪）
CHALLENGED_AUTHORITY_FACTOR: float = 0.5  # challenged 碎片 authority 乘数（排序降权）

# ── cog_key 写时查重（上游 0.92 拦截阈值保留）───────────────────────────────
COG_DUP_JACCARD: float = 0.92
COG_AUTO_SUPERSEDE: bool = True  # 同 key 异值自动建链；False = 只记 conflict_with 不执行


def normalize_cog_key(key: str) -> str:
    """cog_key 归一化：去首尾/内部空白、ASCII 小写。

    返回 "" 表示无效（空串/无分隔符）。中文全角冒号统一为半角。
    """
    if not key:
        return ""
    compact = "".join(str(key).split()).replace("：", ":").lower()
    return compact


def is_valid_cog_key(key: str) -> bool:
    """subject:predicate 格式校验——首个 ':' 两侧均非空。

    例：``华能蒙电:止损线=5.53`` 合法；``华能蒙电:`` / ``:止损`` /
    ``华能蒙电``（无分隔符）非法。写入前校验，非法即报错引导模型重传。
    """
    normalized = normalize_cog_key(key)
    if not normalized or ":" not in normalized:
        return False
    subject, _, predicate = normalized.partition(":")
    return bool(subject.strip()) and bool(predicate.strip())


def _bigrams(s: str) -> set[str]:
    """字符 bigram 集合。中文无需分词库；短串（<2 字符）退化为单字符。"""
    text = "".join(str(s or "").split())
    if len(text) < 2:
        return {text} if text else set()
    return {text[i:i + 2] for i in range(len(text) - 1)}


def bigram_jaccard(a: str, b: str) -> float:
    """两段文本的字符 bigram 集合 Jaccard 相似度 ∈ [0, 1]。

    任一侧为空 → 0.0（空串与任何文本都不算相似，避免空 snippet
    误命中查重）。既有 compute_text_similarity 用 6/8/10/12 长窗
    n-gram，适合长文本去重；cog_key/snippet 短文本用 bigram 更稳。
    """
    sa, sb = _bigrams(a), _bigrams(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _parse_timestamp(value: Any) -> datetime | None:
    """碎片 timestamp（本地时区 ISO）→ aware datetime；不可解析返回 None。"""
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if ts.tzinfo is None:
        # 与 entity_index._compute_recency 同款 naive 补丁：本地时区
        ts = ts.replace(tzinfo=_LOCAL_TZ)
    return ts


def half_life_days(memory: dict[str, Any]) -> float | None:
    """memory_type → 衰减半衰期（天）；None = 永不时间衰减。

    consciousness + 瞬态 tag 覆盖为 HALF_LIFE_LOW_TAG_DAYS；
    未知类型兜底 HALF_LIFE_DEFAULT_DAYS（对齐既有 recency 30 天线）。
    """
    mtype = str(memory.get("memory_type", "") or "").lower()
    if mtype == "consciousness":
        tag = str(memory.get("tag", "") or "").lower()
        for low_tag in LOW_AUTHORITY_TAGS:
            if low_tag in tag:
                return HALF_LIFE_LOW_TAG_DAYS
    return HALF_LIFE_DAYS.get(mtype, HALF_LIFE_DEFAULT_DAYS)


def fragment_age_days(memory: dict[str, Any], *, now: datetime | None = None) -> float | None:
    """碎片年龄（天）；timestamp 不可解析返回 None（backlog 报告展示用）。"""
    ts = _parse_timestamp(memory.get("timestamp"))
    if ts is None:
        return None
    reference = now or datetime.now(_LOCAL_TZ)
    return max(0.0, (reference - ts).total_seconds() / 86400.0)


def fragment_freshness(memory: dict[str, Any], *, now: datetime | None = None) -> float:
    """时间新鲜度 ∈ (0, 1]：``0.5 ** (age_days / half_life)``。

    - 永不衰减类型（rule/lesson）→ 1.0
    - timestamp 不可解析 → 1.0：召回门是强动作（彻底过滤），对损坏
      时间戳假阳性过滤比放行更糟。与 _compute_recency 失败返 0.0
      （排序惩罚，弱动作）方向不同是有意为之。
    """
    half_life = half_life_days(memory)
    if half_life is None:
        return 1.0
    age = fragment_age_days(memory, now=now)
    if age is None:
        return 1.0
    return 0.5 ** (age / half_life)


def passes_recall_gate(memory: dict[str, Any], *, now: datetime | None = None) -> bool:
    """召回门（纯函数，绝不写盘）：

    1. 状态门：status ∈ {superseded, archived} 出局（被推翻/已归档的
       碎片不进被动注入；主动查询路径 recall_entity 可见并带注记）；
    2. 衰减门：freshness < ARCHIVE_FRESHNESS_FLOOR 出局。

    challenged 不在出局名单——被证伪待决断的碎片降权（authority×
    CHALLENGED_AUTHORITY_FACTOR）但仍参与召回，等 dream 决断。
    """
    status = str(memory.get("status") or "") or COG_ACTIVE
    if status in _COG_RECALL_BLOCKED:
        return False
    return fragment_freshness(memory, now=now) >= ARCHIVE_FRESHNESS_FLOOR


__all__ = [
    # 常量
    "COG_ACTIVE",
    "COG_CHALLENGED",
    "COG_SUPERSEDED",
    "COG_ARCHIVED",
    "HALF_LIFE_DAYS",
    "LOW_AUTHORITY_TAGS",
    "HALF_LIFE_LOW_TAG_DAYS",
    "HALF_LIFE_DEFAULT_DAYS",
    "ARCHIVE_FRESHNESS_FLOOR",
    "FALSIFY_TO_CHALLENGED",
    "CHALLENGED_AUTHORITY_FACTOR",
    "COG_DUP_JACCARD",
    "COG_AUTO_SUPERSEDE",
    # 纯函数
    "normalize_cog_key",
    "is_valid_cog_key",
    "bigram_jaccard",
    "half_life_days",
    "fragment_age_days",
    "fragment_freshness",
    "passes_recall_gate",
]
