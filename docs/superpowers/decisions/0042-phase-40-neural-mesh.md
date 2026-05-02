---
adr: 0042
title: Phase 40 — 神经网格式激活（Activation Traces + Plasticity）
status: Accepted
date: 2026-04-19
---

# ADR 0042: Phase 40 — 神经网格式激活

## 状态
Accepted — 2026-04-19

## 背景
`product-mandate` 明写"神经单元网格式激活传播特征"，`runtime/activation.py` 只做了**静态权重**的有界激活传播，没有：
- 激活痕迹（trace）
- 可塑性（plasticity）：高频激活 → 权重上升
- 多跳激活（multi-hop）

vision 提了但代码未兑现。Phase 40 把"神经网格"从隐喻变实体。

## 决策

### D1. migration 0016 activation_traces
新表 `activation_traces`：
- `(from_entity_type, from_entity_id) → (to_entity_type, to_entity_id)`
- `weight / trace_type / hop_distance / scene_id / activated_at`
- 追加式，**不 update**；按 from/to/scene 建索引
- trace_type 枚举：`relation_traversal / scene_participation / event_mention / retrieval_hit / multi_hop`

### D2. activation_trace_service
- `record` / `record_batch`
- `count_by_pair(from, to, since_days)`
- `query_path(from, to, max_hops)` DFS 找路径
- `multi_hop_activation(start, max_hops, decay)` BFS + 权重衰减
- `apply_plasticity(min_count, strength_delta, max_strength)` 高频对 → relation.strength 上调
- `decay_traces(age_days)` 老化清理
- `recent_traces(limit)` introspection

### D3. plasticity 安全边界
- 仅对**已存在的 active relation** 生效；**不凭空造 relation**
- 通过 `entity_links(from_type='relation', relation_type='participant', to_type='person')` 关联
- `max_strength=1.0` 收敛上界
- 可塑性是**显式调用**（不 hook 到 patch_applier）；由 tick 或 runtime 按需触发

### D4. CLI introspection
- `scripts/activation_path.py --from pA --to pB --max-hops 3`
- 省略 `--to` 则返回多跳 activation_map

## 不变式（新，v0.15.0 第 21 条）
**#21**：任何激活传播机制必须可 introspect（能画出"谁激活了谁、权重多少"）。
- `recent_traces` / `query_path` / `multi_hop_activation` 任一方法必须返回可序列化结构
- 不允许"黑盒"权重调整

## 非目标（留 v0.16）
- `runtime/activation.py` 与 `activation_trace_service.record` 的自动 hook（当前是"service 提供，调用方自行决定"）
- retrieval_package 里直接带 activation_trace 字段
- trace 可视化 HTML 面板
- plasticity 反向（遗忘导致权重下降）→ Phase 41

## 版本锚点
- tests: +10 (test_phase_40_nm.py)
- 文件: migration 0016 / `services/activation_trace_service.py` / `scripts/activation_path.py`
- 收敛测试：30 次激活 + 10 轮 plasticity → strength ∈ [0.9, 1.0]

## 拒绝的备选
- 把 activation trace 写入 events 表：events 有语义负载，不该混污
- 全图 Hebbian 学习：太重；限定在 person-person relation + entity_links 足够
- 在 patch_applier 里自动 record trace：违反关注点分离
