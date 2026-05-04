# Claude Code 接入指南

## 1. 装 skill

```bash
git clone https://github.com/yellowpeachxgp/we-together-skill
cd we-together-skill
python -m venv .venv && source .venv/bin/activate
pip install -e .
python scripts/bootstrap.py --root .
```

## 2. 加 MCP

```bash
claude mcp add we-together -- \
  python $(pwd)/scripts/mcp_server.py \
  --root $(pwd)
```

或手动改 `~/.claude.json`：

```json
{
  "mcpServers": {
    "we-together": {
      "command": "python",
      "args": ["/abs/path/scripts/mcp_server.py", "--root", "/abs/path"]
    }
  }
}
```

## 3. 验证

在 Claude Code 里：

```
/mcp
```

应看到 `we-together (stdio)` 连接成功，6 tools + 2 resources + 1 prompt。

## 4. 常用流程

```
# 看当前图谱
let me call we_together_graph_summary

# 导入一段叙述
we_together_import_narration scene_id="scene_work" text="今天 Alice 和 Bob 讨论了发布节奏"

# 跑一次对话
we_together_run_turn scene_id="scene_work" input="下次会议定了吗"
```

## 5. 进阶

- 设环境 `WE_TOGETHER_LLM_PROVIDER=anthropic` 接真 Claude
- `scripts/simulate_week.py --ticks 7` 跑一周自动演化后再回 Claude 看

## 6. 故障排查

- `/mcp reconnect we-together` 手动重连
- `/mcp logs we-together` 看 stderr
- 检查 `scripts/mcp_server.py --root PATH` 手动跑能否打印 initialize 响应
