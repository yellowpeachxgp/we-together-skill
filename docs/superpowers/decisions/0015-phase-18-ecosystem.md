# ADR 0015: Phase 18 — 生态对接真实化

## 状态

Accepted — 2026-04-19

## 背景

Phase 9 的 adapter 都是纯函数契约，尚未"真跑"。Phase 18 让 MCP server / 飞书 bot / PyPI / Docker CI / Obsidian 五条路真实落地。

## 决策

### D1. MCP stdio server（真启动）

`scripts/mcp_server.py` 用 stdlib JSON-RPC 2.0 over stdin/stdout，实现 `initialize` / `tools/list` / `tools/call` 三方法。工具由 `runtime/adapters/mcp_adapter.build_mcp_tools()` 提供，dispatcher 绑真实 `chat_service.run_turn` 与 `graph_summary`。Claude Code 通过 `claude mcp add we-together -- python scripts/mcp_server.py --root <dir>` 接入。

### D2. 飞书 bot 实绑 chat_service

`examples/feishu-bot/server.py` 把 echo 替换为 `chat_service.run_turn`：webhook → parse → retrieval → SkillRequest → LLM → 落图谱 → 回帖。未设 `FEISHU_SIGNING_SECRET` 时跳过签名（开发态）。异常走 `[we-together error]` 友好回帖。

### D3. PyPI 发布工程

- `MANIFEST.in` 保证 migrations / seeds / prompts / benchmarks 打入 wheel
- `pyproject.toml` 加 `[tool.setuptools.package-data]` + `include-package-data = true`
- `scripts/build_wheel.sh` 一键 `python -m build`
- `docs/publish.md` checklist + testpypi 流程

### D4. Docker CI

`.github/workflows/docker.yml` on push/PR 构建镜像 + 跑 `we-together version` / usage 双 smoke，保证 Dockerfile 不退化。

### D5. Obsidian 双向同步

- `importers/obsidian_md_importer`：vault md → identity_candidates + event_candidates + relation_clues（基于 `[[wikilink]]`）
- `services/obsidian_exporter`：active persons → md 文件（含 persona / style / 关联 memories）

## 后果

### 正面
- Skill 第一次真正在非 mock 宿主跑起来（MCP + 飞书）
- 包管理三位一体：pip / Docker / PyPI checklist
- Obsidian 打开第三方笔记工具的通道

### 负面 / 权衡
- MCP 协议只实现最小子集（没有 resources / prompts method）
- 飞书真实 API 流量没压测
- Docker CI 未验证 compose 启动（只是单镜像 smoke）

### 后续
- Phase 22：MCP 加 resources/prompts；CI 加 compose smoke
- Logseq（block reference）导入可借用 Obsidian importer 骨架
