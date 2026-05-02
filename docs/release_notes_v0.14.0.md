# Release Notes — v0.14.0 (2026-04-19)

**Theme**: 真 Skill 宿主 + 持续演化 Tick 闭环 + 媒体资产落盘 + 规模化债务清理

**Test baseline**: 477 passed
**ADR 总数**: 39
**Migrations**: 15
**不变式**: 20

## 新能力

### 真 Skill 宿主
- `SkillRequest/Response` schema 冻结 v1（`schema_version="1"`）。破坏性变更需 v2，不在 v1 里 in-place 改（**不变式 #19**）
- MCP server 补齐完整协议：tools/list + tools/call + resources/list + resources/read + prompts/list + prompts/get
- 6 个 MCP 工具：run_turn / graph_summary / scene_list / snapshot_list / import_narration / proactive_scan
- OpenAI Assistants demo：MCP tools → function schema
- `scripts/verify_skill_package.py` 解包 zip smoke

### 持续演化 Tick 闭环
- `services/time_simulator.py`：
  - `TickResult` / `TickBudget` dataclass
  - `run_tick(db, tick_index, budget, llm_client)` 单次编排 decay + drift + proactive + self_activation
  - `simulate(db, ticks, budget)` N 次连续 tick
  - 每 tick 自动 snapshot（**不变式 #20**：tick 写入可回滚至任一时间点）
  - `register_before/after_hook` 观测接入点
- `services/tick_sanity.py`：`check_growth` / `check_anomalies` / `evaluate`（健康度报告）
- `scripts/simulate_week.py --ticks 7 --budget 30` CLI

### 媒体资产落盘
- Migration `0015_media_assets`：
  - `media_assets(media_id, kind, content_hash, visibility, summary, ...)`
  - `media_refs(media_id, target_type, target_id)` 多对多到 memory / event
- `services/media_asset_service`：register (hash dedup) + list_by_owner/scene + link_to_memory/event + filter_by_visibility
- `services/ocr_service`：
  - `ocr_to_memory(image_bytes, owner_id, vision_client)` → media + memory
  - `transcribe_to_event(audio_bytes, owner_id, transcriber)` → media + event
- `scripts/import_image.py --image path --owner p1 --visibility shared`
- `benchmarks/multimodal_retrieval_groundtruth.json` v1

### 规模化 & 债务清理
- `docs/superpowers/state/2026-04-19-service-inventory.md`：60+ 服务按引用密度审计
- `docs/superpowers/state/2026-04-19-migration-audit.md`：15 条 migration 写/读路径
- `services/vector_index`：`SUPPORTED_BACKENDS = {auto, flat_python, sqlite_vec, faiss}`；真 backend 延迟 import
- `scripts/bench_scale.py --n 10000 --queries 50` 规模化压测

## 三支柱达成度

- A 严格工程化：9 → **9.5**
- B 通用型 Skill：6 → **8**
- C 数字赛博生态圈：5 → **7**

## 不变式

ADR 0039 把不变式从 18 扩展至 20：
- **#19** SkillRuntime 请求/响应 schema 必须版本化
- **#20** tick 写入必须能回滚至任一时间点

## 升级路径

```bash
pip install we-together==0.14.0  # 从 PyPI 后续发布
# 或
git pull && .venv/bin/pip install -e .
.venv/bin/python scripts/bootstrap.py --root .
```

旧 `SkillRequest` 代码无需改动（`schema_version` 默认 "1"）。

## 留给 v0.15 的事

- 真 sqlite-vec / FAISS 集成 + 10k-100k 压测报告归档
- multi_agent_chat.py REPL + simulate_week 真执行报告
- federation 真 RPC（替换 stub）
- tick 真调度（crontab / NATS-trigger 示例）
- Claude Skills marketplace 上架流程
- PyPI 正式发布

## 详细文档

- [Phase 33-37 mega-plan](superpowers/plans/2026-04-19-phase-33-37-mega-plan.md)
- [Phase 33-37 diff 报告](superpowers/state/2026-04-19-phase-33-37-diff.md)
- [Service Inventory](superpowers/state/2026-04-19-service-inventory.md)
- [Migration Audit](superpowers/state/2026-04-19-migration-audit.md)
- ADR 0034 / 0035 / 0036 / 0037 / 0038 / 0039
