# Release Notes — v0.17.0 (2026-04-19)

**Theme**: 维度跃迁——从社会图谱到世界图谱 + 从被动 agent 到自主/梦/学习 + 从孤立代码到社区就绪

**Test baseline**: 638 passed (+44 over v0.16)
**ADR 总数**: 59
**Migrations**: 21
**不变式**: 28

## 三支柱达成度

| 支柱 | v0.16 | **v0.17** | 改进点 |
|------|:-----:|:---------:|-------|
| A 严格工程化 | 9.7 | **9.8** | 3 条新不变式 + OTel + property + fuzz + nightly |
| B 通用型 Skill | 9.7 | **9.8** | 社区四件套 + 3 对比文档 + 发布流程 |
| C 数字赛博生态圈 | 9.0 | **9.5** | 世界建模 + Agent 自主 + 梦循环 + 派生重建 |

## 核心维度跃迁

### 1. 社会图谱 → 世界图谱
```bash
python scripts/world_cli.py register-object --kind possession --name 笔记本电脑 --owner-id person_alice
python scripts/world_cli.py register-place --name 公司 --scope venue
python scripts/world_cli.py register-project --name "v0.18 发布" --participants p_a p_b
```

### 2. 被动 → 自主（梦循环）
```bash
python scripts/dream_cycle.py --root . --lookback 30
# agent 在无外部触发时整理记忆、产出 insight、调整 persona
```

### 3. 孤立代码 → 社区就绪
- `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md` + `SECURITY.md` + `GOVERNANCE.md`
- 3 份对比文档（vs Mem0 / Letta / LangMem）
- 20 条 Good First Issues（4 档难度）
- mkdocs 骨架 + GitHub Issue/PR 模板

## 升级路径

```bash
git pull
.venv/bin/pip install -e .
.venv/bin/python scripts/bootstrap.py --root .   # migrations 0018-0021 自动补齐
```

**Breaking changes**: 无（SkillRuntime v1 继续冻结；所有新能力 additive）。

## 新不变式

- **#26** 世界对象（object / place / project / event）必须有明确时间范围
- **#27** Agent 自主行为必须可解释（能追溯到 drive / memory / trace）
- **#28** 派生字段必须可从底层 events / memories 重建

## 新 CLI

- `scripts/world_cli.py`
- `scripts/dream_cycle.py`
- `scripts/release_prep.py`

## 新 Service 模块

- `world_service` / `autonomous_agent` / `dream_cycle`
- `working_memory` / `derivation_rebuild`
- `observability/otel_exporter`

## 留给 v0.18

- 真 LLM 跑 simulate_year
- 真 sqlite-vec / FAISS
- Claude Skills 真提交
- PyPI 正式发布
- 联邦写路径 + mTLS
- narrative_v2 深度升级
- mkdocs-material 真建站
- task decomposition
- LLM-based drive
- 多 world / 多租户

## 详细文档

- [Phase 51-57 mega-plan](superpowers/plans/2026-04-19-phase-51-57-mega-plan.md)
- [Phase 51-57 diff 报告](superpowers/state/2026-04-19-phase-51-57-diff.md)
- [CONTRIBUTING](../CONTRIBUTING.md)
- [comparisons](comparisons/)
- [tutorials](tutorials/)
- ADR 0053 ~ 0059
