# Phase 18-21 Mega Plan 归档（2026-04-19 第三轮无人值守）

## 目标

v0.9.0 (318 passed, 14 ADR) → v0.10.0：真实宿主接入 + 多模态 + 社会模拟完整版 + eval 扩展。

## 达成情况

| Phase | 主题 | 切片 | 关键产出 | 测试增量 |
|---|---|---|---|---|
| v0.9.1 | 热修 | FIX-1..4 | eval core_type 对齐 / what-if mock fallback / baseline / patch_transactional 文档化妥协 | 0（hotfix） |
| 18 | 生态真实化 | RE-1..5 | MCP stdio server / 飞书实绑 / PyPI checklist / Docker CI / Obsidian 双向 | +8 |
| 19 | 多模态深化 | MM-1..6 | audio / video / document / screenshot + pHash / audio fp | +13 |
| 20 | 社会模拟完整版 | SM-2..5 | conflict_predictor / scene_scripter / retire_person / era_evolution | +6 |
| 21 | Eval 扩展 | EV-7/8/10 | condenser eval / persona drift eval / benchmark 4 个扩容 | +4 |

**总增量**：318 → 349 passed（+31），commits ≈ 10。

## 新增文件（摘要）

- `scripts/mcp_server.py` + `examples/mcp-server/README.md`
- `examples/feishu-bot/server.py`（真绑）+ `examples/obsidian-plugin/`
- `MANIFEST.in` + `scripts/build_wheel.sh` + `docs/publish.md`
- `.github/workflows/docker.yml`
- `src/we_together/llm/providers/audio.py`
- `src/we_together/importers/{audio,video,document,screenshot_series,obsidian_md}_importer.py`
- `src/we_together/services/{retire_person,obsidian_exporter}_service.py`
- `src/we_together/simulation/{conflict_predictor,scene_scripter,era_evolution}.py`
- `src/we_together/eval/{condenser_eval,persona_drift_eval}.py`
- `benchmarks/{condense,persona_drift,society_d,society_work,multimodal}_groundtruth.json`
- `scripts/simulate.py` / `scripts/import_audio.py`
- `docs/superpowers/decisions/0015-0019.md`（5 个新 ADR）

## 不在本轮范围

- PyPI 实际发布（只准备 checklist）
- 真 NATS 集成（Phase 18 只留 stub）
- 10 万/百万 person 压测（留 Phase 22）
- Docker compose smoke（只验证单镜像）
- branch_console 完整 RBAC 集成

## 下一轮候选方向

- Phase 22 规模与真依赖（100 万 person / imagehash / PG 后端）
- Phase 23 真 HITL（完整 fastapi branch_console + RBAC）
- Phase 24 多语言 prompt i18n
- Phase 25 联邦协议 RFC
