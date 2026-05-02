"""内存 Metrics 累加器 + Prometheus 文本格式导出。

不依赖 prometheus_client。提供：
  - counter_inc(name, value=1, labels=None)
  - gauge_set(name, value, labels=None)
  - export_prometheus_text() → str
  - reset()  用于测试
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

_lock = threading.Lock()
_counters: dict[tuple[str, tuple], float] = {}
_gauges: dict[tuple[str, tuple], float] = {}


def _key(name: str, labels: dict | None) -> tuple:
    if not labels:
        return (name, ())
    return (name, tuple(sorted(labels.items())))


def counter_inc(name: str, value: float = 1.0, labels: dict | None = None) -> None:
    k = _key(name, labels)
    with _lock:
        _counters[k] = _counters.get(k, 0.0) + value


def gauge_set(name: str, value: float, labels: dict | None = None) -> None:
    k = _key(name, labels)
    with _lock:
        _gauges[k] = value


def get_counter(name: str, labels: dict | None = None) -> float:
    return _counters.get(_key(name, labels), 0.0)


def get_gauge(name: str, labels: dict | None = None) -> float:
    return _gauges.get(_key(name, labels), 0.0)


def reset() -> None:
    with _lock:
        _counters.clear()
        _gauges.clear()


def _format_labels(labels: tuple) -> str:
    if not labels:
        return ""
    parts = [f'{k}="{v}"' for k, v in labels]
    return "{" + ",".join(parts) + "}"


def export_prometheus_text() -> str:
    lines: list[str] = []
    for (name, labels), value in sorted(_counters.items()):
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name}{_format_labels(labels)} {value}")
    for (name, labels), value in sorted(_gauges.items()):
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name}{_format_labels(labels)} {value}")
    return "\n".join(lines) + "\n"
