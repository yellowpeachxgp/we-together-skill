---
adr: 0029
title: Phase 29 — Multi-Agent Society
status: Accepted
date: 2026-04-19
---

# ADR 0029: Phase 29 — 多智能体社会

## 状态
Accepted — 2026-04-19

## 背景
此前 chat_service 是"单一 Skill 视角对话"。Phase 29 让图谱中的多个 person 真正成为**独立 agent**，每个 agent 拿自己的私有 memory + 共享场景 context，由 turn-taking 调度发言。

## 决策

### D1. PersonAgent 抽象（MA-1）
- `agents/person_agent.py: PersonAgent.from_db(db, person_id, llm_client)`
- 字段: `person_id / primary_name / private_memories / shared_memories / llm`
- `from_db` 直接读 `memories ⨯ memory_owners`，按 `is_shared` + `owner_id` 过滤 private vs shared
- `speak(scene_summary)` → 把私有 + 共享 memory 压成 prompt → LLM → text

### D2. Turn-taking 调度（MA-3）
- `agents/turn_taking.py: next_speaker(agents, activation_map, turn_state)` → 选 score 最高者；全 0 返回 None
- `decide_speak(context, turn_state)` 是 agent 自评分接口；活跃度 + 上轮是否发言可作输入
- `orchestrate_multi_agent_turn(agents, scene_summary, activation_map, turns)` → 跑 N 轮，写 transcript

### D3. 私有 vs 共享分离（MA-2）
- private = `is_shared=0 AND memory_owners.owner_id == person_id`
- shared = `is_shared=1` 且 owner 包含 `person_id`
- 不引入新表；纯查询过滤

## 不变式增量
（参见 ADR 0033 第 17 条）

## 版本锚点
- tests: +4 (test_phase_29_30_31_32 中的 PersonAgent / turn-taking 块)
- 旧 chat_service / agent_runner 不变；多 agent 是新加层

## 拒绝的备选
- 把 PersonAgent 强行接入 SkillRuntime：runtime 默认是单 agent 视角，多 agent 是上层编排，不下沉
- 共享 memory 重复存储 per-agent：违反"图谱即真理"原则
