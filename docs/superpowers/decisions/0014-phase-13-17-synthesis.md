# ADR 0014: Phase 13-17 综合 + 未来不变式扩展

## 状态

Accepted — 2026-04-18

## 背景

ADR 0009 为 Phase 8-12 固化了 5 条不变式。Phase 13-17 继续扩展能力边界，需要把"产品化 / eval / 时间 / 模拟 / 硬化收口"这五个方向的变化折叠进统一约束。

## 决策

### D1. 能力域划分明确化

`src/we_together/` 下形成清晰的功能分层：

| 目录 | 角色 |
|---|---|
| `db/` | schema + migration + bootstrap + schema_version 防御 |
| `llm/` | 跨 provider 抽象（text / vision） |
| `importers/` | 外部数据源 → candidate 层 |
| `services/` | 图谱变更 / 推理 / 查询服务 |
| `runtime/` | retrieval + SkillRuntime + adapters |
| `eval/` | groundtruth + metrics + judge + regression |
| `simulation/` | 社会模拟（teaser + 未来扩展） |
| `observability/` | logger + metrics + sinks |
| `packaging/` | skill 包打包 |
| `config/` | 配置加载 |
| `cli.py` | 统一命令入口 |

### D2. 新增不变式（在 ADR 0009 基础上追加）

6. **任何 LLM-驱动的演化（persona drift / memory condense / causality / what-if）必须产出可回溯的 metadata**（source='llm', confidence, reason），便于 eval 与回滚
7. **时间维度必须独立于"当下"存储**：persona_history append-only；relation strength 时序从 patches 派生而非冗余；as_of 永远不写 cache
8. **Eval 基线是合约**：`benchmarks/*.json` + `eval/baseline.json` 任一改动都视为 breaking change，须在 ADR 备案
9. **Demo 示例不得依赖真实外部服务**：examples/ 下所有示例必须在离线（mock LLM / stdlib）下跑通
10. **RBAC / sinks / NATS 等"可插拔"能力遵循 Protocol + 默认实现**：任何替换必须保持接口向后兼容

### D3. Phase 推进节奏

- 偶数 Phase（8/10/12/14/16...）= 扩能力面
- 奇数 Phase（9/11/13/15/17...）= 收束 / 产品化 / 时间 / 模拟
- 每 5 个 Phase 做一次综合 ADR（0009 / 0014 / 下次 0019）

## 后果

### 正面

- 目录语义稳定，新能力按域对号入座
- LLM 输出全链路可溯源，eval 能定位回归根因
- 离线运行能力让 CI / 本地复现永远可靠

### 负面 / 权衡

- 目录分层要求开发者先选对位置，新手门槛略高
- 每个 Phase 都要 ADR 看起来冗重，但长期看是"代码即历史"的必要税

### 版本锚点

- 代码 tag: `v0.9.0`
- 测试基线: **318 passed**
- schema 版本: 0010（migrations 0001-0010）
- ADR 总数: 14（0001-0014）
- migrations 总数: 10

## 下一阶段候选（Phase 18+）

参考 `docs/superpowers/plans/2026-04-18-phase-13-17-mega-plan.md` 末尾"下一轮候选方向"段落，主要是 Phase 16（多模态 importer 深化）、Phase 17 SM-2/3/4/5、完整多租户 + rbac 集成。
