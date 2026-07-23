"""Consciousness residue text helpers."""

from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional


ENTRY_SEPARATOR = "\n\n---\n\n"
SENT_LOG_HEADER = "# 发送记录（自动维护）"
WORK_HEADER = "# 工作看板\n\n用户交办的任务和自己的计划。\n\n"
SCRATCHPAD_HEADER = "# 草稿本 SCRATCHPAD\n\n我在研究什么、想做什么、最近在玩什么。\n\n---\n\n"
GOALS_HEADER = "# 我的目标\n\n我想做的事、想成为什么样的人、想达成什么。\n不一定要很伟大，可以是很小的愿望。\n\n"
PLANS_HEADER = "# 长期计划\n\n把目标拆成可以一步步完成的里程碑。\n\n"
WORK_SECTIONS = {
    "in_progress": "## 进行中\n",
    "todo": "## 待办\n",
    "done": "## 完成\n",
}
WEEKDAYS_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def split_entries(text: str) -> List[str]:
    """Split a consciousness markdown document into non-empty entries."""
    parts = text.split(ENTRY_SEPARATOR)
    return [part.strip() for part in parts[1:] if part.strip()]


def last_entry(text: str) -> Optional[str]:
    entries = split_entries(text)
    return entries[-1] if entries else None


def recent_entries(text: str, n: int = 3) -> str:
    entries = split_entries(text)
    if not entries:
        return "（意识流为空——这是我第一次醒来）"
    return ENTRY_SEPARATOR.join(entries[-n:]).strip()


def is_duplicate_thought(new_text: str, existing_text: str, *, threshold: float = 0.7) -> bool:
    """Detect whether a new thought repeats any existing entry above threshold.

    When true, the caller should REPLACE the duplicate entry instead of
    appending — preventing stale state (e.g. old "blocking items") from
    persisting alongside updated thoughts.
    """
    entries = split_entries(existing_text)
    if not entries:
        return False

    new_chars = _ngram_chars(new_text)
    if not new_chars:
        return False

    # Check against all entries (not just the last), return True if any
    # entry exceeds threshold. The caller can use find_duplicate_entry()
    # to determine which entry to replace.
    for entry in entries:
        entry_chars = _ngram_chars(entry)
        if not entry_chars:
            continue
        if len(new_chars & entry_chars) / len(new_chars) > threshold:
            return True
    return False


def compute_text_similarity(text1: str, text2: str) -> float:
    """Jaccard similarity between two texts based on character n-grams.

    Returns 0.0 to 1.0. Used by add_lesson() for write-time dedup.
    """
    chars1 = _ngram_chars(text1)
    chars2 = _ngram_chars(text2)
    if not chars1 or not chars2:
        return 0.0
    intersection = len(chars1 & chars2)
    union = len(chars1 | chars2)
    return intersection / union if union > 0 else 0.0


def _ngram_chars(text: str) -> set:
    """Extract character n-grams for similarity comparison."""
    chars = set()
    for i in range(len(text)):
        for n in (6, 8, 10, 12):
            if i + n <= len(text):
                chars.add(text[i:i + n])
    return chars


def find_duplicate_entry(text: str, new_text: str, *, threshold: float = 0.5) -> tuple[int, str] | None:
    """Find the entry most similar to new_text, above threshold.

    Returns (index, entry_text) of the best match, or None.
    Caller should replace this entry instead of appending.
    """
    entries = split_entries(text)
    new_chars = _ngram_chars(new_text)
    if not entries or not new_chars:
        return None

    best_idx, best_score, best_entry = -1, 0.0, ""
    for i, entry in enumerate(entries):
        entry_chars = _ngram_chars(entry)
        if not entry_chars:
            continue
        score = len(new_chars & entry_chars) / len(new_chars)
        if score > best_score:
            best_idx, best_score, best_entry = i, score, entry

    if best_score >= threshold:
        return best_idx, best_entry
    return None


def replace_entry_at(text: str, index: int, new_entry: str) -> str:
    """Replace the entry at index with new_entry. Returns updated text."""
    entries = split_entries(text)
    if 0 <= index < len(entries):
        header = text.split(ENTRY_SEPARATOR)[0]
        new_entries = entries.copy()
        new_entries[index] = new_entry
        return header + ENTRY_SEPARATOR + ENTRY_SEPARATOR.join(new_entries)
    return text


def format_sent_message_entry(timestamp: str, text: str) -> str:
    return f"{timestamp} | {text.strip()[:100]}\n"


def trim_sent_log_content(content: str, *, max_entries: int = 20) -> str:
    lines = content.splitlines()
    header = lines[0] if lines and lines[0].startswith("#") else SENT_LOG_HEADER
    data_lines = [line for line in lines if not line.startswith("#") and line.strip()]
    if len(data_lines) > max_entries:
        data_lines = data_lines[-max_entries:]
    return header + "\n" + "\n".join(data_lines) + ("\n" if data_lines else "")


def recent_sent_messages(content: str, n: int = 5) -> str:
    lines = content.splitlines()
    data_lines = [line for line in lines if not line.startswith("#") and line.strip()]
    if not data_lines:
        return "（还没有发送过消息）"
    return "\n".join(data_lines[-n:])


def initial_scratchpad_content() -> str:
    return SCRATCHPAD_HEADER


def replace_scratchpad_content(text: str) -> str:
    return SCRATCHPAD_HEADER + text.strip() + "\n"


def append_scratchpad_content(existing: str, text: str, timestamp: str) -> str:
    content = existing if existing else SCRATCHPAD_HEADER
    entry = f"\n## {timestamp}\n\n{text.strip()}\n"
    return content + entry


def initial_work_content() -> str:
    content = WORK_HEADER
    for section in WORK_SECTIONS.values():
        content += section + "\n"
    return content


def find_work_line(content: str, text_match: str):
    for match in re.finditer(r"^- \[.\] .+$", content, re.MULTILINE):
        line = match.group(0)
        if text_match in line:
            return match.start(), match.end(), line
    return None


def add_work_item_to_content(
    content: str,
    text: str,
    *,
    created_at: str,
    priority: str = "中",
    source: str = "用户",
) -> str:
    line = f"- [ ] {text.strip()} | 来源:{source} | 创建:{created_at} | 优先级:{priority}\n"
    marker = WORK_SECTIONS["todo"]
    index = content.find(marker)
    if index >= 0:
        insert_at = index + len(marker)
        return content[:insert_at] + line + content[insert_at:]
    return content + marker + line


def move_work_item_to_section(
    content: str,
    text_match: str,
    section: str,
    *,
    completed_at: str | None = None,
) -> tuple[str, bool]:
    result = find_work_line(content, text_match)
    if not result:
        return content, False

    start, end, line = result
    if completed_at is not None:
        line = re.sub(r"^-\ \[.\]", "- [x]", line)
        line = line.rstrip() + f" | 完成于:{completed_at}"

    content = content[:start] + content[end:]
    if content.startswith("\n", start):
        content = content[:start] + content[start + 1:]
    content = content.rstrip() + "\n"

    marker = WORK_SECTIONS[section]
    index = content.find(marker)
    if index >= 0:
        insert_at = index + len(marker)
        content = content[:insert_at] + line + "\n" + content[insert_at:]
    return content, True


def remove_work_item_from_content(content: str, text_match: str) -> tuple[str, bool]:
    result = find_work_line(content, text_match)
    if not result:
        return content, False
    start, end, _ = result
    content = content[:start] + content[end:]
    if content.startswith("\n", start):
        content = content[:start] + content[start + 1:]
    return content, True


def daily_marker(now: datetime) -> str:
    return f"## {now.strftime('%Y-%m-%d')} {WEEKDAYS_CN[now.weekday()]}"


def build_daily_section(text: str, now: datetime) -> tuple[str, int]:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return "", 0
    items = "\n".join(f"- [ ] {line}" for line in lines)
    return f"\n{daily_marker(now)}\n{items}\n", len(lines)


def upsert_daily_plan_content(existing: str, text: str, now: datetime) -> tuple[str, int]:
    section, count = build_daily_section(text, now)
    if not count:
        return existing, 0

    content = existing or "# 每日计划\n"
    marker = daily_marker(now)
    if marker in content:
        index = content.find(marker)
        next_section = content.find("\n## ", index + len(marker))
        header = content[:index].rstrip()
        rest = content[next_section:] if next_section >= 0 else ""
        return header + "\n\n" + section.strip() + "\n" + rest, count
    return content.rstrip() + "\n" + section + "\n", count


def add_planned_item_to_content(existing: str, text: str, now: datetime) -> str:
    marker = daily_marker(now)
    content = existing or "# 每日计划\n"
    line = f"- [ ] {text.strip()}\n"

    if marker in content:
        index = content.find(marker)
        next_section = content.find("\n## ", index + len(marker))
        if next_section < 0:
            next_section = len(content)
        return content[:next_section] + line + content[next_section:]

    entry = f"\n{marker}\n{line}"
    return content.rstrip() + "\n" + entry + "\n"


def complete_planned_item_in_content(existing: str, text_match: str, now: datetime) -> tuple[str, bool]:
    marker = daily_marker(now)
    if marker not in existing:
        return existing, False

    index = existing.find(marker)
    next_section = existing.find("\n## ", index + len(marker))
    section = existing[index:(next_section if next_section >= 0 else len(existing))]

    for match in re.finditer(r"^- \[.\] .+$", section, re.MULTILINE):
        line = match.group(0)
        if text_match in line:
            global_start = index + match.start()
            global_end = index + match.end()
            new_line = re.sub(r"^- \[.\]", "- [x]", line)
            return existing[:global_start] + new_line + existing[global_end:], True
    return existing, False


def check_daily_content(existing: str, now: datetime) -> str:
    marker = daily_marker(now)
    weekday = WEEKDAYS_CN[now.weekday()]
    if not existing or marker not in existing:
        return "今天还没有计划。用 manage_daily plan 来规划一下今天做什么？"

    index = existing.find(marker)
    next_section = existing.find("\n## ", index + len(marker))
    section = existing[index:(next_section if next_section >= 0 else len(existing))]

    total = 0
    done = 0
    pending = []
    for match in re.finditer(r"^- \[(.)\] (.+)$", section, re.MULTILINE):
        total += 1
        if match.group(1) == "x":
            done += 1
        else:
            pending.append(match.group(2))

    if total == 0:
        return f"今天（{weekday}）的计划是空的。想做什么就规划一下吧。"

    status = f"今天（{weekday}）：{done}/{total} 已完成。"
    if pending:
        status += f"\n待做：{', '.join(pending[:5])}"
        if len(pending) > 5:
            status += f" 等{len(pending)-5}项"
    else:
        status += "\n今天的计划全部完成了！"
    return status


def initial_goals_content() -> str:
    return GOALS_HEADER


def find_goal_section(content: str, text_match: str):
    matches = list(re.finditer(r"\n## [🎯✅❌] .+", content))
    for index, match in enumerate(matches):
        section_start = match.start()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        section_text = content[section_start:section_end]
        if text_match in section_text:
            return section_start, section_end, section_text
    return None


def manage_goal_content(
    content: str,
    action: str,
    text: str,
    *,
    today: str,
    description: str = "",
    priority: str = "中",
) -> tuple[str, str]:
    if action == "add":
        if not text.strip():
            return content, "错误：目标名称不能为空"
        entry = f"\n## 🎯 {text.strip()}\n"
        if description.strip():
            entry += f"> {description.strip()}\n"
        entry += f"> 状态：进行中 | 创建：{today} | 优先级：{priority or '中'}\n"
        return content + entry, f"目标「{text.strip()}」已添加。"

    if action == "review":
        goals = re.findall(r"## ([🎯✅❌]) (.+)", content)
        if not goals:
            return content, "目前还没有任何目标。想做什么就设一个吧。"
        result = []
        for icon, name in goals:
            if icon == "🎯":
                result.append(f"🎯 {name} — 进行中")
            elif icon == "✅":
                result.append(f"✅ {name} — 已达成")
            elif icon == "❌":
                result.append(f"❌ {name} — 已放弃")
        return content, f"你目前有 {len(result)} 个目标：\n" + "\n".join(result)

    if action in ("complete", "abandon"):
        if not text.strip():
            return content, "错误：需要指定目标名称关键词"
        result = find_goal_section(content, text.strip())
        if not result:
            return content, f"没找到包含「{text.strip()}」的目标"
        start, end, section = result
        if action == "complete":
            new_section = section.replace("## 🎯 ", "## ✅ ", 1)
            new_section = new_section.replace("状态：进行中", f"状态：达成 | 达成于：{today}")
            label = "达成"
        else:
            new_section = section.replace("## 🎯 ", "## ❌ ", 1)
            new_section = new_section.replace("状态：进行中", f"状态：放弃 | 放弃于：{today}")
            label = "放弃"
        return content[:start] + new_section + content[end:], f"目标「{text.strip()}」已标记为{label}。"

    return content, f"未知操作：{action}"


def initial_plans_content() -> str:
    return PLANS_HEADER


def manage_plan_item_content(content: str, action: str, goal: str, text: str) -> tuple[str, str]:
    if action == "add_milestone":
        if not goal.strip() or not text.strip():
            return content, "错误：需要目标和里程碑描述"
        goal_section = f"\n## {goal.strip()}\n### 里程碑\n"
        line = f"- [ ] {text.strip()}\n"
        if goal_section.rstrip() in content:
            marker = f"\n## {goal.strip()}\n"
            index = content.find(marker)
            next_section = content.find("\n## ", index + len(marker) + 1)
            insert_at = next_section if next_section >= 0 else len(content)
            content = content[:insert_at] + line + content[insert_at:]
        else:
            content = content.rstrip() + goal_section + line + "\n"
        return content, f"里程碑「{text.strip()}」已添加到「{goal.strip()}」的计划。"

    if action in ("complete_milestone", "remove_milestone"):
        if not goal.strip() or not text.strip():
            return content, "错误：需要目标和里程碑描述"
        marker = f"\n## {goal.strip()}\n"
        if marker not in content:
            return content, f"没找到「{goal.strip()}」的计划"
        index = content.find(marker)
        next_section = content.find("\n## ", index + len(marker) + 1)
        section_end = next_section if next_section >= 0 else len(content)
        section = content[index:section_end]

        for match in re.finditer(r"^- \[.\] .+$", section, re.MULTILINE):
            line = match.group(0)
            if text.strip() in line:
                global_start = index + match.start()
                global_end = index + match.end()
                if action == "complete_milestone":
                    new_line = re.sub(r"^- \[.\]", "- [x]", line)
                    return content[:global_start] + new_line + content[global_end:], f"里程碑「{text.strip()}」已完成！"
                return content[:global_start] + content[global_end:], f"里程碑「{text.strip()}」已移除。"
        return content, f"在「{goal.strip()}」的计划中没找到「{text.strip()}」"

    return content, f"未知操作：{action}"


__all__ = [
    "ENTRY_SEPARATOR",
    "SENT_LOG_HEADER",
    "SCRATCHPAD_HEADER",
    "WORK_HEADER",
    "WORK_SECTIONS",
    "GOALS_HEADER",
    "PLANS_HEADER",
    "WEEKDAYS_CN",
    "add_work_item_to_content",
    "add_planned_item_to_content",
    "build_daily_section",
    "check_daily_content",
    "complete_planned_item_in_content",
    "compute_text_similarity",
    "daily_marker",
    "append_scratchpad_content",
    "find_work_line",
    "find_goal_section",
    "format_sent_message_entry",
    "initial_work_content",
    "initial_scratchpad_content",
    "initial_goals_content",
    "initial_plans_content",
    "find_duplicate_entry",
    "is_duplicate_thought",
    "last_entry",
    "move_work_item_to_section",
    "recent_entries",
    "replace_entry_at",
    "recent_sent_messages",
    "remove_work_item_from_content",
    "replace_scratchpad_content",
    "manage_goal_content",
    "manage_plan_item_content",
    "split_entries",
    "trim_sent_log_content",
    "upsert_daily_plan_content",
]
