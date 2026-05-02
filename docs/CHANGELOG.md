# CHANGELOG

本 CHANGELOG 记录 we-together-skill 的阶段性里程碑。

## 2026-05-03 — final skill product / local cockpit hardening

- WebUI 默认通道收口为 local skill bridge：浏览器不默认持有 provider token，真实对话走本地 CLI/runtime 环境。
- `scripts/release_strict_e2e.py --profile strict` 成为发布前主门禁，覆盖 CLI first-run、tenant isolation、fresh MCP stdio、WebUI curl、package verify、Codex skill family validate 与 focused pytest。
- WebUI cockpit 已覆盖 graph / activity / world / branch review，并支持 bootstrap、seed-demo、narration import、branch resolve。
- `.weskill.zip` 验证强化：拒绝 zip-slip、清单外文件、敏感文件、生成物和错误 manifest name。
- `scripts/release_prep.py` 强化开源发布检查：Git root、tracked generated artifacts、package name、LICENSE、wheel/sdist、strict gates。
- README、Getting Started、Codex host、family graph tutorial、publish docs 更新为当前可执行路径。
- 当前本地 pytest 基线：**853 passed, 4 skipped**。

## 2026-04-23 — post-v0.19 local slice

- `services/unmerge_gate_service`：为 merged person 打开 **operator-gated local_branch**，候选固定为 `keep_merged / unmerge_person`
- `scripts/unmerge_gate.py`：新增人工复核入口，支持 `--tenant-id`
- `services/patch_applier`：新增 `unmerge_person` patch operation；unmerge 失败时 patch 会记为 `failed`，不再误记 `applied`
- `services/patch_applier.resolve_local_branch`：新增 `selected_candidate_id` 归属校验，错误 candidate 不再把 branch 提前标成 `resolved`
- `services/branch_resolver_service`：auto resolve 现在会跳过 operator-gated branch，确保 contradiction/unmerge 仍是人工复核后才生效
- `services/entity_unmerge_service` / `services/unmerge_gate_service`：新增 `merged_into` target existence 校验，避免 stale merge metadata 打开或执行错误 unmerge
- `tests/services/test_phase_72_operator_gate.py`：补 `--tenant-id` CLI 回归，确认 unmerge gate 分支写入 tenant DB
- `services/entity_unmerge_service` / `services/unmerge_gate_service`：`merged_into` target 现在还必须是 `active`；非 active target 会拒绝开 branch / 执行 unmerge
- `scripts/unmerge_gate.py`：非 active target 会走明确失败出口（return code `2` + JSON error）
- `services/patch_applier.resolve_local_branch`：带 `effect_patches` 的 branch 现在先跑子 effect，全部成功后才回写 parent branch；子 effect 失败时 parent branch 维持 `open`
- `services/unmerge_gate_service`：operator-gated unmerge 的 `confidence` 现在会 clamp 到 `[0,1]`，避免异常值污染 branch candidate 排序
- `packaging/skill_packager` / `scripts/package_skill.py`：默认打包元数据现在会自动推导当前 `skill_version` 与最新 migration `schema_version`，不再默认写旧的 `0.8.0 / 0007`
- `src/we_together/__init__.py`：`__version__` 现已与 CLI 版本对齐

## v0.19.0 — 2026-04-22 (local)

- `services/vector_index`：`sqlite_vec` backend 从 `*_fallback` 升级为真 SQL 查询路径，使用 `vec_distance_cosine(...)` 直接在现有 embedding 表上做 KNN
- `services/vector_index`：`faiss` backend 从 `*_fallback` 升级为真 `IndexFlatIP` 内存索引，保留现有 BLOB schema
- `services/vector_index.hierarchical_query(..., backend=...)`：分 backend 走 filtered SQL / filtered FAISS / flat_python
- `services/embedding_recall.associate_by_embedding(..., index_backend=...)`：允许显式选择索引 backend
- `pyproject.toml`：新增 `vector` optional extra（`sqlite-vec` / `faiss-cpu` / `numpy`）
- `scripts/bench_scale.py`：新增 `--backend` 参数，输出报告里显式带 `backend`
- `scripts/bench_scale.py`：新增 `build_report()` / `archive_report()` / `--archive` / `--archive-dir`，归档文件名显式带 backend
- `services/vector_similarity.decode_vec`：接受 `bytes | bytearray | memoryview`，对 SQLite BLOB 更稳健
- `scripts/federation_http_server.py`：新增 `POST /federation/v1/memories`，默认关闭，`--enable-write` 显式开启
- `services/federation_client.FederationClient.create_memory(...)`：联邦写入客户端入口
- `services/federation_write_service`：联邦写入走 event -> patch(create_memory) -> owners -> snapshot 闭环
- `scripts/federation_e2e_smoke.sh`：curl 生产 smoke，覆盖 capabilities / bearer / POST / memories
- `scripts/simulate_year.py`：新增 `--provider` / `--dry-run-provider-check` / usage summary / cost estimate
- `scripts/simulate_year.py`：新增 `monthly_report_dir` / `monthly_reports`，可输出每月 usage/cost artifact
- `llm/audited_client.py`：可审计 LLM wrapper，优先读原生 usage，无则回退估算
- `.github/workflows/nightly.yml`：nightly 安装 `. [vector]` 并归档 `sqlite_vec` / `faiss` benchmark
- `scripts/bench_scale.py`：新增 `--backend all` compare 模式，支持隔离 root 逐个 backend 真跑
- `benchmarks/scale/`：新增 `bench_compare_100k_*.json` / `bench_compare_1m_*.json`
- `docs/superpowers/state/2026-04-19-scale-bench-v2-report.md`：首次真 100k / 1M compare 报告
- `bootstrap.py` / `seed_demo.py` / `federation_http_server.py`：新增 `--tenant-id`，把多租户路径路由接到脚本层
- `create_scene.py` / `import_narration.py` / `build_retrieval_package.py` / `graph_summary.py`：新增 `--tenant-id`，tenant 下最小 CLI 工作流已闭环
- `FederationClient`：对 `127.0.0.1/localhost` 显式绕过代理，避免本地联邦 smoke 被环境代理污染
- `mcp_server.py` / `dashboard.py` / `record_dialogue.py` / `dialogue_turn.py` / `skill_host_smoke.py`：新增 `--tenant-id`，宿主与对话入口进入 tenant 路由
- `simulate_week.py` / `simulate_year.py` / `dream_cycle.py` / `fix_graph.py`：新增 `--tenant-id`，tenant 下的演化/修复入口已接通
- `create_group.py` / `import_text_chat.py` / `import_email_file.py` / `import_file_auto.py` / `import_directory.py` / `import_auto.py`：新增 `--tenant-id`，高频导入/建组入口进入 tenant 路由
- `snapshot.py` / `branch_console.py` / `world_cli.py` / `activation_path.py` / `auto_resolve_branches.py` / `merge_duplicates.py`：新增 `--tenant-id`，tenant 下的管理/诊断入口已接通
- `daily_maintenance.py` / `scenario_runner.py` / `agent_chat.py` / `multi_agent_chat.py`：新增 `--tenant-id`，tenant 下的维护/agent/scenario 入口已接通
- `tenant_router`：新增 `normalize_tenant_id()`，tenant id 现已做路径安全校验；补充了 invalid tenant / cross-tenant 负向测试
- `timeline.py` / `relation_timeline.py` / `rollback_tick.py` / `self_activate.py` / `extract_facets.py` / `embed_backfill.py`：新增 `--tenant-id`，tenant 下的时间线/向量维护/自激活入口已接通
- `analyze.py` / `eval_relation.py` / `bench_large.py` / `import_image.py` / `import_llm.py` / `import_wechat.py` / `simulate.py` / `what_if.py` / `narrate.py` / `graph_io.py` / `onboard.py` / `seed_society_m.py` / `seed_society_l.py`：新增 `--tenant-id`，tenant CLI 覆盖面进一步扩展
- `tenant_router`：新增 tenant introspection helper；`graph_summary.py` / `dashboard.py` / `mcp_server.py` 输出现在会显式带 `tenant_id`

## v0.18.0 — 2026-04-19

战略转向版本：不继续堆新能力，集中补纵深验证、反身能力和证据归档。

- `scripts/invariants_check.py`：不变式覆盖检查进入标准验证链路；当前代码注册表以 28 条不变式为准，历史 #29/#30 表达为治理检查。
- `scripts/simulate_year.py`：支持 365 天真跑与月度归档。
- `scripts/self_audit.py`：输出版本、ADR、不变式、migration、service、script 等代码事实。
- `scripts/bench_scale.py`：归档 10k / 50k 规模化压测证据。
- `scripts/scenario_runner.py`：归档 family / work / book_club 三个 exemplar scenario。
- ADR 0060-0066：收口 Phase 58-64 的证据优先路线。

## v0.17.0 — 2026-04-19

第十轮一次性无人值守推进：Phase 51-57。**638 passed (+44, +2 skipped)**，新增 7 个 ADR（0053-0059）。**维度跃迁**：社会图谱→世界图谱，被动 agent→自主+梦+学习，孤立代码→社区就绪。

### Phase 51 — 世界建模升维（C 支柱）

- migration `0018_world_objects` + `0019_world_places` + `0020_world_projects`
- `services/world_service`：register_object / transfer_object / register_place / get_place_lineage / register_project / set_project_status / active_world_for_scene
- 跨类 entity_links：person→owns→object / event→at→place / project→involves→person
- `scripts/world_cli.py`
- **ADR 0053**，不变式 #26 世界对象时间范围

### Phase 52 — AI Agent 元能力（C 支柱）

- migration `0021_agent_drives` + `autonomous_actions`
- `services/autonomous_agent`：compute_drives (5 类) / decide_action / record_autonomous_action
- `services/dream_cycle`：archive + insight 生成 + learning
- `scripts/dream_cycle.py`
- **ADR 0054**，不变式 #27 自主可解释

### Phase 53 — 质量与韧性（A 支柱）

- `observability/otel_exporter`：OpenTelemetry NoOp-safe wrapper
- property-based (optional hypothesis): mask_pii 幂等 / forget_score 单调
- fuzz: 未知 operation / null memory / 5000 条批量
- `.github/workflows/nightly.yml` UTC 02:00 自动 smoke
- **ADR 0055**

### Phase 54 — 社区就绪（B 支柱）

- `CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` / `SECURITY.md` / `GOVERNANCE.md`
- `docs/comparisons/vs_mem0.md / vs_letta.md / vs_langmem.md`
- `mkdocs.yml` + `docs/index.md`
- `docs/good_first_issues.md` 20 条
- `docs/tutorials/family_graph.md`
- `.github/ISSUE_TEMPLATE/` + `PULL_REQUEST_TEMPLATE.md`
- **ADR 0056**

### Phase 55 — 差异化能力（C 支柱）

- `services/working_memory`：per-scene 短时 buffer，TTL + capacity，不落 db
- `services/derivation_rebuild`：insight / narrative / activation 派生可重建验证
- **ADR 0057**，不变式 #28 派生可重建

### Phase 56 — 发布准备（B 支柱）

- `docs/release/pypi_checklist.md`
- `docs/release/claude_skills_submission.md`
- `scripts/release_prep.py --version X.Y.Z` 一键自检
- **ADR 0058**

### 不变式（ADR 0059）

25 → **28**：
- **#26** 世界对象必须有明确时间范围
- **#27** Agent 自主行为必须可解释
- **#28** 派生字段必须可从底层 events/memories 重建

### 三支柱达成度

- A 严格工程化：9.7 → **9.8**
- B 通用型 Skill：9.7 → **9.8**
- C 数字赛博生态圈：9.0 → **9.5**

## v0.16.0 — 2026-04-19

第九轮一次性无人值守推进：Phase 44-50。**594 passed (+73)**，新增 7 个 ADR（0046-0052）+ 1 个 mega-plan + 1 个 diff 报告。

### Phase 44 — Plugin / Extension 架构（B 支柱）

- `src/we_together/plugins/`：4 Protocol（Importer/Service/Provider/Hook）+ `PLUGIN_API_VERSION="1"`
- `plugin_registry.py`：discover via entry_points + register/unregister/disable/enable + status
- 4 个 entry_points group：`we_together.{importers,services,providers,hooks}`
- 错误隔离：单个 plugin 加载失败不影响其他
- `scripts/plugins_list.py` CLI
- `docs/plugins/authoring.md` + `examples/plugin_example_minimal/`
- **ADR 0046**

### Phase 45 — 图谱时间 + 自修复（C 支柱）

- migration `0017_graph_clock`（单行表 + history）
- `services/graph_clock`：set / advance / freeze / unfreeze / clear，fallback `datetime.now(UTC)`
- `services/integrity_audit`：dangling refs / orphaned memories / low conf / relation cycles / merged_without_target
- `services/self_repair`：policy `report_only / propose / auto`，auto 仅 safe fix
- `scripts/fix_graph.py --policy ...` + `scripts/simulate_year.py --days 365`
- **ADR 0047**

### Phase 46 — 多 Agent REPL（C 支柱）

- `services/multi_agent_dialogue`：
  - `TranscriptEntry` + `orchestrate_dialogue`
  - 互听（`_visible_messages_for` 按 audience 过滤）
  - 打断（`interrupt_threshold` 高分可抢占）
  - 私聊（`private_turn_map`）
  - `record_transcript_as_event` 写 dialogue_event
- `scripts/multi_agent_chat.py --scene X --turns N --real-llm --record`
- Phase 29 `orchestrate_multi_agent_turn` 保持不动（兼容）
- **ADR 0048**

### Phase 47 — 规模化 50-500 人（A+C 支柱）

- `scripts/seed_society_m.py`：50 人合成（3 relation/人，6 memory/人，10 scene）
- `scripts/seed_society_l.py`：500 人（复用 m 的 seed）
- 性能基线：50 人 retrieval p95 < 1500ms，50 人 × 3 tick < 15s
- **ADR 0049**

### Phase 48 — 联邦安全 + PII 脱敏（B 支柱）

- `services/federation_security`:
  - Bearer token（sha256 + hmac.compare_digest）
  - RateLimiter 滑动窗口（per-key 分桶）
  - mask_email / mask_phone / mask_pii / sanitize_record
  - is_exportable (`visibility=private` / `metadata.exportable=False`)
- Federation Protocol v1 → **v1.1**：`/capabilities` 暴露新字段
- `FederationClient.bearer_token` 字段
- **ADR 0050**

### Phase 49 — i18n + 时序可观测性（B+C 支柱）

- `runtime/prompt_i18n`：zh/en/ja 三语 PROMPT_TEMPLATES + `get_prompt` + `detect_lang` + `register_prompt`
- `observability/time_series_svg`：memory_growth_trend + event_count_trend + render_sparkline_svg（纯字符串零依赖）
- `observability/webhook_alert`：AlertRule + evaluate + dispatch (dry_run)
- 无第三方依赖（urllib + str.format）
- **ADR 0051**

### 不变式（ADR 0052）

22 → **25**：
- **#23** 扩展点必须通过 plugin registry 注册；核心代码不得硬编
- **#24** 时间敏感服务必须读 graph_clock.now() 优先
- **#25** 跨图谱出口必须支持 PII 脱敏 + visibility 过滤

### 三支柱达成度

- A 严格工程化：9.5 → **9.7**
- B 通用型 Skill：9.5 → **9.7**
- C 数字赛博生态圈：8.5 → **9.0**

## v0.15.0 — 2026-04-19

第八轮一次性无人值守推进：Phase 38-43。**521 passed (+44)**，新增 6 个 ADR（0040-0045）+ 1 个 mega-plan + 1 个 diff 报告 + federation-protocol v1 spec。

### Phase 38 — 消费就绪（B 支柱 8 → 9.5）

- `scripts/dashboard.py`：单文件 HTML + `/api/summary` + `/api/tick` + `/metrics` Prometheus
- `scripts/skill_host_smoke.py`：bootstrap → seed → run_turn → dashboard 4 步验收
- 三份宿主接入文档：`docs/hosts/claude-desktop.md` / `claude-code.md` / `openai-assistants.md`
- `docs/getting-started.md` 5 分钟路径
- **Bug fix**：`time_simulator._make_snapshot_after_tick` 之前 SQL 列名错被 try/except 吞；修后 snapshot 真写入
- **ADR 0040**

### Phase 39 — Tick 真运行 + 归档（C 支柱提升）

- `services/tick_cost_tracker`：track / track_estimated / summary by_provider
- `scripts/simulate_week.py` 拆出 `build_report + archive`，加 `--archive` 开关
- 首份归档 baseline：`benchmarks/tick_runs/2026-04-18T19-37-40Z.json`
- `scripts/rollback_tick.py` CLI
- `docs/tick-scheduling.md`：crontab / k8s CronJob / NATS-trigger 三种示例
- 30-tick 稳定性测试作为回归 baseline
- **ADR 0041**

### Phase 40 — 神经网格式激活（vision 硬伤修复）

- migration `0016_activation_traces`
- `services/activation_trace_service`：record / record_batch / count_by_pair / query_path / multi_hop_activation (BFS+decay) / apply_plasticity / decay_traces
- `scripts/activation_path.py --from X --to Y --max-hops 3` introspection CLI
- **可塑性**：高频 person pair → relation.strength 上调（`max_strength=1.0` 收敛上界）
- **安全边界**：仅对已存在 active relation 生效，不凭空造关系
- 收敛测试：30 激活 + 10 轮 plasticity → strength ∈ [0.9, 1.0]
- **ADR 0042**

### Phase 41 — 遗忘 / 压缩 / 拆分（对称可逆）

- `services/forgetting_service`：
  - Ebbinghaus-like `_forget_score(days_idle, relevance)`
  - `archive_stale_memories` (status → cold，不物理删)
  - `reactivate_memory` 对称撤销
  - `condense_cluster_candidates` 识别 condenser 候选
  - `slimming_report` 指标
- `services/entity_unmerge_service`：
  - `unmerge_person` merged → active，留痕 `events(event_type=unmerge_event)`
  - 不自动迁回关系（人工 gate）
  - `derive_unmerge_candidates_from_contradictions` 只产 candidate
- **ADR 0043**

### Phase 42 — 联邦 MVP Read-Only（B 支柱）

- `docs/superpowers/specs/federation-protocol-v1.md`
- `scripts/federation_http_server.py`：`/capabilities` / `/persons` / `/persons/{pid}` / `/memories`
- `services/federation_client.py`：`FederationClient(base_url).list_persons() / get_person() / list_memories()`
- Read-Only + 无鉴权（v0.15 MVP，localhost/VPC 用）
- e2e 真 HTTP roundtrip 测试
- **ADR 0044**

### 不变式（ADR 0045）

20 条 → **22 条**：
- **#21** 激活机制必须可 introspect（recent_traces / query_path / multi_hop 可序列化）
- **#22** 图谱写入必须有对称撤销（merge ↔ unmerge / archive ↔ reactivate / create ↔ mark_inactive）

### 三支柱达成度

- A 严格工程化：9.5 → **9.5**
- B 通用型 Skill：8 → **9.5**
- C 数字赛博生态圈：7 → **8.5**

## v0.14.0 — 2026-04-19

第七轮一次性无人值守推进：Phase 33-37。**477 passed (+41)**，新增 6 个 ADR（0034-0039）+ 1 个 mega-plan + 1 个 diff 报告 + 2 个 audit 文档。

### Phase 33 — 真 Skill 宿主

- `runtime/skill_runtime.SkillRequest/Response` 加 `schema_version="1"` + `from_dict` 校验
- **ADR 0034**：SkillRuntime v1 schema 冻结（不变式 #19）
- `runtime/adapters/mcp_adapter`：tools 2 → 6（+ scene_list/snapshot_list/import_narration/proactive_scan），新增 `build_mcp_resources` / `build_mcp_prompts`
- `scripts/mcp_server.py`：补齐 resources/list + resources/read + prompts/list + prompts/get
- `scripts/verify_skill_package.py` 解包 zip smoke
- `scripts/demo_openai_assistant.py` MCP → OpenAI function schema
- **ADR 0035**：真 Skill 宿主落地

### Phase 34 — 持续演化 Tick 闭环

- `services/time_simulator.py`：TickResult / TickBudget / run_tick / simulate / rollback_to_tick
- 编排 `state_decay` / `relation_drift` / `proactive_scan` / `self_activation` 到一次 tick
- 每 tick 后自动 snapshot（**不变式 #20**：tick 写入可回滚至任一时间点）
- `register_before/after_hook` 给 observability
- `services/tick_sanity.py`：check_growth / check_anomalies / evaluate
- `scripts/simulate_week.py --ticks 7 --budget 30` CLI
- **ADR 0036**

### Phase 35 — 媒体资产落盘

- migration `0015_media_assets` + `media_refs`
- `services/media_asset_service`：register (hash dedup) / list_by_owner / list_by_scene / link_to_memory / link_to_event / filter_by_visibility
- `services/ocr_service`：`ocr_to_memory` (vision → media + memory) / `transcribe_to_event` (audio → media + event)
- `scripts/import_image.py` 单图 OCR 导入
- `benchmarks/multimodal_retrieval_groundtruth.json` v1
- **ADR 0037**

### Phase 36 — 规模化 & 债务清理

- `docs/superpowers/state/2026-04-19-service-inventory.md`：60+ 服务审计，确认无 dead，3 条 recall / 3 条 relation 职责不重叠
- `docs/superpowers/state/2026-04-19-migration-audit.md`：15 条 migration 写/读路径
- `services/vector_index`：`SUPPORTED_BACKENDS = {auto, flat_python, sqlite_vec, faiss}` + `_require_*` 延迟 import
- `scripts/bench_scale.py`：10k+ 合成 memory 压测
- **ADR 0038**

### 不变式（ADR 0039）

18 条 → **20 条**：
- **#19** SkillRuntime schema 必须版本化（破坏性变更需 v2）
- **#20** tick 写入必须能回滚至任一时间点

### 三支柱达成度

- A 严格工程化：9 → **9.5**
- B 通用型 Skill：6 → **8**
- C 数字赛博生态圈：5 → **7**

## v0.13.0 — 2026-04-19

第六轮一次性无人值守推进：Phase 28-32。**436 passed (+26)**，新增 6 个 ADR（0028-0033）+ 1 个 mega-plan + 1 个 diff 报告。

### Phase 28 — 向量索引 & 规模化

- `services/vector_index.VectorIndex`：flat_python backend + `search_with_filter(person_ids)` 层级查询
- `services/embedding_cache.EmbeddingLRUCache`：批级 dedup + hit/miss 计数
- `db/backends.py`：SQLiteBackend + PGBackend（延迟 import psycopg）
- `runtime/sqlite_retrieval`：+ `query_text` / `embedding_client` 参数 → embedding rerank
- `services/embedding_recall`：+ `filter_person_ids` → 层级路径
- `services/memory_cluster_service`：+ `use_embedding=True/False`，Jaccard fallback
- `services/event_bus_service.NATSBackend.drain` 真实现（subscribe + asyncio timeout）

### Phase 29 — 多智能体社会

- `agents/person_agent.PersonAgent`：`from_db` / `speak` / `decide_speak`，按 `is_shared` + `owner_id` 分离 private vs shared memory
- `agents/turn_taking`：`next_speaker(agents, activation_map, turn_state)` + `orchestrate_multi_agent_turn(agents, ..., turns)`
- 不引入新表；多 agent 共享底层图谱真理（不变式 #17）

### Phase 30 — 主动图谱

- migration `0014_proactive_prefs`：mute / consent 偏好表
- `services/proactive_prefs`：`set_mute / set_consent / is_allowed`
- `services/proactive_agent`：
  - `Trigger` dataclass + 三类扫描：`scan_anniversary_triggers / scan_silence_triggers / scan_all_triggers`
  - `ProactiveIntent` + `generate_intent` (LLM JSON) + `execute_intent` (写 `proactive_intent_event`)
  - `check_budget(daily_budget)` + `proactive_scan` 一键串
- 主动写入必须经预算 + 偏好门控（不变式 #18）

### Phase 31 — 元认知（矛盾检测）

- `services/contradiction_detector`：
  - `find_candidate_pairs(similarity_min)` 用 embedding cosine 配对
  - `judge_contradiction(a, b, llm_client)` LLM JSON 判定
  - `detect_contradictions` 整合，**只读不写**
- `eval/contradiction_eval.run_contradiction_eval` 输出 `tp/fp/tn/fn/precision/recall`
- `benchmarks/contradiction_groundtruth.json` v1，3 对 groundtruth

### Phase 32 — 多模态原生（teaser）

- `llm/providers/multimodal_embedding`：
  - `MultimodalEmbeddingClient` Protocol（共享 dim 的 text/image embedding）
  - `MockMultimodalClient`（sha256 hash → 确定性向量）
  - `CLIPStubClient`（延迟 import transformers，缺包 raise）
- `cross_modal_similarity(query, candidates, k)` 跨模态 top-k
- 不写图谱，仅骨架；真接入留 v0.14（需 media_assets 迁移）

### 不变式

ADR 0027 16 条 → 18 条（参见 ADR 0033）：
- **#17** 多 agent 共享底层图谱真理
- **#18** 主动写入必须经预算 + 偏好门控

## v0.12.0 — 2026-04-19

第五轮：Phase 25-27（真 LLM / embedding 向量化 / 真生产化）。**410 passed (+18)**，新增 4 个 ADR（0024-0027）。

- 真 LLM streaming + tool_use loop（Anthropic / OpenAI 双适配器）
- EmbeddingClient Protocol + Mock + sentence-transformers extra
- migration `0013` memory_embeddings BLOB float32 + cosine 检索
- pyproject extras 矩阵 + ci.yml + pre-commit + coverage 90%
- ADR 0024 真 LLM / 0025 embedding / 0026 production / 0027 综合 + 不变式 14 → 16 条

## v0.11.0 — 2026-04-19

第四轮一次性无人值守推进：Phase 22-24。392 passed (+43)，新增 4 个 ADR（0020-0023）+ 1 个 spec RFC。

### Phase 22 — 联邦与互操作

- `services/federation_fetcher`: LocalFileBackend + HTTPBackend + TTL cache + eager 注入
- `event_bus_service`: 加 NATSBackend + RedisStreamBackend（延迟 import）+ metrics 埋点
- `services/hot_reload`: ReloadRegistry + poll_file_mtime
- `importers/migration_importer`: CSV / Notion export / Signal export
- `services/graph_serializer`: canonical JSON schema v1 + round-trip
- `docs/superpowers/specs/federation-protocol.md` RFC draft

### Phase 23 — 真集成与生产级

- `tests/integration/test_full_flow.py` 端到端 6 个测试
- `runtime/agent_runner.run_tool_use_loop` 真 tool-use 多轮
- `chat_service.run_turn` 加 tools / tool_dispatcher 参数
- `runtime/streaming.StreamingSkillResponse`
- wheel 隔离安装验证（we_together-0.11.0）
- `.github/workflows/ci.yml` + `.pre-commit-config.yaml`

### Phase 24 — 图谱叙事深度

- migration 0011 narrative_arcs + 0012 perceived_memory
- `services/narrative_service` / `perceived_memory_service` / `graph_analytics` / `associative_recall`
- `scripts/narrate.py` + `scripts/analyze.py`

### 基础设施

- pyproject / cli VERSION 0.9.0 → 0.11.0
- MANIFEST.in + include-package-data

### ADR 新增

- 0020: Phase 22 联邦与互操作
- 0021: Phase 23 真集成与生产级
- 0022: Phase 24 图谱叙事深度
- 0023: Phase 22-24 综合 + 不变式扩展至 14 条

---

## v0.10.0 — 2026-04-19

第三轮一次性无人值守推进：Phase 18-21。349 passed (+31)，新增 5 个 ADR（0015-0019）。

### Phase 18 — 生态对接真实化

- MCP stdio server (`scripts/mcp_server.py`) 接 Claude Code
- 飞书 bot 绑真实 `chat_service.run_turn`（examples/feishu-bot）
- PyPI 发布工程：MANIFEST.in / build_wheel.sh / publish.md checklist
- `.github/workflows/docker.yml`
- Obsidian md 双向同步（importer + exporter）

### Phase 19 — 多模态深化

- `AudioTranscriber` Protocol + MockAudioTranscriber + WhisperTranscriber stub
- `audio_importer` / `video_importer` / `document_importer` / `screenshot_series_importer`
- 多模态 dedup: pHash + audio fingerprint + 汉明距离近似去重
- `benchmarks/multimodal_groundtruth.json`

### Phase 20 — 社会模拟完整版

- `simulation/conflict_predictor` (SM-2)
- `simulation/scene_scripter` (SM-3)
- `services/retire_person_service` (SM-4)
- `simulation/era_evolution.simulate_era` (SM-5)
- `scripts/simulate.py` 合一 CLI

### Phase 21 — Eval 扩展

- `eval/condenser_eval` + `eval/persona_drift_eval`
- 4 个新 benchmark: condense / persona_drift / society_d / society_work
- Eval 结果统一形状 `{benchmark, total, passed, pass_rate, cases}`

### v0.9.1 — 热修

- eval groundtruth core_type 对齐 seed_society_c（`work/intimacy/friendship/...`），precision/recall/f1 从 0.0 → 1.0
- what-if mock 模式下给占位 prediction + `mock_mode` 字段
- `eval/baseline.json` 首版真实基线

### ADR 新增

- 0015: Phase 18 生态对接
- 0016: Phase 19 多模态
- 0017: Phase 20 社会模拟
- 0018: Phase 21 eval 扩展
- 0019: Phase 18-21 综合 + 不变式扩展至 12 条

---

## v0.9.0 — 2026-04-18

第二轮一次性无人值守推进：Phase 13-17。318 passed (+37)，新增 5 个 ADR（0010-0014）。

### Phase 13 — 产品化与 Onboarding

- `we-together` pip 包 + 统一 CLI (`src/we_together/cli.py`)
- Docker 多阶段 + compose（app+metrics+branch-console） + README
- `services/onboarding_flow` 5 步状态机 + `scripts/onboard.py --dry-run`
- `examples/claude-code-skill/` + `examples/feishu-bot/`（stdlib webhook）
- `docs/quickstart.md` 5 分钟从零到跑

### Phase 14 — 评估与质量

- `benchmarks/society_c_groundtruth.json`
- `src/we_together/eval/`（groundtruth_loader / metrics / relation_inference / llm_judge / regression）
- `scripts/eval_relation.py` + baseline / regression 门禁

### Phase 15 — 时间维度

- migration 0009 `persona_history` + 0010 `event_causality`
- `services/persona_history_service` / `relation_history_service` / `event_causality_service` / `memory_recall_service`
- `runtime_retrieval` 新增 `as_of` 参数（跳过 cache）
- `scripts/timeline.py` + `scripts/relation_timeline.py`

### Phase 17 — What-if Teaser

- `src/we_together/simulation/what_if_service`（LLM 推演，不改图谱）
- `scripts/what_if.py`

### EXT 收口

- `services/patch_transactional.apply_patches_transactional`（事务 ROLLBACK）
- `services/rbac_service`（Role/Scope/TokenRegistry）
- `observability/sinks`（StdoutSink + OTLPStubSink + Protocol）
- `event_bus_service` 加 LocalFileBackend + NATSStubBackend

### ADR 新增

- 0010: Phase 13 产品化
- 0011: Phase 14 评估
- 0012: Phase 15 时间维度
- 0013: Phase 17 what-if teaser
- 0014: Phase 13-17 综合 + 不变式扩展至 10 条

---

## v0.8.0 — 2026-04-18

一次性无人值守推进完成五个大目标：Phase 8-12。281 passed，新增 8 个 ADR。

### Phase 8 — 图谱活化（Neural Mesh）

- NM-1 多场景并发激活（`runtime/multi_scene_activation`）
- NM-2 记忆聚类 + LLM 凝练（`memory_cluster_service` / `memory_condenser_service`）
- NM-3 Persona drift（`persona_drift_service`）
- NM-4 自发 pair 交互（`self_activate_pair_interactions`）
- NM-5 跨场景 echo（retrieval `cross_scene_echoes`）
- NM-6 冷记忆归档 + 恢复（migration 0007 + `memory_archive_service`）

### Phase 9 — 宿主生态

- HE-1 `SkillRequest.tools` 跨宿主抽象
- HE-2 agent loop（tool_call/result 循环 + events 链）
- HE-3 `.weskill.zip` 打包分发（`packaging/skill_packager`）
- HE-4/5/6/7 飞书 / LangChain / Coze / MCP adapter（纯函数）

### Phase 10 — 真实世界数据化

- RW-1 iMessage 本地 chat.db importer
- RW-2 微信明文 sqlite importer
- RW-3 邮件 MBOX 批处理
- RW-4 VLM image importer + `VisionLLMClient`
- RW-5 社交 JSON dump importer
- RW-6 `evidence_dedup_service` 内容 hash 去重

### Phase 11 — 联邦与协同

- FE-1 migration 0008 `external_person_refs` + `federation_service`
- FE-2 本地 jsonl 事件总线（`event_bus_service`）
- FE-3 裁决 mini-console（stdlib http.server + bearer token）
- FE-4 多租户路径路由（`tenant_router`）

### Phase 12 — 生产化硬化

- HD-1 结构化日志 + trace_id（`observability/logger`）
- HD-2 Metrics + Prometheus 导出
- HD-3 toml 配置系统
- HD-4 `WeTogetherError` 异常层级
- HD-5 `bench_large.py` 大规模压测
- HD-6 schema version 漂移检测
- HD-8 `patch_batch` 批量应用
- HD-9 retrieval cache 预热

### 其他

- ADR 0004-0009 共 6 个新决策文件
- current-status.md 按 Phase 收尾同步（216 → 234 → 254 → 260 → 268 → 281）

## v0.7.0 — 2026-04-17 之前

见 `docs/superpowers/state/current-status.md` Phase 1-7 段落。
