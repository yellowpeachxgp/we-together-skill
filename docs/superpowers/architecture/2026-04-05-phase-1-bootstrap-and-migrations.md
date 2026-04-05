# Phase 1 启动与迁移方案

## 1. 文档目标

本文档定义 `we together` 第一阶段的项目启动方式与数据库迁移策略，确保项目从零开始实现时具备：

- 可重复初始化
- 可追踪迁移历史
- 可在本地稳定重建数据库
- 可在后续 importer 和 runtime 接入前先完成内核落地

## 2. 第一阶段目标

第一阶段启动后，仓库应至少具备：

- 一个可初始化的 SQLite 主库
- 一套可执行的迁移机制
- 一组最小目录结构
- 一套最小种子数据
- 一条可重复执行的 bootstrap 流程

## 3. 目录布局建议

第一阶段建议建立如下运行时目录：

```text
.
├── README.md
├── docs/
│   └── superpowers/
├── data/
│   ├── raw/
│   ├── derived/
│   ├── snapshots/
│   └── runtime/
├── db/
│   ├── main.sqlite3
│   ├── migrations/
│   └── seeds/
├── src/
│   └── we_together/
├── tests/
└── scripts/
```

### 3.1 `data/raw/`

存放原始导入材料归档，例如：

- 聊天导出文本
- 文档导出文本
- 邮件原文
- 图片 OCR 结果

### 3.2 `data/derived/`

存放导入过程中的中间结果，例如：

- 归一化文本
- importer 输出 JSON
- 临时摘要

### 3.3 `data/snapshots/`

存放 snapshot 的导出文件与调试用图谱快照。

### 3.4 `data/runtime/`

存放运行时检索包缓存、临时组合包、调试输出。

### 3.5 `db/`

数据库相关目录：

- `main.sqlite3`
- `migrations/`
- `seeds/`

## 4. SQLite 文件策略

### 4.1 主数据库

第一阶段只维护一个主数据库文件：

- `db/main.sqlite3`

用途：

- 存放规范主对象
- 存放事件、patch、snapshot、local branch
- 存放 importer 产出的结构化索引

### 4.2 测试数据库

测试时使用独立数据库，不共享主库。

建议：

- `tmp/test.sqlite3`
- 或测试框架自动创建临时 sqlite 文件

### 4.3 调试导出

为便于人工检查，可允许导出：

- `data/snapshots/*.json`
- `data/runtime/*.json`

这些不是规范真相，只是辅助视图。

## 5. 迁移机制

### 5.1 迁移编号规则

第一阶段建议使用顺序编号：

```text
db/migrations/
  0001_initial_core_schema.sql
  0002_indexes.sql
  0003_runtime_support.sql
  0004_importer_support.sql
```

### 5.2 迁移执行记录表

数据库初始化后必须创建：

- `schema_migrations`

建议字段：

- `version` TEXT PRIMARY KEY
- `description` TEXT
- `applied_at` TEXT NOT NULL

### 5.3 迁移内容边界

迁移文件只负责：

- 创建表
- 创建索引
- 创建触发器（如确有必要）
- 初始化固定基础数据

迁移文件不负责：

- 导入真实业务数据
- 写入实验性调试数据
- 执行平台抓取逻辑

## 6. 第一阶段迁移拆分建议

### 6.1 `0001_initial_core_schema.sql`

负责创建规范主对象表：

- `persons`
- `identity_links`
- `relations`
- `groups`
- `scenes`
- `events`
- `memories`
- `states`
- `schema_migrations`

### 6.2 `0002_connection_tables.sql`

负责创建连接与子对象表：

- `person_facets`
- `relation_facets`
- `group_members`
- `scene_participants`
- `scene_active_relations`
- `memory_owners`
- `event_participants`
- `event_targets`

### 6.3 `0003_trace_and_evolution.sql`

负责创建留痕与演化表：

- `import_jobs`
- `raw_evidences`
- `patches`
- `snapshots`
- `snapshot_entities`
- `local_branches`
- `branch_candidates`

### 6.4 `0004_indexes_and_constraints.sql`

负责：

- 核心索引
- 唯一约束
- 高价值查询索引

### 6.5 `0005_runtime_cache.sql`

负责：

- `entity_tags`
- `entity_aliases`
- `entity_links`
- `retrieval_cache`

该迁移可根据实现节奏后置。

## 7. Seed 数据策略

### 7.1 第一阶段最小 seed

建议第一阶段只提供系统级 seed，不提供真实社会数据 seed。

可包含：

- 默认 scene type 枚举
- 默认 environment 枚举
- 默认 relation core type 列表
- 默认 activation state 列表

### 7.2 Seed 文件格式

建议保留为：

- `db/seeds/*.json`

由初始化脚本导入。

### 7.3 不建议写进 seed 的内容

第一阶段不建议在种子数据里写：

- 示例真实人物
- 示例真实关系网络
- 示例导入证据

这些更适合测试夹具，而不是默认 seed。

## 8. Bootstrap 流程

### 8.1 标准初始化流程

建议定义一个统一 bootstrap 命令，执行：

1. 创建目录结构
2. 创建 SQLite 文件
3. 执行全部迁移
4. 写入基础 seed
5. 输出数据库版本与初始化结果

### 8.2 幂等要求

bootstrap 应尽量支持重复执行：

- 已存在目录不报错
- 已应用迁移不重复应用
- 已写入基础 seed 不重复灌入

## 9. 回滚策略

### 9.1 第一阶段建议

第一阶段不必实现复杂的数据库 migration down。

推荐策略：

- schema 回滚主要依赖重建本地库
- 图谱内容回滚依赖 snapshot 与 patch 机制

### 9.2 为什么不优先做 down migration

因为第一阶段最重要的是：

- 快速稳定演进 schema
- 保持主对象边界清晰

而不是在 schema 层实现复杂双向迁移。

## 10. 文件与数据库的初始化边界

### 10.1 数据库初始化只负责结构

数据库初始化负责：

- 表
- 索引
- seed

### 10.2 文件目录初始化只负责容器

文件系统初始化负责：

- 创建 `data/raw`
- 创建 `data/derived`
- 创建 `data/snapshots`
- 创建 `data/runtime`
- 创建 `db/migrations`
- 创建 `db/seeds`

### 10.3 原始数据导入不属于 bootstrap

真实导入动作必须在 bootstrap 之后单独执行。

## 11. 测试建议

第一阶段建议至少准备三类测试：

### 11.1 迁移测试

验证：

- 全量迁移能成功执行
- 重复执行不会报错

### 11.2 初始化测试

验证：

- 目录被正确创建
- SQLite 主库被正确初始化
- 基础 seed 被正确写入

### 11.3 数据完整性测试

验证：

- 核心表存在
- 关键唯一约束存在
- 关键索引存在

## 12. 第一阶段最小实现要求

第一阶段启动与迁移方案至少要做到：

- 有明确的 `db/main.sqlite3`
- 有 `db/migrations/`
- 有 `schema_migrations`
- 有统一 bootstrap 流程
- 有最小 seed
- 有迁移测试

## 13. 下一步建议

在本文档之后，建议继续整理：

1. `首版 importer 适配优先级与复用清单`
2. `数据库迁移执行脚本方案`
3. `首版实现计划`

## 14. 结论

第一阶段不应一边写代码一边随手改库。

它应被实现为：

> **一个可重复初始化、可追踪迁移、目录边界清晰、并为后续 importer 与 runtime 落地做好准备的工程化启动体系。**
