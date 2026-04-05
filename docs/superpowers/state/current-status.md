# 当前状态

日期：2026-04-05

当前已完成：

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

当前主设计稿：

- [2026-04-05-we-together-core-design.md](../specs/2026-04-05-we-together-core-design.md)
- [2026-04-05-runtime-activation-and-flow-design.md](../specs/2026-04-05-runtime-activation-and-flow-design.md)
- [2026-04-05-unified-importer-contract.md](../specs/2026-04-05-unified-importer-contract.md)

下一步建议：

- 定义图谱对象的具体 SQLite schema
- 定义 patch 与 snapshot 结构
- 定义 identity 融合策略
