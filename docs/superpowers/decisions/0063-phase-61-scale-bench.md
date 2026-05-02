---
adr: 0063
title: Phase 61 — 规模化真压测归档
status: Accepted
date: 2026-04-19
---

# ADR 0063: Phase 61 — 规模化真压测

## 状态
Accepted — 2026-04-19

## 背景
`VectorIndex(backend='flat_python')` 定义了 SUPPORTED_BACKENDS，但**从未真跑过 10k / 50k 规模**。C 支柱需要规模化证据。

## 决策

### D1. 真跑 + 归档
- 10k 规模：QPS 65.6，per-query 15.23ms（MacBook baseline）
- 50k 规模：QPS 12.7，per-query 78.88ms
- 两份 JSON 归档到 `benchmarks/scale/`

### D2. Scale Report
`docs/superpowers/state/2026-04-19-scale-bench-report.md` 记录：
- 基线表
- bottleneck 分析（50k 时 1.6μs / cosine）
- v0.19 下一步（sqlite-vec 真接）

### D3. 测试强制
`tests/services/test_phase_61_sp.py`：
- `test_scale_archive_exists`：必须有归档
- `test_scale_archive_10k_format` / `50k_format`：格式校验
- `test_vector_index_backends_still_available`：stub 未消失
- `test_scale_report_exists`：报告存在

## 版本锚点
- tests: +5 (test_phase_61_sp.py)
- 归档: `benchmarks/scale/bench_10k_*.json` + `bench_50k_*.json`
- 报告: scale-bench-report.md

## 非目标（v0.19）
- 真 sqlite-vec / FAISS 接入
- 100k / 1M 规模
- 并发 query 压测

## 拒绝的备选
- 把 bench 结果塞 test assertion：硬编基线脆弱，归档 + 事后看即可
