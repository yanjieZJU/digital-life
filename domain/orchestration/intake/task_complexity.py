"""Task complexity classification before orchestration planning."""

from __future__ import annotations

import re
from dataclasses import dataclass


_COMPLEX_KEYWORDS = (
    "复杂",
    "改造",
    "重构",
    "架构",
    "设计",
    "规划",
    "调研",
    "方案",
    "实现",
    "开发",
    "迁移",
    "拆解",
    "多阶段",
    "长期",
    "workflow",
    "pipeline",
    "architecture",
    "refactor",
)


@dataclass(frozen=True)
class TaskComplexityDecision:
    complex: bool
    reason: str


class TaskComplexityClassifier:
    """Classify assigned tasks before they enter orchestration/execution."""

    def classify(self, title: str, description: str = "", priority: str = "medium") -> TaskComplexityDecision:
        text = f"{title}\n{description}".strip()
        if priority == "urgent" and len(text) >= 80:
            return TaskComplexityDecision(True, "urgent_long_task")
        if len(text) >= 160:
            return TaskComplexityDecision(True, "long_task_description")
        if len([line for line in text.splitlines() if line.strip()]) >= 4:
            return TaskComplexityDecision(True, "multi_line_task")
        keyword_hits = [keyword for keyword in _COMPLEX_KEYWORDS if keyword.lower() in text.lower()]
        if len(keyword_hits) >= 2:
            return TaskComplexityDecision(True, "complex_keywords:" + ",".join(keyword_hits[:4]))
        if re.search(r"(第一|第二|第三|阶段|步骤|里程碑|验收|前后端|后端|前端)", text):
            return TaskComplexityDecision(True, "structured_delivery_terms")
        return TaskComplexityDecision(False, "simple_task")


__all__ = ["TaskComplexityClassifier", "TaskComplexityDecision"]
