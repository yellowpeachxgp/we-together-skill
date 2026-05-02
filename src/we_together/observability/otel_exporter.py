"""otel_exporter（Phase 53 QR-1）：OpenTelemetry exporter 可选 wrapper。

不强制安装 opentelemetry；import 时延迟检查。当 sdk 未装 → NoOp。
Nightly / 生产可启用真 OTLP exporter。

API:
- enable(endpoint) → 初始化（如果 sdk 可用）
- span(name) context manager
- set_attribute(key, value)
- is_enabled() → bool
"""
from __future__ import annotations

import contextlib
from typing import Any

_state: dict[str, Any] = {
    "enabled": False,
    "tracer": None,
    "reason": "not-initialized",
}


def is_enabled() -> bool:
    return bool(_state["enabled"])


def enable(endpoint: str | None = None, service_name: str = "we-together") -> dict:
    """尝试初始化 OTel SDK；失败则保持 NoOp。"""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )
                provider.add_span_processor(
                    BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)),
                )
            except ImportError:
                # exporter 可选；没装也能 local-only
                pass

        trace.set_tracer_provider(provider)
        _state["tracer"] = trace.get_tracer("we_together")
        _state["enabled"] = True
        _state["reason"] = "ok"
        return {"enabled": True, "service": service_name, "endpoint": endpoint}
    except ImportError as exc:
        _state["enabled"] = False
        _state["reason"] = f"sdk not installed: {exc}"
        return {"enabled": False, "reason": _state["reason"]}


def disable() -> None:
    _state["enabled"] = False
    _state["tracer"] = None


@contextlib.contextmanager
def span(name: str, attributes: dict | None = None):
    """NoOp-safe span context manager。"""
    if not _state["enabled"] or _state["tracer"] is None:
        yield None
        return
    with _state["tracer"].start_as_current_span(name) as sp:
        if attributes:
            for k, v in attributes.items():
                try:
                    sp.set_attribute(k, v)
                except Exception:
                    pass
        yield sp


def set_attribute(key: str, value: Any) -> None:
    """给 current span 加属性。NoOp 安全。"""
    if not _state["enabled"]:
        return
    try:
        from opentelemetry import trace
        sp = trace.get_current_span()
        if sp is not None:
            sp.set_attribute(key, value)
    except Exception:
        pass


def status() -> dict:
    return {
        "enabled": bool(_state["enabled"]),
        "reason": _state["reason"],
    }
