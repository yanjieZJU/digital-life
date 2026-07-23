"""时间戳工具。

2026-06-18 重要变更：时区基准从 UTC 统一为**本地时间**。

之前 now_iso() 返回 UTC (+00:00)，但 clock.py / alarms.py / routine_scheduler.py
各处存在混用问题（fire_at 存 UTC 但比较 now 也 UTC 理论正确，实际 DB 历史
数据 / dedup 路径有 naive 串 / astimezone 转换不一致等 corner case 导致
定时器提前触发。

新方案：**全部用本地时区时间**（datetime.now().astimezone()，返回 tz-aware
本地时间）。存储、比较、显示全部一致，不再有任何跨时区转换。

与老数据兼容：parse_iso 对无 tz 的老串也按本地时区解析，astimezone(LOCAL)
不会改变值；对有 +00:00 的旧的 UTC 串，astimezone 会正确转成本地时间。

如果部署在 CST (Asia/Shanghai)，本地时间 = 北京时间：
  now_iso() 返回 '2026-06-18T20:00:00+08:00'（不是 +00:00）
  beijing_now_iso() 同 now_iso()（别名，保留向后兼容）
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

BEIJING = timezone(timedelta(hours=8), name="Asia/Shanghai")
UTC = timezone.utc

# 本地时区 —— 取机器 timezone（部署在国内就是 Asia/Shanghai +08:00）
# now_dt() / now_iso() 一律用这个，确保存储比较显示一致
LOCAL = datetime.now().astimezone().tzinfo


def now_dt() -> datetime:
    """当前本地时间（tz-aware）。"""
    return datetime.now(tz=LOCAL)


def now_iso() -> str:
    """当前本地 ISO8601，如 '2026-06-18T20:00:00+08:00'。"""
    return now_dt().isoformat(timespec="seconds")


def beijing_now_dt() -> datetime:
    """当前北京时间（tz-aware）—— 当本地 IS 北京时间时 = now_dt()。"""
    return datetime.now(tz=BEIJING)


def beijing_now_iso() -> str:
    """当前北京时间 ISO8601。"""
    return beijing_now_dt().isoformat(timespec="seconds")


def parse_iso(s: str) -> datetime:
    """解析 ISO8601；无 tz 时按本地时区处理（兼容历史数据）。

    有 tz 的串保留原 tz；无 tz 的老串按 LOCAL 解析。
    """
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL)
    return dt


def to_storage_iso(dt: datetime) -> str:
    """把任意 tz-aware datetime 转成本地时区 ISO 字符串用于 DB 存储。

    这是 2026-06-18 时区统一后替代 `dt.astimezone(UTC).isoformat()` 的统一入口。
    之前各处用 astimezone(UTC) 把时间转成 +00:00 存储，但现在整个系统改用本地
    时间，存储和比较必须一致。所有需要写 DB 时间列的地方都改用这个。
    """
    return dt.astimezone(LOCAL).isoformat(timespec="seconds")


def ts_prefix() -> str:
    """给 user/tool message 正文加的时间戳前缀。"""
    # 用本地时间，不区分 UTC / 北京（统一本地就够了）
    return f"[{now_iso()}]\n"


def humanize_delta(seconds: float) -> str:
    """把秒数转成 '3小时15分' 这样的中文描述。"""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}秒"
    if seconds < 3600:
        return f"{seconds // 60}分钟"
    if seconds < 86400:
        h, m = divmod(seconds, 3600)
        m //= 60
        return f"{h}小时{m}分" if m else f"{h}小时"
    d, rem = divmod(seconds, 86400)
    h = rem // 3600
    return f"{d}天{h}小时" if h else f"{d}天"
