# we-together Federation Protocol v1

**Status**: Accepted (ADR 0044) — v0.15.0
**Target**: 两个 we-together skill 实例之间互相查询 persons / memories，以支持跨图谱联邦。

## 目标

- 允许 Skill A 读取 Skill B 的公开 persons / shared memories
- 允许 A 在自己的 `external_person_refs` 里登记 B 的 person id，供 retrieval 时 lazy-fetch
- **只读**：v1 不支持写（写涉及信任、鉴权、冲突解决，留 v0.16）

## 协议版本

`federation_protocol_version = "1"`，随请求 `/federation/v1/capabilities` 暴露。

## Endpoints

### GET /federation/v1/capabilities
返回 skill 提供的联邦能力：
```json
{
  "federation_protocol_version": "1",
  "skill_schema_version": "1",
  "supported_endpoints": [...],
  "read_only": true,
  "auth": "none (v0.15 MVP)"
}
```

### GET /federation/v1/persons?limit=50
返回 `persons.status='active'` 的公开列表：
```json
{ "persons": [ {person_id, primary_name, status, confidence}, ... ], "count": N }
```

### GET /federation/v1/persons/{pid}
单个 person 详情（含 metadata）：
```json
{ "person_id": "...", "primary_name": "...", "metadata": {...} }
```
404 表示 person 不存在或非 active。

### GET /federation/v1/memories?owner_id=XXX&limit=50
仅返回 `is_shared=1` 且 `status='active'` 的 memory。省略 `owner_id` 则全图 shared memory：
```json
{ "memories": [ {memory_id, summary, relevance_score, ...}, ...], "count": N }
```

## 客户端（Skill A 消费 Skill B）

```python
from we_together.services.federation_client import FederationClient
c = FederationClient("http://b.example:7781")
cap = c.capabilities()
persons = c.list_persons()
p = c.get_person("person_alice")
mems = c.list_memories(owner_id="person_alice")
```

## 身份映射（cross-graph）

- 目前留给上层：`services/federation_service.register_external_person(external_skill_name, external_person_id)`
- 合流策略（v0.16）：
  - 强匹配：external_id / email / 手机号 → 本地 identity_link
  - 弱匹配：姓名 + 共现 → 候选入 `identity_candidates`
  - 无自动融合（遵守不变式 #18：不自动改图）

## 安全

- v1 MVP：**无鉴权**（仅 localhost 或 VPC 内可用）
- v0.16：
  - mTLS 或 token（Bearer）
  - rate limiting
  - visibility policy：owner 可声明 `exportable: false`

## Read-Only 边界

v1 明确不提供：
- POST/PUT/DELETE
- `/memories/write`
- 远端 patch 应用

写路径的设计放到 v0.16 后再讨论。

## 错误语义

- 404：资源不存在或不公开
- 503：db 未准备好
- 其他 HTTP 错误：客户端抛 `RuntimeError("federation GET ... failed: STATUS REASON")`

## 示例：A 引用 B 的 person

```python
# Skill A 端
from we_together.services.federation_service import register_external_person
register_external_person(
    db_path=A_db,
    external_skill_name="skill_b",
    external_person_id="person_alice_at_b",
    display_name="Alice (from B)",
    trust_level=0.6,
    policy="lazy",
)

# 后续 retrieval 时，federation_fetcher 会按 policy 从 B 拉
```
