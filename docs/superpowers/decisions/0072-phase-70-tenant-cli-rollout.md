---
adr: 0072
title: Phase 70 — tenant CLI rollout 范围与例外
status: Accepted
date: 2026-04-22
---

# ADR 0072: Phase 70 — tenant CLI rollout 范围与例外

## 状态
Accepted — 2026-04-22

## 背景

在 Phase 70 的推进里，我们已经把 `tenant_router` 从一个路径 helper 扩展成了贯穿大量 CLI / server / host 入口的真实工作流能力。但如果继续无差别地给所有 `--root` 脚本加 `--tenant-id`，会出现两个问题：

1. **语义漂移**：某些脚本的 `--root` 指向的并不是 tenant 运行时数据，而是项目目录或打包源目录。
2. **维护成本上升**：每补一个不该 tenant 化的脚本，后续都要跟着补测试、文档和误用解释。

因此本阶段需要明确：

- 哪些脚本必须 tenant 化
- 哪些脚本应该暂缓
- 哪些脚本不应 tenant 化

## 决策

### D1. tenant 化的判定标准

只有当一个脚本的 `--root` 明确指向以下之一时，才应该新增 `--tenant-id`：

- `db/main.sqlite3`
- `tenants/<tenant-id>/db/main.sqlite3`
- 或基于该 tenant root 派生的真实运行时数据目录

换句话说，tenant 化针对的是**运行时图谱数据**，而不是任意 filesystem 根。

### D2. 本阶段已 tenant 化的脚本范围

以下脚本现在被视为 tenant-aware：

- bootstrap / seed
- 高频导入 / 建组
- scene / retrieval / summary
- MCP / dashboard / dialogue / skill_host_smoke
- simulate_week / simulate_year / dream_cycle / fix_graph
- snapshot / branch_console / world_cli / activation_path / auto_resolve_branches / merge_duplicates
- daily_maintenance / scenario_runner / agent_chat / multi_agent_chat
- timeline / relation_timeline / rollback_tick / self_activate / extract_facets / embed_backfill
- analyze / eval_relation / bench_large
- import_image / import_llm / import_wechat
- simulate / what_if / narrate
- graph_io
- onboard
- seed_society_m / seed_society_l

### D3. 明确不 tenant 化的脚本

本阶段明确**不新增 `--tenant-id`**：

- `scripts/package_skill.py`
  - 原因：它的 `--root` 是打包源目录，不是 tenant 运行时图谱。
- `scripts/demo_openai_assistant.py`
  - 原因：它只构造 schema 和 payload demo，不读 tenant 数据，当前 `--root` 基本无效。

### D4. 明确暂缓的脚本

本阶段暂缓：

- `scripts/bench_scale.py`
  - 原因：它会主动往选定 DB 写大量 synthetic 数据。虽然 technically 可以 tenant 化，但更合理的路线是先定义更安全的 benchmark contract，再决定是否暴露 tenant 路由。

## 后果

### 正面

- tenant CLI rollout 有了清晰边界，不会无意义扩张。
- 用户能预期“tenant 适配针对运行时图谱，不是所有脚本都必须有 tenant 参数”。
- 后续 PR 和回归测试知道哪些脚本应继续纳入 tenant matrix。

### 负面

- 少数脚本会出现“不支持 tenant-id”与“支持 tenant-id”的混合状态。
- 需要文档明确解释，避免用户误判为遗漏。

## 版本锚点

- tenant-aware CLI 覆盖面已大幅扩展
- `tenant_router.normalize_tenant_id()` 已上线
- 当前基线：**743 passed, 4 skipped**

## 非目标

- `bench_scale.py` 的 tenant 化
- `package_skill.py` 的 tenant 化
- demo-only script 的 tenant 化

## 下一步

1. 继续补 cross-tenant leakage negative tests
2. 在 `README` / `HANDOFF` 中写明 tenant-aware CLI 的覆盖范围
3. 如需推进 `bench_scale.py` tenant 化，先单独写设计说明其安全边界
