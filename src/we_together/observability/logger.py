"""观测性：轻量结构化日志 + 上下文 trace_id（无外部依赖）。

为避免引入 structlog 新依赖，基于 stdlib logging + contextvars 实现：
  - bind_trace_id(trace_id)：上下文设置 trace_id
  - get_logger(name)：返回带 trace_id 的 logger
  - 输出格式：JSON 一行
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar

_trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)


def bind_trace_id(trace_id: str | None = None) -> str:
    tid = trace_id or uuid.uuid4().hex[:12]
    _trace_id_ctx.set(tid)
    return tid


def get_trace_id() -> str | None:
    return _trace_id_ctx.get()


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": _trace_id_ctx.get(),
        }
        # 额外字段走 record.__dict__.extra
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)


_configured = False


def _configure_root() -> None:
    global _configured
    if _configured:
        return
    h = logging.StreamHandler(stream=sys.stderr)
    h.setFormatter(_JsonFormatter())
    root = logging.getLogger("we_together")
    root.setLevel(logging.INFO)
    root.handlers = [h]
    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(f"we_together.{name}")


def log_event(logger: logging.Logger, event: str, **fields) -> None:
    """便利函数：写一条带 structured fields 的 INFO。"""
    extra = dict(fields)
    extra["event"] = event
    logger.info(event, extra={"extra_fields": extra})
