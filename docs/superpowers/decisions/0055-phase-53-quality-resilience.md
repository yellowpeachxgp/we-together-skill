---
adr: 0055
title: Phase 53 — 质量与韧性（OTel / property / fuzz / nightly）
status: Accepted
date: 2026-04-19
---

# ADR 0055: Phase 53 — 质量与韧性

## 状态
Accepted — 2026-04-19

## 背景
v0.16 已 594 tests，但多数是单元 + 浅集成。要真跑一年不崩，需要：
- 可选 **OpenTelemetry** tracing
- **property-based** 验证（Hypothesis）
- **fuzz** 测试（恶意 / NULL / 超大输入）
- **nightly smoke**（自动 simulate + audit + bench）

## 决策

### D1. observability/otel_exporter 可选
- `enable(endpoint, service_name)` 尝试 import opentelemetry；失败时 NoOp
- `span(name, attributes)` context manager，未 enable 时 yield None
- `set_attribute` / `status` NoOp 安全
- **不强依赖**：未装 SDK 代码仍可正常运行

### D2. property / fuzz 测试
- Hypothesis 可选：未装时 pytest.skip
- 两个 property：`mask_pii` 幂等、`_forget_score` 对 days 单调
- Fuzz：
  - 未知 operation 的 patch 必须 raise
  - 空 summary + 0 relevance memory 不崩
  - 5000 条 memory 下 `full_audit` < 5s
  - 200 条随机 unicode memory 不崩

### D3. nightly smoke workflow
`.github/workflows/nightly.yml`：
- cron: UTC 02:00 每日跑
- 流程：install → bootstrap → seed 50 → simulate_week 7d → dream_cycle → fix_graph audit → bench_scale 1000
- artifact 上传 tick_runs/

### D4. 100-scale 即时回归
`test_vector_index_100_items_fast`：断言 100 条 embedding build < 1s（每次 CI 都跑）

## 版本锚点
- tests: +11 + 2 skipped (test_phase_53_qr.py)
- 文件: `observability/otel_exporter.py` / `.github/workflows/nightly.yml`

## 非目标（v0.18）
- 真 OTLP exporter 部署（endpoint 配置留用户）
- 真 Hypothesis 全覆盖（当前只覆盖 2 个 property）
- property-based 的 patch_applier 遍历（运算组合爆炸）
- 1M 规模（留 v0.18 + sqlite-vec 真接）

## 拒绝的备选
- 强制 Hypothesis 依赖：增重；optional skip 更友好
- 用 pytest-benchmark：引入依赖；time.perf_counter 够用
- 立即接 prometheus_client：观察 OTel 优先
- 把 nightly 改为 self-hosted：外部贡献者无法跑
