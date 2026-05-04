<div align="center">

# we-together

**Skill-first 的社会 + 世界图谱运行时**

不是把一段聊天记录塞进 memory cache，而是把 Person、Relation、Scene、Event、Memory、State、Object、Place、Project 放进一个可审计、可回滚、可演化的本地图谱，让 LLM 在“关系和世界”里工作。

[Wiki](docs/wiki/README.md) · [Quickstart](docs/quickstart.md) · [架构](docs/wiki/architecture.md) · [使用方法](docs/wiki/usage.md) · [能力边界](docs/wiki/capabilities.md) · [交互流程](docs/wiki/interaction-flows.md)

</div>

---

## 当前状态

当前本地基线是 `we-together 0.19.0`。项目已经具备可运行的 Skill 产品主路径：

- CLI：bootstrap、seed/import、chat、dialogue-turn、snapshot、graph-summary、maintenance、simulation。
- MCP：self-describe、invariants、graph summary、scene、snapshot、import、run-turn 等本地验证工具。
- Codex native skill family：`we-together` router + `dev/runtime/ingest/world/simulation/release` 六个子 skill。
- WebUI：默认走 local skill bridge，浏览器不需要 provider token。
- 图谱内核：event -> patch -> snapshot 写入链路，local branch / operator review 处理高风险歧义。
- 多租户：默认 root 与 `tenant-id` 路由隔离。
- 发布验证：strict E2E、package verify、open-source readiness、WebUI unit/build/visual gates。

代码事实由 `scripts/self_audit.py` 和 `scripts/invariants_check.py summary` 生成。当前自描述口径为 73 ADR、28/28 不变式覆盖、21 migrations、84 services、76 scripts。

## 一键安装

新电脑推荐入口：

```bash
curl -fsSL https://raw.githubusercontent.com/yellowpeach/we-together-skill/main/scripts/install.sh | bash
```

安装器会自动完成：

- 克隆或更新仓库到 `~/.we-together/repo`
- 创建 venv：`~/.we-together/venv`
- 安装 `we-together` CLI
- 初始化数据 root：`~/.we-together/data`
- 安装 7 个 Codex native skill 到 `~/.codex/skills`
- 写入 `~/.codex/config.toml` 的 `we-together-local-validate` MCP server
- 运行 CLI 和 Codex skill family 验收

完成后重启 Codex，然后直接问：

```text
看一下 we-together 当前状态
```

零配置边界：安装器需要系统已有 `python3 >= 3.11` 和 `git`，不会自动安装系统包管理器、Python 或 Codex 本体。

## 手动 5 分钟运行

```bash
git clone https://github.com/yellowpeach/we-together-skill
cd we-together-skill
python -m venv .venv
source .venv/bin/activate
pip install -e .

.venv/bin/we-together bootstrap --root ./data
.venv/bin/we-together seed-demo --root ./data
.venv/bin/we-together graph-summary --root ./data
```

拿到一个 active `scene_id` 后进入对话：

```bash
.venv/bin/we-together chat --root ./data --scene-id <scene_id>
```

默认 LLM provider 是 `mock`，不需要 API key。真实 provider 属于 CLI/local runtime 环境，而不是浏览器默认状态。

## WebUI

```bash
.venv/bin/we-together webui --root ./data
```

打开：

```text
http://127.0.0.1:5173
```

WebUI 默认通过 `/api/chat/run-turn` 调本地 `scripts/webui_host.py`，再进入 `chat_service.run_turn()`。浏览器不默认持有 WebUI token；token/API remote mode 只是高级部署路径。

## Codex Native Skill

一键安装路径已自动完成本节配置。手动安装或开发调试时执行：

```bash
.venv/bin/python scripts/install_codex_skill.py \
  --family \
  --force \
  --configure-mcp \
  --mcp-root ./data \
  --python-bin "$PWD/.venv/bin/python"
.venv/bin/python scripts/validate_codex_skill.py --installed --family --skill-dir ~/.codex/skills
```

交互式 Codex 中可直接显式询问：

```text
看一下 we-together 当前状态
查一下 we-together 的不变式
给我 we-together 图谱摘要
继续 we-together release 自检
```

## 核心架构

```text
import / user turn
  -> event / evidence / candidate
  -> retrieval_package
  -> SkillRequest
  -> mock or real provider
  -> dialogue_event
  -> inferred patches
  -> graph state + snapshot
```

关键约束：

- 写入优先进入 event / patch / snapshot 链路。
- 高风险身份融合、拆分和矛盾处理进入 local branch / operator review。
- 派生字段必须能从底层 events / memories 重建。
- 跨图谱出口必须做 PII mask 和 visibility 过滤。
- Skill runtime schema 版本化，破坏性变更不能 in-place 改。

## 验证

开发或发布前至少运行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/invariants_check.py summary
.venv/bin/python scripts/self_audit.py
.venv/bin/python scripts/release_strict_e2e.py --profile strict
cd webui && npm test -- --run
cd webui && npm run build
cd webui && npm run visual:check
git diff --check
```

发布包还需要：

```bash
.venv/bin/python -m build --wheel --sdist
.venv/bin/python -m twine check \
  dist/we_together-<version>-py3-none-any.whl \
  dist/we_together-<version>.tar.gz
.venv/bin/python scripts/release_prep.py --version <version>
```

## 包名约定

- GitHub repo：`we-together-skill`
- PyPI distribution：`we-together`
- Python import module：`we_together`
- Wheel/sdist prefix：`we_together`

## 当前边界

- 本地 Skill、CLI、MCP、WebUI cockpit 是当前主产品路径。
- 真实 provider 的 7/30/365 天长跑质量仍依赖外部 key、成本和运行环境。
- PyPI/GitHub Release 是否已经发布，以实际远端发布状态为准；本地通过 gate 不等于远端已经发布。
- 托管 SaaS、多用户计费、商业 SLA 和第三方安全审计不在当前本地开源包完成声明内。

## 文档入口

- [Wiki 首页](docs/wiki/README.md)
- [Quickstart](docs/quickstart.md)
- [Getting Started](docs/getting-started.md)
- [架构 Overview](docs/architecture/overview.md)
- [Codex 接入指南](docs/hosts/codex.md)
- [当前状态](docs/superpowers/state/current-status.md)
- [交接文档](docs/HANDOFF.md)
- [CHANGELOG](docs/CHANGELOG.md)
