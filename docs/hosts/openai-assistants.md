# OpenAI Assistants 接入指南

## 1. 导出 tool spec

```bash
python scripts/demo_openai_assistant.py --root .
```

输出形如：

```json
{
  "skill_schema_version": "1",
  "openai_assistant_tools": [
    { "type": "function",
      "function": {
        "name": "we_together_run_turn",
        "description": "Run a scene-aware conversation turn.",
        "parameters": { ... JSON Schema ... }
      }
    },
    ...
  ]
}
```

## 2. 在 OpenAI Assistants 里注册

```python
from openai import OpenAI
import json, subprocess
client = OpenAI()
spec = json.loads(subprocess.check_output([
    "python", "scripts/demo_openai_assistant.py", "--root", "."
]))
assistant = client.beta.assistants.create(
    name="we-together",
    instructions="You are a we-together social graph agent.",
    model="gpt-4o",
    tools=spec["openai_assistant_tools"],
)
print(assistant.id)
```

## 3. 处理 tool calls

当 Assistant 的 run 进入 `requires_action` 状态：

```python
for tool_call in run.required_action.submit_tool_outputs.tool_calls:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    # 分派到本地 dispatcher（复用 scripts/mcp_server.py 的 _make_dispatcher）
    from scripts.mcp_server import _make_dispatcher
    from pathlib import Path
    dispatcher = _make_dispatcher(Path(".").resolve())
    result = dispatcher[name](args)
    client.beta.threads.runs.submit_tool_outputs(
        thread_id=thread.id, run_id=run.id,
        tool_outputs=[{"tool_call_id": tool_call.id,
                       "output": json.dumps(result, ensure_ascii=False)}],
    )
```

## 4. 注意事项

- OpenAI Assistants API 目前不支持 MCP resources / prompts；只用 tools 子集
- schema_version="1" 固定；v2 发布前接口稳定
- 真 key 需要 `export OPENAI_API_KEY=...`

## 5. 故障排查

- `TypeError: 'NoneType' object is not callable`：确认 `scripts/mcp_server.py` 路径能 import；需要 `sys.path.insert(0, 'src')`
- Tool 被调用但无响应：dispatcher 返回 dict 要 `json.dumps` 后传入 `submit_tool_outputs`
