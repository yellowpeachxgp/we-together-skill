---
adr: 0053
title: Phase 51 — 世界建模升维（从"社会图谱"到"世界图谱"）
status: Accepted
date: 2026-04-19
---

# ADR 0053: Phase 51 — 世界建模升维

## 状态
Accepted — 2026-04-19

## 背景
v0.16 之前 we-together 只建模**人 + 关系 + 事件 + 记忆 + 场景**，即纯**社会图谱**。vision 写的是"**数字赛博生态圈**"——这个词蕴含远超社会的维度：**物、地点、项目**都应该是一等公民。没有这三者，"生态圈"就只是社交记忆器。

这不是"加功能"，是**维度跃迁**。

## 决策

### D1. Migration 三张新表
- `0018_world_objects`：`objects(object_id, kind, owner_type/id, location_place_id, status, effective_from/until, ...)` + `object_ownership_history` 追加式历史
- `0019_world_places`：`places(place_id, name, scope, parent_place_id, ...)` 支持父链
- `0020_world_projects`：`projects(project_id, name, goal, status, started_at, due_at, ended_at, ...)`

### D2. 关联走 entity_links，不建 join 表
- `person→owns→object` 由 `register_object` 自动建立
- `event→at→place` 由 `link_event_to_place` 建立
- `project→involves→person` 由 `register_project(participants=[...])` 自动
- `object.location_place_id` 直接外键（高频访问）

### D3. 服务层
`services/world_service.py`：
- `register_object / transfer_object / list_objects_by_owner`
- `register_place / get_place_lineage / link_event_to_place`
- `register_project / set_project_status / list_projects_for_person`
- `active_world_for_scene`：返回"scene 当前世界快照"（参与者 + 物 + 地 + 项目）

### D4. Retrieval 扩展（additive）
- 新函数 `active_world_for_scene` 单独返回；**不**改旧 `build_runtime_retrieval_package_from_db` 签名
- 上层按需调用合并（保持 SkillRuntime v1 schema 不变——不变式 #19）

### D5. CLI
`scripts/world_cli.py register-object / register-place / register-project / active-world`

## 不变式（新，v0.17 第 26 条）
**#26**：所有世界对象（object / place / project / event）必须有**明确时间范围**——`effective_from` 或 `started_at` 必填，`effective_until / ended_at` 可空（表示"仍有效"）。
> 违反则"不存在"与"已失效"不可区分；图谱无法回答"5 月 12 日 Alice 有什么"这类历史问题。

## 版本锚点
- tests: +12 (test_phase_51_wm.py)
- 文件: 3 migration / `services/world_service.py` / `scripts/world_cli.py`
- schema: 0017 → 0020

## 非目标（v0.18）
- 从叙述文本自动抽 object / place / project（需 LLM importer 升级）
- object / place 的 embedding + 向量检索
- project 任务分解 / 依赖图
- world 级别的 rollback（与 snapshot 关联）
- object 继承 / 亲子关系（家族物件）
- 地理信息（GIS / 经纬度）：保持不在 MVP

## 拒绝的备选
- 把 object / place / project 塞进 `entities`（通用表）：太稀疏，查询痛苦；**三张专表**更清晰
- person-object-place 多对多 join 表：每跨一类多一张表；直接用 entity_links 即可
- retrieval_package 强制含 world：破坏 v1 schema（#19）；新函数合并

## 向后兼容性
- 旧代码不受影响：新表、新服务、新 CLI，全部增量
- 旧 retrieval 接口继续工作；新字段留给 v0.18 整合
