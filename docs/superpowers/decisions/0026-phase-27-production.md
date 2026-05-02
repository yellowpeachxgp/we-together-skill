# ADR 0026: Phase 27 — 规模与真生产（Scale & Production）

## 状态
Accepted — 2026-04-19

> Current release note: tag-push publishing was a historical Phase 27 plan. The active workflow is manual `workflow_dispatch` with strict gates before upload; see `.github/workflows/publish.yml` and `docs/publish.md`.

## 背景
v0.11.0 已有本地 wheel 验证、基础 CI、bench_large 骨架，但没跑过大规模、没发 PyPI、没 coverage、没 tag-push 自动发布、索引未审查。

## 决策

### D1. PyPI 发布基础设施
`.github/workflows/publish.yml`：历史计划为 `push tag v*` 触发 build + `twine upload`（需 secret `PYPI_TOKEN`）。当前实现已改为人工 `workflow_dispatch`，先跑 pytest / strict gate / build / twine check，再上传精确 wheel/sdist artifact。`docs/publish.md` 完整 checklist 含 TestPyPI 流程；`docs/release_notes_template.md` 模板。

### D2. v0.12.0 wheel 真隔离验证
`pyproject` + `cli.VERSION` 升级至 0.12.0；本地 `python -m build` 产出 `we_together-0.12.0-py3-none-any.whl`，全新 venv 安装 → `we-together version` 正确输出。

### D3. CI 增强
`.github/workflows/ci.yml`（已有）+ `.pre-commit-config.yaml`（已有）；`.coveragerc` 定义 `source` 与 `omit`（延迟 import 的 provider 排除）；`pytest-cov` 加入 dev extras。

### D4. WAL 模式
`bootstrap_project` 在 migration 后执行 `PRAGMA journal_mode=WAL`。允许并发读 + 提升崩溃恢复性。

### D5. optional extras 扩展
`pyproject` 加 `[nats]` / `[redis]` / `[embedding]` extras，方便用户按需装：
```
pip install "we-together-skill[anthropic,embedding,nats]"
```

### D6. Coverage 基线 90%
本轮全量 pytest --cov 跑出 **90%** 总覆盖（provider SDK 真路径被 omit）。作为 v0.12.0 首版 baseline。

## 后果
正面：真发布路径跑通；extras 扩展让部署更细粒度；WAL 对高并发有提升；coverage 给工程可信度加一锤定音。
负面：NATS drain 只有 stub（subscribe+timeout 留 Phase 28+）；1M 压测只定义了 CLI 开关，真跑需要特殊硬件；PyPI 实发需要账号 token。

## 后续
- 真发 pypi.org（需账号准备）
- 1M 规模真跑 + 性能报告
- NATS drain + Redis Stream consumer 真实现
