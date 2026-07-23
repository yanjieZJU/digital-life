"""历史对话检索工具——按内容/时间/工具类型检索旧段。

与叙事替换机制配合：
- 叙事注入时会提到 search_history(query="...") 可回溯详情
- 压缩时归档的大文件通过 read_archive(archive_id) 回溯
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from infrastructure.config import get_app_instance_id


# 时间范围 → 秒数
_TIME_RANGE_SECONDS = {
    "1h": 3600,
    "6h": 6 * 3600,
    "24h": 24 * 3600,
    "7d": 7 * 24 * 3600,
}


def search_session_messages(
    query: str,
    session_id: str | None = None,
    time_range: str = "24h",
    tool_type: str | None = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """在 session messages 中按内容/时间/工具类型搜索。

    Args:
        query: 搜索关键词
        session_id: 可选，限定搜索某个 session
        time_range: 时间范围，默认 24h（1h/6h/24h/7d）
        tool_type: 可选，限定工具类型（execute_code/terminal/read_file 等）
        limit: 返回结果数量

    Returns:
        匹配片段列表，每项包含 session_id、role、content、timestamp、tool_name
    """
    try:
        from infrastructure.ai.session_db import SessionDB
    except ImportError:
        return []

    session_db = SessionDB()
    now = time.time()
    cutoff = now - _TIME_RANGE_SECONDS.get(time_range, 24 * 3600)

    try:
        if session_id:
            # 搜索指定 session
            rows = session_db._conn.execute(
                """SELECT session_id, role, content, tool_name, timestamp, tool_calls
                   FROM messages
                   WHERE session_id=? AND timestamp > ? AND content IS NOT NULL AND content != ''
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (session_id, cutoff, limit * 10),
            ).fetchall()
        else:
            # 搜索所有 session
            rows = session_db._conn.execute(
                """SELECT session_id, role, content, tool_name, timestamp, tool_calls
                   FROM messages
                   WHERE timestamp > ? AND content IS NOT NULL AND content != ''
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (cutoff, limit * 20),
            ).fetchall()
    except Exception:
        return []

    if not rows:
        return []

    # 按内容相关性过滤
    query_lower = query.lower()
    results: List[Dict[str, Any]] = []

    for row in rows:
        content = row["content"] or ""
        tool_calls = row["tool_calls"]

        # 工具类型过滤
        if tool_type:
            tool_name = row["tool_name"] or ""
            if tool_type not in tool_name.lower():
                continue

        # 内容关键词匹配
        if query_lower in content.lower():
            # 提取上下文（前后各 100 字符）
            start = max(0, content.lower().find(query_lower) - 100)
            end = min(len(content), content.lower().rfind(query_lower) + len(query_lower) + 100)
            snippet = content[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(content):
                snippet = snippet + "..."

            results.append({
                "session_id": row["session_id"],
                "role": row["role"],
                "content": snippet,
                "full_content": content[:500],  # 完整内容（截断）
                "tool_name": row["tool_name"],
                "timestamp": row["timestamp"],
                "matched_on": "content",
            })

        # 也检查 tool_calls 中的函数名和参数
        elif tool_calls and tool_type is None:
            try:
                import json as _json
                calls = _json.loads(tool_calls) if isinstance(tool_calls, str) else tool_calls
                for call in calls:
                    func = call.get("function", {})
                    name = func.get("name", "")
                    args_str = func.get("arguments", "{}")
                    args = _json.loads(args_str) if isinstance(args_str, str) else args_str

                    # 函数名匹配
                    if query_lower in name.lower():
                        results.append({
                            "session_id": row["session_id"],
                            "role": row["role"],
                            "content": f"[{name}] {args_str[:200]}",
                            "tool_name": name,
                            "timestamp": row["timestamp"],
                            "matched_on": "tool_name",
                        })
                    # 参数内容匹配
                    elif query_lower in str(args).lower():
                        results.append({
                            "session_id": row["session_id"],
                            "role": row["role"],
                            "content": f"[{name}]: {str(args)[:200]}",
                            "tool_name": name,
                            "timestamp": row["timestamp"],
                            "matched_on": "tool_args",
                        })
            except Exception:
                pass

        if len(results) >= limit:
            break

    return results


def format_search_results(results: List[Dict[str, Any]]) -> str:
    """格式化搜索结果为可读文本。"""
    if not results:
        return "未找到匹配的对话片段。"

    lines = ["[历史搜索结果]"]
    for i, r in enumerate(results, 1):
        ts = time.localtime(r["timestamp"])
        time_str = time.strftime("%m-%d %H:%M", ts)
        matched = r.get("matched_on", "content")
        tool_info = f"[{r['tool_name']}] " if r.get("tool_name") else ""

        lines.append(f"\n--- 结果 {i} ---")
        lines.append(f"时间: {time_str} | 匹配: {matched} | Session: {r['session_id'][:20]}...")
        lines.append(f"{tool_info}{r['content']}")

    lines.append("\n[/历史搜索结果]")
    return "\n".join(lines)


__all__ = ["search_session_messages", "format_search_results"]
