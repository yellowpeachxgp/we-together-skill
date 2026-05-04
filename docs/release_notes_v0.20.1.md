# Release Notes — v0.20.1 (2026-05-05)

**Theme**: 人工端到端验收补丁，修正文档路径与统一 CLI surface 的落差

**Verified baseline**: 以本轮 E2E 输出和 `docs/superpowers/state/current-status.md` 为准
**Remote**: `https://github.com/yellowpeachxgp/we-together-skill`
**Tag**: `v0.20.1`
**ADR 总数**: 73
**不变式**: 28
**Migrations**: 21

## 本版核心变化

### 1. 统一 CLI 导入入口补齐

人工测试发现文档期望用户能执行：

```bash
.venv/bin/we-together import-narration ...
```

但 `src/we_together/cli.py` 未暴露部分高频 import scripts。本版补齐：

- `import-narration`
- `import-text-chat`
- `import-email-file`
- `import-file-auto`
- `import-directory`
- `import-auto`

### 2. Snapshot 文档命令兼容

人工测试发现文档里的命令：

```bash
.venv/bin/we-together snapshot list --root ./data
```

旧 argparse 只接受 `--root ./data snapshot list` 这种全局参数顺序。本版让 `list` / `rollback` / `replay` 都兼容子命令后的 `--root` / `--tenant-id`。

### 3. 回归测试补齐

新增 `tests/runtime/test_webui_cli.py` 覆盖：

- 统一 CLI 是否暴露常用 importer
- `snapshot list --root <root>` 是否可执行

## 本轮验证

- 公开远端 `curl | bash` 一键安装 smoke
- 重复安装 smoke，确认 MCP managed block 替换而非重复追加
- Codex skill family validate
- fresh MCP stdio
- CLI bootstrap / seed-demo / graph-summary / import-narration / dialogue-turn / snapshot / tenant
- WebUI local bridge curl
- WebUI Vitest / build / visual check
- `scripts/release_strict_e2e.py --profile strict`
- focused pytest release suite
- `twine check`

## 仍未完成 / 外部依赖

- TestPyPI / PyPI 正式发布
- 外部真实用户机器上的人工验收
