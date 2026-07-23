"""作息调度引擎——从前端可配置的 routines.yaml 生成 routine 事件。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "routines.yaml"


def _current_instance_id() -> str | None:
    """安全取当前实例 id（ContextVar），无实例上下文时返回 None。

    ensure_routine_events 实际只在实例进程的 cron tick 内被调用，ContextVar 总有值；
    但函数本身是无副作用查询，留 None 兜底让它在测试/无上下文场景下也能跑通
    （此时回退全局作息，行为与旧版一致）。
    """
    try:
        from infrastructure.config import get_app_instance_id
        return get_app_instance_id() or None
    except Exception:
        return None


def load_routines(instance_id: str | None = None) -> list[dict[str, Any]]:
    """加载作息条目列表。

    三层路径（作息 2026-06-29 下沉到实例级）:
      1. instance_id 给定 + `apps/{iid}/config/routines.yaml` 存在 → 用实例版（覆盖全局）
      2. 否则回退全局 `config/routines.yaml`
      3. 全局也缺失 → 内置 `_default_routines`

    **instance_id 默认回退 ContextVar**(2026-06-29 联动修复 BUG-B/C):
    instance_id=None 时先尝试 _current_instance_id() 拿当前实例。这样所有
    "在实例上下文里"的调用方（console 监控 6 处 / get_schedule_overview /
    get_quiet_hours）无需逐个改，全部自动读当前实例的 per-instance 作息；
    真正无实例上下文（顶层测试 / 全局工具）才读全局作模板兜底。

    显式传 instance_id 仍优先（ensure_routine_events 用最明确的路径）。
    """
    # instance_id 缺省 → 回退 ContextVar 拿当前实例（可能仍为 None）
    resolved_iid = instance_id or _current_instance_id()

    # 1. per-instance 优先（resolved_iid 非空 + 实例文件存在）
    if resolved_iid:
        try:
            from infrastructure.config import get_instance_routines_path
            inst_path = get_instance_routines_path(resolved_iid)
            if inst_path.exists():
                import yaml
                with open(inst_path, "r", encoding="utf-8") as f:
                    raw = yaml.safe_load(f) or {}
                routines = raw.get("routines", [])
                if routines:
                    return routines
                # 实例文件存在但 routines 为空 → 也走下面全局兜底（视为"未配置"）
        except Exception as exc:
            # 实例作息读取失败不应阻断调度——回退全局。
            logger.warning("Failed to load instance routines for %s: %s", resolved_iid, exc)

    # 2. 全局兜底（无实例上下文 / 实例文件缺失 / 实例文件空）
    try:
        if not _CONFIG_PATH.exists():
            logger.warning("routines.yaml not found, using defaults")
            return _default_routines()
        import yaml
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        routines = raw.get("routines", [])
        if not routines:
            return _default_routines()
        return routines
    except Exception as exc:
        logger.warning("Failed to load routines.yaml: %s", exc)
        return _default_routines()


def _default_routines() -> list[dict[str, Any]]:
    """内置默认作息（防止 YAML 缺失时崩溃）。"""
    return [
        {
            "id": "morning_plan",
            "name": "早起计划",
            "time": "08:00",
            "description": "制定今日计划",
            "prompt_template": "🌅 早上好。`sense_time` + `sense_vitals` + `sense_self` 看状态。`sense_daily` 看计划。如果没有计划，用 `manage_daily plan` 制定。做事 → `update_scratchpad`。",
            "recurrence": "daily",
            "priority": 4,
            "enabled": True,
        },
        {
            "id": "write_diary",
            "name": "写日记",
            "time": "21:00",
            "description": "整理今日碎片日记",
            "prompt_template": "🌙 该整理今天的碎片日记了——用 `write_diary` 写，或者自己总结今天发生的事。",
            "recurrence": "daily",
            "priority": 4,
            "enabled": True,
        },
        {
            "id": "evening_review",
            "name": "晚间复盘",
            "time": "21:30",
            "description": "复盘今日执行情况并制定明日计划",
            "prompt_template": "🌙 复盘今天。`sense_daily` 看完成情况 → `write_diary` 写日记 → `update_scratchpad` 更新 → `rest()`。",
            "recurrence": "daily",
            "priority": 4,
            "enabled": True,
        },
    ]


def save_routines(
    routines: list[dict[str, Any]], instance_id: str | None = None
) -> Path:
    """将作息条目列表写回 YAML。**per-instance 必需**(2026-06-29 BUG-A 修复)。

    作息已下沉到实例级，写入必须落 `apps/{iid}/config/routines.yaml`——找不到
    实例上下文就直接报错，**绝不静默写全局**(那正是 BUG-A：前端在某实例页面
    编辑作息结果改了全局 config/routines.yaml，污染所有实例)。

    instance_id 缺省时回退 _current_instance_id()（与 load_routines 对称）。
    仍拿不到实例（如旧前缀 /api/employee/schedules 无 iid 路由）→ ValueError，
    调用方收到明确错误，避免悄悄污染全局。

    返回写入的文件路径，便于调试/日志。
    """
    import yaml
    resolved_iid = instance_id or _current_instance_id()
    if not resolved_iid:
        raise ValueError(
            "save_routines 需要实例上下文才能写入（拒绝静默写全局）。"
            "请在实例上下文内调用，或显式传 instance_id。"
        )
    from infrastructure.config import get_instance_routines_path
    path = get_instance_routines_path(resolved_iid)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump({"routines": routines}, f, allow_unicode=True, default_flow_style=False)
    logger.info("routines saved (instance=%s, routines=%d) → %s", resolved_iid, len(routines), path)
    return path


def ensure_routine_events() -> None:
    """每天为每个启用的作息创建 routine 事件（幂等）。

    在每次 L4 tick 时调用，检查今天是否已注册，未注册则补建。
    查询不限制 channel，避免 instance ID 迁移后遗留孤儿事件导致重复创建。

    Bug fix: 之前在 fire_dt 已过时 set fire_at = now+5s，但 registered_ids 检测
    不含未 fire 的 alarm 的 schedule_id（list_recent_events 只看已 emit 的 events，
    而 alarm 没 fire 就没 event）—— 结果每个 cron tick 都重复 register 一个 5s 后
    fire 的 alarm。1105 个孤儿 routine timer 就是这么积累的。
    修：在 registered_ids 检测里加上**同一天 fire_at 的 pending routine alarm**，
    任何 fire_at[:10] == today_str 的 schedule_id 视为已注册（不分 fired/unfired）。
    """
    from domain.lifecycle.events import _event_bus
    from domain.lifecycle.clock import now_dt as _now_dt, beijing_now_dt as _beijing_now_dt
    from domain.lifecycle.clock import BEIJING, LOCAL, to_storage_iso as _ts_iso, parse_iso as _parse_iso

    # routine 的 hour:minute 是北京作息语义；now 用北京，
    # fire_at 写库时做 to_storage_iso 转成本地时区（2026-06-18 统一）。
    now_bj = _beijing_now_dt()
    today_str = now_bj.strftime("%Y-%m-%d")

    # 1. events 表：今日已 emit 的 routine
    registered_ids: set[str] = set()
    try:
        existing = _event_bus.list_recent_events(
            hours=48, kinds={"routine"}, include_consumed=True, channel_prefix=None,
        )
        for ev in existing:
            created = ev.get("created_at", "")
            if not created:
                continue
            # created_at 存储已是 UTC ISO；判断"今日"时换算回北京日。
            try:
                ev_bj = _parse_iso(created).astimezone(BEIJING)
            except Exception:
                continue
            if ev_bj.strftime("%Y-%m-%d") == today_str:
                payload = ev.get("payload", {})
                if isinstance(payload, dict):
                    sid = payload.get("schedule_id", "")
                    if sid:
                        registered_ids.add(sid)
    except Exception:
        pass

    # 2. timers 表：今日（不论 fired/unfired）的 routine alarm
    try:
        from domain.lifecycle.alarms import list_pending_alarms
        from domain.lifecycle.alarms import _conn as _alarms_conn
        # Pending
        for alarm in list_pending_alarms(kind="routine"):
            payload = alarm.get("payload_json") or alarm.get("payload") or "{}"
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            sid = payload.get("schedule_id", "") if isinstance(payload, dict) else ""
            if sid:
                registered_ids.add(sid)
        # Already fired today — also count so we don't re-register.
        # Beijing today boundaries as LOCAL ISO for lexical compare against stored fire_at.
        bj_today_start = now_bj.replace(hour=0, minute=0, second=0, microsecond=0)
        bj_today_start_utc = _ts_iso(bj_today_start)
        bj_tomorrow_start_utc = _ts_iso(bj_today_start + timedelta(days=1))
        try:
            with _alarms_conn() as conn:
                rows = conn.execute(
                    "SELECT payload_json FROM timers WHERE event_kind='routine' "
                    "AND fire_at >= ? AND fire_at < ?",
                    (bj_today_start_utc, bj_tomorrow_start_utc),
                ).fetchall()
            for r in rows:
                try:
                    payload = json.loads(r["payload_json"] or "{}")
                except Exception:
                    continue
                sid = payload.get("schedule_id", "")
                if sid:
                    registered_ids.add(sid)
        except Exception as exc:
            logger.debug("Failed to scan fired routine timers: %s", exc)
    except Exception as exc:
        logger.debug("Failed to check pending alarms: %s", exc)

    routines = load_routines(_current_instance_id())

    for entry in routines:
        if not entry.get("enabled", True):
            continue
        sid = entry.get("id", "")
        if sid in registered_ids:
            continue
        if not _matches_today(entry, now_bj):
            continue

        hour_str, minute_str = entry["time"].split(":")
        hour, minute = int(hour_str), int(minute_str)
        fire_dt = now_bj.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if fire_dt <= now_bj:
            # 已过预定时间 2 小时内补发，否则跳到明天。
            # 注意：fire_at 设成预定时间而不是 now+5s，避免每个 cron tick 反复注册。
            if (now_bj - fire_dt).total_seconds() > 7200:
                continue
            # 用预定时间作为 fire_at（c1 次补发），registered_ids 下次 tick 命中
            # 已存在的 alarm 跳过，避免反复 register。
            fire_at_str = _ts_iso(fire_dt)
        else:
            fire_at_str = _ts_iso(fire_dt)

        try:
            from domain.lifecycle.alarms import set_alarm
            set_alarm(
                event_kind="routine",
                fire_at=fire_at_str,
                payload={
                    "schedule_id": sid,
                    "name": entry.get("name", ""),
                    "time": entry["time"],
                    "description": entry.get("description", ""),
                    "prompt": entry.get("prompt_template", ""),
                },
            )
            logger.info("Registered routine: %s at %s", sid, entry["time"])
        except Exception as exc:
            logger.warning("Failed to register routine %s: %s", sid, exc)


def _matches_today(entry: dict, now: datetime) -> bool:
    """检查作息条目今天应不应该触发。"""
    recurrence = entry.get("recurrence", "daily")
    if recurrence == "daily":
        return True
    wd = now.weekday()  # 0=Mon
    if recurrence == "weekdays":
        return wd < 5
    if recurrence == "weekends":
        return wd >= 5
    # 自定义："mon,tue,wed" 格式
    days = [d.strip().lower()[:3] for d in recurrence.split(",")]
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    return day_names[wd] in days


def get_quiet_hours() -> tuple[int, int]:
    """从作息表推导静默时间段（当天最早和最晚时间）。

    Returns:
        (quiet_start_hour, quiet_end_hour): 静默开始和结束的小时数。
        如 (21, 7) 表示 21 点到次日 7 点静默。
    """
    routines = load_routines()
    enabled = [r for r in routines if r.get("enabled", True)]
    if not enabled:
        return (21, 7)

    def _minutes(t: str) -> int:
        parts = t.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    times = [_minutes(r["time"]) for r in enabled]
    earliest = min(times)
    latest = max(times)

    return (latest // 60, earliest // 60)


def resolve_routine_prompt(payload: dict) -> str:
    """从 routine 事件的 payload 中提取最终的 prompt。

    payload 中带有 schedule 条目注入的 prompt 字段，
    直接返回即可。（事件类型的 wake_prompt 模板 {prompt} 会由 build_wake_prompt 填充）
    """
    return payload.get("prompt", "") or payload.get("description", "") or ""
