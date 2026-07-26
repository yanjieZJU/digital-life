"""回归测试：memory 冗余清理——两处行为保持的剪枝。

1. ``query_entities_ranked`` 不再回写 ``entity_index.json``。
   历史上每次召回命中都会调 ``touch_last_accessed`` 更新一个**从未被读取**的
   ``last_accessed`` 字段，触发整份 JSON 的读改写（每条命中一次全文件 IO）。
   现已移除该写路径；本测试锁定"召回不改变磁盘文件"。

2. ``_index_source`` 增量化：未变更文件不再触发 embedding 重算，且文件内容
   变更/删除后 stale chunk 被清理。历史上函数开头 ``DELETE FROM chunks
   WHERE source=?`` 抹掉全部行，使逐 chunk 的 mtime 检查永远 miss → 每次
   ensure_indexed 都全量重 embed。移除该 DELETE 后 mtime 检查真正生效。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


# ─────────────────────────────────────────────────────────────────────
# Cut 1: 召回不应回写 entity_index.json
# ─────────────────────────────────────────────────────────────────────


def test_query_ranked_does_not_rewrite_index(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """召回命中后，entity_index.json 内容必须逐字节不变。"""
    from domain.memory.memory.consciousness import entity_index as ei

    mem_dir = tmp_path / "memories"
    mem_dir.mkdir()
    monkeypatch.setattr(ei, "_get_runtime_home", lambda: tmp_path)

    ei.save_entity_index({
        "version": 1,
        "entities": {
            "BYD": {
                "aliases": ["比亚迪"],
                "type": "stock",
                "memories": [
                    {
                        "memory_type": "lesson",
                        "memory_id": "lesson:test:1",
                        "snippet": "BYD 跌3%要提醒用户",
                        "timestamp": "2026-07-01T00:00:00+08:00",
                        "linked_entities": [],
                        "verification_count": 1,
                        "last_accessed": None,
                    }
                ],
            }
        },
    })
    idx_path = mem_dir / "entity_index.json"
    before = idx_path.read_text(encoding="utf-8")

    results = ei.query_entities_ranked(["BYD"], current_context="盯 BYD 跌3%", limit=3)
    assert results, "应召回 BYD 的 lesson 碎片"

    after = idx_path.read_text(encoding="utf-8")
    assert before == after, (
        "召回不应回写 entity_index.json——last_accessed 写路径应已移除。"
        f"before != after (长度 {len(before)} vs {len(after)})"
    )


def test_touch_last_accessed_removed_from_public_api():
    """touch_last_accessed 已从 __all__ 移除（写路径删除的标志）。"""
    from domain.memory.memory.consciousness import entity_index as ei

    assert "touch_last_accessed" not in ei.__all__
    assert not hasattr(ei, "touch_last_accessed"), "touch_last_accessed 函数应已删除"


# ─────────────────────────────────────────────────────────────────────
# Cut 3: _index_source 增量化
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def vector_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """隔离的向量模块：tmp 目录 + 假 embedding（计数调用）。"""
    import domain.memory.memory.recall.vector as vec

    mem_dir = tmp_path / "memories"
    mem_dir.mkdir()
    monkeypatch.setattr(vec, "_get_mem_dir", lambda: mem_dir)

    calls = {"texts_embedded": 0}

    def fake_embed(texts):
        calls["texts_embedded"] += len(texts)
        # 任意固定向量即可——本测试不验证相似度，只验证是否被调用
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    monkeypatch.setattr(vec, "_embed_texts", fake_embed)
    return vec, mem_dir, calls


def test_index_source_skips_unchanged_chunks(vector_module):
    """文件未变更时再次索引：不触发任何 embedding 调用，chunks 仍在库。"""
    vec, mem_dir, calls = vector_module
    rules = mem_dir / "RULES.md"
    rules.write_text("# Rules\n\n- 规则一\n- 规则二\n- 规则三\n", encoding="utf-8")

    db = vec._get_db()
    try:
        cfg = vec._FILE_SOURCES["rules"]
        n1 = vec._index_source(db, "rules", cfg)
        assert n1 > 0, "首次索引应嵌入若干 chunk"
        embedded_after_first = calls["texts_embedded"]
        assert embedded_after_first > 0

        # 再次索引——文件未变，mtime 不变 → 不应触发 embedding
        n2 = vec._index_source(db, "rules", cfg)
        assert n2 == 0, "未变更文件不应产生新嵌入"
        assert calls["texts_embedded"] == embedded_after_first, (
            "未变更文件不应调用 embedding API"
        )

        cnt = db.execute("SELECT COUNT(*) FROM chunks WHERE source='rules'").fetchone()[0]
        assert cnt > 0, "chunks 应仍保留在库中"
    finally:
        db.close()


def test_index_source_prunes_stale_chunks_on_change(vector_module):
    """文件内容变更后：旧 chunk 被清理，只有新内容的 chunk 留在库中。"""
    vec, mem_dir, calls = vector_module
    rules = mem_dir / "RULES.md"
    rules.write_text("# Rules\n\n- 规则一\n- 规则二\n", encoding="utf-8")

    db = vec._get_db()
    try:
        cfg = vec._FILE_SOURCES["rules"]
        vec._index_source(db, "rules", cfg)
        before_texts = [r["text"] for r in db.execute(
            "SELECT text FROM chunks WHERE source='rules'"
        ).fetchall()]
        assert any("规则二" in t for t in before_texts)

        # 改写为完全不同的内容，并推进 mtime 确保越过旧 file_mtime
        rules.write_text("# Rules\n\n- 全新的规则X\n", encoding="utf-8")
        future = rules.stat().st_mtime + 100
        os.utime(rules, (future, future))

        vec._index_source(db, "rules", cfg)

        after_texts = [r["text"] for r in db.execute(
            "SELECT text FROM chunks WHERE source='rules'"
        ).fetchall()]
        assert any("全新的规则X" in t for t in after_texts), "新内容应被索引"
        assert not any("规则二" in t for t in after_texts), (
            "旧 stale chunk 应被清理，不应残留"
        )
    finally:
        db.close()


def test_index_source_prunes_when_file_deleted(vector_module):
    """源文件被删除后：该 source 的 chunks 全部清理。"""
    vec, mem_dir, calls = vector_module
    rules = mem_dir / "RULES.md"
    rules.write_text("# Rules\n\n- 规则一\n", encoding="utf-8")

    db = vec._get_db()
    try:
        cfg = vec._FILE_SOURCES["rules"]
        vec._index_source(db, "rules", cfg)
        assert db.execute("SELECT COUNT(*) FROM chunks WHERE source='rules'").fetchone()[0] > 0

        rules.unlink()
        n = vec._index_source(db, "rules", cfg)
        assert n == 0
        cnt = db.execute("SELECT COUNT(*) FROM chunks WHERE source='rules'").fetchone()[0]
        assert cnt == 0, "文件删除后该 source 的 chunks 应被清理"
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────
# Cut 4: embedding 不可用时不再降级到关键词召回
# ─────────────────────────────────────────────────────────────────────


def test_vector_recall_returns_empty_when_embedding_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """embedding 不可用 → 诚实返回空串，不再走低质量关键词降级（消除双实现冗余）。"""
    import domain.memory.memory.recall.vector as vec

    mem_dir = tmp_path / "memories"
    mem_dir.mkdir()
    monkeypatch.setattr(vec, "_get_mem_dir", lambda: mem_dir)
    # ensure_indexed 与 recall 都依赖 embedding；模拟"embedding 完全不可用"
    monkeypatch.setattr(vec, "_embed_texts", lambda texts: None)
    monkeypatch.setattr(vec, "_embed_single", lambda text: None)

    out = vec.recall("盯 BYD 跌3%", max_total_chars=400)
    assert out == "", (
        "embedding 不可用时应返回空串，而非降级到关键词召回（双实现冗余已移除）"
    )
