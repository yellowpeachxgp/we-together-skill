# Scale Bench Report v2 (Phase 66)

**Date**: 2026-04-19
**Target**: 真 `flat_python / sqlite_vec / faiss` compare benchmark（100k / 1M）
**Environment**: macOS 26.5 arm64, Python 3.13.1

## 100k Compare

规模：**100,000** vectors

| Backend | dim | seed (s) | build (s) | per-query (ms) | QPS |
|--------|----:|---------:|----------:|---------------:|----:|
| flat_python | 16 | 0.754 | 0.106 | 168.92 | 5.9 |
| sqlite_vec | 16 | 0.768 | 0.080 | 15.73 | 63.6 |
| faiss | 16 | 0.770 | 0.160 | 0.14 | 6924.0 |

观察：

- `sqlite_vec` 相比 `flat_python` 的 per-query 降到约 `1/10.7`
- `faiss` 相比 `flat_python` 的 per-query 降到约 `1/1200`
- 100k 时，`faiss` 已经明显进入“近实时”档，`sqlite_vec` 进入“可用”档，`flat_python` 退化到只适合基线/回归

归档：

- `benchmarks/scale/bench_compare_100k_2026-04-19T10-30-12Z.json`

## 1M Compare

规模：**1,000,000** vectors

| Backend | dim | seed (s) | build (s) | per-query (ms) | QPS |
|--------|----:|---------:|----------:|---------------:|----:|
| flat_python | 16 | 7.814 | 1.622 | 1732.20 | 0.6 |
| sqlite_vec | 16 | 7.675 | 0.598 | 141.28 | 7.1 |
| faiss | 16 | 7.583 | 2.121 | 1.50 | 665.7 |

观察：

- `flat_python` 在 1M 已经基本退出可交互范围
- `sqlite_vec` 比 `flat_python` 快约 `12.3x`，但仍不足以支撑高频交互
- `faiss` 依然保持数量级优势，是 1M 规模下的首选 backend

归档：

- `benchmarks/scale/bench_compare_1m_2026-04-19T10-31-00Z.json`

## 结论

1. `auto -> flat_python` 仍应保留，用于稳定和无 native 依赖环境。
2. `100k` 开始，推荐显式选 `faiss`。
3. `sqlite_vec` 的价值在于：
   - 零外部服务
   - 继续留在 SQLite 生态里
   - 明显优于纯 Python 基线
4. `1M` 档如需交互式查询，`faiss` 是当前默认推荐。

## 下一步

- nightly 加入 compare smoke，监控 `sqlite_vec/faiss` 性能回退
- 若进入 release 阶段，在 README / HANDOFF / release checklist 明确推荐 backend
- 如需更强持久化索引，再评估 `sqlite-vec vec0` 虚表方案
