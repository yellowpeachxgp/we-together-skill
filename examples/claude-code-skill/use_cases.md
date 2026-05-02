# 3 个典型 skill 用例

## 用例 1: 朋友圈"最近谁在做什么"

适用场景：你想知道你认识的人最近整体状态。

```bash
we-together graph-summary --root ~/.we
we-together timeline --person-id person_abc --root ~/.we --since 2025-01
```

we-together 会返回：近期 events / active relations / 最近凝练出的 memory / persona drift 轨迹。

## 用例 2: "帮我分析昨晚和 Alice 的对话"

适用场景：刚导入一段对话记录，想看图谱怎么解读。

```bash
we-together ingest text-chat --root ~/.we --file /path/to/chat.txt
we-together graph-summary --root ~/.we
we-together build-pkg --root ~/.we --scene-id <newly_created_scene>
```

输出的 retrieval_package 含 active_relations、relevant_memories、current_states 和 response_policy。

## 用例 3: "如果 Bob 搬离了小组会怎样"

适用场景：社会模拟 teaser（Phase 17）。

```bash
we-together what-if --root ~/.we --scene-id <work_scene> --hypothesis "Bob 搬离小组"
```

LLM 基于当前图谱 + hypothesis 产出"未来 30 天可能发生的 scene/relation 变化"预测报告。
