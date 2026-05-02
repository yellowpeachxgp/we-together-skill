# MCP server example

## 启动

```bash
we-together bootstrap --root ~/.we-together
we-together seed-demo --root ~/.we-together

python scripts/mcp_server.py --root ~/.we-together
```

## 接入 Claude Code

```bash
claude mcp add we-together -- \
  python /abs/path/scripts/mcp_server.py --root /abs/path/data
```

然后在 Claude Code 对话里，Claude 会看到两个 tool：

- `we_together_graph_summary` — 返回当前图谱统计
- `we_together_run_turn` — 在指定 scene 里跑一轮对话

## 协议

简化版 JSON-RPC 2.0 over stdio（每行一个 message）：

- `initialize` — 握手
- `tools/list` — 返回 tool schema
- `tools/call` — 执行 tool，返回 `content: [{type:"text", text:"<json>"}]`

## 扩展

要加更多 tool：
1. 在 `runtime/adapters/mcp_adapter.py` 的 `WE_TOGETHER_MCP_TOOLS` 追加 schema
2. 在 `scripts/mcp_server.py` 的 `_make_dispatcher` 加对应 handler
3. 可选：用 `build_mcp_tools(extra=[...])` 动态扩展
