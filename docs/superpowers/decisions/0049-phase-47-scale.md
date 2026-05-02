---
adr: 0049
title: Phase 47 — 规模化 50-500 人
status: Accepted
date: 2026-04-19
---

# ADR 0049: Phase 47 — 规模化 50-500 人

## 状态
Accepted — 2026-04-19

## 背景
项目从 Phase 1 起锚定 4-10 人（第一阶段小社会）。vision "可扩展" 要求跨越到 50-500 人中等尺寸。当前 `seed_society_c` 只产 2-3 人，没法真测规模。

## 决策

### D1. seed_society_m.py（50 人）
- 50 persons（NAMES 循环 + 序号避重）
- 每人 3 条 relation（随机 target + 随机 core_type）
- 每人 6 条 memory（half shared / half individual）
- 10 * n 个 events（~500）
- 10 个 scenes，每个 scene 随机取 8 个 person 作 participant
- 用 `random.seed(seed_value)` 确定性

### D2. seed_society_l.py（500 人）
- 直接复用 seed_society_m 的 seed() 函数，改 n=500
- 不维护独立实现，保持合成逻辑统一

### D3. 规模化性能基线
`test_phase_47_sc.py` 里的断言：
- **50 人 retrieval**: p50 < 500ms, p95 < 1500ms
- **50 人 × 3 tick**: 总耗时 < 15s
- **integrity_audit**: seed 后图谱必须 healthy（无 dangling / orphan）

### D4. 对齐现有 schema
实测发现 seed script 需适配 `scenes(environment_json)` 和 `scene_participants(reason_json + activation_state='explicit')`——这次 seed 依照 migrations/0001 + 0002 真实列名写。

### D5. VectorIndex 规模就绪
- `sqlite_vec / faiss` backend 已在 Phase 36 里定义
- 当前 50 人规模 flat_python 完全够用（~300 条 embedding）
- 500 人规模真跑留 v0.17（需要真 sqlite-vec pip 安装）

## 版本锚点
- tests: +8 (test_phase_47_sc.py)
- 文件: `scripts/seed_society_m.py` / `scripts/seed_society_l.py`
- 测试基线：50 人 retrieval p95 < 1500ms（本机 MacBook）

## 非目标（v0.17）
- 真 500 人跑（CI 不跑）
- sqlite-vec 真 extension load
- 并发写压测（当前串行）
- N+1 query profiler

## 拒绝的备选
- 独立 500 人 seed 逻辑：维护成本 × 2，直接复用 m
- 把合成数据塞 `benchmarks/seeds/`：占仓库 space；让 CLI 即时生成
