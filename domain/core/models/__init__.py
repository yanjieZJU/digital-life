"""L4 纯领域模型 — 与 Hermes、SQLite、飞书、文件系统无关的纯数据结构。

事件系统核心模型：

EventTypeDefinition — 事件类型定义（注册在 event_registry 中）
  字段说明：
    type_id:              事件标识（如 message、timer、vital_threshold）
    display_name:         中文显示名称
    trigger_type:         触发类型（time/condition/message/manual/system/external）
    payload_schema:       事件携带数据的 schema 定义
    prompt_template:      唤醒时注入 LLM 的 prompt 模板（含 {占位符}）
    allowed_tools:        该事件推荐使用的工具列表
    priority:             优先级（1-10），越高越优先唤醒
    debounce_window_s:    防抖窗口（秒），窗口期内同类型事件合并
    merge_policy:         合并策略（latest: 覆盖 / accumulate: 累加文本 / count: 只增计数）
    consumption_policy:   消费时机（on_detail: sense_event_detail 时消费 / on_trigger: 触发时消费）
    trigger_description:  人类可读的触发条件说明

EventInstance — 事件实例（运行时的具体事件）
EventStatus — 事件状态枚举（PENDING → RUNNING → DONE/BLOCKED/CANCELLED/EXPIRED）
EventTriggerType — 触发类型枚举
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from .lifecycle_split import LifecycleLayer, LifecycleSourceSlice


class EventStatus(str, Enum):
    """事件生命周期状态。

    PENDING → RUNNING → DONE     正常流转
    PENDING → RUNNING → BLOCKED  执行阻塞
    PENDING → CANCELLED         手动取消
    PENDING → EXPIRED           超时过期
    """
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    DEAD_LETTER = "dead_letter"


class EventTriggerType(str, Enum):
    """事件触发类型 — 决定事件由哪个子系统生成和维护。"""
    TIME = "time"          # 定时触发（timer、routine）
    CONDITION = "condition"  # 条件触发（vital_threshold、initiative）
    MESSAGE = "message"     # 消息触发
    MANUAL = "manual"       # 手动触发（前端按钮、API 调用）
    SYSTEM = "system"       # 系统自动生成（birth、task_reminder）
    EXTERNAL = "external"   # 外部触发（message、group_message）


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str = ""
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    permission: str = "default"
    toolset: str = "default"
    source: str = "l4"


@dataclass(frozen=True)
class EventTypeDefinition:
    """事件类型定义 — 注册在 event_registry 中，描述一种事件的完整元数据。

    数据来源：config/event_types.yaml（唯一数据源），
    启动时由 domain.lifecycle.event_registry._register_all() 加载到内存。
    实例级 prompt 覆写从 apps/{uuid}/data/config.yaml 热加载。

    关键设计决策：
      - priority 决定唤醒顺序：message(10) > birth(9) > vital_threshold(8) > group_message(7) > ...
      - debounce_window_s + merge_policy 避免事件风暴：
        群消息 60s 窗口内 accumulate，vital_threshold 不防抖（每次都要提醒）
      - consumption_policy 决定何时标记已消费：
        on_detail: 调用 sense_event_detail 时消费（默认）
        on_trigger: 事件触发时立即消费（initiative 等无内容事件）
    """
    type_id: str
    display_name: str
    trigger_type: EventTriggerType
    payload_schema: Mapping[str, Any] = field(default_factory=dict)
    prompt_template: str = ""
    allowed_tools: tuple[str, ...] = ()
    context_policy: Mapping[str, Any] = field(default_factory=dict)
    auth_policy: Mapping[str, Any] = field(default_factory=dict)
    # ── 事件引擎新字段 ──
    description: str = ""
    priority: int = 5
    debounce_window_s: tuple[int, int] = (0, 0)  # (min, max) 秒；范围内随机制造 wake 错峰
    merge_policy: str = "latest"  # latest | accumulate | count
    consumption_policy: str = "on_detail"  # on_detail | on_trigger
    trigger_description: str = ""  # 触发条件说明，给人类看的


@dataclass
class EventInstance:
    """事件实例 — 运行时的具体事件。

    与 EventTypeDefinition 的关系：
      EventTypeDefinition 是"类"（描述 message 是什么），
      EventInstance 是"实例"（某条具体的消息）。

    生命周期：emit → PENDING → (debounce merge) → pop → RUNNING → consume → DONE
    """
    id: str
    type_id: str
    trigger_type: EventTriggerType
    payload: Mapping[str, Any] = field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING
    agent_id: str | None = None
    workspace_id: str | None = None
    context_hint: str = ""
    fire_at: str | None = None   # 定时触发时间（NULL = 立即触发）
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class Workspace:
    id: str
    goal: str
    title: str
    status: str = "active"
    current_plan: str = ""
    next_step: str = ""


@dataclass(frozen=True)
class WorkspacePlan:
    id: str
    workspace_id: str
    content: str
    status: str = "pending"
    deadline: str | None = None
    order: int = 0


@dataclass(frozen=True)
class WorkspaceNote:
    id: str
    workspace_id: str
    content: str
    created_at: str | None = None


@dataclass(frozen=True)
class WorkspaceDetail:
    workspace: Workspace
    notes: tuple[WorkspaceNote, ...] = ()
    plans: tuple[WorkspacePlan, ...] = ()
    workspace_notes: str = ""


@dataclass(frozen=True)
class PromptBundle:
    system: str
    event_context: str
    memory_context: str = ""
    workspace_context: str = ""
    vitals_context: str = ""
    execution_context: str = ""


@dataclass(frozen=True)
class AgentRun:
    id: str
    agent_id: str
    event_id: str
    prompt: PromptBundle
    allowed_tools: tuple[ToolDefinition, ...] = ()


@dataclass(frozen=True)
class AgentRunResult:
    run_id: str
    status: str
    final_message: str = ""
    tool_calls: tuple[Mapping[str, Any], ...] = ()
    summary: str = ""


__all__ = [
    "AgentRun",
    "AgentRunResult",
    "EventInstance",
    "EventStatus",
    "EventTriggerType",
    "EventTypeDefinition",
    "LifecycleLayer",
    "LifecycleSourceSlice",
    "PromptBundle",
    "ToolDefinition",
    "Workspace",
    "WorkspaceDetail",
    "WorkspaceNote",
    "WorkspacePlan",
]
