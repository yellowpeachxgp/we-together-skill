---
adr: 0048
title: Phase 46 — 多 Agent REPL（互听 + 打断 + 私聊）
status: Accepted
date: 2026-04-19
---

# ADR 0048: Phase 46 — 多 Agent REPL

## 状态
Accepted — 2026-04-19

## 背景
Phase 29 做了 PersonAgent + `turn_taking.orchestrate_multi_agent_turn` 骨架，但：
- 没有 REPL 入口
- agent 之间**互相听不到**（speak 只收 scene_summary，不收 transcript）
- 没有打断
- 没有 private 发言（公开 / 私聊区分）
- transcript 不落盘

vision 第 9.1 "多人共演"要求这些。Phase 46 补齐。

## 决策

### D1. services/multi_agent_dialogue
新的编排层（不改 turn_taking 原有 API）：
- `TranscriptEntry(speaker, speaker_id, text, audience, is_interrupt, turn_index)`
- `orchestrate_dialogue(agents, scene_summary, activation_map, turns, interrupt_threshold, private_turn_map)`
- `_visible_messages_for(agent, transcript)`：只返公开 + 涉及该 agent 的私聊
- `record_transcript_as_event(db, scene_id, transcript)` 写 `events(event_type='dialogue_event')`

### D2. 互听（agent 能看到前面发言）
每轮 speaker.speak 调用时传入 `recent_messages`，内容已经过 `_visible_messages_for` 过滤。

### D3. 打断机制
- 参数 `interrupt_threshold`
- 每轮起始时遍历非 last_speaker 的 agent，若任一 `decide_speak(..) >= threshold` 则视为打断
- `TranscriptEntry.is_interrupt = True` 标记
- `turn_state["interrupts"]` 计数

### D4. 私聊
- `private_turn_map: {turn_index: [audience_person_ids_or_names]}` 声明
- audience 为空 → 公开
- audience 非空 → 只有 audience + speaker 能看到

### D5. CLI
- `scripts/multi_agent_chat.py --scene X --turns N [--real-llm] [--record]`
- Mock LLM 默认；`--real-llm` 切 provider
- `--record` 把 transcript 作 dialogue_event 入库

## 版本锚点
- tests: +9 (test_phase_46_ma.py)
- 文件: `services/multi_agent_dialogue.py` / `scripts/multi_agent_chat.py`
- 旧 `orchestrate_multi_agent_turn` 保持不变（Phase 29 兼容）

## 非目标（v0.17）
- REPL 交互式 human 加入（当前 one-shot；真交互留以后）
- 对话 summary 服务（condense 多轮为一条 memory）
- 真 LLM 带 streaming 的 REPL
- 多 scene 并发对话

## 拒绝的备选
- 修改 `orchestrate_multi_agent_turn` 加互听：破坏 Phase 29 测试；新增分开函数更安全
- 把 transcript 存 memory 表：dialogue_event 语义更准（memory 是蒸馏后对象）
- interrupt 优先级引入新 priority 算法：复用 `decide_speak` 分数足够
