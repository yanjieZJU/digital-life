"""Token 预算和精力-token 耦合的基础设施层。

公开两个独立的机制（产品语义详见设计文档 15.4 / 二十三）：

1. **TokenUsageTracker**（token_tracker.py）— 每实例 token 用量累加器，
   持久化到 state.db。每次 LLM call 完成后记录一笔，按小时/天窗口聚合。
   是数据基础：没有它，预算闸门和精力-token 耦合都没法落地。

2. **budget_gate**（budget_gate.py）— 每实例每小时/每日 token 上限闸门，
   cron 在决定是否 wake 数字生命之前先问它。超阈值 → 拒绝（高优先级真人
   消息除外）。是核心防线：不管出现什么事件源刷屏，token 用过了就强制躺平。

（历史上曾有第三个机制 task_reminder_gate，已被「队列级去重」取代：
domain.todos.scheduler.schedule_task_wakeup 在 emit 前先 check 队列里
是否已有同 task_id 的未消费 task_reminder——有的话就丢弃。这比之前的
"窗口限流"更符合产品语义：一位待办只需要一个未消费提醒就够。）

设计要点（与用户对齐）：

- 这两个机制**不被业务/精力/事件优先级覆盖**。闸门是基础设施级硬保护，
  不让"任何 bug 或 event 风暴"把 token 配额烧光（历史教训：06-14 一夜
  130MB 日志 + token 配额爆掉死循环、06-13 alpha 完成门禁死循环）。

- 精力-token 耦合（engine.py：consume_energy 接真实 token 数）用 token_tracker
  算出消耗，按 ENERGY_PER_KTOKEN_INPUT/OUTPUT 折算成精力点。
"""

from __future__ import annotations

from .token_tracker import TokenUsageTracker, get_token_tracker
from .budget_gate import (
    BudgetState,
    BudgetGate,
    get_budget_state,
    should_allow_wake,
    HIGH_PRIORITY_KINDS,
    DEFAULT_TOKEN_HOURLY_LIMIT,
    DEFAULT_TOKEN_DAILY_LIMIT,
)
from .circuit_breaker import (
    CircuitBreakerOpen,
    circuit_breaker_db_path,
    clear as clear_circuit_breaker,
    is_tripped,
    resolve_retry_after,
    trip,
)


__all__ = [
    "TokenUsageTracker",
    "get_token_tracker",
    "BudgetState",
    "BudgetGate",
    "get_budget_state",
    "should_allow_wake",
    "HIGH_PRIORITY_KINDS",
    "DEFAULT_TOKEN_HOURLY_LIMIT",
    "DEFAULT_TOKEN_DAILY_LIMIT",
    # 账号级 429 熔断（按 api_key 分区，跨实例共享）
    "CircuitBreakerOpen",
    "circuit_breaker_db_path",
    "clear_circuit_breaker",
    "is_tripped",
    "resolve_retry_after",
    "trip",
]
