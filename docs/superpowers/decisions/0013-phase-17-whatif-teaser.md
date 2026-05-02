# ADR 0013: Phase 17 — 社会模拟 Teaser（What-if Simulator）

## 状态

Accepted — 2026-04-18（单 slice teaser，非完整 Phase 17）

## 背景

Phase 15 给图谱加了"回望"能力。下一步是"前瞻"。`simulation/` 目录的首个切片 SM-1 是概念验证：给定当前场景 + 假设事件，让 LLM 产出未来 30 天的预测报告。

## 决策

### D1. `simulate_what_if` 纯读取 + LLM 推演

```python
simulate_what_if(db_path, scene_id, hypothesis, llm_client=None)
  → {hypothesis, scene_id, predictions: [...], confidence}
```

**不修改图谱**。读 `build_runtime_retrieval_package_from_db` 得 retrieval_package → 提炼 participants / relations → 喂 LLM → 解析 JSON。

### D2. predictions 结构统一

每条 prediction: `{horizon_days: int, prediction: str, affected_entities: [str, ...]}`。这让后续可以有 "按 horizon 折叠" / "按 affected entity 聚合" 等二次分析。

### D3. prompt 强约束"不臆造"

system prompt 明确"严格基于给定信息，不臆造人物或关系"。这避免 LLM 输出中出现 retrieval_package 里不存在的人名。

### D4. 与 Phase 14 eval 的衔接

（未来）可以通过"放入已知真实历史事件 → 跑 what-if → 对比真实结果"来评估模拟质量。当前 teaser 不做这步。

## 后果

### 正面

- Phase 15 回望 + Phase 17 前瞻，时间轴闭环
- LLM 推演结果是纯输出，不污染图谱，可反复尝试
- 模块位于独立的 `simulation/` 包，未来扩展（conflict_predictor / scene_scripter / era_evolution）同构

### 负面 / 权衡

- LLM 质量决定推演可信度，没有任何规则守卫
- 未提供"把 predictions 喂回图谱作为 hypothetical branch"的回路（留给 Phase 17 后续）
- prompt 只有单语版本，跨语言场景下需要 i18n

### 后续

- SM-2 conflict_predictor：基于 Phase 7 U2 的 relation_conflict 做定向预测
- SM-3 scene_scripter：给定 persona + scene 生成对话脚本
- SM-4 retire_person_service：人物退场的生命周期
- SM-5 era_evolution：无输入情况下的长程自演化
