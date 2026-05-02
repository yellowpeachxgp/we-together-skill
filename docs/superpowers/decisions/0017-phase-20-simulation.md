# ADR 0017: Phase 20 — 社会模拟完整版

## 状态

Accepted — 2026-04-19

## 背景

Phase 17 只落地了 SM-1 what-if teaser。Phase 20 补完 SM-2/3/4/5 四个方向，让 `simulation/` 目录能真正承担"向前推演"的职责。

## 决策

### D1. SM-2 Conflict predictor

`simulation/conflict_predictor.predict_conflicts`：
- 先走 `relation_conflict_service.detect_relation_conflicts` 拿近期反转历史
- 把 details 喂 LLM，产 `{predictions: [{relation_id, horizon_days, probability, reason}]}`
- 无冲突历史时短路，不调 LLM

### D2. SM-3 Scene scripter

`simulation/scene_scripter.write_scene_script`：
- 读 retrieval_package 的 participants + persona
- LLM 产 `{script: [{speaker, text}]}` N 轮对话
- 不改图谱，脚本作为输出

### D3. SM-4 Retire person

`services/retire_person_service.retire_person`：
- memories 标 inactive（供后续 cold archive）
- 该 person 相关 relations.strength ×= 0.3（fade）
- scene_participants 标 `latent`
- persons.status = 'retired'
- 二次调用返回 `{already_retired: True}` 幂等

### D4. SM-5 Era evolution

`simulation/era_evolution.simulate_era(days)`：
- 循环 N 天，每天跑 drift + decay + pair_interaction（遍历 top 5 active scenes）+ recall
- 产出 daily_reports 列表
- 受单日 pair_budget 约束，总 pair events 有限

### D5. 新 CLI `scripts/simulate.py` 合一

`predict-conflicts / scene-script / retire-person / era` 四子命令。接入 `we-together simulate <sub>`。

## 后果

### 正面
- `simulation/` 从 SM-1 单点扩到 5 个能力，能承担"社会推演"叙事
- Retire 给图谱生命周期补上"退场"
- Era 给长程自演化提供 dev 观察窗口

### 负面 / 权衡
- conflict_predictor 的质量严重依赖 LLM；无 baseline
- retire_person 是"软删除"，没提供"复活"对称函数（留作 Phase 22）
- era 的 daily tick 只实现了 4 步，完整 daily_maintenance 的 LLM 步骤未接（避免 CI 成本）

### 后续
- Phase 22：`revive_person` + 完整 era 接 daily_maintenance
- 模拟评估：把真实历史事件前半段给出，跑 simulate，对比后半段真实
