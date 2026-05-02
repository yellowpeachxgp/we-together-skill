# v0.20 Candidate Ordering

**Date**: 2026-04-23
**Basis**: local `v0.19.0` state, `782 passed / 4 skipped`, ADR 0073, release-prep green

## 判断前提

当前本地 `v0.19.0` 之后已经同时满足：

- version / CLI / wheel / local tag 一致
- vector backend 真接入 + `100k / 1M` compare 证据已归档
- federation 写路径 + curl 生产 smoke 已闭环
- `simulate_year` usage/cost/monthly artifact 骨架已就位
- tenant CLI 覆盖面已经很广，形成了可工作的多租户基线
- contradiction -> unmerge 已起步为 **operator-gated local_branch**，不再只是纸面 candidate

因此 `v0.20` 不该再从“补旧 stub”开始，而应沿着**已起步的真实闭环**往前推进。

## 推荐阶段顺序

### Phase 72 — Contradiction Review / Operator-Gated Unmerge

目标：

- 保持 `contradiction_detector` **只读不写**
- 把 merged person 的复核路径产品化为 `local_branch`
- 候选固定为 `keep_merged / unmerge_person`
- 只有 `resolve_local_branch` 选中 unmerge candidate 才真正改图
- `auto_resolve_branches` 必须跳过 operator-gated branch

为什么先做：

- 这是当前已经起步的本地切片，最符合“先把真实闭环做扎实”的原则。
- 它把 Phase 41 的 `candidate，不自动改图` 思路推进到了可操作的人工复核路径。
- 这一步强化的是**可逆 + 可审计 + 不自动误写**，优先级高于再做更多外部包装。

### Phase 73 — Tenant / World Isolation Deepening

目标：

- tenant namespace / world namespace contract
- 更系统的 cross-tenant negative tests
- world-aware / tenant-aware 边界语义补强

为什么排第二：

- tenant CLI 覆盖已经够广，下一步价值不在“再补更多 `--tenant-id`”，而在“隔离语义更硬”。
- 这会直接影响后续多 world 与协作场景的可信度。

### Phase 74 — Real LLM Operationalization

目标：

- 真 provider 7-day / 30-day run
- usage/cost 月报真实样本
- `dream_cycle` 真 insight 生成

为什么排第三：

- 骨架已齐，缺的是外部真实证据。
- 但在开始真实成本消耗前，先把图谱写入 guardrail 和隔离语义再压实一层更稳妥。

### Phase 75 — Collaborative Autonomy / Task Decomposition

目标：

- multi-agent task decomposition
- 协作式 goal completion
- narrative / planning / execution 的更强闭环

为什么排第四：

- 这是差异化方向，但要建立在更稳的 graph guardrail 和真实 provider 证据之上。
- 否则容易变成“看上去很强，但难审计”的能力堆叠。

### Phase 76 — Release Externalization

目标：

- GitHub Release
- PyPI 正式发布
- 文档站点 / 外部试用 / release checklist 真实演练

为什么排第五：

- 发布不是不能做，而是应建立在更清楚的 v0.20 叙事之上。
- 当 operator gate、隔离语义和真实 LLM evidence 都更稳之后，对外发布更有说服力。

## 明确不建议优先做的事

- 再大规模补 tenant 参数
  - 当前已经过了“可用”阈值，边际收益很低。
- 立即做多 world 大重构
  - 先做 contract 和 negative tests，比直接大改架构更稳。
- 把 contradiction 说成“自动修复错误 merge”
  - 当前正确语义是：**candidate + operator gate + resolve 后才生效**。

## 一句话结论

如果按当前工程价值排序，`v0.20` 最应该优先做的是：

`operator-gated contradiction review -> tenant/world isolation contract -> real provider evidence -> collaborative autonomy -> external release`
