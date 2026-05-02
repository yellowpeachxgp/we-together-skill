# Phase 44-50 Mega Plan — Plugin + Graph Clock + Self-Repair + Scale + Federation Safety + i18n

**Date**: 2026-04-19
**Version target**: v0.16.0
**Test target**: 594 passed (+73 over v0.15)
**Status**: ✅ Delivered

## 战略图

| Phase | 主题 | Slice | 支柱 | 交付 |
|-------|------|-------|:---:|------|
| 44 | Plugin 架构 | PL-1..20 | A + B | 4 扩展点 / entry_points / registry / authoring 指南 |
| 45 | 图谱时间 + 自修复 | GT-1..20 | C + A | migration 0017 / graph_clock / integrity_audit / self_repair / simulate_year |
| 46 | 多 Agent REPL | MA-1..15 | C | multi_agent_dialogue / 互听 + 打断 + 私聊 / transcript → event |
| 47 | 规模化 50-500 人 | SC-1..15 | A + C | seed_society_m/l / 性能基线 |
| 48 | 联邦安全 + PII | FS-1..15 | A + B | Bearer token / rate limit / PII mask / protocol v1.1 |
| 49 | i18n + 时序观测 | UX-1..15 | B + C | zh/en/ja prompt / SVG sparkline / webhook alert |
| 50 | EPIC | EPIC-1..20 | 全局 | ADR 0046-0052 / mega-plan / CHANGELOG / 不变式 22→25 / tag v0.16.0 |

## 不变式扩展（ADR 0052）
22 → **25**：
- **#23** 扩展点必须通过 plugin registry 注册
- **#24** 时间敏感服务必须读 graph_clock.now() 优先
- **#25** 跨图谱出口必须支持 PII 脱敏 + visibility 过滤

## 三支柱达成度

| 支柱 | v0.15 | v0.16 | 备注 |
|------|:-----:|:-----:|------|
| A 严格工程化 | 9.5 | **9.7** | 3 条新不变式 + plugin + graph_clock |
| B 通用型 Skill | 9.5 | **9.7** | plugin 让第三方扩展 + 联邦 v1.1 可真部署 |
| C 数字赛博生态圈 | 8.5 | **9.0** | 图谱时间 + 自修复 + 多 agent 互听 + 规模化 |

## 交付清单

### 新模块
- `src/we_together/plugins/` (Phase 44)
- `src/we_together/services/graph_clock.py / integrity_audit.py / self_repair.py / multi_agent_dialogue.py / federation_security.py` (Phase 45/46/48)
- `src/we_together/runtime/prompt_i18n.py` (Phase 49)
- `src/we_together/observability/time_series_svg.py / webhook_alert.py` (Phase 49)

### 新 Migration
- `db/migrations/0017_graph_clock.sql`

### 新 Scripts
- `plugins_list.py / fix_graph.py / simulate_year.py / multi_agent_chat.py / seed_society_m.py / seed_society_l.py`

### 新 ADR
- 0046 - Plugin 架构
- 0047 - 图谱时间 + 自修复
- 0048 - 多 Agent REPL
- 0049 - 规模化 50-500 人
- 0050 - 联邦安全 + PII
- 0051 - i18n + 时序观测
- 0052 - Phase 44-50 综合

## 与 vision 对齐

- **A 严格工程化**：新 3 条不变式；service inventory 隐含更新
- **B 通用型 Skill**：plugin API 让 we-together 真正"可扩展"；联邦 v1.1 含鉴权 + PII 可真部署
- **C 数字赛博生态圈**：
  - 图谱**时间**让"一年演化模拟"真可能
  - **自修复**让长期运行不崩坏
  - **多 agent 互听**让多人共演真有对话感
  - **50-500 人规模**验证"可扩展"边界

## 拒绝清单（v0.17 候选）
- 真 LLM 跑 tick 一年（需 key + 真成本）
- 真 sqlite-vec/FAISS（CI 不稳）
- Claude Skills marketplace
- PyPI 正式发布
- 联邦写路径 + mTLS
- mkdocs 真建站 + GH Pages
- 4+ 语言 / LLM 自动翻译
- 性能回归 CI baseline 对比

## 验收

```bash
.venv/bin/python -m pytest -q
# 594 passed in ~20s

git tag v0.16.0
```
