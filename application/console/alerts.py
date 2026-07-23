"""
Alert manager for digital life system.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from pathlib import Path

from infrastructure.config import get_runtime_state_db_path


class AlertManager:
    """管理和触发告警"""
    
    # 告警规则定义
    ALERT_RULES = {
        'energy_critical': {
            'condition': lambda v: v.get('energy', 100) < 20,
            'message': '精力进入耗尽区（<20%），建议立即休息',
            'severity': 'critical',
            'cooldown_minutes': 60,  # 1小时内不重复告警
        },
        'energy_low': {
            'condition': lambda v: v.get('energy', 100) < 35,
            'message': '精力偏低（<35%），建议减少活动',
            'severity': 'warning',
            'cooldown_minutes': 120,  # 2小时内不重复告警
        },
        'energy_high': {
            'condition': lambda v: v.get('energy', 0) > 90,
            'message': '精力充沛（>90%），适合处理复杂任务',
            'severity': 'info',
            'cooldown_minutes': 240,  # 4小时内不重复告警
        },
        'storage_high': {
            'condition': lambda v: v.get('state_db_size_mb', 0) > 100,
            'message': 'state.db存储较大（>100MB），建议清理',
            'severity': 'warning',
            'cooldown_minutes': 1440,  # 24小时内不重复告警
        },
        'pending_events_high': {
            'condition': lambda v: v.get('pending_events', 0) > 5,
            'message': '待处理事件较多（>5个），建议检查',
            'severity': 'info',
            'cooldown_minutes': 180,
        },
        'mode_blocked': {
            'condition': lambda v: v.get('mode') == 'blocked',
            'message': '系统进入阻塞状态，需要处理',
            'severity': 'warning',
            'cooldown_minutes': 60,
        },
    }
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_runtime_state_db_path()
        self._ensure_alert_table()
    
    def _ensure_alert_table(self) -> None:
        """确保告警表存在"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    triggered_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            conn.commit()
        finally:
            conn.close()
    
    def check_alerts(self, status_data: dict[str, Any]) -> list[dict[str, Any]]:
        """检查所有告警规则，返回触发的告警"""
        triggered_alerts = []
        from domain.lifecycle import clock as _clock
        now = _clock.now_dt()
        
        # 构建检查上下文
        context = self._build_context(status_data)
        
        for alert_type, rule in self.ALERT_RULES.items():
            if rule['condition'](context):
                # 检查冷却时间
                if self._is_in_cooldown(alert_type, rule['cooldown_minutes'], now):
                    continue
                
                alert = {
                    'type': alert_type,
                    'severity': rule['severity'],
                    'message': rule['message'],
                    'triggered_at': now.isoformat(),
                    'context': context,
                }
                
                triggered_alerts.append(alert)
                self._record_alert(alert)
        
        return triggered_alerts
    
    def _build_context(self, status_data: dict[str, Any]) -> dict[str, Any]:
        """构建告警检查上下文"""
        vitals = status_data.get('vitals', {})
        runtime = status_data.get('runtime', {})
        
        context = {
            'energy': vitals.get('energy', 100) if isinstance(vitals, dict) else 100,
            'mode': runtime.get('mode', 'idle') if isinstance(runtime, dict) else 'idle',
            'pending_events': status_data.get('pending_events_count', 0),
            'state_db_size_mb': status_data.get('state_db_size', 0) / (1024 * 1024),
        }
        
        return context
    
    def _is_in_cooldown(self, alert_type: str, cooldown_minutes: int, now: datetime) -> bool:
        """检查告警是否在冷却期"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute('''
                SELECT triggered_at FROM alert_history
                WHERE alert_type = ?
                ORDER BY triggered_at DESC
                LIMIT 1
            ''', (alert_type,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            last_triggered = datetime.fromisoformat(row[0])
            cooldown_end = last_triggered + timedelta(minutes=cooldown_minutes)
            
            return now < cooldown_end
        except Exception:
            return False
        finally:
            conn.close()
    
    def _record_alert(self, alert: dict[str, Any]) -> None:
        """记录告警到历史表"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute('''
                INSERT INTO alert_history (alert_type, severity, message, triggered_at, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                alert['type'],
                alert['severity'],
                alert['message'],
                alert['triggered_at'],
                json.dumps(alert.get('context', {}))
            ))
            conn.commit()
        finally:
            conn.close()
    
    def get_recent_alerts(self, hours: int = 24) -> list[dict[str, Any]]:
        """获取最近N小时的告警历史"""
        from domain.lifecycle import clock as _clock
        conn = sqlite3.connect(str(self.db_path))
        try:
            since = _clock.now_dt() - timedelta(hours=hours)
            cursor = conn.execute('''
                SELECT alert_type, severity, message, triggered_at, metadata
                FROM alert_history
                WHERE triggered_at >= ?
                ORDER BY triggered_at DESC
                LIMIT 50
            ''', (since.isoformat(),))
            
            alerts = []
            for row in cursor.fetchall():
                alert = {
                    'type': row[0],
                    'severity': row[1],
                    'message': row[2],
                    'triggered_at': row[3],
                    'metadata': json.loads(row[4]) if row[4] else {}
                }
                alerts.append(alert)
            
            return alerts
        finally:
            conn.close()


__all__ = ['AlertManager']
