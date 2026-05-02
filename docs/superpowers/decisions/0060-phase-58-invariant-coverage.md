---
adr: 0060
title: Phase 58 — 不变式 → 测试映射（纸面工程化根除）
status: Accepted
date: 2026-04-19
---

# ADR 0060: Phase 58 — 不变式 → 测试映射

## 状态
Accepted — 2026-04-19

## 背景
v0.17 累计 28 条不变式写在各 synthesis ADR 里，但**没有强制测试映射**——违反某条是否会触发 CI 红？不明。这是"纸面工程化"的典型症状：**写了规矩但没强制执行**。

## 决策

### D1. `src/we_together/invariants.py` 注册表
- `Invariant(id, phase, title, description, adr_refs, test_refs)` dataclass
- `INVARIANTS: list[Invariant]` 全局列表，28 条
- 每条 `test_refs` 至少 1 个 "tests/path::test_name" 字符串

### D2. Meta-tests 保护
`tests/invariants/test_phase_58_in.py`：
- `test_every_invariant_has_at_least_one_test_ref`：空 test_refs → CI 红
- `test_test_refs_point_to_existing_files`：指向不存在文件 → CI 红
- `test_coverage_summary_100_percent`：覆盖率必须 100%
- 15 个其他 meta-tests（格式 / 不重复 / phase 覆盖等）

### D3. CLI introspection
`scripts/invariants_check.py`：
- `summary` 看整体覆盖
- `show <id>` 单条详情
- `list` 全部

### D4. 维护协议
- 新增不变式必须同步更新 `invariants.py`
- 不允许"不变式先写 ADR 再说"——test_refs 先挂才算数
- ADR 的 synthesis 小节必须引用对应的 Invariant ID

## 不变式（新，v0.18 第 29 条）
**#29**：纸面不变式禁止。每条不变式必须在 `invariants.py` 里有 >= 1 个 test_refs，且测试真实存在且 pytest 可跑通。
> 违反则 CI 红，阻挡 merge。

## 版本锚点
- tests: +16 (test_phase_58_in.py)
- 文件: `src/we_together/invariants.py` / `scripts/invariants_check.py` / `docs/superpowers/state/2026-04-19-invariants-coverage.md`
- 不变式: 28 → 29

## 非目标
- 不为每条不变式再写独立专题测试；复用已有的 test_refs 即可
- 不把 invariants.py 放进 migration/schema（它是运行时 constant）

## 拒绝的备选
- 用 decorator 标记测试 → 和 pytest plugin 耦合；注册表更清晰
- JSON 配置不变式 → Python 类更能表达关系 + 可 import
