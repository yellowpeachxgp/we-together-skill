# HANDOFF — we-together-skill 项目交接文档

> **对象**：Codex（或任一继任 AI assistant）
> **目标**：读完本文档 + [`docs/superpowers/state/current-status.md`](superpowers/state/current-status.md) 后 **5 分钟**内回到工作状态。
> **当前版本**：**v0.19.0（local）** — 本地 tag `v0.19.0` 已打；wheel/build/check 已通过。
> **代码事实补丁（2026-04-29）**：当前代码自审为 **73 ADR / 28 条不变式 / 21 migrations / 84 services / 76 scripts**；28 条不变式全部有测试覆盖；本地已起步 **Phase 72：矛盾复核 / operator-gated unmerge**，并已把 **Codex native skill family** 扩展为 **7 个本地 skill**（router + `dev/runtime/ingest/world/simulation/release`）。WebUI 现已默认走 local skill bridge，浏览器不再默认持有 WebUI token。
> **post-v0.19 local cockpit 补丁（2026-05-03）**：WebUI bridge 已扩展为本地 cockpit API，默认读取真实 graph / activity / world / branch review，并支持 WebUI 内 bootstrap、seed-demo、narration import、branch resolve；默认生产路径不静默注入 demo，demo 只在 `?demo=1` 或 `localStorage.we_together_demo_mode=1` 时启用。
> **strict gate 补丁（2026-05-03）**：`.venv/bin/python scripts/release_strict_e2e.py --profile strict` 覆盖 CLI first-run、tenant isolation、fresh MCP stdio、WebUI curl、package verify、Codex skill family validate 与 focused pytest。Fresh MCP `snapshot_list` 已通过；长驻旧 MCP 进程若仍报 `no such column: scene_id`，重启 MCP 后复测。

---

## 0. TL;DR（30 秒概览）

- **项目**：`we-together-skill` —— 一个 Skill-first 的**社会 + 世界图谱运行时**。不是给 LLM 加一层 memory，是给 LLM 一个**可演化的数字社会**。
- **三支柱**：
  - **A 严格工程化** 9.95/10（73 ADR + 28 不变式 + 当前全量 pytest 基线 + 反身能力）
  - **B 通用型 Skill** 9.8/10（Claude Skills / OpenAI Assistants / MCP 三路宿主 + plugin 扩展点）
  - **C 数字赛博生态圈** 9.7/10（tick + 神经网格 + 世界建模 + Agent 自主 + 年度真跑证据）
- **Codex 状态**：本机 `~/.codex/skills/` 下已安装 `we-together`、`we-together-dev`、`we-together-runtime`、`we-together-ingest`、`we-together-world`、`we-together-simulation`、`we-together-release` 七个原生 skill；交互式 Codex 在 `~` 下对显式中文请求已能自动进入 `we-together` 语境，并可用 `capture_codex_skill_evidence.py` 归档命中证据。`codex exec` 仍不适合需要 MCP 审批的调用。
- **验证链路状态**：`verify_skill_package.py` 与 `skill_host_smoke.py` 的历史假阳性已修复，当前 release / host smoke 证据可信度更高；WebUI local bridge 已有后端、前端、build、visual 和 curl E2E 证据；严格发布门禁为 `.venv/bin/python scripts/release_strict_e2e.py --profile strict`。
- **工作模式**：用户每次说**"继续推进任务"** / **"进入无人值守连续推进模式"** / **"至少小一百个 task"** → Codex 进入**大批量 TaskCreate → 按 phase 交付 → commit → ADR → bump → tag** 的长工作流。
- **绝对规则**：新功能不能破坏当前不变式注册表；任何新 migration / 破坏性变更必须先写 ADR。

---

## 1. 项目当前状态（v0.19.0 本地收口后）

| 项 | 值 |
|---|---|
| git tag | `v0.19.0`（local） |
| pyproject version | `0.19.0` |
| cli VERSION | `0.19.0` |
| pytest 基线 | **853 passed + 4 skipped**，~45s 本机 |
| ADR 总数 | 73（`docs/superpowers/decisions/0001-0073`）|
| 不变式 | **28 条**（`src/we_together/invariants.py`）|
| Migrations | **21 条**（`db/migrations/0001..0021`）|
| Benchmarks | 10（含 `year_runs/` `scale/` `tick_runs/`）|
| Test coverage | 约 90% |

**快速自检**：
```bash
cd we-together-skill
.venv/bin/python -m pytest -q         # 期望 853 passed, 4 skipped
.venv/bin/python scripts/self_audit.py        # 整体自描述
.venv/bin/python scripts/invariants_check.py summary  # 28 条不变式 100% 覆盖
.venv/bin/we-together version         # we-together 0.19.0
.venv/bin/python scripts/install_codex_skill.py --family --force
.venv/bin/python scripts/validate_codex_skill.py --installed --family --skill-dir ~/.codex/skills
.venv/bin/python scripts/capture_codex_skill_evidence.py --session-root ~/.codex/sessions --limit 20
```

---

## 2. 项目 Vision（永远以这个为最高约束）

来自 [`docs/superpowers/vision/2026-04-05-product-mandate.md`](superpowers/vision/2026-04-05-product-mandate.md) 和 `docs/superpowers/specs/2026-04-05-we-together-core-design.md`：

**三条最高优先级约束**：
1. **A 严格工程化推进** — 规划 / 跟进 / 归档 / 约束四者缺一不可。不得"先做出来再说"。
2. **B 通用型 Skill** — 产物是**可在任意 LLM Runtime 运行的 Skill**，不是某宿主专属脚本。
3. **C 数字赛博生态圈** — 自适应 / 可扩展 / 神经单元网格式激活传播 / 可持续演化。

**核心术语**（任何改动都应基于这套词汇）：
- Person / IdentityLink / Relation / Group / Scene / Event / Memory / State
- v0.17 扩展：**Object** / **Place** / **Project** / **agent_drives** / **autonomous_actions**
- v0.18 扩展：**Invariant Registry** / **Reflexive API**（`self_introspection`）

**设计原则**（贯穿所有 phase）：
- 工程优先（结构化 > 自然语言）
- 统一社会图谱内核（不是四套系统）
- 默认自动化 + 默认可逆
- 事件优先于直接改写（event → patch → snapshot）
- 歧义局部化（只用 `local_branch`，不做整图分叉）

---

## 3. 当前 28 条不变式（历史文档曾写 30；以代码为准）

**完整列表见** [`src/we_together/invariants.py`](../src/we_together/invariants.py) + [`docs/superpowers/state/2026-04-19-invariants-coverage.md`](superpowers/state/2026-04-19-invariants-coverage.md)。

**工程铁律**（最高优先 — 每条都有强制测试）：
- **#1** 事件优先（先写 event 再改图谱）
- **#18** 主动写入必须经预算 + 偏好门控
- **#19** SkillRuntime schema 必须版本化（破坏性变更需 v2，不 in-place 改）
- **#20** tick 写入必须可回滚
- **#22** 写入必须对称撤销（merge↔unmerge / archive↔reactivate）
- **#23** 扩展点必须通过 plugin registry 注册（核心代码不硬编）
- **#24** 时间敏感服务必须读 `graph_clock.now()` 优先
- **#25** 跨图谱出口必须 PII mask + visibility 过滤
- **#26** 世界对象（object/place/project/event）必须有明确时间范围
- **#27** Agent 自主行为必须可解释（必须追溯到 drive/memory/trace）
- **#28** 派生字段必须可从底层 events/memories 重建

历史 ADR 中曾讨论过 #29 / #30 治理候选；当前 `src/we_together/invariants.py` 只注册 28 条，不应把候选编号当作当前不变式引用。

**新增不变式的协议**：
1. 先在 `src/we_together/invariants.py` 的 `INVARIANTS` list 加入
2. 必须挂至少 1 个真实存在的 test_refs
3. 在对应 synthesis ADR 里明确引用
4. 跑 `pytest tests/invariants/` 全绿

---

## 4. 代码地图（哪里有什么）

```
we-together-skill/
├── src/we_together/
│   ├── __init__.py
│   ├── cli.py                  # VERSION = "0.19.0"，CLI 入口
│   ├── invariants.py           # 28 条不变式注册表（以代码为准）
│   ├── agents/                 # PersonAgent + turn_taking（v0.13）
│   ├── db/
│   │   ├── bootstrap.py        # 初始化入口
│   │   ├── connection.py
│   │   └── backends.py         # SQLite + PG stub
│   ├── llm/
│   │   ├── client.py           # LLMClient Protocol
│   │   └── providers/          # mock / anthropic / openai_compat / embedding /
│   │                           #   multimodal_embedding / vision / audio
│   ├── observability/
│   │   ├── metrics.py          # Prometheus 文本导出
│   │   ├── llm_hooks.py
│   │   ├── otel_exporter.py    # NoOp-safe OTel（v0.18）
│   │   ├── time_series_svg.py  # SVG sparkline（v0.16）
│   │   └── webhook_alert.py    # 阈值告警（v0.16）
│   ├── packaging/
│   │   └── skill_packager.py   # .weskill.zip 打包
│   ├── plugins/                # 4 类扩展点 + registry（v0.16）
│   ├── runtime/
│   │   ├── skill_runtime.py    # SkillRequest/Response v1 冻结（#19）
│   │   ├── activation.py       # 有界激活传播
│   │   ├── prompt_composer.py
│   │   ├── prompt_i18n.py      # zh/en/ja（v0.16）
│   │   ├── sqlite_retrieval.py # 唯一 retrieval_package 入口
│   │   ├── agent_runner.py     # tool_use loop
│   │   ├── streaming.py
│   │   └── adapters/           # claude / openai / mcp / feishu / langchain / coze
│   └── services/               # 60+ 服务（见下）
├── db/migrations/              # 0001..0021（见下）
├── tests/                      # 本地测试基线见 current-status / 最新验证输出
├── scripts/                    # 76 个脚本（self_audit 代码事实）
├── benchmarks/
│   ├── year_runs/              # 365 天真跑归档（v0.18 新增）
│   ├── scale/                  # 10k/50k 压测归档（v0.18 新增）
│   ├── tick_runs/              # 7 天 tick 归档
│   └── *.json                  # embedding / contradiction groundtruth 等
├── examples/
│   ├── scenarios/              # 3 场景真跑归档（v0.18 新增）
│   └── plugin_example_minimal/ # 最小 plugin 示例
└── docs/
    ├── CHANGELOG.md
    ├── getting-started.md
    ├── tick-scheduling.md
    ├── release_notes_v0.*.md
    ├── hosts/                  # Claude Desktop / Claude Code / OpenAI
    ├── comparisons/            # vs Mem0 / Letta / LangMem
    ├── tutorials/
    ├── plugins/
    ├── release/
    └── superpowers/
        ├── decisions/          # 73 ADR（0001-0073）
        ├── plans/              # 10 份 mega-plan
        ├── specs/              # 核心设计稿
        ├── state/              # current-status + 各期 diff 报告
        └── vision/             # product mandate
```

### 关键 services（60+ 里挑最重要）

| 类别 | 服务 | 备注 |
|------|------|------|
| Patch/演化 | `patch_service` / `patch_applier` / `snapshot_service` | 所有图谱改写唯一入口 |
| 导入 | `ingestion_service` / `email_ingestion_service` / `file_ingestion_service` / `directory_ingestion_service` / `auto_ingestion_service` | 统一 importer 契约 |
| 融合 | `identity_fusion_service` / `fusion_service` / `candidate_store` / `branch_resolver_service` | Phase 4 |
| Retrieval | `memory_recall_service` / `embedding_recall` / `associative_recall` | 三条职责不重叠 |
| Vector | `vector_index` / `vector_similarity` / `embedding_cache` | flat_python + sqlite_vec/faiss 真 backend（`auto` 仍保持 flat_python） |
| 演化 | `state_decay_service` / `relation_drift_service` / `self_activation_service` / `time_simulator` / `tick_sanity` | tick 闭环 |
| 主动 | `proactive_agent` / `proactive_prefs` | v0.13（#18）|
| 元认知 | `contradiction_detector` | v0.13（只读不写，判定层） |
| 媒体 | `media_asset_service` / `ocr_service` | v0.14 |
| 多 Agent | `multi_agent_dialogue` | v0.16（互听+打断+私聊） |
| 世界建模 | `world_service` | v0.17（object/place/project） |
| Agent 元能力 | `autonomous_agent` / `dream_cycle` | v0.17（#27） |
| 遗忘/拆分门控 | `forgetting_service` / `entity_unmerge_service` / `unmerge_gate_service` | v0.15 + post-v0.19 local slice（candidate + operator gate，不自动改图） |
| 激活痕迹 | `activation_trace_service` | v0.15（#21） |
| 联邦 | `federation_service` / `federation_client` / `federation_security` | v0.15-0.16 |
| 短时记忆 | `working_memory` | v0.17（#28 派生可重建） |
| 派生重建 | `derivation_rebuild` | v0.17（#28） |
| 自修复 | `integrity_audit` / `self_repair` | v0.16（policy 三档） |
| **反身能力** | **`self_introspection`** | **v0.18 — 独特差异化** |
| 图谱时间 | `graph_clock` | v0.16（#24） |

### 21 条 Migrations

```
0001  initial_core_schema        P1
0002  connection_tables           P1
0003  trace_and_evolution         P1
0004  indexes_and_constraints     P1
0005  runtime_cache               P4
0006  candidate_layer             P4
0007  cold_memories               P15
0008  external_person_refs        P22
0009  persona_history             P16
0010  event_causality             P17
0011  narrative_arcs              P24
0012  perceived_memory            P24
0013  embeddings                  P26
0014  proactive_prefs             P30
0015  media_assets                P35
0016  activation_traces           P40
0017  graph_clock                 P45
0018  world_objects               P51
0019  world_places                P51
0020  world_projects              P51
0021  agent_drives                P52
```

**重要**：每条 migration 都有 **写路径 + 读路径** 的 ADR 说明；不允许"写了没人读"的死 schema。

---

## 5. ADR 地图（73 条按 phase 分组）

| Phase | ADR | 主题 |
|-------|-----|------|
| P1 | 0001-0008 | 项目基线 / 核心 schema / event-first / 局部分支 |
| P2-3 | 0009-0011 | Retrieval package / patch + snapshot / 身份融合 |
| P4-5 | 0012-0014 | 候选中间层 / 融合服务 / importer 契约 |
| P6-7 | 0015-0017 | Drift / decay / self_activation |
| P8-12 | 0018 | v0.7 综合（+指标统一 / 不变式 1-4） |
| P13-17 | 0019 | v0.8 综合（导入矩阵 / SkillRuntime） |
| P18-21 | 0020-0023 | 联邦 / 真集成 / 叙事（v0.11 综合） |
| P22-24 | 0023 | v0.11 综合（不变式 12→14） |
| P25-27 | 0024-0027 | 真 LLM / embedding / production（v0.12） |
| P28-32 | 0028-0033 | 向量规模 / 多 agent / 主动 / 元认知 / 多模态（v0.13） |
| P33-37 | 0034-0039 | 真 Skill 宿主 / Tick / 媒体 / 规模（v0.14 — #19/#20） |
| P38-43 | 0040-0045 | 消费就绪 / Tick 归档 / 神经网格 / 遗忘 / 联邦 MVP（v0.15 — #21/#22） |
| P44-50 | 0046-0052 | Plugin / 图谱时间 / 多 Agent / 规模 / i18n（v0.16 — #23/#24/#25） |
| P51-57 | 0053-0059 | 世界建模 / Agent 元能力 / 质量 / 社区 / 发布（v0.17 — #26/#27/#28） |
| P58-64 | 0060-0066 | **不变式覆盖强化 / 年度真跑 / 反身 / 压测 / 证据**（v0.18） |
| P65-70 | 0067-0073 | **向量生产化 / 联邦写路径 / 年运行审计 / 多租户基线**（v0.19 local） |

**每个阶段综合都应参考 synthesis ADR**：0033 / 0039 / 0045 / 0052 / 0059 / 0066 / 0073

---

## 6. 无人值守工作模式（用户习惯）

### 用户的触发指令
用户会周期性问下列问题：

**A**："**可以的，核对开发文档和我们的构思，以及你可以再启发性思考一下，按照我们的设想和目标，接下来我们应该继续做些什么呢？**"
→ 你应该：深度核对 product-mandate + current-status + 最近 synthesis ADR → 启发性思考 → 列 5 个大方向（按优先级） → 规划 Phase N→N+7 → **等用户拍板**（不立即动手）

**B**："**对，依旧继续进入无人值守连续推进模式，然后因为毕竟是无人值守长工作流，我希望你尽可能的将这些进行一个超级 pending，将其全部分解为至少小一百个 task，然后自动化、多次思考的进行推进和落实**"
→ 你应该：
1. 用 `TaskCreate` 批量创建 **100-120 个 task**（每 phase 约 15-20 slice）
2. 按 phase 顺序执行：
   - 写代码 + 测试（先红灯再绿灯）
   - 跑 phase 内测试
   - 跑全量 pytest 回归
   - 写 phase ADR
   - `git commit` 带详细 message
3. 最后一个 phase 是 **EPIC**：
   - synthesis ADR（Phase N-N+7 综合 + 不变式累加）
   - `mega-plan` + `diff` + `CHANGELOG` + `release_notes` + `current-status`
   - `README` 加新段落
   - bump `pyproject.toml` + `cli.py` VERSION
   - `.venv/bin/python -m build --wheel`
   - 隔离 venv 安装验证：`python3 -m venv /tmp/wt_vX_check && /tmp/wt_vX_check/bin/pip install -q dist/we_together-X.Y.Z-py3-none-any.whl && /tmp/wt_vX_check/bin/we-together version`
   - `git tag vX.Y.0`
   - **批量 TaskUpdate 结清**（completed / deleted）

**C**："**继续推进任务**" → 直接做下一 phase，不再规划

### 每个 phase 的提交节奏

```
1. 创建该 phase 的所有文件（migration + services + tests + CLI + ADR）
2. 跑 pytest tests/<new>.py -q → 先看本 phase 红灯多少
3. 修测试或代码到绿灯
4. 跑全量 pytest -q → 确认不破坏已有
5. git add <specific files>   ← 不要用 git add -A，避免带外部目录
6. git commit with detailed message（格式见历史 commit）
```

### 绝对禁止

- ❌ 不要修改既有不变式 id 号（只能 additive 加新的）
- ❌ 不要在不写 ADR 的情况下引入破坏性 schema 改动
- ❌ 不要删除已有测试来让新功能通过（而是修代码或明确标 skip）
- ❌ 不要 `git add -A` — 仓库在 monorepo 下（上层有其他无关项目）
- ❌ 不要 `git reset --hard` / `git push --force` — 用户未授权
- ❌ 不要默认发 PyPI / 不要默认推 remote — 只打本地 tag，等用户指示
- ❌ 不要私自删除 ADR 或 migration — 即使它们"看起来低热"也要保留（参考 service-inventory 审计方式）

---

## 7. 下一轮（v0.20）候选方向（基于 ADR 0073 + 当前未完成项）

### 留给 v0.20 的候选（按优先级）

**方向 1 ★★★★★ — 矛盾复核 / operator-gated unmerge**
- `contradiction_detector` 保持只读不写
- merged person 走 `local_branch` 人工 gate
- `keep_merged / unmerge_person` 二选一

**方向 2 ★★★★★ — tenant / world 隔离语义**
- tenant namespace / world namespace contract
- cross-tenant negative tests 系统化
- world-aware 边界补强

**方向 3 ★★★★☆ — 真 LLM 端到端**（需要 key）
- 真跑 `simulate_year --budget 30`
- usage/cost 月报真实样本
- dream_cycle 真 insight

**方向 4 ★★★★☆ — 协作式 autonomy / decomposition**
- task decomposition（多 agent 协作完成 goal）
- autonomous_agent 更强 goal completion
- narrative / planning / execution 闭环增强

**方向 5 ★★★☆☆ — 外部发布**
- GitHub Release / PyPI / 文档站点
- 真实试用 / case study
- 发布流程真实演练

---

## 8. 首次上手清单（codex 第一次接触）

```bash
# 1. 确认工作区
cd /Users/yellowpeachmac/mac-code/mac-code/we-together-skill
git status                                     # clean
git log --oneline | head -5                    # 看最近 5 commits
git tag -l | tail -5                           # 确认 v0.19.0 已 tag

# 2. 确认测试绿
.venv/bin/python -m pytest -q                  # 期望 853 passed, 4 skipped

# 3. 自描述（反身能力的使用）
.venv/bin/python scripts/self_audit.py
# 输出：ADR=73, invariants=28, services=80+, migrations=21

# 4. 不变式覆盖
.venv/bin/python scripts/invariants_check.py summary
# 期望 {"total_invariants": 28, "coverage_ratio": 1.0}

# 5. 跑一份 exemplar scenario 看看
.venv/bin/python scripts/scenario_runner.py --scenario family --root /tmp/wt_test
# 输出：persons_seeded=4, events=3, memories=3

# 6. 365 天真跑复现（<1s）
rm -rf /tmp/wt_year_test
.venv/bin/python scripts/bootstrap.py --root /tmp/wt_year_test
.venv/bin/python -c "
import sys; sys.path.insert(0, 'scripts')
from seed_demo import seed_society_c
from pathlib import Path
seed_society_c(Path('/tmp/wt_year_test'))"
.venv/bin/python scripts/simulate_year.py --root /tmp/wt_year_test --days 365 --budget 0
# 期望 healthy=True, integrity=True
```

### 阅读顺序（必读）

1. **[`docs/superpowers/vision/2026-04-05-product-mandate.md`](superpowers/vision/2026-04-05-product-mandate.md)** — 最高约束
2. **[`docs/superpowers/specs/2026-04-05-we-together-core-design.md`](superpowers/specs/2026-04-05-we-together-core-design.md)** — 核心设计
3. **[`docs/superpowers/state/current-status.md`](superpowers/state/current-status.md)** — 实时状态（长文档，扫读即可）
4. **[`docs/superpowers/decisions/0073-phase-65-70-synthesis.md`](superpowers/decisions/0073-phase-65-70-synthesis.md)** — 最新综合 ADR
5. **[`docs/superpowers/state/2026-04-19-invariants-coverage.md`](superpowers/state/2026-04-19-invariants-coverage.md)** — 不变式覆盖历史记录；当前以 `scripts/invariants_check.py summary` 和 `src/we_together/invariants.py` 为准
6. **[`src/we_together/invariants.py`](../src/we_together/invariants.py)** — 不变式源代码（必看）
7. **[`CLAUDE.md`](../CLAUDE.md)** — 项目根 CLAUDE.md（规则）

---

## 9. 工具 / 脚本速查

| 目的 | 命令 |
|------|------|
| 项目自描述 | `scripts/self_audit.py` |
| 不变式覆盖 | `scripts/invariants_check.py summary` |
| 查看单条不变式 | `scripts/invariants_check.py show <id>` |
| Bootstrap 新 root | `scripts/bootstrap.py --root <path>` |
| 创建场景 | `scripts/create_scene.py` |
| 导入叙述 | `scripts/import_narration.py` |
| 对话 | `scripts/chat.py` |
| 多 agent 对话 | `scripts/multi_agent_chat.py --scene X --turns 3` |
| Dashboard HTML | `scripts/dashboard.py --port 7780` |
| /metrics | `scripts/metrics_server.py --port 7781` |
| MCP server | `scripts/mcp_server.py --root .` |
| 联邦 server | `scripts/federation_http_server.py --port 7782` |
| 世界 CLI | `scripts/world_cli.py register-object/place/project` |
| 梦循环 | `scripts/dream_cycle.py --lookback 30` |
| Tick 1 周 | `scripts/simulate_week.py --ticks 7 --budget 10` |
| Tick 1 年 | `scripts/simulate_year.py --days 365 --budget 0 --archive-monthly` |
| 规模化压测 | `scripts/bench_scale.py --n 10000` |
| Exemplar 场景 | `scripts/scenario_runner.py --scenario all --archive` |
| Skill 打包 | `scripts/package_skill.py pack --output dist/we-together.weskill.zip` |
| 自修复 | `scripts/fix_graph.py --policy propose` |
| 审计 integrity | `scripts/fix_graph.py --policy report_only` |
| Rollback tick | `scripts/rollback_tick.py --snapshot snap_tick_N_...` |
| Release 自检 | `scripts/release_prep.py --version 0.19.0` |

---

## 10. 常见失败 / 故障处理

### Migration schema 与测试 seed 不匹配
- **症状**：`sqlite3.OperationalError: table X has no column Y`
- **原因**：测试 seed SQL 和 migration 定义不一致
- **修法**：`grep "CREATE TABLE X" db/migrations/*.sql` 找真实列；改 seed SQL

### Bootstrap 幂等冲突
- **症状**：某 migration 重复执行 `UNIQUE constraint failed`
- **原因**：migration 缺 `INSERT OR IGNORE` / `CREATE TABLE IF NOT EXISTS`
- **修法**：migration 文件加 `IF NOT EXISTS` / `OR IGNORE`

### pytest 失败但本地单独跑绿
- **原因**：fixture 顺序 / 全局状态（比如 working_memory 的全局 buffers、invariants 的 INVARIANTS 列表）
- **修法**：在测试里调 `clear_all()` / `reset()`，或用 `monkeypatch` 隔离

### wheel 打包失败
- **原因**：`pyproject.toml` 版本 vs `cli.py` VERSION 不一致
- **修法**：`scripts/release_prep.py --version X.Y.Z` 会自检

### git commit 意外加了外部目录
- **原因**：用 `git add -A` 或 `.` 且上层有 AgentPentest / bilibili 等 sibling
- **修法**：`git reset --soft HEAD~1` → `git reset HEAD` → 只 `git add <specific paths>` 再 commit

### pending task 堆积
- **位置**：TaskList 里会残留旧 phase 的 pending
- **修法**：每个 EPIC phase 最后做批量 `TaskUpdate status=completed|deleted`，保持清洁

---

## 11. 约定 / 仓库规约

### Commit message 格式
```
feat: Phase NN 主题 (XXX passed)

<详细修改列表，分 service / migration / test / CLI>

<涉及的 ADR / 不变式 / 向后兼容说明>

Co-Authored-By: <你使用的 model>
```

ADR commits 用 `docs:` prefix（Phase 综合 / EPIC 用）。

### 代码规约
- Python **3.11+**
- 所有公开 API 必须类型注解
- 所有新 service 必须有 pytest 测试覆盖
- 延迟 import 真 SDK（anthropic / openai / transformers / torch / faiss / sqlite_vec / opentelemetry / hypothesis 等）
- Mock 优先（测试必须走 mock，除非带 `# pragma: no cover`）
- 中文优先（commit message / ADR / 文档都是中文；变量名 / 标识符保持英文）
- **禁止在 core path 里 `import anthropic` / `import openai` / `import hypothesis`** — 一律延迟 import

### 文件命名
- ADR：`docs/superpowers/decisions/NNNN-phase-X-topic.md`
- Migration：`db/migrations/NNNN_topic.sql`
- Plan：`docs/superpowers/plans/2026-04-19-phase-X-Y-mega-plan.md`
- Diff：`docs/superpowers/state/2026-04-19-phase-X-Y-diff.md`
- Release notes：`docs/release_notes_vX.Y.Z.md`
- Test：`tests/<subdir>/test_phase_NN_XX.py`

---

## 12. 版本历史（快速定位）

| tag | passed | 重点 |
|-----|:------:|------|
| v0.8.0 | 初期 | 基线 ADR 0001-0008 |
| v0.11.0 | 392 | 联邦 + 真集成 + 叙事 |
| v0.12.0 | 410 | 真 LLM + embedding + production |
| v0.13.0 | 436 | 向量规模 + 多 agent + 主动 + 元认知 + 多模态 |
| v0.14.0 | 477 | 真 Skill 宿主 + Tick 闭环 + 媒体 + 规模 |
| v0.15.0 | 521 | 消费就绪 + Tick 归档 + 神经网格 + 遗忘 + 联邦 |
| v0.16.0 | 594 | Plugin + 图谱时间 + 多 Agent + 规模 + i18n |
| v0.17.0 | 638 | 世界建模 + Agent 元能力 + 质量 + 社区 + 发布 |
| **v0.18.0** | **690** | **不变式强制 + 年度真跑 + 反身 + 压测 + 证据** |
| **v0.19.0** | **836** | **真向量后端 + 联邦写路径 + 年运行审计 + 多租户基线 + 本地发布前基线收口 + WebUI/MCP strict gate** |

---

## 13. Codex 继任时的具体下一步建议

### 如果用户只说"继续推进" → 你需要：
1. 跑 `pytest -q` 确认 **853 passed / 4 skipped** 基线保持
2. 读 [`docs/superpowers/decisions/0073-phase-65-70-synthesis.md`](superpowers/decisions/0073-phase-65-70-synthesis.md)
3. 优先沿当前本地 `Phase 72` 推进：矛盾复核 / operator-gated unmerge → 再进入 tenant/world isolation

### 如果用户说"新的启发性规划" → 你需要：
1. 重读 product-mandate（不变！）
2. 重读 ADR 0066
3. 重新评估三支柱（**9.95 / 9.8 / 9.7**），找最短板
4. 提 5 个方向（按优先级） + Phase 65-71 草图 + 不变式 31-33 候选
5. 等用户拍板

### 如果用户说"无人值守连续推进到 v0.20.0" → 你需要：
1. 基于当前已起步的 `Phase 72` 本地切片继续往后拆 Phase 73+
2. 按 phase 交付（每个 phase commit + ADR）
3. 最后 EPIC：bump VERSION 0.19.0 → 0.20.0 + wheel verify + `git tag v0.20.0`
4. 批量结清 task

---

## 14. 给 Codex 的最后一条建议

这是一个**非常工程化**的项目：
- 不是 "先做出来再说" 的原型
- 所有改动都要对得起当前不变式注册表
- 所有新能力都要给得出证据（测试 / 归档 / ADR）

但它也**不是死板**的：
- 用户鼓励"启发性思考"
- 被暂搁置的事（真 sqlite-vec / 真上架 / 真 LLM 跑）**都可以重启**
- 新不变式可以加，只是要配套测试

**作者的工作风格**：快、决策快、批量推进、周期性回来问"接下来做什么"。保持这个节奏。

**最重要的一句话**：
> 一个 memory 框架不会记住自己有哪些 ADR。**we-together 记得**。这是我们的独特差异化。v0.19 继续守住这条线。

——`Claude Opus 4.7 (1M context)`，v0.19.0 本地收口后备注，2026-04-22
