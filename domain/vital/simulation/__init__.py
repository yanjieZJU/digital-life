"""Simulation — 数字生命环境模拟层。

精力 + 钱包 + 股票交易。所有持久状态走 state.db。
"""

from .engine import (
    SimulationEngine,
    get_engine,
    reset_engine,
    ENERGY_SEGMENTS,
    ENERGY_MAX,
    ENERGY_RECOVERY_PER_HOUR,
    ENERGY_COST_PER_CALL,
    INITIATIVE_ENERGY_THRESHOLD,
    INITIATIVE_IDLE_HOURS,
)

__all__ = [
    "SimulationEngine",
    "get_engine",
    "reset_engine",
    "ENERGY_SEGMENTS",
    "ENERGY_MAX",
    "ENERGY_RECOVERY_PER_HOUR",
    "ENERGY_COST_PER_CALL",
    "INITIATIVE_ENERGY_THRESHOLD",
    "INITIATIVE_IDLE_HOURS",
]
