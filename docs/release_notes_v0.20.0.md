# Release Notes — v0.20.0 (2026-05-05)

**Theme**: 新电脑 zero-config installer 成熟基线

**Verified baseline**: 863 passed, 4 skipped；以 `docs/superpowers/state/current-status.md` 的最新代码事实为准
**Remote**: `https://github.com/yellowpeachxgp/we-together-skill`
**Tag**: `v0.20.0`
**ADR 总数**: 73
**不变式**: 28
**Migrations**: 21

## 本版核心变化

### 1. 新电脑一键安装

新增 `scripts/install.sh`，推荐入口：

```bash
curl -fsSL https://raw.githubusercontent.com/yellowpeachxgp/we-together-skill/main/scripts/install.sh | bash
```

安装器会自动完成：

- 克隆或更新仓库到 `~/.we-together/repo`
- 创建 venv：`~/.we-together/venv`
- 安装 `we-together` CLI
- bootstrap 数据 root：`~/.we-together/data`
- 安装 7 个 Codex native skill 到 `~/.codex/skills`
- 写入 `~/.codex/config.toml` 的 `we-together-local-validate` MCP server
- 执行 CLI 与 Codex skill family 验收

### 2. Codex MCP 配置自动化

`scripts/install_codex_skill.py` 新增：

- `--configure-mcp`
- `--config-path`
- `--mcp-root`
- `--python-bin`
- `--force-mcp`

底层由 `codex_skill_support.upsert_codex_mcp_server_config()` 写入 managed TOML block。重复执行会替换同名托管 block，不会重复追加。遇到非托管同名配置时默认拒绝覆盖，需要显式 `--force-mcp`。

### 3. 发布门禁更严格

`scripts/release_prep.py` 现在检查 `v<version>` tag 是否指向当前 `HEAD`。这避免了“tag 存在但发布提交不是当前代码”的假阳性。

### 4. 文档主路径更新

README、Quickstart、Getting Started、Codex host doc、Wiki usage 已把一键安装设为新用户主路径；手动安装保留为开发和排障路径。

## 本地收口已完成

- `pyproject.toml` version = `0.20.0`
- `src/we_together/cli.py` VERSION = `0.20.0`
- Codex skill family metadata version = `0.20.0`
- 临时 HOME + `file://` repo 安装 smoke 通过
- 第二次重复安装 smoke 通过，MCP managed block 仍只有 1 个
- `pytest`: 863 passed, 4 skipped
- `release_strict_e2e.py --profile strict`: `ok: true`

## 发布状态

本次 GitHub 发布动作已完成：

- `main` 已推送到 `yellowpeachxgp/we-together-skill`
- `v0.20.0` tag 已指向发布提交
- GitHub Release 使用本文档作为 release notes

## 仍未完成 / 外部依赖

以下项仍依赖外部条件，当前不宣称已完成：

- TestPyPI / PyPI 正式发布
- 外部真实用户机器上的人工验收

## 关键文档

- [Zero Config Install Design](superpowers/specs/2026-05-05-zero-config-install-design.md)
- [Zero Config Install Plan](superpowers/plans/2026-05-05-zero-config-install.md)
- [Quickstart](quickstart.md)
- [Codex host guide](hosts/codex.md)
- [Current status](superpowers/state/current-status.md)
