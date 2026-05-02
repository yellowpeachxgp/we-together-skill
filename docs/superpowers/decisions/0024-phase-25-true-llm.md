# ADR 0024: Phase 25 — 真 LLM 集成（True LLM Integration）

## 状态
Accepted — 2026-04-19

## 背景
Phase 23 的 agent_runner 是 mock 协议（`{action: tool_call, tool, args}` JSON），不匹配真 Anthropic 的 `content_block.type=tool_use` / OpenAI 的 `choice.message.tool_calls`。飞书 bot 也只能收到完整回复再发，无流式。

## 决策

### D1. chat_with_tools 作为 provider 第三方法
所有 LLM Client 加 `chat_with_tools(messages, tools)` → `{text, tool_uses, stop_reason, raw}`。Anthropic/OpenAI 真解析原生 `content_block` / `tool_calls`。Mock 走 `_scripted_tool_uses` 队列。

### D2. agent_runner 优先 native，Mock 兼容
`_prefers_native(llm_client)`：
- 无 chat_with_tools → False（走 chat_json 旧路径）
- MockLLMClient + `_scripted_tool_uses` 非空 → True
- 真 provider → True

保证既有 mock 测试 0 改动即可继续通过。

### D3. chat_stream 作为第四方法
Anthropic `messages.stream()` / OpenAI `stream=True` / Mock `scripted_stream`。`chat_service.run_turn_stream` 返回 `StreamingSkillResponse`，`.finalize_turn()` 触发落图谱。

### D4. 观测 hook 可插拔
`observability/llm_hooks`: `register_hook` + `timed_call` context manager + `LangSmithStubSink`。所有 LLM 调用可被 wrap 记录 provider/method/duration/error。

## 后果
正面：真跑 Claude/OpenAI 后 agent_runner 自动切换原生协议；飞书支持流式；观测链路可延迟接 LangSmith。
负面：`chat_with_tools` / `chat_stream` 真实路径未在单元测试中跑（无 API key），只有 mock。真 SDK 升级时需要集成测试。

## 后续
- Phase 28+：tool_use content_block 里的 image / input_schema 复杂类型支持
- 真 streaming SSE 反压控制
