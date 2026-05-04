# we-together

> Skill-first 的社会 + 世界图谱运行时。不是给 LLM 加一层 memory，而是给 LLM 一个可演化、可审计、可回滚的数字社会。

## 当前事实

| 项 | 当前值 |
|---|---|
| 版本 | `0.20.0` |
| ADR | 73 |
| 不变式 | 28 条，28 条有测试覆盖 |
| Migrations | 21 |
| Services | 84 |
| Scripts | 76 |
| 默认 provider | `mock` |
| 默认存储 | 本地 SQLite |
| WebUI 默认通道 | local skill bridge，无需 WebUI token |

这些数字来自 `scripts/self_audit.py`、`scripts/invariants_check.py summary`、`.venv/bin/we-together --help`、`docs/HANDOFF.md` 与 `docs/superpowers/state/current-status.md`。

## 从哪里开始

1. [Wiki 首页](wiki/README.md)
2. [架构总览](wiki/architecture.md)
3. [使用方法](wiki/usage.md)
4. [能力边界](wiki/capabilities.md)
5. [交互流程](wiki/interaction-flows.md)
6. [5 分钟 Quickstart](quickstart.md)
7. [Codex 接入指南](hosts/codex.md)
8. [最终 Skill 产品定义与开发 Prompt](superpowers/specs/2026-05-03-final-skill-product-prompt.md)

## 为什么这个项目存在

常见 LLM memory 方案多把 memory 当键值或向量。we-together 的核心判断是：如果要让 Skill 持续理解一群人和一个世界，memory 不够，必须有结构化社会图谱和演化机制。

它关注：

- Person / IdentityLink / Relation / Group / Scene
- Event / Memory / State / Patch / Snapshot / LocalBranch
- Object / Place / Project
- event-first 的写入链
- retrieval package 的 scene-grounded 上下文
- tick、drift、decay、forgetting、dream 等长期演化
- Claude / OpenAI / MCP / Codex / WebUI 等宿主接入

## 三支柱

| 支柱 | 当前落点 |
|---|---|
| A 严格工程化 | ADR + 不变式 + migration + 测试 + self-audit |
| B 通用型 Skill | SkillRuntime schema + adapters + MCP + Codex native skill family + packaging |
| C 数字赛博生态圈 | 神经网格激活、世界建模、tick、Agent drives、dream cycle |

## 当前推荐运行路径

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

.venv/bin/we-together bootstrap --root ./data
.venv/bin/we-together seed-demo --root ./data
.venv/bin/we-together graph-summary --root ./data
.venv/bin/we-together webui --root ./data
```

打开 `http://127.0.0.1:5173` 后，WebUI 会走本地 skill bridge。默认不需要填写 WebUI token。

## 状态与交接

- [当前状态](superpowers/state/current-status.md)
- [交接文档](HANDOFF.md)
- [v0.20 release notes](release_notes_v0.20.0.md)
- [v0.19 release notes](release_notes_v0.19.0.md)
- [2026-05-03 final/local cockpit hardening](CHANGELOG.md#2026-05-03--final-skill-product--local-cockpit-hardening)
- [变更历史](CHANGELOG.md)

## 对比

- [vs Mem0](comparisons/vs_mem0.md)
- [vs Letta / MemGPT](comparisons/vs_letta.md)
- [vs LangMem](comparisons/vs_langmem.md)

## 贡献与扩展

- [Plugin authoring](plugins/authoring.md)
- [Good First Issues](good_first_issues.md)
- [发布检查](publish.md)
