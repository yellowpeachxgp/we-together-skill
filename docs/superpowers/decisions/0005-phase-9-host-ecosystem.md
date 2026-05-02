# ADR 0005: Phase 9 — 宿主生态（Host Ecosystem）

## 状态

Accepted — 2026-04-18

## 背景

Phase 5 已经建立 SkillRequest/SkillResponse + Claude/OpenAI 两套 adapter，但距离 `product-mandate.md` 第 B 条 "通用型 Skill，支持任意 LLM Runtime / Skill Host" 仍有差距：

1. adapter 不支持 tool_use（只做单轮 chat 翻译）
2. 没有多轮 agent loop，chat_service.run_turn 只跑一步
3. 没有可分发的 skill 包，宿主无法把 we-together 作为独立组件装载
4. 没有飞书/LangChain/Coze/MCP 等具体宿主的 adapter

## 决策

### D1. SkillRequest.tools：跨宿主 tool_use 抽象

`SkillRequest` 新增 `tools: list[dict]` 字段，每条契约 `{name, description, input_schema}`（借鉴 Anthropic 命名）。Claude adapter 直接透传；OpenAI adapter 翻译为 `{type: 'function', function: {name, description, parameters}}`。tools 为空时 payload 不包含 tools 键，保持向后兼容。

### D2. Agent loop = 最小 mock-first 循环

`services/agent_loop_service.run_turn_agent`：
- LLM 通过 `chat_json` 返回 `{action: tool_call|respond, tool, args, text}`
- tool_call 时查 `tool_dispatcher: dict[name, Callable]` 本地分发
- 每步落 events 表（tool_use_event / tool_result_event / dialogue_event，source_type='agent_loop'）
- max_iters 兜底防止无限循环

单元测试全部走 MockLLMClient，无网络依赖。CLI `scripts/agent_chat.py` 内置 graph_summary / retrieval_pkg 两个示例工具。

### D3. Skill 可分发包 .weskill.zip

`packaging/skill_packager.pack_skill` 用 Python 内置 zipfile，把 SKILL.md + db/migrations + db/seeds + scripts + src 打包。manifest.json 含 format_version / skill_version / schema_version / files。`unpack_skill` 反向还原。无需外部依赖。

### D4. 四个新宿主 adapter 作为纯转换函数

- **飞书**: `feishu_adapter.parse_webhook_payload` / `format_reply` / `verify_signature`（HMAC-SHA256）
- **LangChain**: `WeTogetherLCTool` 包装 `run_turn_fn`，以 `.name` / `.description` / `.run()` 暴露为 LC Tool
- **Coze/Dify**: `build_plugin_schema` / `parse_plugin_invocation`
- **MCP**: `build_mcp_tools` 生成 MCP server tool 列表

所有 adapter 保持纯函数，**不 import 任何平台 SDK**，测试无网络。

## 后果

### 正面

- 单次改 `SkillRequest` 即可为所有 adapter 加新字段
- agent loop 让 chat 能真正调工具（graph_summary / retrieval_pkg 等）
- skill 包可以脱离本仓库运行（前提是宿主能执行 Python 脚本）
- 新增宿主 adapter 的成本是一个纯函数 + 几个测试，不影响核心图谱

### 负面 / 权衡

- adapter 目前只覆盖"核心转换"，真实宿主可能需要处理 OAuth / refresh token / pagination，这部分尚未实现
- agent loop 的 action 契约是 JSON mock-first，真实 Claude tool_use 的 content_block 形态还需在 `AnthropicLLMClient` 里转换
- 打包格式随 schema 演进需要兼容性策略（目前 format_version=1）

### 后续

- Phase 10 增加真实平台 importer 后，adapter 的 reply 路径（HTTP）需要正式接通
- Phase 11 的联邦/多租户会让 SkillRequest 再加 `tenant_id`
- Phase 12 会增加 tool_use 的 tracing 字段（trace_id 贯穿 agent loop）
