"""Wake prompt policy helpers that are independent of Hermes storage."""

from __future__ import annotations

from datetime import datetime


FAILURE_TERMS = (
    "失败",
    "错误",
    "报错",
    "无法",
    "找不到",
    "未找到",
    "timeout",
    "timed out",
    "exit 124",
    "ModuleNotFoundError",
)

LEGACY_VITAL_TERMS = ("饱腹", "心情", "清洁", "联结", "LQ=", "生命状态")


def parse_sent_timestamp(line: str):
    try:
        raw = line.split("|", 1)[0].strip()
        if not raw:
            return None
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def drop_legacy_vitals_lines(text: str) -> str:
    lines = []
    for line in str(text or "").splitlines():
        if any(term in line for term in LEGACY_VITAL_TERMS):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def proactive_reporting_triggers(
    *,
    hours_since_last: float | None,
    failure_count: int,
    vital_alerts: list[str],
    reason: str,
    threshold_hours: int,
) -> list[str]:
    triggers = []
    if reason == "vital_threshold":
        triggers.append("本次由精力阈值事件唤醒")
    if vital_alerts:
        triggers.append("精力状态明显下降：" + "、".join(vital_alerts[:5]))
    if failure_count >= 2:
        triggers.append(f"最近连续 {failure_count} 次会话出现阻塞或失败")
    if hours_since_last is not None and hours_since_last >= threshold_hours:
        triggers.append(f"距离上次主动汇报已约 {hours_since_last:.1f} 小时，超过 {threshold_hours} 小时")
    return triggers


def format_proactive_reporting_policy(
    *,
    hours_since_last: float | None,
    failure_count: int,
    vital_alerts: list[str],
    reason: str,
    threshold_hours: int,
) -> str:
    triggers = proactive_reporting_triggers(
        hours_since_last=hours_since_last,
        failure_count=failure_count,
        vital_alerts=vital_alerts,
        reason=reason,
        threshold_hours=threshold_hours,
    )

    lines = [
        "\n\n## 主动汇报策略",
        "",
        "平时仍然先做事再说话。以下情况可以关注一下，但不强制汇报：",
        f"- 超过 {threshold_hours} 小时没有主动汇报",
        "- 遇到阻塞或连续失败",
        "- 精力状态明显下降",
        "- 已经做出明确成果或发现需要用户知道的异常",
        "",
        "如果有实质内容需要汇报，可以在 rest() 前调用一次 express_to_human。",
        "没有新内容则不发送——不要为了发而发。消息保持简短，1-2 句即可。",
    ]
    if triggers:
        lines.extend(["", "### 本次强制汇报触发", *[f"- {trigger}" for trigger in triggers]])
    else:
        lines.extend(["", "### 本次未触发强制汇报", "- 没有新成果时可以不主动发送消息。"])
    return "\n".join(lines)


__all__ = [
    "FAILURE_TERMS",
    "LEGACY_VITAL_TERMS",
    "drop_legacy_vitals_lines",
    "format_proactive_reporting_policy",
    "parse_sent_timestamp",
    "proactive_reporting_triggers",
]
