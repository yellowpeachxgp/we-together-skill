# Release Notes — v0.18.0 (2026-04-19)

**Theme**: 战略转向——不加新能力，**纵深验证 + 反身 + 证据**

**Test baseline**: 690 passed (+52 over v0.17, +2 skipped)
**ADR 总数**: 66
**不变式**: 历史计划口径 30；当前代码注册表为 28 条不变式，#29/#30 为治理检查项
**Migrations**: 21（未变）

## 三支柱达成度

| 支柱 | v0.17 | **v0.18** |
|------|:-----:|:---------:|
| A 严格工程化 | 9.8 | **9.95** |
| B 通用型 Skill | 9.8 | **9.8** |
| C 数字赛博生态圈 | 9.5 | **9.7** |

## 核心 shift

v0.18 是第一次**反方向版本**。前 10 轮不停加新能力，本轮回头补证据。

- **从"声明"到"证据"**：tick 可回滚 → **真跑 365 天归档**；world service → **3 个 scenario 真跑归档**
- **从"增长"到"审计"**：ADR status 强制；不变式必须有测试
- **从"不透明"到"反身"**：Claude 可问 `we_together_self_describe` 看自己

## 新能力

### 1. 不变式强制（治理检查 #29）
当前代码注册表为 28 条不变式，并要求每条必须挂 pytest 测试。历史文档中的 #29/#30 是本轮引入的治理检查，不应被当作当前 `src/we_together/invariants.py` 的注册不变式编号：
```bash
python scripts/invariants_check.py summary
python scripts/invariants_check.py show 28
```

### 2. 365 天真跑
```bash
python scripts/simulate_year.py --root . --days 365 --budget 0 --archive-monthly
```
仓库里已归档首份真跑结果：`benchmarks/year_runs/year_run_*.json`

### 3. 反身能力
```bash
python scripts/self_audit.py           # 整体描述
python scripts/self_audit.py --coverage # 不变式覆盖
python scripts/self_audit.py --adrs     # 所有 ADR
```

在 Claude Desktop / Claude Code：
```
@we-together 用 we_together_self_describe 工具描述你自己
```

### 4. 规模化真跑
```bash
python scripts/bench_scale.py --root . --n 10000 --dim 16 --queries 50
python scripts/bench_scale.py --root . --n 50000 --dim 16 --queries 30
```
10k: QPS 65.6 / 50k: QPS 12.7（flat_python baseline）

### 5. Exemplar Scenarios
```bash
python scripts/scenario_runner.py --scenario all --archive
```
3 场景（family/work/book_club）端到端真跑 + 归档

## 治理检查

- **#29/#30 历史治理检查**：纸面不变式禁止；ADR 必须声明 status。当前代码注册表为 28 条不变式。

## 证据清单

本版本产出的**可审计证据**（入仓库）：

| 类别 | 位置 | 内容 |
|------|------|------|
| 年度真跑 | `benchmarks/year_runs/` | 365 天 healthy/integrity |
| 规模化压测 | `benchmarks/scale/` | 10k + 50k |
| Exemplar | `examples/scenarios/` | 3 场景归档 |
| 不变式覆盖 | `docs/superpowers/state/2026-04-19-invariants-coverage.md` | 当前 28 条注册不变式 + 历史治理检查说明 |
| 报告 | `docs/superpowers/state/2026-04-19-*.md` | 年度/压测/不变式 |

## 升级路径

```bash
git pull && .venv/bin/pip install -e .
# 无 migration 变化，无需 bootstrap 刷新
```

无 Breaking changes。

## 留给 v0.19

- 真 sqlite-vec / FAISS 接入（stub → 真实现）
- 真 LLM 跑（需 key）
- mkdocs 真建站
- Claude Skills 真提交
- PyPI 正式发布
- 100k / 1M 规模
- ADR 互引图

## 详细文档

- [Phase 58-64 mega-plan](superpowers/plans/2026-04-19-phase-58-64-mega-plan.md)
- [Phase 58-64 diff](superpowers/state/2026-04-19-phase-58-64-diff.md)
- [不变式覆盖](superpowers/state/2026-04-19-invariants-coverage.md)
- [年度真跑报告](superpowers/state/2026-04-19-year-run-report.md)
- [规模化报告](superpowers/state/2026-04-19-scale-bench-report.md)
- ADR 0060 ~ 0066
