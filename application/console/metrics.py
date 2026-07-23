"""
Prometheus metrics collector for digital life system.
"""

from __future__ import annotations

from typing import Any

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest, REGISTRY


class MetricsCollector:
    """收集和暴露Prometheus指标"""
    
    # 使用默认registry
    _registry = REGISTRY
    
    # 精力相关指标
    energy_gauge = Gauge(
        'digital_life_energy_current',
        'Current energy level',
        registry=_registry
    )
    
    energy_segment_gauge = Gauge(
        'digital_life_energy_segment',
        'Energy segment (0=exhausted, 1=tired, 2=normal, 3=active, 4=excited)',
        registry=_registry
    )
    
    # 存储指标
    state_db_size_bytes = Gauge(
        'digital_life_state_db_size_bytes',
        'Size of state.db in bytes',
        registry=_registry
    )
    
    memory_vectors_size_bytes = Gauge(
        'digital_life_memory_vectors_size_bytes',
        'Size of memory_vectors.db in bytes',
        registry=_registry
    )
    
    # 事件指标
    pending_events_count = Gauge(
        'digital_life_pending_events_total',
        'Number of pending events in queue',
        registry=_registry
    )
    
    recent_sessions_count = Gauge(
        'digital_life_recent_sessions_total',
        'Number of sessions in last 24 hours',
        registry=_registry
    )
    
    # 向量库指标
    vector_count = Gauge(
        'digital_life_memory_vectors_total',
        'Number of vectors in memory',
        registry=_registry
    )
    
    # 健康状态
    health_status = Gauge(
        'digital_life_health_status',
        'Health status (1=healthy, 0=unhealthy)',
        registry=_registry
    )
    
    # 工作模式
    mode_gauge = Gauge(
        'digital_life_mode',
        'Current mode (0=idle, 1=working, 2=resting, 3=blocked, 4=conserving)',
        registry=_registry
    )
    
    @classmethod
    def collect_from_status(cls, status_data: dict[str, Any]) -> None:
        """从status数据收集指标"""
        try:
            # 精力
            vitals = status_data.get('vitals', {})
            energy = vitals.get('energy', 0) if isinstance(vitals, dict) else 0
            cls.energy_gauge.set(float(energy))
            
            # 能量段
            segment_map = {'exhausted': 0, 'tired': 1, 'normal': 2, 'active': 3, 'excited': 4}
            vitals_detail = status_data.get('vitals_detail', {})
            energy_detail = vitals_detail.get('energy', {}) if isinstance(vitals_detail, dict) else {}
            segment = energy_detail.get('segment', 'normal') if isinstance(energy_detail, dict) else 'normal'
            cls.energy_segment_gauge.set(segment_map.get(segment, 2))
            
            # 工作模式
            runtime = status_data.get('runtime', {})
            mode = runtime.get('mode', 'idle') if isinstance(runtime, dict) else 'idle'
            mode_map = {'idle': 0, 'working': 1, 'resting': 2, 'blocked': 3, 'conserving': 4}
            cls.mode_gauge.set(mode_map.get(mode, 0))
            
        except Exception:
            # 静默失败，不影响其他指标
            pass
    
    @classmethod
    def collect_storage_metrics(cls, state_db_size: int, memory_vectors_size: int) -> None:
        """收集存储指标"""
        try:
            cls.state_db_size_bytes.set(float(state_db_size))
            cls.memory_vectors_size_bytes.set(float(memory_vectors_size))
        except Exception:
            pass
    
    @classmethod
    def collect_from_memory_stats(cls, stats: dict[str, Any]) -> None:
        """从memory stats收集指标"""
        try:
            vector_count = stats.get('vector_count', 0)
            cls.vector_count.set(float(vector_count))
        except Exception:
            pass
    
    @classmethod
    def collect_event_metrics(cls, pending_events: int, recent_sessions: int) -> None:
        """收集事件指标"""
        try:
            cls.pending_events_count.set(float(pending_events))
            cls.recent_sessions_count.set(float(recent_sessions))
        except Exception:
            pass
    
    @classmethod
    def set_health_status(cls, healthy: bool) -> None:
        """设置健康状态"""
        cls.health_status.set(1.0 if healthy else 0.0)
    
    @classmethod
    def get_metrics_output(cls) -> bytes:
        """生成Prometheus格式的输出"""
        return generate_latest(cls._registry)


__all__ = ['MetricsCollector']

