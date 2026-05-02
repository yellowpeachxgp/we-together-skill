# ADR 0021: Phase 23 — 真集成与生产级

## 状态
Accepted — 2026-04-19

## 背景
v0.10.0 的 349 passed 全是单元/mock 测试，没有一次"真跑完整链路"；adapter 的 tool_use 也是纯契约；没有流式；没有真 wheel 安装验证。

## 决策
### D1. tests/integration 真跑链
6 个端到端测试：bootstrap→seed→graph / ingest→snapshot→rollback / dialogue_turn / eval-relation baseline / CLI dispatch / federation round-trip。**不 mock 基础设施**，仅 mock LLM。

### D2. Agent runner tool-use 真循环
`runtime/agent_runner.run_tool_use_loop`：LLM 通过 chat_json 驱动 `{action: tool_call|respond}` 多轮循环，每步落 `tool_use_event` / `tool_result_event`（source_type='agent_runner'）。错误路径：tool handler 抛异常 → `tool_result: [ERROR]` 回喂 LLM。

### D3. chat_service.run_turn 支持 tools
`run_turn(... tools=[...], tool_dispatcher={...}, max_tool_iters=3)`：非空 tools 时走 agent_runner，否则走既有 adapter.invoke。保持向后兼容。

### D4. 流式响应
`runtime/streaming.StreamingSkillResponse`：`__iter__` 产 chunks，`.finalize()` 得 SkillResponse。`mock_stream_chunks(text, chunk_size)` 用于测试。adapter 真流式实现留给真 LLM 接入期。

### D5. wheel + 隔离安装验证
`scripts/build_wheel.sh`：venv 优先 → python3 fallback。本地产出 `we_together-0.11.0-py3-none-any.whl`，在全新 venv 安装后 `we-together version` 正确输出。pyproject + cli VERSION 同步 0.11.0。

### D6. CI 完整 workflow
`.github/workflows/ci.yml`：lint + mypy（核心模块）+ pytest + integration + eval regression gate + docker smoke。pre-commit-config.yaml：ruff + pytest fast subset。

## 后果
正面：首次真正"全链路活着"；tool_use 有真实多轮语义；wheel 可分发。
负面：流式只有 mock 骨架，真 Claude/OpenAI stream 待实现；CI 需要 GitHub 环境才能验证。

## 后续
- Phase 25+：真 streaming；PyPI 正式发布
