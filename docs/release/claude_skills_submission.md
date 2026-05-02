# Claude Skills 提交材料

v0.19.0 本地基线下的 Claude Skills marketplace 上架准备材料（Phase 56 / ADR 0058）。

**注意**：是否真提交由 Core Maintainer 决定；本文件只是**准备**。

## 提交前检查

- [ ] Skill 在本地可以被 Claude Desktop MCP 成功调用（见 `docs/hosts/claude-desktop.md`）
- [ ] Skill 在 Claude Code 可以被 `claude mcp add` 识别（见 `docs/hosts/claude-code.md`）
- [x] `.weskill.zip` 打包通过 `scripts/verify_skill_package.py` 验证
- [x] 所有 tool / resource / prompt 已被真实调用过至少 1 次（见 `tests/runtime/test_phase_33_skill_host.py`）

## 2026-04-23 本地证据

- `scripts/release_prep.py --version 0.19.0`：`ok: true`
- `scripts/skill_host_smoke.py --root <tmp>`：通过
- `scripts/skill_host_smoke.py --root <tmp> --tenant-id alpha`：通过
- `python -m twine check dist/we_together-0.19.0-py3-none-any.whl`：通过
- `scripts/package_skill.py pack --root . --output dist/we-together-0.19.0.weskill.zip`：默认产物元数据为 `skill_version=0.19.0` / `schema_version=0021`
- `scripts/verify_skill_package.py --package dist/we-together-0.19.0.weskill.zip`：通过

## 当前仍待外部验证

- Claude Desktop 手工接线 / 真 MCP 调用
- Claude Code `claude mcp add` 真接线验证
- marketplace 实际提交流程与审批

## 申请材料

### 1. Skill metadata

```json
{
  "name": "we-together",
  "description": "Skill-first 社会 + 世界图谱运行时。给 AI 一个可演化的数字社会：人、关系、记忆、事件、物、地点、项目统一在一个 SQLite 图谱内核中。",
  "version": "0.19.0",
  "author": "we-together maintainers",
  "license": "MIT",
  "repo": "https://github.com/yellowpeach/we-together-skill",
  "homepage": "https://github.com/yellowpeach/we-together-skill/tree/main/docs",
  "categories": ["memory", "social-graph", "agent", "skill-framework"]
}
```

### 2. 支持的 Hosts
- Claude Desktop（MCP stdio）
- Claude Code（MCP stdio）
- OpenAI Assistants（function calling）
- LangChain / Coze / 飞书 / 任意 MCP-compatible

### 3. Tool 清单（Phase 33）
1. `we_together_run_turn`：对话 turn
2. `we_together_graph_summary`：图谱 counts
3. `we_together_scene_list`：场景列表
4. `we_together_snapshot_list`：快照列表
5. `we_together_import_narration`：导入叙述
6. `we_together_proactive_scan`：主动扫描

### 4. Resources
- `we-together://graph/summary`
- `we-together://schema/version`

### 5. Prompts
- `we_together_scene_reply`

### 6. Demo 场景
参见 `docs/tutorials/family_graph.md`。

### 7. 合规与安全
- Federation Protocol v1.1 Bearer token 鉴权
- PII 自动脱敏（email/phone mask）
- visibility 过滤（is_exportable）
- 不变式 #25 跨图谱出口必须 PII mask

### 8. 许可
MIT（见 LICENSE）

## 提交流程

1. 打包：`python scripts/package_skill.py pack --root . --output dist/we-together-0.19.0.weskill.zip`
2. 验证：`python scripts/verify_skill_package.py --package dist/we-together-0.19.0.weskill.zip`
3. 提交到 Claude Skills 官方渠道（按当前 marketplace 要求；此文档无绑定具体 URL）
4. 等审批

## 审批后

- GitHub Release 加 Claude Skills 徽章
- README 顶部加徽章
- CHANGELOG 标记
- 公告社区

## 当前时点的诚实限制

本 ADR 准备材料但**不代表已提交 / 已获批**。Phase 56 做的是**流程固化**，上架与否由 Core Maintainer 单独决定。
