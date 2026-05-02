---
adr: 0038
title: Phase 36 — 规模化 & 债务清理
status: Accepted
date: 2026-04-19
---

# ADR 0038: Phase 36 — 规模化与债务清理

## 状态
Accepted — 2026-04-19

## 背景
v0.13 后 `src/we_together/services/` 膨胀到 60+ 文件，14 条 migrations 中有 3 条（0007/0010/0012）怀疑低热，SkillRuntime schema 一直 in-place 扩展，VectorIndex 还没有真 backend 切换能力。这些是 A 支柱"严格工程化"的技术债。

## 决策

### D1. Service Inventory 文档
- `docs/superpowers/state/2026-04-19-service-inventory.md`
- 60+ 服务按引用密度分"🟢 核心 / 🟡 次路径 / stub"
- 结论：**无完全 dead 服务**；3 条 recall 职责不重叠；3 条 relation 职责不重叠
- 12 个 stub/低热服务的删除决策留 v0.15（需先真部署验证）

### D2. Migration 审计文档
- `docs/superpowers/state/2026-04-19-migration-audit.md`
- 所有 0001-0015 逐条列写/读路径
- 3 条低热（0007/0010/0012）均有 ≥1 写 + ≥1 读，**不是 dead schema**，全部保留
- 加强规则：新 migration 必须在 ADR 里说明写/读路径

### D3. VectorIndex backend 扩展
- `services/vector_index.py`：
  - `SUPPORTED_BACKENDS = {"auto", "flat_python", "sqlite_vec", "faiss"}`
  - `_resolve_backend(name)` 非法值抛 ValueError
  - `_require_sqlite_vec()` / `_require_faiss()`：延迟 import，缺包时 raise RuntimeError
  - 当前 `sqlite_vec` / `faiss` backend 落地为 `*_fallback`（回 flat_python），等真 lib CI 支持后升级

### D4. 规模化压测脚本
- `scripts/bench_scale.py --n 10000 --dim 32 --queries 50`
- 合成 N 条 memory + embedding → 测 build_s / query_qps
- 结果归档 `benchmarks/` 由未来执行产出

### D5. Skill schema 版本号常量测试
- `SKILL_SCHEMA_VERSION == "1"` 加入测试断言
- 任何改动都会触发红灯（保护 ADR 0034 的冻结）

### D6. LLM provider 延迟 import 验证
- `MockLLMClient` 不依赖任何真 SDK，测试保证
- 真 provider（Anthropic/OpenAI/sentence-transformers/sqlite_vec/faiss）都走延迟 import，缺包抛友好提示

## 版本锚点
- tests: +10 (test_phase_36_debt.py)
- 新文档: service-inventory / migration-audit
- 新脚本: bench_scale.py
- VectorIndex: + sqlite_vec / faiss backend stub

## 拒绝的备选
- 立即删除低热 service / migration：无证据 dead；等真部署后做
- 真接 sqlite-vec / faiss：CI 不稳定，留 v0.15
- 拆分服务层到多个子 package：引入 import path 变动，破坏 B 支柱稳定性，不值当

## 留给 v0.15+
- 把 `bench_scale.py` 输出归档到 benchmarks/
- 真接 sqlite-vec 或 faiss，重跑压测确认"N=100k 时 flat_python 不再是瓶颈"
- 若 stub 服务仍未激活，走降级 → 移至 `docs/future/`
