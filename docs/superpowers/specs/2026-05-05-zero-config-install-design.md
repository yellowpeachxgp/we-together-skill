# Zero Config Install Design

日期：2026-05-05

## 目标

把 we-together 从“本地可验证 release-ready”推进到“新电脑一键安装可用”。用户在满足基础前置条件后，只执行一条安装命令，即可获得：

- 本地仓库副本
- 隔离 Python venv
- 可运行的 `we-together` CLI
- 初始化后的本地数据 root
- 已安装的 Codex native skill family
- 已注册的 Codex MCP server
- 安装后验收报告

## 零配置定义

“零配置”不表示脚本越权安装系统软件。它的边界是：

- 用户已有 `python3`，版本 `>=3.11`
- 用户已有 `git`
- 用户已安装或准备使用 Codex
- 安装器可写入用户目录下的 `~/.we-together` 和 `~/.codex`

若系统前置缺失，安装器必须明确失败，输出可执行的修复建议。

## 用户入口

主入口：

```bash
curl -fsSL https://raw.githubusercontent.com/yellowpeachxgp/we-together-skill/main/scripts/install.sh | bash
```

可覆盖参数：

```bash
WE_TOGETHER_REPO_URL=https://github.com/yellowpeachxgp/we-together-skill \
WE_TOGETHER_HOME="$HOME/.we-together" \
WE_TOGETHER_CODEX_HOME="$HOME/.codex" \
bash scripts/install.sh
```

本地开发 smoke：

```bash
WE_TOGETHER_REPO_URL="file://$PWD" \
WE_TOGETHER_HOME="$(mktemp -d)/we-together" \
WE_TOGETHER_CODEX_HOME="$(mktemp -d)/codex" \
bash scripts/install.sh
```

## 架构

Shell 脚本只负责外部编排：

1. 检查 `python3` / `git`
2. 克隆或更新仓库
3. 创建 venv
4. 安装 Python 包
5. 初始化数据 root
6. 调用 Python 安装工具安装 skill family 并写 MCP 配置
7. 调用 Python 验证工具做验收

可测试的配置逻辑放在 Python：

- `codex_skill_support.upsert_codex_mcp_server_config(...)`
- `scripts/install_codex_skill.py --configure-mcp`
- `scripts/validate_codex_skill.py` 继续作为验收入口

MCP TOML 写入采用受控 block：

```toml
# BEGIN we-together managed MCP server: we-together-local-validate
[mcp_servers.we-together-local-validate]
command = "/abs/path/to/venv/bin/python"
args = ["/abs/path/to/repo/scripts/mcp_server.py", "--root", "/abs/path/to/data"]
# END we-together managed MCP server: we-together-local-validate
```

重复执行时替换同名 managed block，不追加重复配置。若用户已有非托管同名配置，安装器默认不覆盖；需要 `--force-mcp` 才替换。

## 完成标准

- 临时 HOME 中可以执行安装 smoke。
- `~/.codex/skills/we-together*` 七个 skill 都存在并带 `local-runtime.md/json`。
- `config.toml` 包含正确 MCP server。
- `we-together version` 输出当前版本。
- `bootstrap --root <data>` 成功。
- `validate_codex_skill.py --installed --family` 返回 `ok: true`。
- 安装脚本可重复执行，不产生重复 MCP block。
- 文档把一键安装设为首选路径，手动路径保留为开发/排障路径。

## 非目标

- 不自动安装 Codex 本体。
- 不自动安装 Homebrew、Python、Xcode Command Line Tools。
- 不自动上传 PyPI 或 GitHub Release。
- 不把浏览器 token 作为默认交互通道；默认仍走 CLI/local bridge/MCP。
