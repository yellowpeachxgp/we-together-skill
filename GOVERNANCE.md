# Governance

## 项目愿景

**"Skill-first 的数字赛博生态圈"** —— 见 [`docs/superpowers/vision/2026-04-05-product-mandate.md`](docs/superpowers/vision/2026-04-05-product-mandate.md)。

三支柱：
- A 严格工程化
- B 通用型 Skill
- C 数字赛博生态圈

## 角色

### 用户
任何使用 we-together 的个体 / 团队。

### 贡献者
任何提交过 PR、issue 或文档的人。

### 维护者（Maintainer）
通过持续贡献获得合并权：
- 合并 PR
- 参与 ADR 评审
- 做 release

### 核心维护者（Core Maintainer）
至少 6 个月持续参与：
- 设定路线图
- 制定 ADR
- 决定 release timing
- 处理安全事件

## 决策流程

### 小改动（bug fix / docs）
- 1 个 maintainer review 即可合并

### 中改动（新 service / 新 plugin 扩展点）
- ADR 提议
- 至少 2 个 maintainer 同意
- 不违反当前不变式

### 大改动（新 migration / 破坏 schema）
- ADR 必需
- Core Maintainer 决定
- 必须有 migration 路径 + 不变式审视

### 不变式新增 / 修改
- Core Maintainer 共识
- 在 synthesis ADR 里明确入册

## Release 流程

**谁来 release**: Core Maintainer
**频率**: 约每 2-3 个月一个 minor version
**流程**:
1. 完成 Phase 清单
2. 全量 pytest 绿
3. bump VERSION
4. Wheel 隔离安装验证
5. `git tag vX.Y.0`
6. 可选 PyPI 发布

详见 [`docs/release/pypi_checklist.md`](docs/release/pypi_checklist.md)（v0.17 的 Phase 56 落地）。

## 冲突解决

设计冲突优先级：
1. 与 vision / mandate 冲突 → 以 mandate 为准
2. 与不变式冲突 → 以现行不变式为准（要改先改不变式）
3. 其他 → Core Maintainer 共识，多数票

技术冲突无法达成共识 → 提 ADR 记录两种方案 + 选定的一方 + 理由。

## 退出机制

维护者可主动退出（邮件 / issue 声明）；6 个月无活动会被降级为贡献者。
