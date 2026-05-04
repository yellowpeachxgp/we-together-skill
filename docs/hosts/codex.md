# Codex 接入指南

## 1. 一键安装

推荐：

```bash
curl -fsSL https://raw.githubusercontent.com/yellowpeach/we-together-skill/main/scripts/install.sh | bash
```

该脚本会：

- 克隆或更新 `~/.we-together/repo`
- 创建 `~/.we-together/venv`
- 初始化 `~/.we-together/data`
- 安装 7 个 Codex native skill
- 写入 `~/.codex/config.toml` 的 MCP server
- 执行安装后验收

完成后重启 Codex。

## 2. 手动前置

```bash
git clone https://github.com/yellowpeach/we-together-skill
cd we-together-skill
python -m venv .venv && source .venv/bin/activate
pip install -e .
python scripts/bootstrap.py --root ./data
```

## 3. 配置 Codex MCP

确保 `~/.codex/config.toml` 中存在：

```toml
[mcp_servers.we-together-local-validate]
command = "/绝对路径/we-together-skill/.venv/bin/python"
args = ["/绝对路径/we-together-skill/scripts/mcp_server.py", "--root", "/绝对路径/we-together-skill/data"]
```

手动自动写入：

```bash
.venv/bin/python scripts/install_codex_skill.py \
  --family \
  --force \
  --configure-mcp \
  --mcp-root ./data \
  --python-bin "$PWD/.venv/bin/python"
```

## 4. 安装 Codex native skill family

如果只想安装 skill 而不写 MCP：

```bash
.venv/bin/python scripts/install_codex_skill.py \
  --family \
  --force \
  --configure-mcp \
  --mcp-root ./data \
  --python-bin "$PWD/.venv/bin/python"
```

会安装 7 个本地 skill：

- `we-together`
- `we-together-dev`
- `we-together-runtime`
- `we-together-ingest`
- `we-together-world`
- `we-together-simulation`
- `we-together-release`

## 5. 校验

```bash
.venv/bin/python scripts/validate_codex_skill.py --installed --family --skill-dir ~/.codex/skills
```

应返回整族 `ok: true`，并列出 7 个 skill 的独立校验结果。

如需采集交互式命中证据，可再执行：

```bash
.venv/bin/python scripts/capture_codex_skill_evidence.py --session-root ~/.codex/sessions --limit 20
```

该脚本会扫描 `~/.codex/sessions/**/*.jsonl`，归纳已安装 skill 的路径读取、`local-runtime.md` 读取与相关 commentary 命中。

## 6. 使用方式

从任意目录启动交互式 Codex：

```bash
codex
```

示例中文请求：

- `看一下 we-together 当前状态`
- `继续 we-together 的 Phase 72`
- `查一下 we-together 的不变式`
- `给我 we-together 图谱摘要`
- `帮我导入一段 we-together 材料`
- `看一下 we-together tenant/world 状态`
- `跑一下 we-together simulate_year`
- `做一个 we-together release 自检`

## 7. 当前限制

- 推荐路径是 **交互式 `codex`**
- `codex exec` 不适合需要 MCP 审批 / elicitation 的调用
- skill 触发是启发式，不是硬路由；显式带上 `we-together` 语义的中文请求命中率最高
- 如果本地环境里残留了错误的 Codex API key 并导致认证失败，可临时清掉该环境变量再启动交互式 Codex 排障；这不是 we-together 的默认启动方式。
- 安装器不会自动安装 Python、git 或 Codex 本体；缺失时会明确失败。
