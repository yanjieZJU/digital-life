"""Keyword-based associative memory recall."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from infrastructure.config import get_runtime_memories_dir

DEFAULT_MEMORY_DIR = get_runtime_memories_dir()

SOURCES = {
    "identity": {"path": "CONSCIOUSNESS.md", "max_chars": 600, "weight": 1.5},
    "journal": {"path": "DIARY.md", "max_chars": 400, "weight": 1.0},
    "notes": {"path": "SCRATCHPAD.md", "max_chars": 500, "weight": 1.2},
    "goals": {"path": "GOALS.md", "max_chars": 400, "weight": 1.3},
    "plans": {"path": "PLANS.md", "max_chars": 300, "weight": 1.2},
    "him": {"path": "HIM.md", "max_chars": 300, "weight": 1.3},
}

STOP_WORDS = frozenset(
    "的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 "
    "自己 这 他 她 它 们 那 些 什么 怎么 可以 这个 那个 但 如果 因为 所以 或者 虽然 "
    "已经 可能 应该 需 要 做 使 用 让 被 把 从 对 与 而 为 以 及 等 还 再 吧 啊 呢 吗 "
    "嗯 哦 哈 呀 没关系 但是 然后 不过 其实 另外 首先 其次 最后 一下 一点 一个 "
    "用户 联系人".split()
)


def tokenize(text: str) -> List[str]:
    """Simple tokenizer: Latin words plus Chinese bigrams and chars."""
    tokens = []
    for word in re.findall(r"[a-zA-Z0-9]+", text.lower()):
        if len(word) > 1:
            tokens.append(word)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    for index in range(len(chinese_chars) - 1):
        bigram = chinese_chars[index] + chinese_chars[index + 1]
        if bigram not in STOP_WORDS:
            tokens.append(bigram)
    for char in chinese_chars:
        if char not in STOP_WORDS:
            tokens.append(char)
    return tokens


def term_frequency(tokens: List[str]) -> Dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {token: count / total for token, count in counts.items()}


def cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    if not common:
        return 0.0
    dot = sum(a[key] * b[key] for key in common)
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def sliding_chunks(text: str, max_chars: int = 300, overlap: int = 50) -> List[str]:
    if len(text) <= max_chars:
        return [text] if text.strip() else []
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        paragraph_break = chunk.rfind("\n\n")
        if paragraph_break > max_chars // 2:
            chunk = chunk[:paragraph_break]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += max_chars - overlap
    return chunks


def recall(
    query: str,
    extra_context: str = "",
    max_total_chars: int = 800,
    min_score: float = 0.05,
    memory_dir: Optional[Path] = None,
) -> str:
    """Recall related memory fragments using keyword similarity."""
    full_query = f"{query} {extra_context}".strip()
    query_tokens = tokenize(full_query)
    if not query_tokens:
        return ""
    query_tf = term_frequency(query_tokens)

    results: List[Tuple[float, str, str]] = []
    root = memory_dir or DEFAULT_MEMORY_DIR

    for label, config in SOURCES.items():
        file_path = root / config["path"]
        if not file_path.exists():
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        if not content.strip():
            continue

        tail = content[-(config["max_chars"] * 3):]
        chunks = sliding_chunks(tail, max_chars=config["max_chars"])

        for chunk in chunks:
            chunk_tf = term_frequency(tokenize(chunk))
            score = cosine_similarity(query_tf, chunk_tf) * config["weight"]
            if score >= min_score:
                results.append((score, label, chunk))

    if not results:
        return ""

    results.sort(key=lambda item: item[0], reverse=True)

    lines = ["[联想记忆 — 自动召回的相关片段]"]
    total_chars = 0
    for score, label, text in results:
        entry = f"\n[{label.upper()} score={score:.2f}] {text[:200]}"
        if total_chars + len(entry) > max_total_chars:
            break
        lines.append(entry)
        total_chars += len(entry)

    if len(lines) <= 1:
        return ""

    lines.append("\n[/联想记忆]")
    return "".join(lines)


__all__ = [
    "DEFAULT_MEMORY_DIR",
    "SOURCES",
    "STOP_WORDS",
    "cosine_similarity",
    "recall",
    "sliding_chunks",
    "term_frequency",
    "tokenize",
]
