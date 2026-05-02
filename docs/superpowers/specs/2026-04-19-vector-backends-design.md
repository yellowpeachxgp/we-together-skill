# Dual Vector Backends Design

> **状态**：Accepted — 2026-04-19
> **目标**：把 `VectorIndex(backend='sqlite_vec'|'faiss')` 从 stub 升级为真 backend，同时保持现有 SQLite schema、BLOB 存储和测试基线稳定。

## 1. 背景

当前 `src/we_together/services/vector_index.py` 只真正支持 `flat_python`。`sqlite_vec` 和 `faiss` 仅做延迟 import 检查，然后统一回退到 `*_fallback`。这在 v0.14-v0.18 阶段是合理妥协，但 v0.19 要继续推进规模化与真部署，不能再停留在“有 backend 名称，没有 backend 行为”。

约束也很明确：

- 不能破坏当前 `memory_embeddings / event_embeddings / person_embeddings` 三张表的 BLOB 存储。
- 不能要求 core path 在 import 阶段强依赖 `sqlite-vec` / `faiss`。
- 不能把 `auto` 语义直接改成“随环境飘忽不定”，否则现有测试和行为会变得不可预测。
- 需要给 `bench_scale.py` 和 `embedding_recall` 一条真实使用新 backend 的路径，而不只是“build 成功”。

## 2. 方案对比

### 方案 A：继续保留 stub，只补 benchmark 和文档

优点：

- 风险最低。
- 不引入新依赖路径。

缺点：

- 对用户没有真实能力增量。
- `sqlite_vec/faiss` 仍然只是名字，和 v0.18 的问题没有本质区别。

结论：拒绝。

### 方案 B：只做一个真 backend，另一个继续 stub

优点：

- 单次改动更小。
- 验证更聚焦。

缺点：

- 用户已经明确要“两条都做”。
- 后续第二条 backend 仍要再拆一次接口和测试。
- 文档、bench、调用面会重复改。

结论：拒绝。

### 方案 C：双 backend 同步落地，保持统一接口和稳定回退

做法：

- `flat_python` 保持现状，作为稳定基线。
- `sqlite_vec` 走“加载扩展 + SQL 距离函数”的真实查询路径。
- `faiss` 走“内存索引 + cosine/IP 查询”的真实查询路径。
- `auto` 仍保持 `flat_python`，显式 backend 选择才切真后端。

优点：

- 一次把接口、测试、bench、文档全部理顺。
- 不改 schema，只改查询实现，风险可控。
- 与现有 delayed-import / mock-first 风格一致。

缺点：

- 需要同时覆盖两套实现路径。
- 可选依赖未安装时，只能走单元级仿真测试，不能完全依赖真实集成测试。

结论：采用。

## 3. 架构

### 3.1 总体原则

- `VectorIndex` 继续作为统一入口。
- `backend='flat_python'` 维持现有 dataclass 路径。
- `backend='sqlite_vec'` 和 `backend='faiss'` 不再返回 `*_fallback`，而是返回真实 backend 名称。
- backend 特定状态放到 `VectorIndex` 新字段中，而不是新暴露独立 public class，避免 API 扩散。

### 3.2 sqlite-vec backend

`sqlite-vec` 不要求新增 `vec0` 虚表，也不要求迁移现有 embedding schema。原因是现有三张 embedding 表已经稳定，且都把向量存成 float32 BLOB；强行改成 `vec0` 会放大 schema 和写路径改动。

因此本次选用官方支持的“普通 SQLite 表 + sqlite-vec 距离函数”模式：

- build 阶段：
  - 打开 SQLite 连接。
  - 延迟 import `sqlite_vec`。
  - 加载扩展到连接。
  - 验证目标表存在可查询行。
- query 阶段：
  - 把 query vector 编码为 float32 BLOB。
  - 直接执行 `SELECT ... ORDER BY vec_distance_cosine(vec, ?) ASC LIMIT ?`。
  - 把距离换算为 similarity，统一返回 `(id, score)`。
- hierarchical query：
  - 在原 SQL 上 JOIN `memory_owners`，再做 `owner_id IN (...)` 过滤。

这条路径的优点是：

- 不改 schema。
- 不复制数据到额外索引结构。
- 真正使用 sqlite-vec 的扩展能力。

### 3.3 FAISS backend

`faiss` 走纯内存索引：

- build 阶段：
  - 从 embedding 表读出 `(id, vec_blob)`。
  - 解码为 float32。
  - 用 `IndexFlatIP` 建索引。
  - 对所有向量做 L2 normalize，使 inner-product 等价于 cosine similarity。
  - 保存 `id_map`，把 FAISS 返回的行号映射回业务 id。
- query 阶段：
  - normalize query vector。
  - `search(k)`。
  - 过滤掉 `-1` 和无效结果。
- hierarchical query：
  - 不复用全量索引后再二次过滤，而是对过滤后的候选集即时建一个小型临时索引。
  - 理由：当前只有 `memory` 走层级查询，且过滤集通常远小于全量；这样实现简单，也不污染主索引状态。

### 3.4 auto 语义

`auto` 保持解析到 `flat_python`。本轮不改成“如果装了 `faiss` 就自动用 `faiss`”，因为：

- 这会让行为随本地环境漂移。
- 现有测试已经把 `auto -> flat_python` 固定下来。
- 生产方如果要用真 backend，应显式传入 backend。

## 4. 调用面改动

### 4.1 `embedding_recall.associate_by_embedding`

新增可选参数：

- `index_backend: str = "auto"`

语义：

- 无 `filter_person_ids` 时也统一走 `VectorIndex.build(...).query(...)`。
- 有 `filter_person_ids` 时继续走 `VectorIndex.hierarchical_query(...)`。
- 默认仍是 `auto`，保持现有行为不变。

### 4.2 `scripts/bench_scale.py`

新增参数：

- `--backend`，默认 `flat_python`

这样 bench 可以直接产出不同 backend 的 build/query 数据，后续 100k/1M 扩展时不需要再改脚本接口。

## 5. 错误处理

- backend 非法值：继续抛 `ValueError`。
- 缺包：继续抛友好 `RuntimeError`。
- sqlite-vec 扩展加载失败：
  - 抛 `RuntimeError`，错误里包含 backend 名称和原始异常。
- 目标表无数据：
  - build 成功，但 `size()==0`，query 返回空列表。
- 向量维度不一致：
  - 对 `faiss` 在 build 时检测并抛 `ValueError`。
  - 对 `sqlite_vec` 保持数据库查询层行为，query 返回空或抛出 runtime error，由调用方看到清晰错误。

## 6. 测试策略

### 6.1 保持已有测试

- 现有 `flat_python`、unknown backend、missing dependency、bench importability 测试必须继续通过。

### 6.2 新增测试

- `sqlite_vec` 真路径：
  - monkeypatch 一个假的 `sqlite_vec` 模块，验证 build/query 走真实 backend 名称且执行 SQL 路径，不再返回 `sqlite_vec_fallback`。
  - 若环境中真实安装 `sqlite_vec`，补一条真实集成测试。
- `faiss` 真路径：
  - monkeypatch 一个假的 `faiss` 模块，验证 `IndexFlatIP.add/search` 路径和结果映射。
  - 若环境中真实安装 `faiss`，补一条真实集成测试。
- `bench_scale.py --backend ...`：
  - 至少验证 CLI 可接受新参数。
- `associate_by_embedding(index_backend=...)`：
  - 显式 backend 选择可以到达 `VectorIndex`。

### 6.3 回归范围

- `tests/services/test_phase_28_scale.py`
- `tests/services/test_phase_36_debt.py`
- `tests/services/test_phase_47_sc.py`
- `tests/services/test_phase_53_qr.py`
- `tests/services/test_phase_61_sp.py`
- `tests/services/test_phase_26_embedding.py`

## 7. 文档更新

需要同步更新：

- `docs/HANDOFF.md`
- `docs/superpowers/state/current-status.md`
- `docs/CHANGELOG.md`

并明确：

- `sqlite_vec/faiss` 已不再是 stub。
- `auto` 仍然保持 `flat_python`，这是稳定性选择，不是遗漏。

## 8. 非目标

- 不修改 migrations。
- 不把 embedding 表改造成 `vec0` 虚表。
- 不新增后台常驻索引缓存层。
- 不把 `auto` 变成环境探测式 backend。
- 不在本轮承诺 100k/1M benchmark 真归档。
