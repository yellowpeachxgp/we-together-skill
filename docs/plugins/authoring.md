# 编写 we-together Plugin — 快速上手

Phase 44 / ADR 0046 让第三方可以通过 Python `entry_points` 向 we-together 注册：
1. **Importer**：新的数据源（Slack / Discord / 飞书 / Notion…）
2. **Service**：自定义服务（自定义 recall / 自定义 fusion 策略）
3. **Provider**：新的 LLM / embedding / vision / audio 后端
4. **Hook**：订阅运行时事件（tick.before / tick.after / patch.applied）

核心原则：**核心 we-together 代码不为特定 importer/provider 硬编**（不变式 #23）。

## 最小示例

```python
# my_plugin/slack_importer.py

class SlackImporter:
    name = "slack_importer"
    plugin_api_version = "1"

    def run(self, *, source, db_path):
        # 读 slack export → 写 event/raw_evidence → 返回报告
        return {"imported": source, "events_created": 42}
```

## 注册到 entry_points

`pyproject.toml`：

```toml
[project.entry-points."we_together.importers"]
slack_importer = "my_plugin.slack_importer:SlackImporter"
```

4 个 group 名：
- `we_together.importers`
- `we_together.services`
- `we_together.providers`
- `we_together.hooks`

## 验证

```bash
pip install -e .                # 先装好 we-together
pip install -e /path/to/my_plugin

python scripts/plugins_list.py
```

应看到：
```json
{
  "discover": {"loaded": 1, "failed": 0},
  "status": {
    "by_kind": {
      "importer": [{"name": "slack_importer", "source": "entry_point:slack_importer", "enabled": true}]
    }
  }
}
```

## 4 类扩展点的最小协议

### Importer
```python
class YourImporter:
    name: str
    plugin_api_version: str = "1"

    def run(self, *, source: str, db_path) -> dict: ...
```

### Service
```python
class YourService:
    name: str
    plugin_api_version: str = "1"

    def invoke(self, db_path, **kwargs): ...
```

### Provider
```python
class YourProvider:
    name: str
    provider_kind: str   # "llm" / "embedding" / "vision" / "audio"
    plugin_api_version: str = "1"
```

Provider 必须实现对应 Protocol（`we_together.llm.LLMClient` / `EmbeddingClient` / `VisionLLMClient` / `AudioTranscriber`）。

### Hook
```python
class YourHook:
    name: str
    event_type: str      # "tick.before" / "tick.after" / "patch.applied"
    plugin_api_version: str = "1"

    def handle(self, payload: dict) -> None: ...
```

## API 版本

- 当前：`PLUGIN_API_VERSION = "1"`
- 破坏性变更会 bump 到 "2"，plugin 必须同时声明支持
- 加字段（新 event_type 等）属于 additive，不 bump 版本

## 错误隔离

一个 plugin 加载失败不影响其他。`discover()` 返回：
```json
{"loaded": 3, "failed": 1, "errors": [{"kind": "importer", "ref": "bad=foo:Bar", "reason": "..."}]}
```

## 禁忌

- **不要**在 plugin `__init__` 里做重 I/O；让 `run()` / `invoke()` 里做
- **不要**依赖 we-together 内部未导出的 `_private` API
- **不要**假设 discover 顺序；用 `get_by_name` 取

## 参考

- `src/we_together/plugins/__init__.py` — Protocol 定义
- `src/we_together/plugins/plugin_registry.py` — discover / register / list
- `scripts/plugins_list.py` — CLI
- ADR 0046 — 架构决策
