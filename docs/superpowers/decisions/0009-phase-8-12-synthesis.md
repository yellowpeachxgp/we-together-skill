# ADR 0009: Phase 8-12 综合架构总结

## 状态

Accepted — 2026-04-18

## 背景

Phase 8-12 一次性无人值守推进中产出的五个 ADR 已各自独立。本 ADR 聚合"这一轮演进让产品整体往 product-mandate 三条约束移动了多少"，并固化后续的不变式。

## 三条约束的进度

### A. 严格工程化

- 新增 9 个 ADR 级决策（0004-0008）
- 每个 Phase 收尾都有 current-status 段落与测试基线记录
- 216 → 281 passed；无测试跳过；CI 依然无 extra deps
- 所有跨 Phase 变更均在 docs/superpowers/plans/2026-04-18-phase-8-12-mega-plan.md 归档

### B. 通用型 Skill

- SkillRequest.tools 让所有 adapter 能协商 tool_use
- 新增 4 个宿主 adapter（飞书 / LangChain / Coze / MCP），纯函数实现
- skill 打包分发（.weskill.zip）
- 事件总线 + 多租户路由 + 冲突裁决 UI 让多实例共存成为可能

### C. 赛博生态圈

- 多场景并发激活 / cross_scene_echoes 让图谱能"看"邻接场景
- 记忆凝练 + 冷归档让图谱能"压缩"与"唤回"
- 自发交互 + persona drift 让图谱能"自演化"
- 冲突检测 + daily_maintenance 让图谱能"自体检"

## 未来不变式（后续所有变更必须遵守）

1. **任何宿主接入必须走 SkillRequest/SkillResponse + adapter**，不得直接引用 adapter-specific 结构
2. **任何结构性变更必须走 patch**，新操作在 patch_applier.py 集中分派
3. **任何 schema 变更必须新增 migration**，schema_version 预检拦截漂移
4. **任何新外部依赖必须在 ADR 说明理由**，默认拒绝
5. **任何 LLM 调用必须通过 LLMClient/VisionLLMClient Protocol**，SDK 延迟 import

## 版本锚点

- 代码：`git tag v0.8.0`（本地）
- 测试基线：281 passed
- schema 版本：0008（migrations/0001-0008）

## 下一阶段可能方向（未决）

- **Phase 13 生产回归**：日志/metrics 外置 sink（OTLP / Prometheus push gateway）、RBAC、真正事务化 patch
- **Phase 14 多模态**：音频（语音会议）importer、视频片段理解
- **Phase 15 社会模拟**：无真实输入情况下的"代际演化"（记忆消失 / 人物退出 / 关系重组）
