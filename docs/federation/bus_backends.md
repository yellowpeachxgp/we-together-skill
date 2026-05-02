# Event Bus Backends (Phase 22)

## 默认

`LocalFileBackend`（无依赖）：写 `<bus_dir>/<topic>.jsonl` + `<topic>.cursor` 作为 checkpoint。

## NATS

`NATSBackend(server_url="nats://localhost:4222")`

- 可选依赖：`pip install nats-py`
- topic 直接作为 NATS subject
- 当前只实现 publish；drain 留空（需要 subscribe + timeout，Phase 25+ 完成）

## Redis Stream

`RedisStreamBackend(url="redis://localhost:6379")`

- 可选依赖：`pip install redis`
- 内部 key 前缀 `wt.<topic>`
- 当前只实现 publish，drain 留空

## Metrics 埋点

- `event_bus_published{topic}` counter
- `event_bus_drained{topic}` counter（drain 时按处理数加）

## 切换示例

```python
from we_together.services.event_bus_service import (
    LocalFileBackend, NATSBackend, RedisStreamBackend,
)
from pathlib import Path

# 本地
bus = LocalFileBackend(Path("./bus"))

# NATS
bus = NATSBackend(server_url="nats://localhost:4222")

# Redis
bus = RedisStreamBackend(url="redis://localhost:6379")

bus.publish("scene.evolved", {"scene_id": "s1"})
```

## Stub（无依赖）

`NATSStubBackend`：用于测试，不需要 NATS server，仅记录 publish 调用到 `self.published`。
