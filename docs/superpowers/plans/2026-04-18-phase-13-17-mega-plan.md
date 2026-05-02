# Phase 13-17 Mega Plan 归档（2026-04-18 第二轮无人值守）

## 目标

v0.8.0 (281 passed, ADR 0009 定稿) 之后，继续一次无人值守连续推进：把 we-together-skill 从 "功能齐全开发 SDK" 推到 "可被非开发者用 + 质量可测 + 时间维度完整" 的 v0.9.0 状态。

## 达成情况

| Phase | 主题 | 切片 | 关键产出 | 测试增量 |
|---|---|---|---|---|
| 13 | 产品化 | PD-1..6 | pip `we-together` CLI / Docker / onboarding 状态机 / 两个 demo / Quickstart | +7 |
| 14 | 评估与质量 | EV-1..6 | benchmarks + groundtruth + metrics + judge + baseline 回归 | +10 |
| 15 | 时间维度 | TL-1..6 | persona_history / relation_history / event_causality / as_of retrieval / memory_recall | +13 |
| 17 | What-if teaser | SM-1 | simulation/what_if_service 单切片 | +5 |
| EXT | 收口 | 1..5 | patch_transactional / RBAC / sinks / NATSStub | +9 |

**总增量**：281 → 318 passed（+37），commits ≈ 14。

## 新增文件（摘要）

- `src/we_together/cli.py`（pip 统一入口）
- `src/we_together/services/onboarding_flow.py` / `persona_history_service.py` / `relation_history_service.py` / `event_causality_service.py` / `memory_recall_service.py` / `rbac_service.py` / `patch_transactional.py`
- `src/we_together/eval/`（5 模块）
- `src/we_together/simulation/what_if_service.py`
- `src/we_together/observability/sinks.py`
- `benchmarks/society_c_groundtruth.json`
- `db/migrations/0009_persona_history.sql` + `0010_event_causality.sql`
- `docker/Dockerfile` + `docker-compose.yml` + `.dockerignore` + `docker/README.md`
- `examples/claude-code-skill/` + `examples/feishu-bot/`
- `scripts/onboard.py` / `eval_relation.py` / `timeline.py` / `relation_timeline.py` / `what_if.py`
- `docs/quickstart.md` / `docs/onboarding.md`
- `docs/superpowers/decisions/0010-0013.md`

## 不在本轮范围

- 完整 point-in-time retrieval（当前 as_of 只过滤 recent_changes）
- memory condenser / persona drift 的专门 benchmark
- event bus 真实 NATS/Redis Stream backend（只留 stub）
- `apply_patch_record` 本体 refactor 接受外部 conn（transactional 版本通过副本绕开）
- prompts 模板目录集中化（Phase 18+ 做）
- 飞书 bot 真实 chat_service 绑定（当前是 echo）

## 下一轮候选方向（Phase 18+）

- RW-续（音频/视频 importer，见 Phase 16 草案）
- SM-续（conflict predictor / scene scripter / era evolution）
- 完整多租户 + rbac 集成（branch_console / tenant_router / rbac_service 三者接线）
- Phase 14 eval 拓展到 condenser / drift 质量评估
