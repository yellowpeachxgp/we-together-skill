# Phase 33-37 Mega Plan — Skill Host + Tick + Media + Debt + Release

**Date**: 2026-04-19
**Version target**: v0.14.0
**Test target**: 477 passed (+41 over v0.13)
**Status**: ✅ Delivered

## 战略图

| Phase | 主题 | Slice | 对应 vision 支柱 | 交付 |
|-------|------|-------|-----------------|------|
| 33 | 真 Skill 宿主 | SP-1..20 | B | SkillRuntime v1 冻结 / MCP 全协议 / OpenAI demo / verify_skill |
| 34 | 持续演化 Tick | EV-1..20 | C | time_simulator / tick_sanity / simulate_week CLI |
| 35 | 媒体落盘 | MM-1..20 | C | migration 0015 / media_asset_service / ocr + 转录 |
| 36 | 规模 & 债务 | DT-1..20 | A | service inventory / migration audit / VectorIndex backend |
| 37 | 综合 + 发布 | EPIC-1..20 | 全局 | ADR 0034-0039 / CHANGELOG / tag v0.14.0 |

## 不变式扩展（ADR 0039）
18 → 20 条。新增：
- **#19** SkillRuntime schema 必须版本化（v1 冻结）
- **#20** tick 写入必须可 snapshot 回滚至任一时间点

## v0.14.0 vs v0.13.0 差异
- 测试 436 → **477**（+41）
- ADR 33 → **39**（+6：0034-0039）
- Migrations 14 → **15**（+0015_media_assets）
- Benchmarks 8 → **9**（+multimodal_retrieval_groundtruth）
- 不变式 18 → **20**
- 新增 services: time_simulator / tick_sanity / media_asset_service / ocr_service
- 新增 scripts: simulate_week.py / import_image.py / bench_scale.py / verify_skill_package.py / demo_openai_assistant.py

## 三支柱达成度变化
- A 严格工程化：9 → **9.5**
- B 通用型 Skill：6 → **8**
- C 数字赛博生态圈：5 → **7**

## 与 vision 对齐

- **A 严格工程化**：+ 新 20 条不变式、service-inventory、migration-audit
- **B 通用型 Skill**：+ schema v1 冻结、MCP 全协议（resources/prompts）、OpenAI Assistants demo、Skill zip verify
- **C 数字赛博生态圈**：+ 持续演化 tick 闭环、媒体资产真入图谱、"跑完一周看图谱是否炸"的合理性评估

## 拒绝清单（留 v0.15+）
- 真 sqlite-vec / FAISS 集成（CI 依赖约束）
- Claude Skills marketplace 真上架（外部审批）
- 真 cron daemon（让宿主调度）
- multi_agent_chat.py REPL + simulate_week 真执行报告
- contradiction → patch 自动联动（违反 #18）
- federation 真 RPC（stub 足够 v0.14，真实现留 v0.15）
- PyPI 正式发布（需 token）
- i18n prompts

## 验收

```bash
.venv/bin/python -m pytest -q
# expected: 477 passed

git tag v0.14.0
```
