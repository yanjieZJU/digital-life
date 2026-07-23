"""BudgetGate — 每实例 token 预算闸门，cron 在 wake 前先问它。

产品语义（设计文档 二十三章）：
  数字生命醒来时，系统先问"这个小时还能烧么？"不能烧，再说。
  除非有人 @ 他（高优先级真人消息），否则一律推迟到下个窗口。

为什么这件事必须独立于精力值、独立于事件优先级：
  - 精力值低不阻断 cron 触发新 wake（产品上"数字生命累"但还能被叫醒处理真事）
  - 事件优先级决定了"哪个最重要"，但不能回答"还能不能烧"
  - 历史教训：06-14 一夜 130MB 日志 + GLM 配额爆掉死循环——精力是满的
    (账面 99+),但 token 已经被烧光。预算闸门是基础设施级别的硬保护，用
    fix 单点 bug 没法替代。

设计要点：
  - 双轴阈值：每小时上限 + 每日上限。两道独立，谁触发就拒绝。
  - 高优先级"穿透"：人类私聊/群聊消息、出生事件 即使超额也放行，否则
    用户主动 @ 却叫不醒模型就太蠢。
  - 失败处理：超阈值时把当前 due events 推到下个窗口（或临时退避 5 分钟），
    不删事件、不发 retry alarm。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Set, Tuple


logger = logging.getLogger(__name__)


# 默认预算（可被 env override）
# 2026-06-16 调整：实测 2000万/天 + 200万/小时 在多实例同时长跑场景容易
# 打穿——任意一实例连续工作 1 小时就超 200万 → 事件被退避循环 → routine
# 等待 5 小时才执行。
# 按用户决策（2026-06-16），开发期统一挂 5000万/天 当顶配，
# 同时把 hourly 也设成 5000万（实际不会拦），不再有 hourly 限制。
# 生产部署可以用 env 调小。
DEFAULT_TOKEN_HOURLY_LIMIT = 50_000_000   # = daily, 实际不拦，留配置位以备未来
DEFAULT_TOKEN_DAILY_LIMIT = 50_000_000    # 每天每实例 5000 万

# 高优先级事件即使超预算也放行（真人交互不能被基础设施故障挡住）
HIGH_PRIORITY_KINDS: Set[str] = {
    "message",          # 人类私聊
    "group_message",    # 人类群聊（@机器人）
    "birth",            # 实例初始化（理论上不会在运行中超预算）
}


@dataclass
class BudgetState:
    """预算闸门当前状态快照。"""
    hour_used: int
    hour_limit: int
    day_used: int
    day_limit: int
    hour_resets_at: str   # ISO，前端展示用
    day_resets_at: str

    @property
    def hour_exceeded(self) -> bool:
        return self.hour_used >= self.hour_limit

    @property
    def day_exceeded(self) -> bool:
        return self.day_used >= self.day_limit

    @property
    def is_throttled(self) -> bool:
        """是否已进入 throttle 状态（小时或日已超）。"""
        return self.hour_exceeded or self.day_exceeded


def _read_int_env(name: str, default: int) -> int:
    import os
    v = os.environ.get(name)
    if not v:
        return default
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return default


def _limits() -> Tuple[int, int]:
    """读 env，返回 (hour_limit, day_limit)。"""
    return (
        _read_int_env("DIGITAL_LIFE_TOKEN_HOURLY_LIMIT", DEFAULT_TOKEN_HOURLY_LIMIT),
        _read_int_env("DIGITAL_LIFE_TOKEN_DAILY_LIMIT", DEFAULT_TOKEN_DAILY_LIMIT),
    )


def get_budget_state(instance_id: str = "") -> BudgetState:
    """读 token_tracker + limits 拼 BudgetState 快照。"""
    try:
        from infrastructure.budget import get_token_tracker
        t = get_token_tracker()
        hour_used = t.usage_last_hour(instance_id)
        day_used = t.usage_today(instance_id)
        hour_resets = t.hour_resets_at()
        day_resets = t.day_resets_at()
    except Exception as exc:
        logger.debug("budget_state lookup failed: %s", exc)
        hour_used = day_used = 0
        hour_resets = day_resets = ""

    hour_limit, day_limit = _limits()
    return BudgetState(
        hour_used=hour_used,
        hour_limit=hour_limit,
        day_used=day_used,
        day_limit=day_limit,
        hour_resets_at=hour_resets,
        day_resets_at=day_resets,
    )


def should_allow_wake(
    reason: str,
    instance_id: str = "",
) -> Tuple[bool, str, BudgetState]:
    """cron 在 wake dispatch 前调一次。

    Args:
        reason: 本次唤醒原因（事件 kind）；高优先级事件即使超预算也放行。
        instance_id: 当前实例 ID（用于查 token_tracker）。

    Returns:
        (True, "", state)        — 允许 wake
        (False, reason, state)   — 拒绝，reason 是哪道阈值超了
    """
    state = get_budget_state(instance_id)
    if reason in HIGH_PRIORITY_KINDS:
        # 高优先级穿透；不写 log（避免每条真人消息产生噪音）
        return True, "", state

    if state.day_exceeded:
        msg = (f"token daily budget exceeded — {state.day_used}/{state.day_limit}; "
               f"resets at {state.day_resets_at}")
        logger.warning("L4: %s", msg)
        return False, msg, state

    if state.hour_exceeded:
        msg = (f"token hourly budget exceeded — {state.hour_used}/{state.hour_limit}; "
               f"resets at {state.hour_resets_at}")
        logger.warning("L4: %s", msg)
        return False, msg, state

    return True, "", state


__all__ = [
    "BudgetState",
    "BudgetGate",
    "get_budget_state",
    "should_allow_wake",
    "HIGH_PRIORITY_KINDS",
    "DEFAULT_TOKEN_HOURLY_LIMIT",
    "DEFAULT_TOKEN_DAILY_LIMIT",
]


class BudgetGate:
    """兼容类（was planned；现在用 module-level 函数即可，保留以备将来扩展）。

    现版本所有调用都走 should_allow_wake / get_budget_state 函数。
    """

    HIGH_PRIORITY_KINDS = HIGH_PRIORITY_KINDS

    @staticmethod
    def should_allow_wake(reason: str, instance_id: str = "") -> Tuple[bool, str, BudgetState]:
        return should_allow_wake(reason, instance_id)

    @staticmethod
    def get_state(instance_id: str = "") -> BudgetState:
        return get_budget_state(instance_id)
