"""精力衍生事件 — tick 时从精力状态生成事件。

两种事件：
  1. vital_threshold — RUNNING 状态下精力跌破阈值（进入 疲惫/精疲力竭），提醒休息
  2. initiative — BLOCKED 状态下精力充足 + 空闲超时 → 触发主动探索

check_energy_events() 由 SimulationEngine.tick() 调用。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _get_current_segment(energy: float) -> str | None:
    from domain.vital.simulation.engine import ENERGY_SEGMENTS
    for name, lo, hi, _ in ENERGY_SEGMENTS:
        if lo <= energy <= hi:
            return name
    return None


def _segment_index(name: str) -> int | None:
    from domain.vital.simulation.engine import ENERGY_SEGMENTS
    for i, s in enumerate(ENERGY_SEGMENTS):
        if s[0] == name:
            return i
    return None


def _affair_is_running() -> bool:
    try:
        from domain.lifecycle.affairs.runtime import get_affair
        from domain.lifecycle.state_machine import AffairStatus
        aff = get_affair()
        return aff is not None and aff.status == AffairStatus.RUNNING
    except Exception:
        return False


def check_energy_events(engine) -> list[dict]:
    """每次 tick 检查并生成精力衍生事件。由 SimulationEngine.tick() 调用。

    RUNNING 状态 → 检查是否跌破到 疲惫/精疲力竭，生成 vital_threshold 事件提醒休息。
    BLOCKED 状态 → 精力充足 + 空闲超时 + 无已有 initiative 事件 + 非静默时段 → 生成 initiative 事件。
    """
    from domain.lifecycle.events import emit_event, pop_due_events

    results: list[dict] = []

    if _affair_is_running():
        # ── RUNNING: vital_threshold（精力跌破底线 → 提醒休息） ──
        v = engine._v()
        energy = v["energy"]
        cur_seg = _get_current_segment(energy)
        if not cur_seg:
            return results

        prev = engine._current_segment
        if prev is not None and prev != cur_seg:
            prev_idx = _segment_index(prev)
            cur_idx = _segment_index(cur_seg)
            # 只在进入 疲惫(3) 或 精疲力竭(4) 时触发
            if prev_idx is not None and cur_idx is not None and cur_idx > prev_idx and cur_idx >= 3:
                emit_event("vital_threshold", {"from_seg": prev, "to_seg": cur_seg})
                results.append({"kind": "vital_threshold", "from_seg": prev, "to_seg": cur_seg})

        engine._current_segment = cur_seg
        return results

    # ── BLOCKED: initiative（精力充足 + 空闲超时 → 主动探索） ──
    engine._current_segment = None

    from domain.vital.simulation.engine import (
        INITIATIVE_ENERGY_THRESHOLD,
        INITIATIVE_IDLE_HOURS,
        _now,
    )

    v = engine._v()
    energy = v["energy"]

    if energy < INITIATIVE_ENERGY_THRESHOLD:
        return results

    # 静默时段检查（晚上睡觉时间不触发主动探索）
    # 关键：get_quiet_hours() 返回的是北京作息小时（routines.yaml 的 time 是北京时间），
    # 但 clock.now_dt() 默认 UTC——必须把当前时刻换算到北京时区再取 hour，
    # 否则北京半夜 00:00-05:00 对应 UTC 16-21 点，完全不在 (21,8) 静默段判定内，
    # 导致 initiative 半夜集中误触发。
    try:
        from domain.lifecycle.routine_scheduler import get_quiet_hours
        from domain.lifecycle.clock import BEIJING, now_dt
        quiet_start, quiet_end = get_quiet_hours()
        h = now_dt().astimezone(BEIJING).hour
        if quiet_start >= quiet_end:
            if h >= quiet_start or h < quiet_end:
                return results
        elif quiet_start <= h < quiet_end:
            return results
    except Exception as exc:
        logger.warning("initiative quiet-hours check failed (allowing trigger): %s", exc)
        # 原本是静默吞掉 — 这正是"只要异常就放行"的 BUG。改为放行但打 warning，
        # 避免静默段判定彻底失效而不可见。
        pass

    # 空闲时间检查：使用 vitals.updated_at（最后真实事件时间）
    last_activity = engine._last_activity_at
    if last_activity is None:
        return results

    elapsed_h = (_now() - last_activity).total_seconds() / 3600.0
    if elapsed_h < INITIATIVE_IDLE_HOURS:
        return results

    # 去重：已存在未消费的 initiative 事件则跳过
    try:
        due = pop_due_events(limit=20)
        for e in due:
            if e.get("kind") == "initiative":
                return results
    except Exception:
        pass

    # 动态计算 urgency
    energy_factor = (energy - INITIATIVE_ENERGY_THRESHOLD) / (100 - INITIATIVE_ENERGY_THRESHOLD)
    idle_factor = min(elapsed_h / INITIATIVE_IDLE_HOURS, 2.0)
    urgency = round(5 + energy_factor * 2.5 + (idle_factor - 1) * 2.5)

    emit_event("initiative", {
        "hours_idle": round(elapsed_h, 1),
        "energy": energy,
        "urgency": urgency,
    })
    results.append({"kind": "initiative", "urgency": urgency, "hours_idle": round(elapsed_h, 1)})

    return results
