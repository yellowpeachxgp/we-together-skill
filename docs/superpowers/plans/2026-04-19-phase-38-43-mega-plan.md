# Phase 38-43 Mega Plan — Consumption + Tick Archive + Neural Mesh + Forgetting + Federation

**Date**: 2026-04-19
**Version target**: v0.15.0
**Test target**: 521 passed (+44)
**Status**: ✅ Delivered

## 战略图

| Phase | 主题 | Slice | 支柱 | 交付 |
|-------|------|-------|:---:|------|
| 38 | 消费就绪 | CR-1..20 | B | Dashboard HTML/JSON/metrics / 三路宿主文档 / getting-started / e2e smoke |
| 39 | Tick 真归档 | CT-1..20 | C | simulate_week --archive / 首份 baseline / tick_cost_tracker / rollback CLI / 调度文档 |
| 40 | 神经网格 | NM-1..20 | C | migration 0016 / activation_trace_service / plasticity / multi-hop / activation_path CLI |
| 41 | 遗忘/压缩/拆分 | FO-1..20 | C + A | forgetting_service / entity_unmerge_service / 对称撤销不变式 |
| 42 | 联邦 MVP | FD-1..10 | B | HTTP server + client / protocol v1 spec / Read-Only |
| 43 | EPIC | EPIC-1..20 | 全局 | ADR 0040-0045 / mega-plan / CHANGELOG / 不变式 20→22 / tag v0.15.0 |

## 不变式扩展（ADR 0045）
20 → **22**：
- **#21** 激活机制必须可 introspect
- **#22** 写入必须有对称撤销路径

## 三支柱达成度

| 支柱 | v0.14 | v0.15 | 备注 |
|------|:-----:|:-----:|------|
| A 严格工程化 | 9.5 | **9.5** | 维持 |
| B 通用型 Skill | 8 | **9.5** | 三路宿主文档 + Dashboard + 联邦 MVP |
| C 数字赛博生态圈 | 7 | **8.5** | tick 归档 + 神经网格 + 遗忘 + 联邦 |

## Slice 清单（约 110 task）

完整 ID 列表见 TaskList #676-#785。关键里程碑：

### Phase 38 CR
- CR-1..20：Dashboard / 三路宿主文档 / getting-started / e2e smoke ✅
- PyPI 正式发布 + CI verify_skill 留 v0.16

### Phase 39 CT
- CT-1..20：simulate_week --archive / baseline / tick_cost_tracker ✅
- 真 key 跑 tick：留 v0.16

### Phase 40 NM
- NM-1..20：activation_traces migration + service + plasticity + multi-hop ✅
- 全部核心落地

### Phase 41 FO
- FO-1..20：forgetting + unmerge ✅
- tick 自动触发 archive：留 v0.16

### Phase 42 FD
- FD-1..10：HTTP MVP + protocol v1 + client ✅
- 写路径 + 鉴权：留 v0.16

### Phase 43 EPIC
- EPIC-1..20：ADR / mega-plan / CHANGELOG / bump / tag ✅

## 验收

```bash
.venv/bin/python -m pytest -q
# 521 passed

git tag v0.15.0
```

## 与 vision 对齐

- **A 严格工程化**：新 2 条不变式（#21/#22），6 个新 ADR
- **B 通用型 Skill**：三路宿主真文档，联邦 MVP 让两 skill 能互查
- **C 数字赛博生态圈**：
  - **神经单元网格式激活传播**（vision 原话）从概念变实体（activation_trace + plasticity + multi-hop）
  - **可持续演化**真闭环：tick 真归档 + 遗忘/压缩抗衡膨胀

## 拒绝清单（v0.16 候选）
- 真 LLM 跑 tick（需 key）
- 真 sqlite-vec / FAISS（CI 约束）
- 联邦写 + 鉴权
- Claude Skills marketplace 上架
- multi_agent_chat.py REPL
- plugin 机制
- i18n prompts
