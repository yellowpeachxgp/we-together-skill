---
adr: 0065
title: Phase 63 — 纸面工程化根除（ADR status + #30）
status: Accepted
date: 2026-04-19
---

# ADR 0065: Phase 63 — 纸面工程化根除

## 状态
Accepted — 2026-04-19

## 背景
59 条 ADR 累积至今，但没有统一的 `status` 机器可读字段——未来可能出现"僵尸 ADR"（该归档却还在"Active"状态）。

## 决策

### D1. 所有 ADR 必须有机器可读 status
- frontmatter 里 `status: Accepted|Active|Superseded|Archived`
- 测试 `test_all_adrs_have_status_frontmatter` 强制

### D2. 不变式 #30
**每条 ADR 必须标注 Active / Superseded-by / Archived；不允许僵尸状态。**

### D3. 本 phase 检查
- 不变式 #29 保持（每条不变式有测试）
- migration 无跳号
- self_introspection 继续工作

## 版本锚点
- tests: +4 (test_phase_62_63.py 后 4 条)
- 不变式: 29 → 30

## 非目标
- 真重写过时 ADR 为 Superseded（留 v0.19 细审）
- ADR 互引图（"#0020 被 #0050 深化"）
