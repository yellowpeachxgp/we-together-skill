# FAQ

## 我需要 LLM API key 才能跑吗？

不需要。默认 `WE_TOGETHER_LLM_PROVIDER=mock`，可跑通 bootstrap、seed、retrieval、dialogue turn、WebUI local bridge、MCP smoke 和测试链路。

真实 LLM 是高级模式：

```bash
export WE_TOGETHER_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=...
```

或 OpenAI-compatible：

```bash
export WE_TOGETHER_LLM_PROVIDER=openai_compat
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://...
```

## WebUI 为什么还有 token 输入框？

默认使用本地 skill bridge，不需要 WebUI token。token 输入框只用于高级远程 API 模式。默认流程是：

```text
Browser -> Vite proxy -> scripts/webui_host.py -> chat_service.run_turn()
```

provider key 留在本地 CLI/runtime 环境，不由浏览器默认持有。

## WebUI 显示没有 scenes 怎么办？

说明当前 root 的 DB 可能已经 bootstrap，但还没有 active scene。请任选一种：

```bash
.venv/bin/we-together seed-demo --root <root>
.venv/bin/we-together create-scene --root <root> ...
.venv/bin/python scripts/import_narration.py --root <root> --source-name "manual" --text "..."
```

然后刷新 WebUI。

## 数据会被上传到哪里吗？

默认不会。数据在本地 SQLite：

```text
<root>/db/main.sqlite3
```

命名 tenant 在：

```text
<root>/tenants/<tenant_id>/db/main.sqlite3
```

只有在你显式配置真实 LLM provider、联邦出口或远程 API 时，才会有外部调用。

## 怎么部署或运行？

三条常见路径：

1. 本地源码：`pip install -e .`
2. CLI：`.venv/bin/we-together <subcommand>`
3. 直接脚本：`.venv/bin/python scripts/<name>.py --root <root>`

WebUI：

```bash
.venv/bin/we-together webui --root <root>
```

MCP：

```bash
.venv/bin/we-together mcp-server --root <root>
```

## 我的聊天、文本、邮件怎么导入？

| 来源 | 推荐入口 |
|---|---|
| 旁白文本 | `scripts/import_narration.py` |
| 结构化聊天文本 | `scripts/import_text_chat.py` |
| 单封 `.eml` | `scripts/import_email_file.py` |
| 文件自动判断 | `scripts/import_file_auto.py` |
| 目录批量导入 | `scripts/import_directory.py` |
| LLM 驱动候选抽取 | `scripts/import_llm.py` |
| 微信导出 | `scripts/import_wechat.py` 或 importer 模块 |
| 图片 / 音频 | `scripts/import_image.py`, `scripts/import_audio.py` |

运行前可先看脚本帮助：

```bash
.venv/bin/python scripts/import_narration.py --help
```

## 出错了去哪看？

```bash
.venv/bin/we-together graph-summary --root <root>
.venv/bin/we-together snapshot list --root <root>
.venv/bin/we-together branch-console --root <root>
.venv/bin/python scripts/invariants_check.py summary
```

WebUI bridge：

```bash
curl -s http://127.0.0.1:5173/api/runtime/status
curl -s http://127.0.0.1:5173/api/scenes
curl -s http://127.0.0.1:5173/api/summary
```

## 怎么判断文档和代码哪个可信？

优先级：

1. 当前代码和测试。
2. `scripts/self_audit.py` 与 `scripts/invariants_check.py summary`。
3. [Wiki](wiki/README.md)、[HANDOFF](HANDOFF.md)、[current-status](superpowers/state/current-status.md)。
4. 最新 synthesis ADR。
5. 历史 phase 文档和旧 README 段落。

如果冲突，以可执行验证为准。
