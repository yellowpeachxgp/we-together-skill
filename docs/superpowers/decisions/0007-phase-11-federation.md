# ADR 0007: Phase 11 — 联邦与协同（Federation）

## 状态

Accepted — 2026-04-18

## 背景

Phase 8/9/10 让单 skill 实例能自演化、对接多个宿主、吃真实数据，但仍假设"一个 SQLite = 一个用户 = 一个世界"。`product-mandate.md` 第 C 条要求的"可扩展的数字赛博生态圈"需要：

1. 不同 skill 用户的图谱能互相引用 person / relation
2. 场景之间的事件可广播，保证一个人物在多场合出现时状态协同
3. 冲突 local_branch 需要 human-in-the-loop 界面
4. 多个租户共享同一部署，互不污染

## 决策

### D1. 外部 person 引用以 migration 0008 为锚

新增 `external_person_refs` 表（`ref_id / external_skill_name / external_person_id / local_alias / display_name / trust_level / policy / metadata_json`），policy ∈ {lazy|eager|never}。eager 引用由 retrieval 层主动加载，lazy 只在显式调用时加载。`(external_skill_name, external_person_id)` 唯一。

### D2. 本地 jsonl 事件总线

`services/event_bus_service`：`publish_event(bus_dir, topic, payload)` 追加 `{topic}.jsonl`；`drain_events` 带 sidecar `{topic}.cursor` 做偏移推进；`peek_events` 用于 debug。**不引入 kafka/rabbitmq**，最小依赖。后续如果需要跨机器，上游可替换 `_topic_file` 为 HTTP/S3。

### D3. 裁决 UI：stdlib http.server + bearer token

`scripts/branch_console.py` 用 Python stdlib `http.server`，无 fastapi 依赖：
- `GET /branches` 列出 open local_branches + candidates
- `POST /resolve?branch_id=&candidate_id=` 通过 `resolve_local_branch` patch 落库
- `--token` 配置 Bearer Authorization，强制鉴权

保证 CI 无 extra deps；真实生产可换 fastapi+htmx 作为 drop-in 替换（接口契约相同）。

### D4. 多租户以路径路由实现

`services/tenant_router`：`resolve_tenant_db_path(root, tenant_id)` 把 tenant=default 映射为原路径 `<root>/db/main.sqlite3`（向后兼容），其他租户映射为 `<root>/tenants/<tenant_id>/db/main.sqlite3`。retrieval/ingest 全链路透传 tenant_id 由 CLI 层负责。**不做权限隔离**（这是 Phase 12 鉴权层的职责）。

## 后果

### 正面

- 4 个联邦能力以最小 schema 变更落地（只有一张新表 + 一个辅助路由函数）
- 事件总线是本地文件 + cursor，不依赖任何外部中间件
- 裁决 UI 不引入 web 框架依赖，单文件部署

### 负面 / 权衡

- external_person_refs 目前只存引用元数据；真实远端 person 数据获取协议未定（Phase 12 规范）
- 事件总线缺失 consumer group / 重试 / ack，生产级别需要升级
- 多租户只是路径隔离，未做鉴权，所有租户共用同一进程

### 后续

- Phase 12 把 tenant_id 与 rbac 对接
- Phase 13（未来）考虑把事件总线升级为 NATS / Redis Stream
- 联邦协议规范：`docs/superpowers/specs/federation-protocol.md`（待写）
