---
adr: 0069
title: Phase 66 — 100k / 1M 三 backend compare 基线
status: Accepted
date: 2026-04-19
---

# ADR 0069: Phase 66 — 100k / 1M 三 backend compare 基线

## 状态
Accepted — 2026-04-19

## 背景

在 Phase 65 之后，项目已经具备：

- `flat_python`
- `sqlite_vec`
- `faiss`

三条真实向量 backend 路径。

但没有同一环境、同一脚本、同一维度下的**并排证据**。这会导致：

- 推荐 backend 仍停留在口头判断
- nightly 无法做性能漂移检查
- release 文档无法给出 100k / 1M 规模建议

## 决策

### D1. `bench_scale.py` 增加 compare 模式

新增：

- `--backend all`

行为：

- 在隔离临时 root 中依次运行 `flat_python` / `sqlite_vec` / `faiss`
- 不污染用户传入的主 root 数据库
- 最终输出 compare JSON，而不是单 backend JSON

### D2. compare 报告必须包含 winner 字段

compare 输出必须含：

- `fastest_backend`
- `highest_qps_backend`

原因：

- 报告需要直接支持“推荐 backend”判断
- 不要求读者手工翻三条子报告再计算

### D3. compare 归档单独命名

格式：

```text
bench_compare_<n_label>_<timestamp>.json
```

例如：

- `bench_compare_100k_2026-04-19T10-30-12Z.json`
- `bench_compare_1m_2026-04-19T10-31-00Z.json`

避免和旧版单 backend 归档混淆。

### D4. 100k / 1M 当前推荐 backend = `faiss`

根据本地归档：

- `100k`：`faiss` per-query `0.14ms`
- `1M`：`faiss` per-query `1.50ms`

结论：

- `flat_python` 只保留为稳定基线和无 native 依赖环境
- `sqlite_vec` 适合“仍希望留在 SQLite 生态”的中间态
- `faiss` 是 100k / 1M 规模下的默认推荐

## 版本锚点

- 新增 compare 报告：`docs/superpowers/state/2026-04-19-scale-bench-v2-report.md`
- 新增 compare 归档：
  - `benchmarks/scale/bench_compare_100k_2026-04-19T10-30-12Z.json`
  - `benchmarks/scale/bench_compare_1m_2026-04-19T10-31-00Z.json`
- 测试基线：**715 passed, 4 skipped**

## 非目标

- ANN/HNSW 等更多索引结构
- vec0 虚表 schema 迁移
- 自动根据规模切 backend

## 拒绝的备选

### 备选 A：只跑单 backend benchmark

拒绝原因：无法直接比较，证据密度不足。

### 备选 B：在用户 root 里连跑三 backend

拒绝原因：会把 synthetic 数据堆进主库，污染真实环境。

### 备选 C：只做 100k，不做 1M

拒绝原因：无法给出大规模上限趋势，仍缺关键证据。

## 下一步

1. 把 compare 报告纳入 nightly / release evidence。
2. 在 README / HANDOFF 中明确推荐 backend。
3. 若后续引入 `vec0` 虚表，再用同一 compare 框架对比新路径。
