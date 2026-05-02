# Phase 58-64 Mega Plan — Verification + Reflexive + Evidence

**Date**: 2026-04-19
**Version target**: v0.18.0
**Test target**: 690 passed (+52 over v0.17)
**Status**: ✅ Delivered

## 战略转向

v0.17 前六轮都在**加新能力**（社会→世界、被动→自主）。v0.18 是第一次**反方向**：
- 不加新 schema
- 不加新 feature
- 只做 **验证 + 反身 + 证据**

这让 we-together 从"声明式 9.8/9.8/9.5"变成"**可验证 9.95/9.8/9.7**"。

## 战略图

| Phase | 主题 | Slice | 方向 | 交付 |
|-------|------|-------|:---:|------|
| 58 | 不变式 → 测试映射 | IN-1..15 | 验证 | invariants.py + 30 条测试映射 + CLI（不变式 #29） |
| 59 | 年度真跑 | SY-1..10 | 验证 | simulate_year 365 天真归档 + 报告 |
| 60 | 反身能力 | RX-1..16 | 反身 | self_introspection + 3 MCP 工具 + self_audit CLI |
| 61 | 规模化压测 | SP-1..10 | 验证 | 10k/50k 真跑归档 + 报告 |
| 62 | Exemplar Scenarios | EX-1..9 | 证据 | 3 场景真跑归档（family/work/book_club） |
| 63 | 纸面工程化根除 | NT-1..9 | 治理 | ADR status frontmatter 强制（不变式 #30） |
| 64 | EPIC | EPIC | 全局 | ADR 0066 + mega-plan + CHANGELOG + tag v0.18.0 |

## 不变式扩展（ADR 0066）
28 → **30**：
- **#29** 纸面不变式禁止（每条必须有 >= 1 测试 + 真实存在）
- **#30** ADR 必须声明 status（禁止僵尸 ADR）

## 三支柱达成度

| 支柱 | v0.17 | v0.18 | 改进点 |
|------|:-----:|:-----:|-------|
| A 严格工程化 | 9.8 | **9.95** | 不变式强制 + 反身 + 年度真跑 + ADR status |
| B 通用型 Skill | 9.8 | **9.8** | 反身 MCP 工具（差异化），真上架留外部 |
| C 数字赛博生态圈 | 9.5 | **9.7** | 365 天证据 + 50k 压测 + 3 exemplar |

## 核心 shift

### 从"声明"到"证据"
- v0.16: 声明"tick 可回滚" → v0.18: **真跑 365 天并归档**
- v0.17: 声明"world service" → v0.18: **真跑 3 个 scenario 并归档**
- v0.17: 声明"plugin 架构" → v0.18: **不变式 #29 强制 plugin API 测试**

### 从"增长"到"审计"
- v0.17 前：ADR 0-52 不停累加
- v0.18：新增 7 个 ADR (0060-0066)，主要是**审计性**而非**新能力**

### 从"不透明"到"反身"
- v0.17: 59 ADR 写在磁盘 → v0.18: MCP 工具 `we_together_self_describe` 让 Claude 问自己
- v0.17: 28 不变式在 ADR → v0.18: `invariants_check` CLI 立即查看覆盖率

## Slice 清单（约 119 task）

完整 ID 见 TaskList #1007-#1095。关键里程碑：

### Phase 58 IN - 15 slice ✅
invariants.py 30 条 + test_refs + coverage_summary + CLI

### Phase 59 SY - 10 slice ✅
simulate_year --archive-monthly + 365 天真跑报告 + 首份归档

### Phase 60 RX - 16 slice ✅
self_introspection + 3 MCP tools + self_audit CLI

### Phase 61 SP - 10 slice ✅
10k/50k 真跑 + benchmarks/scale/ 归档 + 报告

### Phase 62 EX - 9 slice ✅
scenario_runner + 3 场景真跑 + examples/scenarios/ 归档

### Phase 63 NT - 9 slice ✅
ADR status 强制 + 不变式 #30

### Phase 64 EPIC - 20 slice ✅
ADR 0066 + mega-plan + CHANGELOG + bump + tag v0.18.0

## 验收

```bash
.venv/bin/python -m pytest -q
# 690 passed, 2 skipped

git tag v0.18.0
```

## 拒绝清单（v0.19 候选）
- 真 sqlite-vec / FAISS 接入
- 真 LLM 跑 + 成本采样
- mkdocs 真建站 + GitHub Pages
- Claude Skills 真提交
- PyPI 正式发布
- 多 world / 多租户
- task decomposition
- LLM-based drive 检测升级
