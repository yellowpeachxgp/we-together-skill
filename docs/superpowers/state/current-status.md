# 当前状态

日期：2026-04-25

> 代码事实快照：
> - 本地测试基线：**853 passed, 4 skipped**
> - ADR：**73**
> - 不变式：**28**
> - Migrations：**21**
> - 参考综合：[`docs/superpowers/decisions/0073-phase-65-70-synthesis.md`](../decisions/0073-phase-65-70-synthesis.md)
> - 参考进度：[`docs/superpowers/state/2026-04-22-phase-65-70-progress.md`](2026-04-22-phase-65-70-progress.md)
> - 参考排序：[`docs/superpowers/state/2026-04-23-v0-20-candidate-ordering.md`](2026-04-23-v0-20-candidate-ordering.md)

## 2026-05-03 final skill product / strict gate 补丁

- `scripts/release_strict_e2e.py --profile strict` 已成为当前 release 前严格门禁，覆盖 CLI first-run、tenant isolation、fresh MCP stdio、WebUI local bridge curl、package verify、Codex skill family validate 与 focused pytest。
- Fresh MCP stdio 的 `we_together_snapshot_list` 已在 strict gate 中通过；但本 Codex 会话中已挂载的长驻 MCP 进程可能仍运行旧代码，若仍报 `no such column: scene_id`，需要重启 MCP 后复测。
- WebUI 默认生产路径现在是 honest local runtime：local bridge 不可用或本地库为空时展示离线/空状态，不静默注入 demo graph。视觉开发 demo 需显式使用 URL `?demo=1` 或 `localStorage.we_together_demo_mode=1`。
- WebUI graph cockpit 已覆盖 person / relation / memory / group / scene / state / object / place / project；world cockpit 已覆盖 participants / objects / places / projects / agent_drives / autonomous_actions。
- Operator Review 的 resolve 操作已支持 operator note，并把 note 作为 branch resolve `reason` 写入 patch payload。
- 最新 self-audit 代码事实：`version=0.19.0`，`ADR=73`，`invariants=28/28 covered`，`migrations=21`，`services=84`，`scripts=76`。

## 2026-04-29 文档 / WebUI local runtime 补丁

- `docs/wiki/` 已新增为当前稳定 Wiki 入口，覆盖架构、使用方法、能力边界和交互流程。
- `docs/index.md`、`docs/quickstart.md`、`docs/getting-started.md`、`docs/architecture/overview.md`、`docs/FAQ.md` 已同步到 v0.19.0 事实基线。
- WebUI 默认通道已改为 local skill bridge：浏览器无 WebUI token 时通过 `/api/chat/run-turn` 调用本地 `scripts/webui_host.py`，bridge 再调用 `chat_service.run_turn()`。
- WebUI no-token 模式现在会从本地 `/api/scenes` 读取 active scenes；当前 root 没有 scene 时提示先 bootstrap + seed-demo 或导入材料，不再静默发送静态 demo scene id。
- `scripts/webui_host.py` 暴露只读 `/api/scenes` 和 `/api/summary`；图谱写入仍集中在 `chat_service.run_turn()`。
- 最新 self-audit 代码事实：`version=0.19.0`，`ADR=73`，`invariants=28/28 covered`，`migrations=21`，`services=84`，`scripts=76`。

## 2026-05-03 post-v0.19 local cockpit 推进

- 已锚定计划：`docs/superpowers/plans/2026-05-03-v0-20-local-cockpit-todo.md`。
- `scripts/webui_host.py` 已从 chat-only bridge 扩展为本地 cockpit bridge：
  - 只读：`/api/graph`、`/api/events`、`/api/patches`、`/api/snapshots`、`/api/branches`、`/api/world`。
  - 写入动作：`/api/bootstrap`、`/api/seed-demo`、`/api/import/narration`、`/api/branches/<branch_id>/resolve`。
- WebUI no-token 模式已默认读取真实本地 graph/activity/world/review 数据；demo mode 仅在 `?demo=1` 或 `localStorage.we_together_demo_mode=1` 下显式启用。
- WebUI 已新增本地 operator action strip：可直接 bootstrap、seed demo，并在 Chat 面板执行 narration import。
- Operator Review 在 local bridge 在线时会调用本地 branch resolve API；离线 demo 模式仍保留交互预览。
- 关键理念已固化：浏览器默认不持有 provider token，skill 交互应走当前 CLI / local bridge / tenant SQLite 通道；Remote API token 仅为高级部署模式。

## 2026-04-24 本地切片 — Phase 72 + Codex native skill（进行中）

- `contradiction_detector` 与 `derive_unmerge_candidates_from_contradictions()` 仍然是 **只读不写**
- 新增 `unmerge_gate_service.open_unmerge_branch_for_merged_person(...)`，把 merged person 打开为 `local_branch`
- 候选固定为 `keep_merged / unmerge_person`；只有 `resolve_local_branch` 选中 unmerge candidate 才真正改图
- `scripts/unmerge_gate.py` 提供 CLI 入口，并已支持 `--tenant-id`
- `auto_resolve_branches` 现在会跳过 operator-gated branch，保持“人工复核后才生效”
- `patch_applier` 额外补了两层 guardrail：`unmerge_person` 失败会记 `failed`；`selected_candidate_id` 必须属于目标 branch
- `entity_unmerge_service` / `unmerge_gate_service` 现在会校验 `merged_into` target 必须真实存在且 `status=active`
- `unmerge_gate.py --tenant-id` 已有回归测试；非 active target 会走明确失败出口
- `resolve_local_branch` 对带 `effect_patches` 的 candidate 现在先跑子 effect，再回写 parent branch；子 effect 失败时 branch 保持 `open`
- `unmerge_gate_service` 现在会把输入 `confidence` clamp 到 `[0,1]`，避免异常值把 operator gate 的候选排序带偏
- `package_skill.py pack` 不传版本参数时，现已自动推导当前 `skill_version=0.19.0` 与 `schema_version=0021`
- `we_together.__version__` 现已与 CLI `VERSION` 对齐
- 本机已新增 `codex_skill/` 原生技能包，以及 `scripts/install_codex_skill.py` / `scripts/update_codex_skill.py` / `scripts/validate_codex_skill.py` / `scripts/capture_codex_skill_evidence.py`
- 本机已把 Codex native skill 扩展为 7 个技能：`we-together`（router）/ `we-together-dev` / `we-together-runtime` / `we-together-ingest` / `we-together-world` / `we-together-simulation` / `we-together-release`
- `~/.codex/skills/we-together*` 七个技能目录已完成本机安装，安装后 `local-runtime.md/json` 已写入真实 `repo_root` 与 `mcp_server_name`
- `scripts/validate_codex_skill.py --installed --family --skill-dir ~/.codex/skills` 已通过，确认七个技能的安装结构与 `~/.codex/config.toml` 中的 `we-together-local-validate` MCP 注册一致
- `scripts/capture_codex_skill_evidence.py --session-root ~/.codex/sessions/2026/04/24 --limit 20` 已能提取交互式命中证据；当前观测到 1 个 `we-together` session 命中，包含 `SKILL.md` / `local-runtime.md` / `prompts/dev.md` 读取与 commentary 证据
- `verify_skill_package.py` 与 `skill_host_smoke.py` 的假阳性已修复：前者会做真实解包/文件/runtime 校验，后者会校验非空回复文本
- `we-together` router 已进一步变薄：新增 `intent-examples` 正负样例库，并把 `router/dev/runtime/ingest/world/simulation/release` 的命中边界固化成内容级回归测试
- `docs/hosts/codex-acceptance-matrix.md` 已新增，用于人工验收 7 个 skill 家族的命中边界
- `validate_codex_skill.py` 已新增 `--family` 模式；安装与校验现在都支持整族一条命令完成
- 从 `~` 目录启动交互式 Codex，对显式中文请求 `看一下 we-together 当前状态` 已观察到 `we-together` skill 被启用，并正确回答最新版本与测试基线
- 旧的 `codex exec 401 Unauthorized` 结论已过时；当前真实限制是：`codex exec` 模式不适合作需要 MCP 审批/elicitation 的工具调用，支持路径应以交互式 Codex + 本地原生 skill 为准

当前已完成：

- 已确立产品最高约束：严格工程化、通用型 Skill、数字赛博生态圈目标
- 明确项目定位为 Skill-first 的社会图谱系统
- 选定第一阶段锚点场景为 `C：混合小社会`
- 确定采用统一社会图谱内核，而不是工作/亲密双系统拼接
- 确定关系模型为“核心维度固定 + 自定义扩展 + 自然语言摘要”
- 确定导入策略为默认全自动、自动入图谱
- 确定身份融合策略为激进自动融合，但必须可逆、可追溯
- 确定演化策略为“先写事件，再归并入图谱”
- 确定留痕模型为 Git 式混合结构
- 确定第一阶段只支持局部分支，不支持整图分叉
- 确定运行时采用“有界激活传播模型”
- 确定环境参数采用“核心维度固定 + 自定义扩展”
- 确定主存储采用 SQLite 与文件系统的混合模型
- 确定 importer 采用“统一证据层 + 候选层”的输出契约
- 确定 SQLite 为规范主对象与留痕对象的核心存储层
- 确定 Event / Patch / Snapshot 为第一阶段的标准演化链
- 确定默认激进融合、底层可逆的 identity 融合策略
- 确定运行时采用固定结构的检索包
- 确定 Scene 与环境参数采用“核心枚举 + 自定义扩展”
- 已补齐启动与迁移方案
- 已补齐 importer 复用矩阵
- 已写入 Phase 1 架构基线 ADR
- 已生成 Phase 1 implementation plan
- 已落地首批 Python 工程骨架
- 已落地 SQLite 主库迁移执行器与基础 schema
- 已接入基础枚举 seed 初始化
- `bootstrap` 已能对空白外部 `--root` 自动补齐内置 migrations / seeds，并保持 seed 装载幂等
- 已落地 narration importer、patch 构造器、identity 融合评分基线与 runtime retrieval package 基线
- 已落地最小 CLI 端到端链路：bootstrap / create_scene / import_narration / build_retrieval_package
- 已接通群组创建与目录级导入 CLI，可直接构建 group 并批量扫描 `.txt` / `.md` / `.eml`
- narration 导入已能自动抽取简单人物与关系并落图谱
- 已接通 text_chat importer，可从通用聊天文本中抽取人物、事件与基础关系
- text_chat 导入已能为每条消息写入 `event_participants`
- 已接通 auto import 入口，可在 narration 与 text_chat 之间自动判别
- 已接通 email importer，可从 `.eml` 文件中抽取发件人、主题、正文并落图谱
- 已接通文件级 auto import，可对文本文件与 `.eml` 自动分流
- narration / text_chat / email 导入已开始落地 identity_links
- retrieval package 已能回填参与者姓名并带出场景下已知关系
- narration / text_chat 导入已能沉淀共享记忆并写入 retrieval package
- email 导入现在也通过推理 patch 生成共享 memory，并把发件人链接到该 memory
- 已落地最小 patch applier，可统一应用 memory/state 类 patch
- text_chat 导入已能生成更具体的互动关系摘要
- retrieval package 已能回填关系参与者、`current_states` 与群组场景下的 `latent` 激活成员
- 运行时 `response_policy` 已由静态 scene participant 推断升级为基于显性/潜伏激活的有界收敛
- shared memory 已可在非 group 场景下触发额外 `latent` 激活
- active relation 已可在非 group 场景下触发额外 `latent` 激活，且 `strict` activation barrier 会阻断派生激活
- event participants 已可触发额外 `latent` 激活，并纳入 activation budget 统计
- retrieval package 已开始输出可解释的 `activation_budget` / `propagation_depth` / `source_weights` / `event_decay_days` 信息
- retrieval package 现已按 `relation/event/group/memory` 输出来源级 used / blocked 统计
- create_local_branch 已可同时写入 branch_candidates
- patch applier 已扩到 `link_entities`、`unlink_entities`、`create_local_branch`、`resolve_local_branch`、`mark_inactive`
- unsupported patch operation 已会落痕为 `failed`
- narration 导入已开始通过推理出的结构化 patch 落 `create_memory` / `link_entities`
- text_chat 导入现已通过推理 patch 构建共享 memory 与 relation link
- narration / text_chat / email 导入现已可通过推理 patch 落部分 `update_state`
- 运行时 `current_states` 已可读到导入阶段推理出的 person / relation 状态
- `auto` / `file` 路由已继承上述 state inference 行为
- runtime 已会忽略被标记为 `inactive` 的 relation / memory
- runtime `safety_and_budget` 已暴露 open local branch 风险数量、branch id 列表与候选总数
- narration / text_chat / email 导入现已开始写入 `snapshot_entities`
- runtime retrieval 已支持按 `scene + input_hash` 写入和命中 `retrieval_cache`，并在 scene / patch 变更后失效
- build_retrieval_package CLI 已支持 `--input-hash`
- group 相关变更也会触发 retrieval cache 失效
- retrieval build 现已同步刷新 `scene_active_relations`
- retrieval package CLI 在 scene 不存在时已能干净失败并输出明确错误
- 文件/目录导入服务已具备清晰失败路径，并会返回 `skipped_count` / `skipped_files`
- 文件/目录导入 CLI 在目标路径缺失时已能干净失败并输出明确错误
- graph summary 已可展示 snapshot/cache/runtime 派生计数
- retrieval cache 已支持默认 TTL（DEFAULT_CACHE_TTL_SECONDS = 3600），不传 TTL 时自动使用默认值
- build_retrieval_package CLI 已支持 `--cache-ttl` 参数
- graph summary 已扩展 memory_count、state_count、patch_count 与 candidate_status_distribution 字段
- resolve_local_branch 已可读取 selected candidate 的 payload_json 中的 effect_patches，并逐个应用到主图谱
- ingestion 共用 SQL 已抽取为 ingestion_helpers.py（persist_import_job / persist_raw_evidence / persist_patch_record / persist_snapshot_with_entities）
- ingestion_service.py 和 email_ingestion_service.py 已调用共用 helper，消除重复代码
- `VectorIndex(backend='sqlite_vec'|'faiss')` 已从 stub 升级为真 backend：前者走 sqlite-vec SQL 距离函数，后者走 FAISS `IndexFlatIP`
- `embedding_recall.associate_by_embedding()` 已支持 `index_backend` 显式选择；`bench_scale.py` 已支持 `--backend`
- `pyproject.toml` 已新增 `vector` optional extra；`bench_scale.py` 已支持 benchmark 归档并写入 backend/platform/python_version 元数据
- `federation_http_server.py` 已支持显式开启的 `POST /federation/v1/memories`；联邦写路径走 event -> patch -> snapshot，不直接写业务 memory 表
- `simulate_year.py` 已支持 provider-check、LLM usage summary、成本估算与月度 report artifact；夜间 smoke 已切到 `. [vector]` 并归档 native backend benchmark
- `bench_scale.py` 已支持 `--backend all` compare 模式；仓库已归档 100k / 1M 三 backend compare 证据，当前 1M 默认推荐 `faiss`
- `bootstrap.py` / `seed_demo.py` / `federation_http_server.py` 已支持 `--tenant-id`；tenant path routing 已从 helper 进入实际 CLI / server 路径
- `create_scene.py` / `import_narration.py` / `build_retrieval_package.py` / `graph_summary.py` 已支持 `--tenant-id`；tenant 下的导入 -> scene -> retrieval -> summary 最小工作流已可运行
- `FederationClient` 已对 localhost 显式禁用代理，tenant 联邦 smoke 在本机更稳定
- `mcp_server.py` / `dashboard.py` / `record_dialogue.py` / `dialogue_turn.py` / `skill_host_smoke.py` 已支持 `--tenant-id`；tenant 下的宿主与对话入口已可运行
- `simulate_week.py` / `simulate_year.py` / `dream_cycle.py` / `fix_graph.py` 已支持 `--tenant-id`；tenant 下的长期演化与修复入口已可运行
- `create_group.py` / `import_text_chat.py` / `import_email_file.py` / `import_file_auto.py` / `import_directory.py` / `import_auto.py` 已支持 `--tenant-id`；tenant 下的高频导入/建组入口已可运行
- `snapshot.py` / `branch_console.py` / `world_cli.py` / `activation_path.py` / `auto_resolve_branches.py` / `merge_duplicates.py` 已支持 `--tenant-id`；tenant 下的管理/诊断入口已可运行
- `daily_maintenance.py` / `scenario_runner.py` / `agent_chat.py` / `multi_agent_chat.py` 已支持 `--tenant-id`；tenant 下的维护/agent/scenario 入口已可运行
- `tenant_router` 已新增 `normalize_tenant_id()` 与非法 tenant 拒绝；cross-tenant 负向测试已覆盖 default vs alpha 基本隔离
- `timeline.py` / `relation_timeline.py` / `rollback_tick.py` / `self_activate.py` / `extract_facets.py` / `embed_backfill.py` 已支持 `--tenant-id`；tenant 下的时间线/向量维护/自激活入口已可运行
- `analyze.py` / `eval_relation.py` / `bench_large.py` / `import_image.py` / `import_llm.py` / `import_wechat.py` / `simulate.py` / `what_if.py` / `narrate.py` / `graph_io.py` / `onboard.py` / `seed_society_m.py` / `seed_society_l.py` 已支持 `--tenant-id`；tenant CLI 覆盖面继续扩展
- `tenant_router` 已支持从 root / db_path 反推 tenant；`graph_summary.py` / `dashboard.py` / `mcp_server.py` 的摘要输出已显式带 tenant 上下文
- retrieval package 的 participants 已丰富 persona_summary / style_summary / boundary_summary 人物摘要
- 对话演化循环已闭合：dialogue_service.record_dialogue_event() 将对话写为 dialogue_event + snapshot
- infer_dialogue_patches() 从对话内容推理 scene mood state 和多人共享 memory
- 对话 → Event → Patch → Graph State 的完整演化链已可运行
- snapshot 已支持 list_snapshots() 历史遍历和 rollback_to_snapshot() 回滚
- rollback 会标记后续 patch 为 rolled_back、删除后续 states 和 snapshots、清空 retrieval cache
- patch applier 已支持 update_entity，可对 person/relation/group/memory 做字段级增量更新
- 新增 record_dialogue.py CLI（记录对话事件）和 snapshot.py CLI（list / rollback）
- patch applier 已支持 merge_entities，可迁移 identity_links / event_participants / memory_owners / scene_participants / group_members 并标记源 person 为 merged
- identity_fusion_service 已新增 find_and_merge_duplicates()，可自动发现同名重复人物并合并
- 新增 merge_duplicates.py CLI（自动合并重复人物）
- 对话端到端闭环：process_dialogue_turn() 一键串联 retrieval → record_event → infer_patches → apply
- 新增 dialogue_turn.py CLI（一键对话处理）
- scene_service 已支持 close_scene() 和 archive_scene()，场景可关闭和归档
- retrieval 已拒绝对非 active 场景的检索请求（抛出 ValueError）
- retrieval package 已支持预算裁剪：max_memories / max_relations / max_states 参数
- build_retrieval_package CLI 已新增 --max-memories / --max-relations / --max-states
- retrieval package 已新增 recent_changes 字段，展示最近已应用的 patch 摘要
- retrieval package 已新增 max_recent_changes 参数控制返回条数
- snapshot 已支持 replay_patches_after_snapshot() 回滚后重放
- snapshot CLI 已新增 replay 子命令
- 历史 Phase 1 最小内核曾记录 `122 passed`；当前活跃基线见本文件顶部。

## Phase 4 — 让蒸馏变真（已完成）

- 新增 migration 0006：identity_candidates / event_candidates / facet_candidates / relation_clues / group_clues
- candidate_store 统一写入 API，confidence 分层（high/medium/low）
- LLM adapter 抽象（`src/we_together/llm/`）：Protocol + mock/anthropic/openai_compat providers
- factory 按 `WE_TOGETHER_LLM_PROVIDER` 切换；核心路径不直接 import SDK
- fusion_service：candidate → persons / identity_links / relations，所有变更走 patch
- 低置信 identity 冲突自动开 local_branch（含 merge/new 两候选），不直接合并
- llm_extraction_service：LLM 驱动的 narration 候选抽取（内部创建 evidence + candidates）
- ADR 0002 定稿 LLM-in-the-loop 五个决策

## Phase 5 — 让 Skill 变通用（已完成）

- runtime/skill_runtime.py：SkillRequest / SkillResponse 数据结构（平台无关）
- runtime/prompt_composer.py：retrieval_package → {system, messages}（含参与者/关系/记忆/状态/recent_changes/policy 七段）
- adapters/claude_adapter + adapters/openai_adapter：两套宿主语义等价
- chat_service.run_turn：端到端 retrieval → adapter → LLM → 图谱演化
- scripts/chat.py REPL，支持 /who /pkg /switch /exit

## Phase 6 — 让图谱变活（已完成）

- patch_applier 新增 upsert_facet，复用现有 person_facets 表
- retrieval 按 scene.scene_type 投影 facets（SCENE_FACET_POLICY）
- relation_drift_service：按 event 窗口重算 strength（+/-0.03..0.05），落 update_entity patch
- state_decay_service：linear/exponential/step/none 四种 decay_policy，低置信标记 deactivated
- _build_relevant_memories：综合分 = type_weight × relevance × confidence × recency × overlap × scene_match
- branch_resolver_service：显著占优的 branch 自动 resolve
- scene_transition_service：给出下一场景候选（切 type / 扩 group / 引入关系对方）

## Phase 7 — 生态自转（进行中）

- importers/wechat_text_importer.py：CSV → candidate 层，fusion 后创建 persons/relations
- self_activation_service：无输入时生成 self_reflection_event，受 daily_budget 约束

## 工程基建

- pyproject.toml 加入 ruff + mypy；scripts/lint.sh 本地工程化检查
- scripts/e2e_smoke.sh：10 步端到端链路（bootstrap→seed→retrieve→turn→snapshot→drift→decay→merge→summary）
- scripts/bench.py：build_retrieval cold/warm + apply_state_patch 延迟百分位
- .github/workflows/ci.yml：install + ruff + mypy + pytest + e2e smoke
- scripts/seed_demo.py：Society C 小社会（8 人 × 8 关系 × 3 场景）

- 当前本地全量测试通过：216 passed

## Phase 7 收尾增补（2026-04-18）

- person_activity_service：聚合 person 近期活动（persona/facets/events/relations/memories/scenes）为单份 profile，供 debug / skill 展示（Slice C1）
- runtime_retrieval 新增 `debug_scores` 开关，memory 附带 `score_breakdown` 暴露 base_type / relevance / confidence / recency / overlap / scene_factor 中间量；debug 模式跳过缓存读写（Slice W2）
- relation_conflict_service：按窗口内 relation 相关 events 做 sentiment 分析，统计 ± 反转次数，识别"正负情绪反复震荡"的冲突关系；emit_memory=True 时生成 `conflict_signal` 低置信 memory（Slice U2）
- `docs/superpowers/importers/2026-04-18-importer-status-matrix.md`：已实现层 importer 契约矩阵（8 类 importer 的 patch 类型、是否直接落主图、fuse_all 升级路径、retrieval 可见性差异）

当前主设计稿：

- [2026-04-05-we-together-core-design.md](../specs/2026-04-05-we-together-core-design.md)
- [2026-04-05-runtime-activation-and-flow-design.md](../specs/2026-04-05-runtime-activation-and-flow-design.md)
- [2026-04-05-unified-importer-contract.md](../specs/2026-04-05-unified-importer-contract.md)
- [2026-04-05-sqlite-schema-design.md](../specs/2026-04-05-sqlite-schema-design.md)
- [2026-04-05-patch-and-snapshot-design.md](../specs/2026-04-05-patch-and-snapshot-design.md)
- [2026-04-05-identity-fusion-strategy.md](../specs/2026-04-05-identity-fusion-strategy.md)
- [2026-04-05-runtime-retrieval-package-design.md](../specs/2026-04-05-runtime-retrieval-package-design.md)
- [2026-04-05-scene-and-environment-enums.md](../specs/2026-04-05-scene-and-environment-enums.md)
- [2026-04-05-phase-1-bootstrap-and-migrations.md](../architecture/2026-04-05-phase-1-bootstrap-and-migrations.md)
- [2026-04-05-importer-reuse-matrix.md](../importers/2026-04-05-importer-reuse-matrix.md)
- [2026-04-05-phase-1-kernel-implementation.md](../plans/2026-04-05-phase-1-kernel-implementation.md)
- [0001-phase-1-architecture-baseline.md](../decisions/0001-phase-1-architecture-baseline.md)
- [2026-04-05-product-mandate.md](../vision/2026-04-05-product-mandate.md)

## Phase 8 — 图谱活化（Neural Mesh，已完成）

- runtime/multi_scene_activation.build_multi_scene_activation 聚合多个 active scene 的 activation_map（NM-1）
- memory_cluster_service.cluster_memories + memory_condenser_service.condense_memory_clusters：LLM 驱动的记忆聚类与凝练（NM-2）
- persona_drift_service.drift_personas：窗口 events → LLM 重新蒸馏 persona/style_summary（NM-3）
- self_activation_service.self_activate_pair_interactions：pair 自发交互事件 + 双人 shared_memory（NM-4）
- runtime_retrieval 新增 cross_scene_echoes：其他 active scene 的高权重事件回响（NM-5）
- migration 0007 cold_memories / cold_memory_owners + memory_archive_service：归档 + 恢复（NM-6）
- daily_maintenance.py 扩展至 6 步（原 4 步 + persona_drift + memory_condense），--skip-llm 开关
- ADR 0004 定稿 Phase 8 六个决策
- 当前本地全量测试通过：234 passed

## Phase 9 — 宿主生态（Host Ecosystem，已完成）

- SkillRequest.tools 跨宿主抽象；Claude 透传、OpenAI 翻译为 function schema（HE-1）
- agent_loop_service.run_turn_agent：tool_call→tool_result 循环，每步落 events 表（HE-2）
- packaging/skill_packager：pack/unpack .weskill.zip + manifest（HE-3）
- 四个新宿主 adapter（纯函数，无 SDK）：飞书（+ 签名校验）/ LangChain / Coze / MCP（HE-4/5/6/7）
- scripts/agent_chat.py 内置 graph_summary / retrieval_pkg 工具示例
- ADR 0005 定稿 Phase 9 四个决策
- 当前本地全量测试通过：254 passed

## Phase 10 — 真实世界数据化（Real-world Ingestion，已完成）

- imessage_importer（macOS chat.db 只读）/ wechat_db_importer（明文 sqlite）/ mbox_importer（RW-1/2/3）
- vision provider + image_importer（VLM 图片描述链路，含 AnthropicVisionClient 延迟 SDK）（RW-4）
- social_importer（通用 JSON dump: 关注/被关注/帖子/@提及）（RW-5）
- evidence_dedup_service + evidence_hash_registry 辅助表（RW-6）
- ADR 0006 定稿 Phase 10 四个决策
- 当前本地全量测试通过：260 passed

## Phase 11 — 联邦与协同（Federation，已完成）

- migration 0008 external_person_refs + federation_service（register/list/eager）（FE-1）
- event_bus_service: jsonl 队列 + cursor，publish/drain/peek 无外部依赖（FE-2）
- scripts/branch_console.py: stdlib http.server，GET /branches + POST /resolve + bearer token（FE-3）
- tenant_router: db_path 按 tenant_id 路由，default 保持向后兼容（FE-4）
- ADR 0007 定稿 Phase 11 四个决策
- 当前本地全量测试通过：268 passed

## Phase 12 — 生产化硬化（Hardening，已完成）

- observability/logger: stdlib + contextvars trace_id + JSON 格式（HD-1）
- observability/metrics: 内存 counter/gauge + Prometheus 文本导出（HD-2）
- config/loader: `we_together.toml` + env 两级合并，WeTogetherConfig dataclass（HD-3）
- errors.py: WeTogetherError 六级层级（HD-4）
- scripts/bench_large.py: 批量 person 插入 + 冷/热检索延迟 p50/p95（HD-5）
- db/schema_version: bootstrap 预检漂移 → SchemaVersionError（HD-6）
- services/patch_batch: apply_patches_bulk 顺序批处理（HD-8）
- services/cache_warmer: warm_retrieval_cache 预热 active scenes（HD-9）
- ADR 0008 定稿 Phase 12 九个决策
- ADR 0009 综合架构总结 + 未来不变式（5 条）
- docs/CHANGELOG.md 首版 + v0.8.0 条目
- docs/superpowers/plans/2026-04-18-phase-8-12-mega-plan.md 归档
- scripts/README.md CLI 索引
- 当前本地全量测试通过：281 passed

## Phase 13 — 产品化与 Onboarding（已完成）

- pyproject: 完整 metadata + 4 个 optional deps 分组 + console_scripts entry_point
- src/we_together/cli.py 统一 CLI 入口，20+ 子命令 dispatch
- docker/Dockerfile 多阶段 + docker-compose.yml (app + metrics:9100 + branch-console:8765) + .dockerignore + docker/README.md
- services/onboarding_flow 5 步状态机 + scripts/onboard.py --dry-run
- examples/claude-code-skill/（SKILL.md 专版 + use_cases.md + README）+ examples/feishu-bot/（stdlib webhook server + 签名校验 + url_verification challenge）
- docs/quickstart.md: 5 分钟从零到跑
- ADR 0010 定稿 Phase 13 五个决策
- 当前本地全量测试通过：288 passed

## Phase 14 — 评估与质量（已完成）

- benchmarks/society_c_groundtruth.json（8 人 / 4 期望关系 / 3 期望场景）
- src/we_together/eval/：groundtruth_loader / metrics / relation_inference / llm_judge / regression
- scripts/eval_relation.py + --save-baseline + --baseline 回归门禁（exit 3 on regression）
- ADR 0011 定稿 Phase 14 六个决策
- 当前本地全量测试通过：298 passed

## Phase 15 — 时间维度（Timeline，已完成）

- migration 0009 persona_history + 0010 event_causality
- services/persona_history_service：record / query / as_of
- persona_drift_service 整合 history 写入
- services/relation_history_service：按 day/week/month bucket 聚合 patches 中 strength 时序
- services/event_causality_service：LLM 推理事件因果边
- runtime_retrieval 新增 `as_of` 参数（过滤 recent_changes，跳过 cache）
- services/memory_recall_service：anniversary 30/90/180/365 天高置信 memory 自动回忆
- scripts/timeline.py + relation_timeline.py 两个时间视图 CLI
- ADR 0012 定稿 Phase 15 七个决策

## Phase 17 — What-if Teaser（单切片）

- src/we_together/simulation/what_if_service.simulate_what_if：纯读取 + LLM 推演，不改图谱
- scripts/what_if.py CLI
- ADR 0013 定稿 Phase 17 teaser 四个决策
- 当前本地全量测试通过：309 passed

## Phase 18 — 生态对接真实化（v0.10.0，已完成）

- MCP stdio server + Claude Code 接入指南
- 飞书 bot 绑真实 chat_service.run_turn（含签名校验）
- PyPI 发布工程（MANIFEST.in / build_wheel.sh / publish.md）
- Docker CI workflow
- Obsidian md 双向（importer + exporter）
- ADR 0015

## Phase 19 — 多模态深化（v0.10.0，已完成）

- AudioTranscriber Protocol + Mock/Whisper stub
- audio / video / document(PDF+DOCX) / screenshot_series importer
- pHash + audio fingerprint + 汉明距离近似去重
- multimodal benchmark 占位
- ADR 0016

## Phase 20 — 社会模拟完整版（v0.10.0，已完成）

- simulation/conflict_predictor (SM-2)
- simulation/scene_scripter (SM-3)
- services/retire_person_service (SM-4)
- simulation/era_evolution.simulate_era (SM-5)
- scripts/simulate.py 合一 CLI
- ADR 0017

## Phase 21 — Eval 扩展（v0.10.0，已完成）

- eval/condenser_eval + eval/persona_drift_eval
- benchmark 扩至 6 个（society_c/d/work + condense + persona_drift + multimodal）
- ADR 0018

## v0.9.1 热修（已完成）

- eval groundtruth core_type 对齐 seed_society_c（`work/intimacy/friendship/family/authority`）
- what-if mock fallback + mock_mode 字段
- eval/baseline.json 首版真实基线

## Phase 18-21 综合

- ADR 0019 不变式从 10 → 12 条
- 当前本地全量测试通过：349 passed
- tag: v0.9.1, v0.10.0

## Phase 22 — 联邦与互操作（v0.11.0，已完成）

- services/federation_fetcher: LocalFileBackend + HTTPBackend + TTL cache + eager retrieval 注入
- event_bus: NATSBackend / RedisStreamBackend（延迟 import）+ metrics 埋点
- services/hot_reload: ReloadRegistry + poll_file_mtime
- importers/migration: CSV / Notion export / Signal export（CSV 1000 行 < 1s）
- services/graph_serializer: canonical JSON schema v1 round-trip
- docs/superpowers/specs/2026-04-19-federation-protocol.md RFC draft
- ADR 0020

## Phase 23 — 真集成与生产级（v0.11.0，已完成）

- tests/integration/test_full_flow.py: 6 个端到端真跑链
- runtime/agent_runner.run_tool_use_loop: tool-use 多轮 + events 落库 + 错误路径
- chat_service.run_turn 加 tools + tool_dispatcher
- runtime/streaming.StreamingSkillResponse
- scripts/build_wheel.sh: 隔离 venv 安装 we_together-0.11.0 验证通过
- .github/workflows/ci.yml + .pre-commit-config.yaml
- ADR 0021

## Phase 24 — 图谱叙事深度（v0.11.0，已完成）

- migration 0011 narrative_arcs + 0012 perceived_memory
- services/narrative_service: LLM aggregate events → chapters
- services/perceived_memory_service: 多视角记忆
- services/graph_analytics: degree / density / isolated / full_report
- services/associative_recall: LLM 主题联想触发 stub
- scripts/narrate.py + scripts/analyze.py
- ADR 0022

## v0.11.0 综合

- ADR 0023 不变式从 12 → 14 条
- 当前本地全量测试通过：392 passed
- tag: v0.11.0
- schema 版本: 0012（migrations 0001-0012）
- benchmarks: 6（未增）

## Phase 25 — 真 LLM 集成（v0.12.0，已完成）

- LLMClient 新增 chat_with_tools / chat_stream 两方法（Mock+Anthropic+OpenAI）
- agent_runner 优先 native tool_use；Mock 仅在 scripted_tool_uses 非空时切 native
- chat_service.run_turn_stream 流式版
- observability/llm_hooks: register_hook + timed_call + LangSmithStubSink
- ADR 0024

## Phase 26 — 向量化图谱（v0.12.0，已完成）

- llm/providers/embedding: EmbeddingClient Protocol + Mock + OpenAI + sentence-transformers
- migration 0013 memory/event/person_embeddings
- services/vector_similarity: encode/decode BLOB + cosine + top_k
- services/embedding_recall.associate_by_embedding
- scripts/embed_backfill.py
- benchmarks/embedding_retrieval_groundtruth.json + eval 链路
- ADR 0025

## Phase 27 — 规模与真生产（v0.12.0，已完成）

- pyproject + cli VERSION 0.11.0 → 0.12.0；wheel 隔离验证通过
- .github/workflows/publish.yml tag-push 自动发布
- .coveragerc + pytest-cov；Coverage 基线 90%
- WAL 模式（bootstrap 时 PRAGMA journal_mode=WAL）
- optional extras: [embedding][nats][redis]
- docs/release_notes_template.md + publish.md 完整流程
- ADR 0026

## v0.12.0 综合

- ADR 0027 不变式从 14 → 16 条
- 当前本地全量测试通过：**410 passed**，Coverage 90%
- tag: v0.12.0
- schema 版本: 0013（migrations 0001-0013）
- benchmarks: 7（+ embedding_retrieval）
- pyproject / cli VERSION: 0.11.0

## Phase 28 — 向量索引 & 规模化（v0.13.0，已完成）

- `services/vector_index.VectorIndex(flat_python)` + `search_with_filter(person_ids)` 层级查询
- `services/embedding_cache.EmbeddingLRUCache` 批级 dedup + hit/miss 计数
- `db/backends.py` SQLiteBackend + PGBackend (延迟 import psycopg)
- `runtime/sqlite_retrieval` 接 `query_text + embedding_client` → embedding rerank
- `services/embedding_recall` 加 `filter_person_ids` → 层级路径
- `services/memory_cluster_service` 加 `use_embedding=True/False`，Jaccard fallback
- `event_bus_service.NATSBackend.drain` 真实现（subscribe + asyncio timeout）
- ADR 0028

## Phase 29 — 多智能体社会（v0.13.0，已完成）

- `agents/PersonAgent.from_db / speak / decide_speak`
- `agents/turn_taking.next_speaker + orchestrate_multi_agent_turn`
- 按 `is_shared + owner_id` 过滤 private vs shared memory（不引新表）
- ADR 0029

## Phase 30 — 主动图谱（v0.13.0，已完成）

- migration `0014_proactive_prefs`
- `services/proactive_prefs` set_mute / set_consent / is_allowed
- `services/proactive_agent` Trigger 三类（anniversary/silence/conflict）+ Intent generate+execute + check_budget
- 主动写入必须经预算 + 偏好门控（不变式 #18）
- ADR 0030

## Phase 31 — 元认知（v0.13.0，已完成）

- `services/contradiction_detector`：embedding 配对 + LLM 判定，**只读不写**
- `eval/contradiction_eval.run_contradiction_eval` 输出 P/R
- `benchmarks/contradiction_groundtruth.json` v1
- ADR 0031

## Phase 32 — 多模态原生 teaser（v0.13.0，已完成）

- `MultimodalEmbeddingClient` Protocol + MockMultimodalClient + CLIPStubClient（延迟 import）
- `cross_modal_similarity(query, candidates, k)`
- 不写图谱（teaser 边界）；真接入留 v0.14
- ADR 0032

## v0.13.0 综合

- ADR 0033 不变式从 16 → 18 条
- 当前本地全量测试通过：**436 passed**
- tag: v0.13.0
- schema 版本: 0014（migrations 0001-0014）
- benchmarks: 8（+ contradiction_groundtruth）
- pyproject / cli VERSION: 0.13.0
- ADR 总数: 33（0001-0033）

## Phase 33 — 真 Skill 宿主（v0.14.0，已完成）

- `runtime/skill_runtime`：加 `SKILL_SCHEMA_VERSION="1"` + `from_dict` 校验（不变式 #19）
- `runtime/adapters/mcp_adapter`：tools 2→6，新增 resources + prompts
- `scripts/mcp_server.py`：补齐 resources/read + prompts/get
- `scripts/verify_skill_package.py` + `scripts/demo_openai_assistant.py`
- ADR 0034 + 0035

## Phase 34 — 持续演化 Tick 闭环（v0.14.0，已完成）

- `services/time_simulator.py`：TickResult / TickBudget / run_tick / simulate / rollback
- 每 tick 自动 snapshot（不变式 #20 tick 写入可回滚）
- `services/tick_sanity.py`：check_growth / check_anomalies / evaluate
- `scripts/simulate_week.py` CLI
- ADR 0036

## Phase 35 — 媒体资产落盘（v0.14.0，已完成）

- migration 0015 media_assets + media_refs
- `services/media_asset_service`：register / list / link / filter_by_visibility (hash dedup)
- `services/ocr_service`：ocr_to_memory / transcribe_to_event
- `scripts/import_image.py`
- benchmark: multimodal_retrieval_groundtruth.json
- ADR 0037

## Phase 36 — 规模化 & 债务清理（v0.14.0，已完成）

- service inventory（60+ 服务，无 dead）
- migration audit（15 条，3 低热全保留）
- VectorIndex backend 扩展到 sqlite_vec / faiss（延迟 import；现已真接）
- `scripts/bench_scale.py` 10k+ 压测
- ADR 0038

## v0.14.0 综合

- ADR 0039 不变式从 18 → 20 条
- 当前本地全量测试通过：**477 passed**
- tag: v0.14.0
- schema 版本: 0015（migrations 0001-0015）
- benchmarks: 9（+ multimodal_retrieval_groundtruth）
- pyproject / cli VERSION: 0.14.0
- ADR 总数: 39（0001-0039）

三支柱达成度：
- A 严格工程化: 9.5/10
- B 通用型 Skill: 8/10
- C 数字赛博生态圈: 7/10

## Phase 38 — 消费就绪（v0.15.0，已完成）

- `scripts/dashboard.py` HTML + JSON API + /metrics
- `scripts/skill_host_smoke.py` e2e
- `docs/hosts/{claude-desktop,claude-code,openai-assistants}.md`
- `docs/getting-started.md`
- Bug fix: time_simulator snapshot SQL
- ADR 0040

## Phase 39 — Tick 真运行 + 归档（v0.15.0，已完成）

- `services/tick_cost_tracker`
- `simulate_week.py --archive` + 首份 baseline
- `scripts/rollback_tick.py`
- `docs/tick-scheduling.md`（crontab/k8s/NATS）
- ADR 0041

## Phase 40 — 神经网格式激活（v0.15.0，已完成）

- migration 0016 activation_traces
- `services/activation_trace_service`（record / query_path / multi_hop / plasticity / decay）
- `scripts/activation_path.py`
- 不变式 #21
- ADR 0042

## Phase 41 — 遗忘 / 压缩 / 拆分（v0.15.0，已完成）

- `services/forgetting_service`（Ebbinghaus + archive ↔ reactivate）
- `services/entity_unmerge_service`（merged → active，留痕 events）
- 不变式 #22
- ADR 0043

## Phase 42 — 联邦 MVP Read-Only（v0.15.0，已完成）

- `docs/superpowers/specs/federation-protocol-v1.md`
- `scripts/federation_http_server.py`
- `services/federation_client.py`
- ADR 0044

## v0.15.0 综合

- ADR 0045 不变式从 20 → 22 条
- 当前本地全量测试通过：**521 passed**
- tag: v0.15.0
- schema 版本: 0016（migrations 0001-0016）
- benchmarks: 10（+ tick_run baseline）
- pyproject / cli VERSION: 0.15.0
- ADR 总数: 45（0001-0045）

三支柱达成度：
- A 严格工程化: 9.5/10
- B 通用型 Skill: **9.5/10**
- C 数字赛博生态圈: **8.5/10**

## Phase 44 — Plugin 架构（v0.16.0，已完成）

- `src/we_together/plugins/` 4 Protocol + plugin_registry
- entry_points groups: we_together.{importers,services,providers,hooks}
- 不变式 #23
- ADR 0046

## Phase 45 — 图谱时间 + 自修复（v0.16.0，已完成）

- migration 0017 graph_clock
- graph_clock.now/set/advance/freeze 带 fallback
- integrity_audit + self_repair（policy 三档）
- simulate_year CLI
- 不变式 #24
- ADR 0047

## Phase 46 — 多 Agent REPL（v0.16.0，已完成）

- multi_agent_dialogue 互听 + 打断 + 私聊
- multi_agent_chat.py CLI
- ADR 0048

## Phase 47 — 规模化 50-500 人（v0.16.0，已完成）

- seed_society_m/l 合成
- 50 人 retrieval p95 < 1500ms 基线
- ADR 0049

## Phase 48 — 联邦安全 + PII（v0.16.0，已完成）

- Bearer token + RateLimiter + PII mask
- Federation Protocol v1.1
- 不变式 #25
- ADR 0050

## Phase 49 — i18n + 时序观测（v0.16.0，已完成）

- runtime/prompt_i18n (zh/en/ja)
- observability/time_series_svg sparkline
- observability/webhook_alert
- ADR 0051

## v0.16.0 综合

- ADR 0052 不变式从 22 → 25 条
- 当前本地全量测试通过：**594 passed**
- tag: v0.16.0
- schema 版本: 0017（migrations 0001-0017）
- benchmarks: 10
- pyproject / cli VERSION: 0.16.0
- ADR 总数: 52（0001-0052）

三支柱达成度：
- A 严格工程化: **9.7/10**
- B 通用型 Skill: **9.7/10**
- C 数字赛博生态圈: **9.0/10**

下一步建议：

- 当前主路线以 [`2026-04-22-phase-65-70-progress.md`](2026-04-22-phase-65-70-progress.md) + [`2026-04-23-v0-20-candidate-ordering.md`](2026-04-23-v0-20-candidate-ordering.md) 为准
- 已起步的本地 Phase 72 是 `contradiction/unmerge operator gate`；继续推进时优先补强其剩余 guardrail，而不是把它说成“自动修复错误 merge”
- 若继续向后推进，优先进入 tenant/world isolation contract，其次是真 provider evidence、协作式 task decomposition、再到外部发布
