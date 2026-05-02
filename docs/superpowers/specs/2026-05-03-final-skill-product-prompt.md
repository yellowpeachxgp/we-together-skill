# we-together 最终 Skill 产品定义与开发 Prompt

日期：2026-05-03
状态：Draft for next development command
适用对象：Codex、继任开发者、维护者、开源贡献者、宿主集成者

本文档用于回答一个严肃的产品问题：

> we-together 最终会产出一个什么样的 Skill 产品？它的细节、交互、作用、意义、体验和开源价值应该是什么？后续开发应如何围绕这个终局持续推进？

结论先行：

we-together 的最终产品不是一个单页 WebUI，不是一个向量记忆库，也不是某个宿主的插件样例。它应该成为一个 **Skill-first 的社会 + 世界图谱运行时**：让任意 LLM 宿主通过统一 Skill 协议接入一个本地优先、可审计、可回滚、可长期演化的数字社会与世界模型。

它的产品价值不在于“记住更多文本”，而在于把人、关系、场景、事件、记忆、状态、地点、物体、项目、agent drive 和长期演化都放进同一套结构化运行时，让 LLM 可以在一个可解释的社会语境中对话、推理、导入、复核、模拟和演化。

---

## 1. 当前事实基线

本节只记录已经由代码、文档或 MCP 运行态确认的事实。

### 1.1 MCP 运行态核对

通过 `we-together-local-validate` MCP 核对：

| 项 | 当前值 |
|---|---|
| name | `we-together` |
| version | `0.19.0` |
| tagline | `Skill-first 的社会 + 世界图谱运行时` |
| ADR | 73 |
| Invariants | 28 |
| Invariants covered | 28 / 28 |
| Services | 84 |
| Migrations | 21 |
| Scripts | 76 |

MCP 同时返回三支柱：

1. 严格工程化：ADR + 不变式 + 测试覆盖。
2. 通用型 Skill：Claude / OpenAI / MCP 三路 + plugin 扩展点。
3. 数字赛博生态圈：tick + 神经网格 + 遗忘 + 世界建模 + Agent 自主。

### 1.2 当前 MCP 暴露的风险与状态

当前 MCP 默认图谱摘要返回空图：

```json
{
  "tenant_id": "default",
  "person_count": 0,
  "relation_count": 0,
  "scene_count": 0,
  "event_count": 0,
  "memory_count": 0
}
```

这说明当前 MCP 连接的默认 runtime root 可能不是最近 WebUI/curl E2E 中 seed 过的 root，或默认 tenant 尚未初始化。它不否定系统能力，但会影响“打开即有体验”的产品感。

此前暴露过的 snapshot schema 漂移问题，其历史症状是：

```text
we_together_snapshot_list -> no such column: scene_id
```

当前代码中的 fresh MCP stdio 路径已修复，并已纳入 `.venv/bin/python scripts/release_strict_e2e.py --profile strict`。但交互式 Codex 会话中已挂载的长驻 MCP 进程可能仍运行旧代码；若当前会话仍复现该错误，应重启 MCP 后复测，而不是把它重新判定为代码层 blocker。

### 1.3 代码与文档确认的能力

当前仓库已经具备以下可确认能力：

| 能力 | 当前状态 | 主要入口 |
|---|---|---|
| 本地初始化 | 可用，bootstrap 幂等 | `we-together bootstrap` |
| Demo 小社会 | 可用 | `we-together seed-demo` |
| Scene-grounded retrieval | 可用 | `we-together build-pkg` |
| 一轮对话演化 | 可用 | `chat_service.run_turn()` / `we-together chat` / WebUI |
| Event -> Patch -> Snapshot | 已闭合 | `dialogue_service` / `patch_service` / `patch_applier` |
| SkillRuntime v1 | 已版本化 | `runtime/skill_runtime.py` |
| Claude/OpenAI adapter | 可用 | `runtime/adapters/` |
| MCP server | 可用 | `we-together mcp-server` |
| Codex native skill family | 已安装结构和验证脚本 | `codex_skill/`, `scripts/install_codex_skill.py` |
| WebUI local bridge | 已成为默认通道；默认不静默注入 demo | `we-together webui`, `scripts/webui_host.py` |
| Operator review | 已有 local branch resolve 路径，operator note 会进入 resolve reason | WebUI / `branch_resolver_service` |
| 世界模型 | Object / Place / Project / agent_drives / autonomous_actions 可注册、查询或展示 | `world_service`, `world_cli.py`, WebUI `/api/world` |
| Tick / drift / decay / dream | 有服务和脚本入口 | `daily-maint`, `simulate_week.py`, `simulate_year.py` |
| 多租户 | 已贯穿大量 CLI / host / maintenance 入口 | `tenant_router` |
| Plugin registry | 已有扩展点 | `src/we_together/plugins/` |
| Packaging | `.weskill.zip` 打包可用 | `package_skill.py` |

### 1.4 不应伪装成完成的事项

以下事项不能在产品文案中写成“已完全生产可用”：

- 真 LLM 7 天、30 天、365 天长期样本运行。
- PyPI / GitHub Release / 远端发布已经完成。
- 所有 importer 都达到高保真真实世界生产级。
- WebUI 已达到最终产品体验。
- 当前已挂载的长驻 MCP 进程一定已经重启到最新代码。
- 空 root 打开 WebUI 就自然呈现完整可理解的产品旅程。

---

## 2. 产品身份

### 2.1 一句话定义

we-together 是一个本地优先、可审计、可回滚、可长期演化的 **社会 + 世界图谱 Skill 运行时**，用于让 LLM 宿主在结构化社会语境中对话、记忆、模拟和自我维护。

### 2.2 不是这些东西

we-together 不是：

- 仅保存聊天历史的 memory 插件。
- 仅做 RAG 的向量检索库。
- 只服务 Claude、Codex、OpenAI 任一单一宿主的专用插件。
- 单纯的 WebUI 可视化玩具。
- 没有审计链的“自动写库”系统。
- 把人压缩成 prompt 的人格卡生成器。

### 2.3 是这些东西

we-together 应该是：

- 一个通用 Skill 产品。
- 一个社会图谱内核。
- 一个世界状态运行时。
- 一个事件优先的图谱演化引擎。
- 一个可解释的长期 agent memory / world state 层。
- 一个面向开源社区的可运行研究基线。
- 一个让人类 operator 能参与高风险复核的 cockpit。

---

## 3. 最高产品约束

来自 `docs/superpowers/vision/2026-04-05-product-mandate.md`，并结合当前代码事实，最终产品必须遵守三条最高约束。

### 3.1 A 支柱：严格工程化

任何能力进入主线前必须具备：

1. 明确设计或 ADR。
2. 明确 schema / service / runtime 边界。
3. 明确测试覆盖。
4. 明确失败路径。
5. 明确可审计证据。

工程判断：

- 不允许只写 demo，不写测试。
- 不允许只写文档，不落代码证据。
- 不允许绕过 event / patch / snapshot 改图谱。
- 不允许新增“纸面不变式”。
- 不允许破坏 SkillRuntime v1 schema。

### 3.2 B 支柱：通用型 Skill

最终产物必须能被多个宿主调用：

- Codex native skill。
- Claude Desktop / Claude Code style skill。
- OpenAI-compatible assistant / agent runtime。
- MCP server。
- CLI。
- Local WebUI bridge。
- 后续第三方插件和 importer。

WebUI 是入口之一，不是产品内核。浏览器默认不持有 provider token。默认交互必须走当前 CLI / local bridge / tenant SQLite / provider environment。

### 3.3 C 支柱：数字赛博生态圈

最终产品不仅要“记住”，还要“演化”：

- relation drift。
- state decay。
- memory condensation。
- forgetting / archive / reactivate。
- local branch / operator review。
- tick / simulation。
- world object / place / project。
- autonomous action with source trace。
- dream cycle。
- activation trace / neural mesh。

这些能力必须保持可解释、可逆、可预算控制。

---

## 4. 目标用户

### 4.1 第一类：个人使用者

目标：

- 把自己的长期对话、口述材料、项目状态和关系上下文整理为本地社会图谱。
- 用任意 LLM 宿主和这个图谱对话。
- 看见系统为什么记住、为什么联想到、为什么建议某个行动。

核心体验：

- 不需要先理解数据库。
- 不需要浏览器填 provider token。
- 可以从 WebUI 直接 bootstrap / seed demo / import narration。
- 可以看到 graph、activity、snapshot、review queue。
- 可以在高风险身份拆分、冲突合并时人工确认。

### 4.2 第二类：AI 应用开发者

目标：

- 需要一个比“向量库 + chat history”更强的 long-term memory / social graph runtime。
- 希望能在 Claude、OpenAI、Codex、MCP、local CLI 之间复用同一套状态。
- 需要测试、ADR、不变式和 schema，避免 agent memory 系统不可控。

核心体验：

- `pip install -e .` 后 5 分钟跑通。
- `we-together bootstrap -> seed-demo -> build-pkg -> chat` 有稳定闭环。
- SkillRequest / SkillResponse 可直接 adapter 到自己的宿主。
- importer / provider / service / hook 可通过 plugin registry 扩展。

### 4.3 第三类：研究者和开源贡献者

目标：

- 研究长期 agent memory、社会模拟、世界模型、可回滚图谱演化。
- 需要一个可跑、可测试、可复现实验结果的基线项目。
- 需要对比 Mem0 / Letta / LangMem 等不同方向。

核心体验：

- ADR 和 invariant 清楚说明系统约束。
- benchmark / simulation / self-audit 可复现。
- 真实能力和未完成项不混淆。
- Good First Issues、plugin authoring、host examples 清晰。

### 4.4 第四类：团队和社区维护者

目标：

- 把团队知识、项目历史、协作关系、决策链做成本地可审计图谱。
- 在保护隐私的前提下跨工具使用。
- 对高风险信息合并、遗忘、导出进行人工治理。

核心体验：

- 多租户隔离明确。
- PII mask / visibility 过滤可用。
- operator review 可控。
- federation write path 默认关闭，显式开启。

---

## 5. 最终产品体验

### 5.1 第一次打开

理想路径：

1. 用户安装项目。
2. 用户运行：

```bash
we-together webui --root ./data
```

3. 浏览器打开 cockpit。
4. WebUI 自动检测 local bridge：

```json
{
  "mode": "local_skill",
  "token_required": false
}
```

5. 如果 root 为空，WebUI 明确给出三条操作：

- Bootstrap：初始化 schema。
- Seed demo：体验 Society C 小社会。
- Import narration：导入自己的第一段材料。

6. 用户完成任一条路径后，WebUI 进入真实 cockpit。静态 demo mode 只在显式 `?demo=1` 或 `localStorage.we_together_demo_mode=1` 时启用。

### 5.2 核心 cockpit

最终 WebUI 应是“操作舱”，不是 marketing page。

建议主视图：

1. **Run**：当前 scene 对话，显示 retrieval context、response、event_id、snapshot_id。
2. **Graph**：Person / Relation / Memory / Scene / State / Object / Place / Project 图谱视图。
3. **Activity**：events / patches / snapshots 时间线。
4. **Review**：local branch、identity conflict、unmerge candidate、contradiction queue。
5. **World**：objects / places / projects / agent drives / autonomous actions。
6. **Invariants**：ADR、invariant、test refs、当前通过状态。
7. **Settings**：root、tenant、provider mode、advanced remote token。

视觉方向：

- 扁平化、低噪声、强信息密度。
- 可以保留 Liquid Glass 风格，但不能牺牲可读性。
- 核心是 cockpit，不是装饰页。
- 数据必须是真实 runtime state；demo mode 只用于显式视觉/交互开发开关，不作为默认生产路径。

### 5.3 CLI 体验

CLI 是产品的根入口。

理想路径：

```bash
we-together bootstrap --root ./data
we-together seed-demo --root ./data
we-together graph-summary --root ./data
we-together build-pkg --root ./data --scene-id <scene_id>
we-together chat --root ./data --scene-id <scene_id>
```

CLI 必须保证：

- 输出能被人读懂。
- 错误能明确说明下一步。
- 空 root、无 scene、schema 漂移、tenant 不合法等都不能以 traceback 作为用户体验。
- 所有高风险写入走 patch。

### 5.4 Codex / MCP 体验

目标体验：

```text
用户：看一下 we-together 当前状态
Codex：自动命中 we-together-dev，读取 local-runtime，调用 MCP self-describe 和代码文档，返回当前事实。

用户：给我 we-together 图谱摘要
Codex：自动命中 we-together-runtime，优先调用 MCP graph summary，必要时补充本地 DB 检查。

用户：帮我导入一段 we-together 材料
Codex：自动命中 we-together-ingest，使用本地 skill / MCP import，不要求浏览器 token。
```

Codex skill family 的最终质量标准：

- router 边界清晰。
- dev / runtime / ingest / world / simulation / release 子 skill 不互相抢任务。
- 每个 skill 首步读取 `local-runtime.md`。
- 对 graph / invariant / self-describe 优先 MCP。
- 对代码、测试、文档直接用 repo root。
- 不从 `~` 开始全盘搜索。

### 5.5 Open source 安装体验

目标：

```bash
git clone https://github.com/yellowpeach/we-together-skill
cd we-together-skill
python -m venv .venv
source .venv/bin/activate
pip install -e .
we-together bootstrap --root ./data
we-together seed-demo --root ./data
we-together webui --root ./data
```

5 分钟内用户应看到：

- 版本信息。
- active scenes。
- graph nodes / edges。
- 可运行对话。
- event / patch / snapshot 生成。
- review queue 即使为空也解释清楚。

---

## 6. 核心交互闭环

### 6.1 导入闭环

```text
source material
  -> importer
  -> raw_evidence
  -> candidates
  -> fusion / branch decision
  -> patches
  -> graph state
  -> snapshot
```

产品含义：

- 用户导入材料后，不只是获得文本索引。
- 系统生成可审计 evidence、candidate 和 patch。
- 低置信冲突不应直接污染主图谱。
- operator 可以复核 high-risk candidate。

### 6.2 对话闭环

```text
scene_id + user_input
  -> retrieval_package
  -> SkillRequest
  -> adapter
  -> LLM or mock
  -> SkillResponse
  -> dialogue_event
  -> inferred patches
  -> snapshot
```

产品含义：

- 对话不是孤立聊天，而是图谱演化事件。
- 每次输出都能追溯到 scene、retrieval package 和后续 patch。
- mock provider 也必须跑通完整写入链。

### 6.3 复核闭环

```text
contradiction / identity ambiguity
  -> local_branch
  -> candidates
  -> operator review
  -> selected candidate
  -> effect patches
  -> branch closed or remains open on failure
```

产品含义：

- 系统可自动提出候选，但不能对高风险身份拆分自作主张。
- operator 的选择必须进入审计链。
- 错误选择应可回滚或通过对称操作修正。

### 6.4 长期演化闭环

```text
tick
  -> relation drift
  -> state decay
  -> safe branch auto resolve
  -> merge / forgetting / condensation
  -> dream / autonomous action where gated
  -> snapshot / metrics / sanity
```

产品含义：

- 数字社会不是静态知识库。
- 关系和状态会随事件变化。
- 长期维护必须可预算、可解释、可回滚。

### 6.5 世界模型闭环

```text
object / place / project
  -> scene grounding
  -> entity links
  -> events
  -> active_world_for_scene
  -> LLM response context
```

产品含义：

- “世界”不是装饰字段。
- 地点、物体、项目应进入 scene-grounded context。
- agent 的行动必须能追溯到 drive / memory / trace。

---

## 7. 架构终局

### 7.1 分层

```text
Hosts
  CLI / Codex Skill / MCP / WebUI / Claude / OpenAI / Plugins

Runtime
  SkillRequest / SkillResponse / adapters / prompt composer

Context
  retrieval_package / activation / scene policy

Services
  ingestion / chat / patch / snapshot / branch / world / tick / federation

Storage
  SQLite tenant DB / file artifacts / optional vector backends

Governance
  ADR / invariants / tests / self-audit / release checks
```

### 7.2 数据主权

默认原则：

- 本地 SQLite 为主。
- provider token 留在 CLI/runtime 环境。
- 浏览器默认不持有 token。
- federation write path 默认关闭。
- 跨图谱出口必须 PII mask + visibility 过滤。

### 7.3 Skill 协议

`SkillRequest` 和 `SkillResponse` 是关键产品资产。它们必须保持：

- JSON 可序列化。
- schema_version 明确。
- 破坏性变更必须升 v2。
- 不绑定任何单一 LLM SDK。
- adapters 只做宿主翻译，不改变核心语义。

### 7.4 插件生态

最终扩展点应覆盖：

- Importer plugin。
- Provider plugin。
- Service plugin。
- Hook plugin。
- WebUI panel extension。
- Host adapter extension。

原则：

- 核心不能为某个 importer / provider 硬编码。
- plugin 必须声明能力、输入输出契约、测试样例。
- plugin 不能绕过 event-first 写入链。

---

## 8. 最终能为用户实现什么

### 8.1 已经接近能稳定实现

- 本地启动一个可运行社会图谱。
- 导入 narration / chat / email / directory 等材料。
- 创建 person / relation / memory / scene。
- 基于 scene 构建 retrieval package。
- 通过 mock 或真实 provider 跑一轮对话。
- 把对话落为 event、patch、snapshot。
- 在 WebUI 里查看 graph、events、patches、snapshots、world、branches。
- 使用 Codex native skill family 进行开发态和运行态查询。
- 使用 MCP 查询 self-describe、graph summary、invariants。

### 8.2 下一阶段应补强后可以明确承诺

- 空 root 到首次成功对话的完整引导。
- MCP snapshot list 与 schema 对齐。
- WebUI 中完整展示 invariant / ADR / test refs。
- WebUI 中 review candidate 的解释、diff、影响范围、失败原因。
- WebUI 中 graph node drilldown。
- WebUI 中 tenant / root / provider 状态更透明。
- Release package 的端到端验收。

### 8.3 更长期可以成为独特优势

- 可视化长期社会演化。
- 多 agent 共享底层图谱并保留私有/共享过滤。
- 真 provider 长期 simulation 成本与质量报告。
- 联邦图谱交换与隐私治理。
- 研究级 benchmark：memory correctness、identity merge safety、relation drift sanity、agent autonomy traceability。
- 插件市场式 importer/provider 生态。

---

## 9. 对 GitHub 开源社区的价值

### 9.1 提供一个不同于现有 memory 项目的方向

很多项目把 memory 做成：

- embedding store。
- chat history summarizer。
- profile facts。
- agent workspace notes。

we-together 提供的方向是：

- 社会图谱。
- 事件优先演化。
- 可回滚 patch。
- operator-gated ambiguity。
- scene-grounded retrieval。
- world model。
- long-run tick。
- invariant-driven engineering。

这对开源社区的价值是：给 agent memory 一个更强的结构化参照系。

### 9.2 提供可复制的工程范式

开源项目常见风险是 demo 很强、工程约束很弱。we-together 可以展示一种更严格的 AI runtime 开发方式：

- 每个关键约束进入 invariant registry。
- 每个 invariant 绑定真实 test refs。
- 每个大阶段有 synthesis ADR。
- self-audit 汇总代码事实。
- release 前做 package / host smoke / visual / curl E2E。

### 9.3 提供本地优先与隐私优先基线

对个人和团队而言，关系、记忆、项目历史是高敏数据。we-together 的默认路线应坚持：

- 本地 SQLite。
- 本地 bridge。
- provider token 不进浏览器。
- federation 显式开启。
- PII mask。
- 多租户隔离。

这比默认云端 SaaS memory 更适合开源社区试验和自托管。

### 9.4 提供研究和应用之间的桥

we-together 可以连接：

- AI companion / personal AI。
- Agent memory。
- Knowledge graph。
- Social simulation。
- Digital twin / world model。
- Human-in-the-loop governance。
- Local-first tools。

它的开源意义在于把这些方向落到一个可运行项目，而不是停留在论文或概念图。

---

## 10. 产品质量标准

### 10.1 最低可发布标准

Release candidate 前必须满足：

- `we-together version` 与 package version 一致。
- `scripts/self_audit.py` 数字与文档一致。
- `scripts/invariants_check.py summary` 显示 28/28 covered，或新增 invariant 全部覆盖。
- `pytest -q` 通过。
- WebUI focused pytest 通过。
- WebUI build 通过。
- WebUI visual check 通过。
- curl E2E 覆盖 runtime status、scenes、graph、chat run-turn、events、patches、snapshots。
- MCP self-describe / graph summary / invariants / scene list / snapshot list 可用。
- `.weskill.zip` 打包与 verify 通过。
- `.venv/bin/python scripts/release_strict_e2e.py --profile strict` 通过。

### 10.2 体验质量标准

用户不应遇到：

- 空 root 不知道下一步。
- WebUI 要求填 token 才能默认对话。
- bridge 离线时假装真实 runtime 在线。
- graph 无数据但无解释。
- review queue 无候选但无状态说明。
- patch / snapshot 写入失败但 UI 显示成功。
- CLI 出现裸 traceback 作为普通用户错误。

### 10.3 文档质量标准

文档必须区分：

- 已完成。
- 已有代码路径但需强化体验。
- 依赖真实 provider 或外部环境。
- 后续愿景。

不能把未来愿景写成当前事实。

---

## 11. 关键风险与下一阶段优先级

### 11.1 P0：运行态一致性

问题：

- Fresh MCP stdio 已通过 strict gate；但长驻旧 MCP 进程可能仍需重启。
- MCP 默认 graph summary 为空，可能和 WebUI/curl E2E root 不一致。

下一步：

- 将 MCP 重启/刷新步骤写入宿主使用说明。
- 统一 MCP 默认 root / tenant 和 local-runtime 的显示。
- 给 MCP graph summary 增加 root / db_path / tenant context 输出。

### 11.2 P0：空库 onboarding

问题：

- 产品最重要的第一印象是“我打开后下一步做什么”。

下一步：

- WebUI 空库引导要形成单一明确流程。
- CLI 错误信息要指向 bootstrap / seed-demo / import。
- Wiki quickstart 与 UI 文案保持一致。

### 11.3 P1：WebUI cockpit 深化

下一步：

- Graph node detail drawer。
- Timeline diff。
- Patch status and failure reason。
- Snapshot restore preview。
- Branch candidate comparison。
- Invariant health panel。
- Tenant/root/provider status strip。

### 11.4 P1：开源产品包装

下一步：

- 更新 README 的“当前事实”到 v0.20 cockpit。
- 增加 screenshots / GIF / demo run artifacts。
- 增加 contributor map。
- 增加 release checklist 到 wiki。
- 明确 project roadmap。

### 11.5 P2：研究级可信度

下一步：

- 真 LLM sample run。
- 长期 simulation artifact。
- memory correctness eval。
- identity merge/unmerge eval。
- benchmark compare 报告稳定化。

---

## 12. 后续开发路线建议

### Node 1：Runtime coherence and MCP host refresh

目标：

- MCP、CLI、WebUI 使用同一 root / tenant 心智模型。
- self-describe、summary、scene、snapshot、invariants 在 fresh host 中都可用。
- 交互式宿主能清楚知道何时需要重启 MCP。

交付：

- MCP 输出 tenant/root context。
- MCP restart / refresh 指南。
- MCP smoke tests。
- 文档同步。

### Node 2：First-run product path

目标：

- 新用户 5 分钟内从空 root 到真实对话和可见图谱。

交付：

- WebUI first-run guide。
- CLI first-run guide。
- seed/import state refresh。
- no-scene UX。
- curl E2E 固化。

### Node 3：Operator cockpit

目标：

- 让人类 operator 能看懂并处理高风险歧义。

交付：

- Branch detail。
- Candidate diff。
- Effect patches preview。
- Resolve failure display。
- Audit timeline。

### Node 4：Open-source release hardening

目标：

- GitHub 用户能安装、运行、理解、贡献。

交付：

- README refresh。
- Wiki release guide。
- screenshots。
- `.weskill.zip` verify。
- GitHub issue templates 和 good first issues 更新。

### Node 5：Long-run evidence

目标：

- 把“数字社会长期演化”从架构能力变成可展示证据。

交付：

- 7-day mock run artifact。
- optional real-provider sample。
- cost report。
- evolution visual report。
- known limitations。

---

## 13. 面向下一阶段的 Master Prompt

下面是一段可直接给 Codex 或继任 agent 使用的开发 prompt。它用于约束下一阶段长工作流。

```text
你正在开发 we-together-skill。

项目终局：
we-together 是一个 Skill-first 的社会 + 世界图谱运行时，不是普通 memory 插件，不是单一宿主 WebUI，也不是向量缓存。它应让 CLI、Codex native skill、MCP、WebUI、Claude/OpenAI adapters 和 plugin ecosystem 共享同一个本地优先、可审计、可回滚、可长期演化的社会/世界图谱。

最高约束：
1. 严格工程化：所有关键能力必须有代码、测试、ADR/文档或自审证据；不得绕过 event -> patch -> snapshot 写图谱。
2. 通用型 Skill：核心 runtime 不绑定单一宿主；SkillRequest/SkillResponse schema v1 不得原地破坏，破坏性变更必须升 v2。
3. 数字赛博生态圈：长期演化、神经网格激活、世界建模、agent autonomy、tick、dream、forgetting、review 都必须可解释、可逆、可预算控制。

当前基线：
- version: 0.19.0
- ADR: 73
- invariants: 28 / 28 covered
- migrations: 21
- services: 84
- scripts: 76
- WebUI 默认走 local skill bridge，浏览器不默认持有 token
- provider token 属于 CLI/local runtime environment
- fresh MCP stdio self-describe / snapshot_list 可用；长驻旧 MCP 进程可能需要重启
- 默认 MCP graph summary 可能为空，必须明确 root/tenant context

下一阶段优先事项：
1. 统一 MCP / CLI / WebUI 对 root 和 tenant 的显示、默认值和错误信息。
2. 将 MCP 重启/刷新与 snapshot smoke 写入宿主文档。
3. 强化 first-run UX：空 root -> bootstrap -> seed/import -> active scene -> chat -> graph/activity/snapshot 可见。
4. 深化 WebUI operator cockpit：branch candidate diff、effect patch preview、resolve failure、timeline、invariant health。
5. 更新开源文档：README、Wiki、quickstart、release checklist、capabilities、interaction flows，明确已完成/依赖环境/后续愿景。

开发规则：
- 先建立代码事实基线，再写计划。
- 优先使用 MCP 查询 graph/invariants/self-describe/runtime state。
- 代码、测试、文档以 repo root 为准，不从 home 做全盘搜索。
- 每个行为改动先补 focused tests。
- 对 WebUI 改动必须运行 frontend tests/build/visual check 或说明无法运行原因。
- 对 runtime/API 改动必须运行 pytest focused tests 和 curl E2E。
- 不回滚用户或其他 agent 的未关联改动。
- 最终汇报必须列出修改文件、验证命令、剩余风险。
```

---

## 14. 面向 GitHub README 的产品摘要 Prompt

这段可用于后续重写 README hero / repo description。

```text
we-together is a skill-first social and world graph runtime for long-lived AI agents.

Instead of treating memory as a vector cache or chat summary, it models people, relations, scenes, events, memories, states, objects, places, projects, patches, snapshots, and local review branches in one auditable SQLite-backed runtime.

It is local-first by default. CLI, MCP, Codex skills, WebUI, and Claude/OpenAI adapters all share the same event-first graph evolution chain. Browser UI does not need provider tokens for the default local path.

The project is built around ADRs, invariant tests, reversible writes, schema-versioned SkillRequest/SkillResponse objects, operator-gated ambiguity resolution, and long-run simulation primitives such as drift, decay, forgetting, world modeling, and agent drives.

Use it when you need a reproducible open-source baseline for agent memory, social graph context, local-first AI companions, world modeling, or human-in-the-loop long-term AI state.
```

---

## 15. 面向贡献者的任务 Prompt

```text
你是 we-together 的贡献者。

不要只加 feature。先确认你触碰的是哪条产品闭环：
- import loop
- chat loop
- review loop
- tick loop
- world loop
- host adapter loop
- WebUI cockpit loop
- release verification loop

然后回答：
1. 这个改动是否经过 event -> patch -> snapshot？
2. 是否影响 SkillRuntime schema？
3. 是否需要新增/更新 invariant？
4. 是否需要 ADR？
5. 是否有失败路径和测试？
6. 是否对 local-first/token ownership 有影响？
7. 是否会破坏 tenant isolation？
8. 是否会把未来愿景伪装成当前事实？

如果这些问题不能回答清楚，先写设计文档，不要直接实现。
```

---

## 16. 本文档的审计结论

### 16.1 当前项目已经做到的阶段

we-together 已经不是早期原型。它已经具备一个严肃 Skill 产品的内核：

- 统一 CLI。
- SQLite schema 和 migration。
- SkillRuntime v1。
- adapters。
- importer。
- event / patch / snapshot。
- retrieval package。
- WebUI local bridge。
- Codex skill family。
- MCP tools。
- invariant registry。
- world model。
- long-run services。

这说明下一步重点不应再只是横向堆 feature，而是把“已经有的内核”包装成更一致、更可用、更可信的产品体验。

### 16.2 当前最大短板

当前最大短板不是缺少概念，而是：

- 运行态入口一致性还需要修。
- first-run 产品旅程还需要压实。
- WebUI cockpit 需要从“能看”进化到“能判断、能操作、能解释”。
- MCP / CLI / WebUI / Wiki 需要共享同一套 root/tenant/status 语言。
- 开源发布叙事需要从“阶段堆叙”整理成“用户能立即理解的产品”。

### 16.3 最终产品判断

最终产物应该是：

1. 一个可以 `pip install` / clone 后本地运行的 Python package。
2. 一个可以打包成 `.weskill.zip` 的 skill artifact。
3. 一组 Codex native skills。
4. 一个 MCP server。
5. 一个本地 WebUI cockpit。
6. 一套 plugin / importer / provider 扩展机制。
7. 一套 ADR + invariant + tests + audit 的工程治理样板。

如果这些部分统一起来，we-together 对开源社区的意义会很清楚：

它提供一个可运行、可审计、可扩展、可长期演化的 agent social/world memory runtime，让开源社区不必在“简单向量记忆”和“不可控黑盒 agent state”之间二选一。
