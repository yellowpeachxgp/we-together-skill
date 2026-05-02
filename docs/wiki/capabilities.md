# 能力边界

## 已确认能做什么

以下能力有代码、测试、脚本或最近运行证据支撑：

| 能力 | 当前状态 | 入口 |
|---|---|---|
| 初始化本地图谱 | 可用，bootstrap 幂等 | `we-together bootstrap --root <root>` |
| Demo 小社会 | 可用，8 人 / 8 关系 / 3 scenes | `we-together seed-demo --root <root>` |
| Scene-grounded retrieval | 可用，包含 participants、relations、memories、states、recent_changes | `we-together build-pkg --root <root> --scene-id <id>` |
| 一轮对话演化 | 可用，输出 event / snapshot / patch | `we-together chat ...`、`dialogue-turn --user-input ... --response-text ...` 或 WebUI |
| WebUI 本地 cockpit | 可用，默认 local skill bridge；真实 graph/activity/world/review/import/chat，无 WebUI token | `we-together webui --root <root>` |
| Codex native skill family | 可用，7 个 skill | `scripts/install_codex_skill.py --family --force` |
| MCP 工具入口 | 可用，run_turn / summary / scene list / import / proactive scan 等 | `we-together mcp-server --root <root>` |
| 导入文本材料 | narration / text chat / email / directory / auto import 可用 | `scripts/import_*.py` |
| 图谱摘要与时间线 | 可用 | `graph-summary`, `timeline`, `relation-timeline` |
| snapshot / rollback / replay | 可用 | `we-together snapshot ...` |
| 身份融合与 operator-gated unmerge | 可用，人工复核后才真正改图 | `merge-duplicates`, `unmerge_gate.py`, WebUI review |
| daily maintenance / tick | 可用，可跳过 LLM | `daily-maint`, `simulate_week.py`, `simulate_year.py` |
| 世界模型 | Object / Place / Project / agent_drives / autonomous_actions 可注册、查询或展示 | `world_cli.py`, `world_service`, WebUI `/api/world` |
| Plugin registry | 可用 | `docs/plugins/authoring.md` |
| 联邦 v1.1 | 读路径、安全过滤、显式写路径 | `federation_http_server.py`, `federation_client` |

## 默认不需要什么

- 不需要 WebUI token 才能在本机 WebUI 对话。
- 不需要真实 LLM API key 才能跑完整工程链路。
- 不需要外部数据库，默认 SQLite 即可。

默认 provider 是 `mock`。它适合验证 runtime、写入链、WebUI、MCP、测试和演示。需要真实 LLM 时再配置：

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

## 高级或依赖环境的能力

| 能力 | 说明 |
|---|---|
| 真 LLM 对话 | 需要 provider 环境变量和 API key |
| sqlite_vec / faiss 向量后端 | 需要安装 `.[vector]` optional extra |
| iMessage / 微信 DB 导入 | 依赖本机数据源权限和外部解密/导出工具 |
| 飞书 / OpenAI Assistants / Claude Desktop | 需要宿主侧配置 |
| 联邦写路径 | 必须显式开启，并遵守 PII mask + visibility 过滤 |
| 长周期 simulation | 可跑，但生产成本/运行时长取决于 provider 和数据规模 |

## 当前限制

- 空 root 只有 schema 和 seeds，不会自动拥有可对话 scene。需要 `seed-demo`、`create-scene` 或导入材料。
- WebUI 默认生产路径会诚实展示 local bridge 离线或空库状态，不静默伪装成 demo。视觉/交互开发 demo 需要显式设置 `localStorage.we_together_demo_mode=1` 或 URL `?demo=1`。
- 当前 Codex 会话中的长驻 MCP 进程可能仍使用旧代码；若 `we_together_snapshot_list` 报 `no such column: scene_id`，重启 MCP 后按 strict gate 复测。新启动的 stdio MCP 已纳入严格门禁。
- `codex exec` 不适合作需要 MCP 审批或 elicitation 的交互；推荐交互式 Codex + 本地 skill family。
- 文档中旧 phase 记录仍保留为历史材料，判断当前能力时优先看 `docs/wiki/`、`docs/HANDOFF.md`、`docs/superpowers/state/current-status.md` 和代码事实脚本。

## 怎么判断某能力是否可信

优先级从高到低：

1. 当前代码和测试。
2. `scripts/self_audit.py`、`scripts/invariants_check.py summary`、MCP self-describe。
3. `docs/HANDOFF.md` 和 `current-status.md`。
4. 最新 synthesis ADR。
5. 旧 README 或历史 phase 过程文档。

如果文档和代码冲突，以代码和可执行验证为准。
