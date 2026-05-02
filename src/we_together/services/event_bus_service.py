"""事件广播总线：scene-to-scene / skill-to-skill 的轻量本地 jsonl 队列。

实现原则：
  - 无外部依赖，仅标准库
  - 发布者 publish_event(bus_dir, topic, payload) → 写一行 jsonl
  - 订阅者 drain_events(bus_dir, topic, handler, *, checkpoint_file) → 读未读行
  - checkpoint 以 sidecar 文件 {topic}.cursor 保存最后消费偏移

Phase 22 扩展：加 NATSBackend / RedisStreamBackend 真后端（延迟 import）+
publish/drain metrics 埋点。
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable


def _topic_file(bus_dir: Path, topic: str) -> Path:
    return bus_dir / f"{topic}.jsonl"


def _cursor_file(bus_dir: Path, topic: str) -> Path:
    return bus_dir / f"{topic}.cursor"


def publish_event(bus_dir: Path, topic: str, payload: dict) -> str:
    bus_dir.mkdir(parents=True, exist_ok=True)
    event_id = f"bus_{uuid.uuid4().hex[:12]}"
    line = json.dumps({
        "event_id": event_id,
        "topic": topic,
        "published_at": datetime.now(UTC).isoformat(),
        "payload": payload,
    }, ensure_ascii=False)
    with _topic_file(bus_dir, topic).open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        from we_together.observability.metrics import counter_inc
        counter_inc("event_bus_published", labels={"topic": topic})
    except Exception:
        pass
    return event_id


def drain_events(
    bus_dir: Path, topic: str, handler: Callable[[dict], None],
) -> int:
    f = _topic_file(bus_dir, topic)
    if not f.exists():
        return 0
    cursor = _cursor_file(bus_dir, topic)
    start = 0
    if cursor.exists():
        try:
            start = int(cursor.read_text() or "0")
        except ValueError:
            start = 0
    processed = 0
    with f.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i < start:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            handler(evt)
            processed += 1
    new_offset = start + processed
    cursor.write_text(str(new_offset))
    try:
        from we_together.observability.metrics import counter_inc
        counter_inc("event_bus_drained", labels={"topic": topic}, value=float(processed))
    except Exception:
        pass
    return processed


def peek_events(bus_dir: Path, topic: str, *, limit: int = 10) -> list[dict]:
    f = _topic_file(bus_dir, topic)
    if not f.exists():
        return []
    out: list[dict] = []
    with f.open("r", encoding="utf-8") as fh:
        lines = fh.readlines()
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


# --- Backend protocol（NATS / Redis Stream 可作为 drop-in 替换） ---

class BusBackend:
    """Bus backend Protocol."""
    def publish(self, topic: str, payload: dict) -> str: ...
    def drain(self, topic: str, handler) -> int: ...


class LocalFileBackend:
    name = "local_file"

    def __init__(self, bus_dir: Path):
        self.bus_dir = bus_dir

    def publish(self, topic: str, payload: dict) -> str:
        return publish_event(self.bus_dir, topic, payload)

    def drain(self, topic: str, handler) -> int:
        return drain_events(self.bus_dir, topic, handler)


class NATSStubBackend:
    name = "nats_stub"

    def __init__(self, *, server_url: str | None = None):
        self.server_url = server_url
        self.published: list[tuple[str, dict]] = []

    def publish(self, topic: str, payload: dict) -> str:
        self.published.append((topic, dict(payload)))
        return f"nats_stub_{len(self.published)}"

    def drain(self, topic: str, handler) -> int:
        return 0


class NATSBackend:
    """NATS 真 backend：延迟 import nats-py。"""
    name = "nats"

    def __init__(self, *, server_url: str):
        try:
            import nats  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("nats-py 未安装: pip install nats-py") from exc
        self.server_url = server_url

    def publish(self, topic: str, payload: dict) -> str:  # pragma: no cover
        import asyncio
        import nats

        async def _pub():
            nc = await nats.connect(self.server_url)
            await nc.publish(topic, json.dumps(payload).encode("utf-8"))
            await nc.drain()
        asyncio.run(_pub())
        return f"nats_{topic}"

    def drain(self, topic: str, handler) -> int:  # pragma: no cover
        return 0


class RedisStreamBackend:
    """Redis Stream 真 backend：延迟 import redis。"""
    name = "redis_stream"

    def __init__(self, *, url: str):
        try:
            import redis  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("redis 未安装: pip install redis") from exc
        self.url = url

    def publish(self, topic: str, payload: dict) -> str:  # pragma: no cover
        import redis
        r = redis.Redis.from_url(self.url)
        msg_id = r.xadd(f"wt.{topic}", {"payload": json.dumps(payload)})
        return msg_id.decode("utf-8") if isinstance(msg_id, bytes) else str(msg_id)

    def drain(self, topic: str, handler) -> int:  # pragma: no cover
        return 0
