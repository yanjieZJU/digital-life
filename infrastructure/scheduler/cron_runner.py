"""Cron 定时守护线程 — 每隔 L4_TICK_INTERVAL 秒为每个活跃实例调用 run_l4_tick()。

工作流程：
  1. 主线程启动 cron daemon 线程
  2. 每隔 interval 秒扫描所有活跃实例（通过 discover_active_instances()）
  3. 切换 DIGITAL_LIFE_INSTANCE_ID 环境变量 → 调用 run_l4_tick()
  4. 支持通过 stop_event 优雅关闭

这是整个数字生命系统的"心跳"，所有定时检查（精力衰减、事件生成、唤醒判断）
都由这个循环驱动。
"""

from __future__ import annotations

import logging
import os
import threading
import time

logger = logging.getLogger("gateway.cron")

_DEFAULT_INTERVAL = 60


def _cron_loop(stop_event: threading.Event, interval: int) -> None:
    """cron 循环：每隔 interval 秒遍历所有活跃实例并执行 tick。"""
    logger.info("Cron loop started: interval=%ds", interval)

    from infrastructure.config import discover_active_instances

    prev_id = os.environ.get("DIGITAL_LIFE_INSTANCE_ID")

    while not stop_event.is_set():
        instances = discover_active_instances()
        if not instances:
            instances = ["zero"]  # fallback: always tick at least zero

        logger.debug("Cron tick: instances=%s", instances)

        for instance_id in instances:
            try:
                # Switch instance context so all path functions resolve correctly
                os.environ["DIGITAL_LIFE_INSTANCE_ID"] = instance_id

                from infrastructure.scheduler.cron_lifecycle import run_l4_tick

                run_l4_tick(instance_id=instance_id)
            except Exception as exc:
                logger.exception("Cron tick failed for %s: %s", instance_id, exc)

        # Restore previous instance id
        if prev_id:
            os.environ["DIGITAL_LIFE_INSTANCE_ID"] = prev_id

        # Wait but allow early shutdown
        if stop_event.wait(timeout=interval):
            break

    logger.info("Cron loop stopped")


def start_cron_daemon(stop_event: threading.Event) -> threading.Thread:
    """启动 cron 守护线程。"""
    interval = int(os.getenv("L4_TICK_INTERVAL") or _DEFAULT_INTERVAL)
    thread = threading.Thread(
        name="l4-cron-tick",
        target=_cron_loop,
        args=(stop_event, interval),
        daemon=True,
    )
    thread.start()
    return thread
