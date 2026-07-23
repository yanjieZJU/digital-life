"""L4 状态机枚举。

Agent 整体生命态、事务态、唤醒原因的统一定义。
"""

from __future__ import annotations

from enum import Enum


class LifecycleState(str, Enum):
    """数字员工整体生命态（当前进程维度）。"""
    STASIS = "STASIS"       # 休眠：无活跃事务，等下一次唤醒
    RUNNING = "RUNNING"     # 正在执行某个事务
    BLOCKED = "BLOCKED"     # 当前事务被阻塞，等待切换或唤醒


class AffairStatus(str, Enum):
    """单个事务的状态。"""
    PENDING = "PENDING"         # 刚创建，尚未开始
    RUNNING = "RUNNING"         # 正在执行
    BLOCKED = "BLOCKED"         # 已进入等待（wait_until / wait_for_event / wait_for_condition）
    COMPLETED = "COMPLETED"     # agent 通过 emit_done 主动归档
    CANCELLED = "CANCELLED"     # 用户或系统强制终结


class WakeReason(str, Enum):
    """唤醒原因。re-hydration prompt 根据这个切模板。"""
    TIMER = "timer"             # wait_until 到期
    EVENT = "event"             # wait_for_event 被推入
    CONDITION = "condition"     # wait_for_condition 的 check 返回 true
    INTERRUPT = "interrupt"     # 人类打断
    EXTERNAL = "external"       # affair resume 等外部命令
    BOOT = "boot"               # 进程刚启动、事务从头开始


class WaitType(str, Enum):
    """WaitIntent 的类型。"""
    UNTIL = "until"             # 等到某个具体时间
    EVENT = "event"             # 等某个 channel 的事件
    CONDITION = "condition"     # 等某个 check_skill 返回 true
