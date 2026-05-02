# ADR 0020: Phase 22 — 联邦与互操作

## 状态
Accepted — 2026-04-19

## 背景
`external_person_refs` 表（Phase 11）只记录引用元数据，从未真正拉过远端；图谱也无跨实例迁移格式。

## 决策
### D1. FederationFetcher + Backend Protocol
`services/federation_fetcher`: `LocalFileBackend` / `HTTPBackend` / TTL 内存 cache。eager refs 自动注入 retrieval_package.participants，remote 字段打标 `"remote": True`。

### D2. 事件总线真 backend
`event_bus_service` 加 `NATSBackend` / `RedisStreamBackend` 延迟 import 版本；Metrics 埋点：`event_bus_published{topic}` / `event_bus_drained{topic}`。

### D3. 热加载骨架
`services/hot_reload.ReloadRegistry` + `poll_file_mtime`：registry 模式存 loader，invalidate 时重拉；供 MCP server hot-swap。

### D4. 迁移 importer 三件套
`importers/migration_importer`: CSV / Notion export / Signal export 统一输出候选层；CSV 1000 行 < 1 秒。

### D5. Graph Canonical JSON
`services/graph_serializer` schema v1：`persons/relations/memories/memory_owners/scenes/scene_participants/events/event_participants/event_targets` 九张表。不包含 patches/snapshots。支持 serialize → deserialize round-trip。

### D6. 联邦协议 RFC
`docs/superpowers/specs/2026-04-19-federation-protocol.md`：Remote stub schema、disclosure_level、trust_level 三档、cache TTL 默认 300s、HTTP Bearer token 规范。

## 后果
正面：能真跨实例引用 person；能在不同 we-together 间迁移图谱；事件总线可升级到 NATS/Redis。
负面：NATS/Redis 的 drain 尚未实现（只有 publish）；Canonical schema 省略 patches，换机器后留痕链路丢失。

## 后续
- Phase 25+：完整 NATS consumer + 跨实例认证握手
- 联邦协议 v1.1：事件广播规范
