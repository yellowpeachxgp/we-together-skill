# we-together Getting Started

从零到第一次 `run_turn` 的本地路径。当前基线为 v0.20.1。

## 0. 一键安装

新电脑推荐入口：

```bash
curl -fsSL https://raw.githubusercontent.com/yellowpeachxgp/we-together-skill/main/scripts/install.sh | bash
```

它会安装本地 repo、venv、CLI、数据 root、Codex skill family，并写入 Codex MCP server。完成后重启 Codex，直接问：

```text
看一下 we-together 当前状态
```

前置条件：

- `python3 >= 3.11`
- `git`
- Codex 本体由用户自行安装

## 1. 手动开发安装

```bash
python --version
git clone https://github.com/yellowpeachxgp/we-together-skill
cd we-together-skill
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

确认 CLI：

```bash
.venv/bin/we-together version
.venv/bin/we-together --help
```

## 2. Bootstrap

```bash
.venv/bin/we-together bootstrap --root .
```

这会在 `db/main.sqlite3` 应用当前 migrations。v0.20.1 代码事实为 21 条 migrations。

## 3. 安装一个示例社会

```bash
.venv/bin/we-together seed-demo --root .
.venv/bin/we-together graph-summary --root .
```

如果你不 seed 或导入材料，DB 可以健康存在，但没有 active scene 时不能运行 scene-grounded 对话。

## 4. 跑一次对话

先拿到一个 scene id，然后：

```bash
.venv/bin/we-together chat --root . --scene-id <scene_id>
```

进入 REPL 后输入：

```text
早上好，请根据当前 scene 回复。
```

这条链路会走 retrieval -> SkillRequest -> LLM/mock -> dialogue event -> inferred patches -> snapshot。

如果你已经有外部回复文本，要把一轮对话落盘，用：

```bash
.venv/bin/we-together dialogue-turn \
  --root . \
  --scene-id <scene_id> \
  --user-input "早上好" \
  --response-text "早上好，我会根据当前 scene 回应。"
```

## 5. 打开 WebUI

```bash
.venv/bin/we-together webui --root .
```

打开：

```text
http://127.0.0.1:5173
```

WebUI 默认走 local skill bridge。浏览器不需要 WebUI token，provider 和 key 从本地 CLI 环境继承。

## 6. 看图谱和指标

```bash
.venv/bin/we-together graph-summary --root .
.venv/bin/we-together snapshot list --root .
.venv/bin/python scripts/dashboard.py --root . --port 7780
```

dashboard 打开：

```text
http://127.0.0.1:7780
```

## 7. 跑维护或模拟

```bash
.venv/bin/we-together daily-maint --root . --skip-llm
.venv/bin/python scripts/simulate_week.py --root . --ticks 7 --budget 10
```

## 8. 接入 Claude / Codex / MCP

一键安装已自动完成 Codex skill family 和 MCP 配置。手动安装：

Codex：

```bash
.venv/bin/python scripts/install_codex_skill.py \
  --family \
  --force \
  --configure-mcp \
  --mcp-root . \
  --python-bin "$PWD/.venv/bin/python"
.venv/bin/python scripts/validate_codex_skill.py --installed --family --skill-dir ~/.codex/skills
```

MCP server：

```bash
.venv/bin/we-together mcp-server --root .
```

Codex/host 配置里通常会把该入口注册为 `mcp_server`，例如本地 Codex skill family 的 `local-runtime.md` 会记录 `mcp_server_name=we-together-local-validate`。如果宿主里已经挂载了旧 MCP 进程，升级代码后需要重启宿主或 MCP 进程，再复测 snapshot/list 类工具。

更多宿主说明：

- [Codex](hosts/codex.md)
- [Claude Code](hosts/claude-code.md)
- [Claude Desktop](hosts/claude-desktop.md)
- [OpenAI Assistants](hosts/openai-assistants.md)

## 9. 故障排查

- **sqlite3 no such table**：先跑 `bootstrap`。
- **WebUI 提示没有 scenes**：先跑 `seed-demo`、`create-scene` 或导入材料。
- **真实 LLM 不工作**：检查 `WE_TOGETHER_LLM_PROVIDER` 和对应 API key。
- **Codex skill 没命中**：请求里显式带 `we-together`，并优先使用交互式 Codex。

## 延伸

- [Wiki 首页](wiki/README.md)
- [架构总览](wiki/architecture.md)
- [能力边界](wiki/capabilities.md)
- [当前状态](superpowers/state/current-status.md)
