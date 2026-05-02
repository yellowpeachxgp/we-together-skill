# Federation Protocol RFC

> **状态**：Draft — 2026-04-19
> **目的**：为 we-together-skill 多实例间的 person / event 引用定义最小互操作协议。

## 1. 动机

v0.10.0 的 `external_person_refs` 表只记录引用元数据（`external_skill_name / external_person_id / trust_level / policy`），但没有规范**怎么真正拉取远端数据**。Phase 22 通过 `federation_fetcher` 解决实现问题，本 RFC 把协议本身正式化。

## 2. 术语

- **Skill Instance**：一个运行中的 we-together 实例（本地 SQLite + runtime）
- **Source skill**：被引用方
- **Consumer skill**：引用方
- **Ref**：一行 `external_person_refs` 记录
- **Remote stub**：source 暴露的 person 数据（subset）

## 3. 协议分层

```
┌──────────────────────────────────────────────┐
│  Consumer skill                               │
│  ─ external_person_refs (policy, trust)       │
│  ─ FederationFetcher(backend)                 │
│       ↓ get_remote_person(skill_name, pid)    │
└──────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│  Backend 层（可替换）                        │
│  ─ LocalFileBackend：读 federation/          │
│    <skill>/<pid>.json                        │
│  ─ HTTPBackend：GET <base>/skill/<skill>/    │
│    persons/<pid>                             │
│  ─ （未来）Gossip / IPFS / WebDAV            │
└──────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│  Source skill（导出 endpoint）               │
│  ─ 文件格式：json                            │
│  ─ HTTP：返回 200 + canonical JSON body      │
└──────────────────────────────────────────────┘
```

## 4. Remote stub schema

Source skill 必须暴露以下最小字段：

```json
{
  "person_id": "...",
  "display_name": "...",
  "persona_summary": "...",
  "style_summary": "...",
  "boundary_summary": "...",
  "exported_at": "ISO8601",
  "source_skill": "self_name",
  "disclosure_level": "public | partner | private"
}
```

- `disclosure_level=private` 的 person **MUST NOT** 被外部拉取
- `disclosure_level=partner` 需配合 Backend 层的 token 认证
- `persona_summary / style_summary / boundary_summary` 为派生字段，可为空

## 5. Policy 枚举

| policy | 行为 |
|---|---|
| `lazy` | 仅在 CLI 显式 `federation-fetch <ref_id>` 时拉取 |
| `eager` | retrieval 入口自动 prefetch 并注入 participants |
| `never` | ref 只作元数据用，fetcher 不会调 backend |

## 6. Trust level

`trust_level: float` ∈ [0, 1]

- ≥ 0.8：远端 persona_summary 可直接作为 participants 显示
- 0.5-0.8：远端信息可读，但 retrieval_package 标 `trusted: partial`
- < 0.5：仅显示 display_name，其他字段 masked

## 7. 缓存

Consumer skill **必须** 实现 TTL 缓存（默认 300 秒），避免对 Source 施加意外压力。

## 8. 安全

- HTTP backend **MUST** 支持 Bearer token
- 实例间首次连接建议走 challenge-response（Phase 23+）
- Source skill **MUST** 拒绝 disclosure_level='private' 的请求

## 9. 版本兼容

Remote stub 的 `format_version` 字段（当前隐含 = 1）：
- format_version 不兼容时，consumer 应优雅降级：只取 `display_name`，其他字段视为 null

## 10. 未规定（留给 Phase 25+ 实现）

- 事件广播协议（Phase 22 FE-6 的 NATSBackend/RedisStreamBackend 是实现，语义未规范）
- 跨实例一致性（两个 consumer 看到同一 person 的不同版本）
- 撤回协议（source 如何让 consumer 知道某 person 已删）
- 访问审计（fetch 记录哪里）

## 11. 对齐实现

- `src/we_together/services/federation_service.py` — `external_person_refs` schema
- `src/we_together/services/federation_fetcher.py` — Backend + Fetcher + TTL cache + eager injection
- `migrations/0008_external_person_refs.sql`
- `tests/services/test_federation_fetcher.py`

## 12. 后续版本

- v1.1（Phase 25+）：事件广播的正式 RFC
- v2.0（Phase 26+）：federation 去中心化（IPFS / libp2p）
