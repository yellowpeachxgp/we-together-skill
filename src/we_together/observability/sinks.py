"""Observability sinks：可插拔的日志/metrics sink。

当前提供:
  - StdoutSink: 直接打印（默认）
  - OTLPStubSink: 只记录调用，stub 级实现，留作未来接入 OTLP collector
"""
from __future__ import annotations

from typing import Protocol


class ObservabilitySink(Protocol):
    def emit_log(self, event: str, fields: dict) -> None: ...
    def emit_counter(self, name: str, value: float, labels: dict | None) -> None: ...
    def emit_gauge(self, name: str, value: float, labels: dict | None) -> None: ...


class StdoutSink:
    name = "stdout"

    def emit_log(self, event: str, fields: dict) -> None:
        print(f"[log] {event} {fields}")

    def emit_counter(self, name: str, value: float, labels: dict | None) -> None:
        print(f"[metric counter] {name}={value} labels={labels}")

    def emit_gauge(self, name: str, value: float, labels: dict | None) -> None:
        print(f"[metric gauge] {name}={value} labels={labels}")


class OTLPStubSink:
    """OTLP stub：把调用累计到 self.calls，不做真实 HTTP。"""
    name = "otlp_stub"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def emit_log(self, event: str, fields: dict) -> None:
        self.calls.append({"kind": "log", "event": event, "fields": dict(fields)})

    def emit_counter(self, name: str, value: float, labels: dict | None) -> None:
        self.calls.append({"kind": "counter", "name": name, "value": value,
                            "labels": dict(labels or {})})

    def emit_gauge(self, name: str, value: float, labels: dict | None) -> None:
        self.calls.append({"kind": "gauge", "name": name, "value": value,
                            "labels": dict(labels or {})})


_default_sink: ObservabilitySink | None = None


def set_sink(sink: ObservabilitySink) -> None:
    global _default_sink
    _default_sink = sink


def get_sink() -> ObservabilitySink:
    return _default_sink if _default_sink else StdoutSink()
