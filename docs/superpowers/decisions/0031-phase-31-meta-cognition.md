---
adr: 0031
title: Phase 31 — Meta-cognition (Contradiction Detection)
status: Accepted
date: 2026-04-19
---

# ADR 0031: Phase 31 — 元认知（矛盾检测）

## 状态
Accepted — 2026-04-19

## 背景
图谱长大后必然出现"前后说法冲突"的 memory（Alice 昨天在北京 / Alice 昨天在上海）。Phase 31 让系统具备**自检能力**：embedding 相似度筛候选 → LLM 判定是否矛盾 → 输出报告（不自动改图，留给上层 patch 决策）。

## 决策

### D1. Two-stage detection（MC-1）
- `services/contradiction_detector.py`:
  - `find_candidate_pairs(db, similarity_min=0.7)`：joins memories ⨯ memory_embeddings，cosine 配对
  - `judge_contradiction(a, b, llm_client)` → `{is_contradiction, confidence, reason}` JSON
  - `detect_contradictions(db, ...)` → `{candidate_count, contradiction_count, contradictions[]}`
- 早返回也保留 `contradiction_count: 0`（schema 一致性，便于上层无条件取键）

### D2. 不自动改图
- 检测器不写表；报告经人工 / 上层 patch 决策再修复
- 与 patch_applier 解耦，避免"自动错改"

### D3. Benchmark + Eval（MC-6）
- `benchmarks/contradiction_groundtruth.json`：v1，3 对 groundtruth（地点冲突 / 习惯冲突 / 不冲突）
- `eval/contradiction_eval.py: run_contradiction_eval(bench, llm_client)` → `{tp, fp, tn, fn, precision, recall}`
- mock LLM 下 P/R 都是 1.0；真 LLM 留作离线评估

## 不变式（参见 ADR 0033）
检测类服务**只读不写**；任何修复都必须走 patch。

## 版本锚点
- tests: +4 (find_candidate_pairs / judge / integration / benchmark eval)
- 新文件: contradiction_detector.py / eval/contradiction_eval.py / benchmarks/contradiction_groundtruth.json

## 拒绝的备选
- 自动 mark 冲突 memory 为 inactive：风险太大（可能两条都对，上下文不同）
- 用 NLI 模型本地推理：依赖 transformers，留作 v0.14
