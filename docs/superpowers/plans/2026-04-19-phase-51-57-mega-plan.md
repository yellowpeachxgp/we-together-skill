# Phase 51-57 Mega Plan — World Modeling + Agent Meta + QR + Community + Release

**Date**: 2026-04-19
**Version target**: v0.17.0
**Test target**: 638 passed (+44 over v0.16)
**Status**: ✅ Delivered

## 战略图

| Phase | 主题 | Slice | 支柱 | 交付 |
|-------|------|-------|:---:|------|
| 51 | 世界建模升维 | WM | C | migration 0018/0019/0020 / world_service / 不变式 #26 |
| 52 | AI Agent 元能力 | AG | C | migration 0021 / autonomous_agent / dream_cycle / 不变式 #27 |
| 53 | 质量与韧性 | QR | A | OTel NoOp / property / fuzz / nightly workflow |
| 54 | 社区就绪 | CM | B | CONTRIBUTING + 对比 + mkdocs + Good First Issues |
| 55 | 差异化能力 | DF | C | working_memory / derivation_rebuild / 不变式 #28 |
| 56 | 发布准备 | RL | B | PyPI checklist + Claude Skills 材料 + release_prep |
| 57 | EPIC | EPIC | 全局 | ADR 0053-0059 / mega-plan / CHANGELOG / 不变式 25→28 / tag v0.17.0 |

## 不变式扩展（ADR 0059）
25 → **28**：
- **#26** 世界对象必须有时间范围
- **#27** Agent 自主行为必须可解释
- **#28** 派生必须可从底层重建

## 三支柱达成度

| 支柱 | v0.16 | v0.17 | 改进点 |
|------|:-----:|:-----:|-------|
| A 严格工程化 | 9.7 | **9.8** | +3 不变式 + OTel + fuzz + nightly |
| B 通用型 Skill | 9.7 | **9.8** | 社区四件套 + 3 对比 + 发布流程 |
| C 赛博生态圈 | 9.0 | **9.5** | 世界建模 + Agent 自主 + 梦 + 派生重建 |

## 核心升维

### 从"社会图谱"到"世界图谱"
v0.16 前只建模人 + 关系 + 事件 + 记忆 + 场景。
v0.17 起加入 **物（objects） / 地点（places） / 项目（projects）** —— 完整的"世界"。

### 从"被动 agent"到"自主 + 梦 + 学习"
v0.16 前所有 agent 行为被外部触发。
v0.17 起 agent 有**内在驱动力**（connection / curiosity / resolve / obligation / rest），有**梦循环**（dream_cycle 自动压缩 + 产生 insight），有**学习**（persona 随时间调整）。

### 从"孤立代码"到"社区就绪"
v0.16 前 CONTRIBUTING/COC/SECURITY 都缺。
v0.17 起有完整治理四件套、3 份对比文档、20 条 Good First Issues、mkdocs 骨架。

## Slice 清单

完整 ID 列表见 TaskList #906-#1006。关键里程碑：

### Phase 51 WM - 20 slice ✅
migration 0018/0019/0020 / world_service / entity_links 关联 / active_world_for_scene

### Phase 52 AG - 16 slice ✅
migration 0021 / autonomous_agent / dream_cycle / insight / 不变式 #27

### Phase 53 QR - 12 slice ✅
otel_exporter (NoOp) / property tests / fuzz tests / nightly workflow / bench

### Phase 54 CM - 13 slice ✅
CONTRIBUTING/COC/SECURITY/GOVERNANCE / 3 对比文档 / mkdocs / Good First Issues

### Phase 55 DF - 10 slice ✅
working_memory / derivation_rebuild / 不变式 #28

### Phase 56 RL - 10 slice ✅
PyPI checklist / Claude Skills 材料 / release_prep.py

### Phase 57 EPIC - 20 slice ✅
ADR 0053-0059 / mega-plan / CHANGELOG / bump / tag

## 验收

```bash
.venv/bin/python -m pytest -q
# 638 passed + 2 skipped

git tag v0.17.0
```

## 拒绝清单（v0.18 候选）
- 真 LLM 跑 simulate_year
- 真 sqlite-vec / FAISS
- Claude Skills 真提交
- PyPI 正式发布
- 联邦写路径 + mTLS
- narrative_v2 深度升级
- mkdocs-material 建站
- task decomposition
- LLM-based drive
- 多 world / 多租户
