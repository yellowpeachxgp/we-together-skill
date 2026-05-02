# ADR 0003: SkillRuntime 协议与宿主适配器

## 状态

Accepted — 2026-04-18

## 背景

Phase 3 末期我们拥有了 `build_runtime_retrieval_package_from_db` 这个 Python dict 形式的检索包，但距离产品最高约束的"通用型 Skill 必须能运行在 Claude / Codex / 任意 LLM Runtime 上"还有两个工程缺口：

1. retrieval_package 的字段结构是 Python 内部契约，没有面向宿主 LLM 的 prompt 组装规范
2. 各 Skill 宿主（Anthropic Messages、OpenAI Chat Completions、飞书机器人、Coze）对 system/messages/tool 的字段结构要求不同

如果让每种 importer / agent / CLI 各自拼 prompt，就会把宿主逻辑散布到整个代码库，违反"严格工程化"和"通用型 Skill"两条最高约束。

## 决策

### D1. 引入 SkillRuntime 协议层

`src/we_together/runtime/skill_runtime.py` 定义两个平台无关 dataclass：

- `SkillRequest(system_prompt, messages, retrieval_package, scene_id, user_input, metadata)`
- `SkillResponse(text, speaker_person_id, supporting_speakers, usage, raw)`

这两个结构是所有 Skill 宿主与本系统之间的唯一 I/O 边界。核心代码永远操作这两个对象，不直接构造 Claude/OpenAI 的 payload。

### D2. prompt_composer 作为 retrieval_package → SkillRequest 的唯一路径

`runtime/prompt_composer.py` 的 `build_skill_request()` 负责：

- 调用 `compose_system_prompt(package)`，把场景、环境约束、参与者、关系、记忆、状态、最近变更、response_policy 七段格式化为单一 system prompt
- 调用 `compose_messages(user_input, history)`，产生 OpenAI 风格的 messages 序列
- 将 retrieval_package 原始对象也保留在 SkillRequest 中，以备 adapter 需要

这保证 "上下文 → prompt" 的所有规则都集中在一处。

### D3. adapters/ 目录是唯一可以依赖宿主结构的地方

- `adapters/claude_adapter.py`：system 作为 Anthropic `system` 字段，messages 只含 user/assistant
- `adapters/openai_adapter.py`：system 作为 messages 列表的第 0 条，整体仍符合 OpenAI Chat Completions

每个 adapter 实现两个方法：
- `build_payload(request)`：纯函数，不碰 LLM
- `invoke(request, llm_client)`：通过 `LLMClient` Protocol 调 LLM，把结果归一化为 SkillResponse

### D4. 端到端入口：chat_service.run_turn

一次对话轮次的合规执行路径：

```
retrieval_package
    ↓ prompt_composer.build_skill_request
SkillRequest
    ↓ adapter.invoke(llm_client)
SkillResponse
    ↓ record_dialogue_event + infer_dialogue_patches + apply_patch_record
图谱更新
```

REPL 入口 `scripts/chat.py` 只是此函数的薄包装。

### D5. 降级与 mock-first

- `MockLLMClient` 提供 scripted_responses / scripted_json，所有单元测试默认用它
- `factory.get_llm_client(provider=None)` 按环境变量 `WE_TOGETHER_LLM_PROVIDER` 切换
- 真实 provider（`AnthropicLLMClient`、`OpenAICompatClient`）在实例化时才延迟 import 第三方 SDK

## 后果

### 正面

- 新增 Skill 宿主只需实现一个 adapter，不影响图谱演化和候选层
- 所有 prompt 组装逻辑集中在 `prompt_composer`，单点演进
- 测试永远不依赖网络/API Key，CI 无需 secrets

### 负面 / 权衡

- adapter 层目前只支持 "单轮 chat"；多轮 agent loop / tool use 需要后续扩展
- `SkillResponse.raw` 字段暴露了一点 provider 差异，但这是可接受的 metadata 透出

### 后续

- 当接入飞书机器人 / 腾讯文档 / 钉钉助手等宿主时，新增对应 adapter
- Phase 8 计划增加 `tool_use` 支持：SkillRequest 扩展 `tools` 字段，adapter 翻译为各平台 tool schema
- 考虑引入 `response_format`（json mode）的跨平台抽象
