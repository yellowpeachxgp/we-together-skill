# Phase 65-70 Progress Snapshot

**Date**: 2026-04-22
**Status**: Phase 65-70 delivered locally; Phase 71 EPIC in progress
**Current test baseline**: `761 passed, 4 skipped`

## 完成情况

### Phase 65

- vector extra
- native backend integration tests
- bench archive helper
- native backend nightly smoke
- ADR 0067

### Phase 66

- `100k / 1M` compare benchmark
- compare archives in `benchmarks/scale/`
- v2 scale report
- ADR 0069

### Phase 67-68

- federation write path
- `FederationClient.create_memory(...)`
- `federation_e2e_smoke.sh`
- HTTP error path coverage (`400/401/403/422/429`)
- ADR 0068

### Phase 69

- yearly LLM usage audit
- monthly usage/cost artifacts
- provider dry-run check

### Phase 70

- tenant CLI rollout across almost all db-backed scripts
- tenant hardening (`normalize_tenant_id`)
- cross-tenant negative tests
- tenant introspection in summary surfaces
- ADR 0070 / 0071 / 0072

## 本地已完成

- release notes v0.19.0
- README / HANDOFF / current-status 第一轮收口
- version bump / wheel / local tag

## 仍待外部条件

- real provider 7-day / 30-day / 365-day runs
- PyPI 正式发布
- remote push / GitHub Release

## 仍有意不做

- `package_skill.py` tenant 化
- `demo_openai_assistant.py` tenant 化
- `bench_scale.py` tenant 化（暂缓）

## Subsequent note (2026-04-23)

- Phase 71 文档收口后，本地已起步 Phase 72：`contradiction/unmerge operator gate`
- 当前语义是：`contradiction_detector` 只读不写，先开 `local_branch`，人工 resolve 后才真正执行 `unmerge_person`
- 详见 [`2026-04-23-v0-20-candidate-ordering.md`](2026-04-23-v0-20-candidate-ordering.md)
