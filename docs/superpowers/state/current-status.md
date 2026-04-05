# 当前状态

日期：2026-04-05

当前已完成：

- 已确立产品最高约束：严格工程化、通用型 Skill、数字赛博生态圈目标
- 明确项目定位为 Skill-first 的社会图谱系统
- 选定第一阶段锚点场景为 `C：混合小社会`
- 确定采用统一社会图谱内核，而不是工作/亲密双系统拼接
- 确定关系模型为“核心维度固定 + 自定义扩展 + 自然语言摘要”
- 确定导入策略为默认全自动、自动入图谱
- 确定身份融合策略为激进自动融合，但必须可逆、可追溯
- 确定演化策略为“先写事件，再归并入图谱”
- 确定留痕模型为 Git 式混合结构
- 确定第一阶段只支持局部分支，不支持整图分叉
- 确定运行时采用“有界激活传播模型”
- 确定环境参数采用“核心维度固定 + 自定义扩展”
- 确定主存储采用 SQLite 与文件系统的混合模型
- 确定 importer 采用“统一证据层 + 候选层”的输出契约
- 确定 SQLite 为规范主对象与留痕对象的核心存储层
- 确定 Event / Patch / Snapshot 为第一阶段的标准演化链
- 确定默认激进融合、底层可逆的 identity 融合策略
- 确定运行时采用固定结构的检索包
- 确定 Scene 与环境参数采用“核心枚举 + 自定义扩展”
- 已补齐启动与迁移方案
- 已补齐 importer 复用矩阵
- 已写入 Phase 1 架构基线 ADR
- 已生成 Phase 1 implementation plan
- 已落地首批 Python 工程骨架
- 已落地 SQLite 主库迁移执行器与基础 schema
- 已落地 narration importer、patch 构造器、identity 融合评分基线与 runtime retrieval package 基线

当前主设计稿：

- [2026-04-05-we-together-core-design.md](../specs/2026-04-05-we-together-core-design.md)
- [2026-04-05-runtime-activation-and-flow-design.md](../specs/2026-04-05-runtime-activation-and-flow-design.md)
- [2026-04-05-unified-importer-contract.md](../specs/2026-04-05-unified-importer-contract.md)
- [2026-04-05-sqlite-schema-design.md](../specs/2026-04-05-sqlite-schema-design.md)
- [2026-04-05-patch-and-snapshot-design.md](../specs/2026-04-05-patch-and-snapshot-design.md)
- [2026-04-05-identity-fusion-strategy.md](../specs/2026-04-05-identity-fusion-strategy.md)
- [2026-04-05-runtime-retrieval-package-design.md](../specs/2026-04-05-runtime-retrieval-package-design.md)
- [2026-04-05-scene-and-environment-enums.md](../specs/2026-04-05-scene-and-environment-enums.md)
- [2026-04-05-phase-1-bootstrap-and-migrations.md](../architecture/2026-04-05-phase-1-bootstrap-and-migrations.md)
- [2026-04-05-importer-reuse-matrix.md](../importers/2026-04-05-importer-reuse-matrix.md)
- [2026-04-05-phase-1-kernel-implementation.md](../plans/2026-04-05-phase-1-kernel-implementation.md)
- [0001-phase-1-architecture-baseline.md](../decisions/0001-phase-1-architecture-baseline.md)
- [2026-04-05-product-mandate.md](../vision/2026-04-05-product-mandate.md)

下一步建议：

- 进入真正的实现计划
- 优先实现数据库与 bootstrap 链路
- 再接 narration importer 与最小 runtime 链路
