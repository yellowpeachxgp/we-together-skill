# Claude Desktop 接入指南

## 1. 安装 we-together

```bash
git clone https://github.com/yellowpeach/we-together-skill ~/src/we-together
cd ~/src/we-together
python -m venv .venv && source .venv/bin/activate
pip install -e .
python scripts/bootstrap.py --root .
```

## 2. 配置 MCP server

打开 Claude Desktop 的 MCP 设置（`Settings → Developer → Edit Config`）。
在 `mcpServers` 下加一条：

```json
{
  "mcpServers": {
    "we-together": {
      "command": "python",
      "args": [
        "/Users/你的用户名/src/we-together/scripts/mcp_server.py",
        "--root",
        "/Users/你的用户名/src/we-together"
      ],
      "env": {
        "WE_TOGETHER_LLM_PROVIDER": "mock"
      }
    }
  }
}
```

> 如果要走真 Claude SDK 生成，把 `WE_TOGETHER_LLM_PROVIDER` 改为 `anthropic` 并 `env` 加 `ANTHROPIC_API_KEY`。

## 3. 重启 Claude Desktop

重启后在聊天里应该能看到 `we-together` 工具出现。试：

```
使用 we_together_graph_summary 工具告诉我当前图谱有多少人
```

## 4. 暴露能力

- **tools**：run_turn / graph_summary / scene_list / snapshot_list / import_narration / proactive_scan
- **resources**：graph/summary（JSON）/ schema/version
- **prompts**：scene_reply 模板

详见 `scripts/mcp_server.py` 实现。

## 5. 故障排查

| 症状 | 排查 |
|------|------|
| 工具不出现 | 检查 Claude Desktop 日志 `~/Library/Logs/Claude/`，确认 stdout 行格式对 |
| `ImportError: no module named we_together` | `pip install -e .` 忘记在 venv 里做 |
| `db not found` | 忘记 `python scripts/bootstrap.py --root .` |
| 回复是空的 | provider 未配 key；或 scene_id 不存在（先 `scripts/create_scene.py`） |

## 6. 语义

SkillRuntime 请求/响应 v1 schema 冻结（ADR 0034 / 不变式 #19）。此文档只需适配 MCP 协议层变化；SkillRequest 字段**additive-only**。
