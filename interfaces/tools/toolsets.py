"""Digital Life toolset definitions."""

from __future__ import annotations


CORE_TOOLS = [
    "sense_wake_reason",
    "sense_vitals",
    "sense_time",
    "sense_event_queue",
    "sense_event_detail",
    "sense_self",
    "sense_memory",
    "sense_nurture_log",
    "sense_scratchpad",
    "sense_todos",
    "sense_daily",
    "skills_list",
    "skill_view",
    "express_to_human",
    "write_diary",
    "record_thought",
    "remember_him",
    "update_scratchpad",
    "todo",
    "todo_note",
    "todo_plan",
    "todo_trigger",
    "rest",
]


TOOLSETS = {
    "senses": {
        "description": "Digital Life sense tools for time, state, events, and memory",
        "tools": [
            "sense_wake_reason",
            "sense_vitals",
            "sense_time",
            "sense_event_queue",
            "sense_event_detail",
            "sense_self",
            "sense_memory",
            "sense_nurture_log",
            "sense_scratchpad",
            "sense_todos",
            "sense_daily",
            "sense_contacts",
            "skills_list",
            "skill_view",
            "recall_tool_result",
        ],
        "includes": [],
    },
    "actions": {
        "description": "Digital Life action tools for expression, journaling, thoughts, and rest",
        "tools": [
            "express_to_human",
            "write_diary",
            "record_thought",
            "remember_him",
            "update_scratchpad",
            "manage_daily",
            "rest",
            "terminal",
            "execute_code",
            "process",
        ],
        "includes": [],
    },
    "tasks": {
        "description": "Digital Life todo execution tools for assigned work",
        "tools": [
            "sense_todos",
            "todo",
            "todo_note",
            "todo_plan",
            "todo_trigger",
        ],
        "includes": [],
    },
    "web": {
        "description": "Digital Life web tools for searching and reading online pages",
        "tools": [
            "web_search",
            "web_fetch",
        ],
        "includes": [],
    },
}


def extend(*, toolsets: dict, core_tools: list[str]) -> None:
    for tool_name in CORE_TOOLS:
        if tool_name not in core_tools:
            core_tools.append(tool_name)
    toolsets.update(TOOLSETS)
