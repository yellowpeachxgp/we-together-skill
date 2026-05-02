# ADR 0008: Phase 12 — 生产化硬化（Hardening）

## 状态

Accepted — 2026-04-18

## 背景

Phase 8-11 让系统功能面拉宽，但生产运行的基础设施（可观测性、配置、错误分级、性能验证、schema 演进安全）仍依赖临时手段。本 ADR 汇总 Phase 12 的九项硬化决策，目标是"可长期运行、可排错、可上报"。

## 决策

### D1. 轻量结构化日志（不引 structlog）

`observability/logger.py` 用 stdlib `logging` + `contextvars` 实现：
- `bind_trace_id(trace_id=None)` 上下文注入
- `get_logger(name)` 返回 `we_together.<name>` logger，输出 JSON 行
- `log_event(logger, event, **fields)` 便利函数
保持零新依赖；未来若需要扩展 sampling/sink，可无缝替换。

### D2. 零依赖 Metrics 累加器

`observability/metrics.py` 内存 counter/gauge + `export_prometheus_text()`。`scripts/metrics_server.py` 用 stdlib HTTPServer 暴露 `/metrics`。核心路径调 `counter_inc("patches_applied", labels={...})` 即可。

### D3. 配置系统：toml + env 两级合并

`config/loader.py` 定义 `WeTogetherConfig` dataclass；`load_config(path)` 读 toml，再用 `WE_TOGETHER_*` env 覆盖。`we_together.sample.toml` 提供模板。

### D4. 错误分级：`WeTogetherError` 层级

`errors.py` 暴露 `WeTogetherError` / `IngestError` / `RetrievalError` / `PatchError` / `ConfigError` / `SchemaVersionError`。上层可按 domain 统一捕获。目前现有代码继续抛 `ValueError`，后续增量迁移。

### D5. Schema 版本检测

`db/schema_version.check_schema_version(db_path, migrations_dir)`：若 db 记录的 migrations 在本地缺失，抛 `SchemaVersionError`。`bootstrap_project` 在 `run_migrations` 之前预检。防止"删文件 / 回退到老版本"导致的隐式漂移。

### D6. Patch 批量应用

`services/patch_batch.apply_patches_bulk(db_path, patches, stop_on_error=True)`：顺序 apply，单 patch 失败时返回 `{applied_count, failed_count, failures}`。完整事务化留给后续（需要先 refactor `apply_patch_record` 接受外部 conn）。

### D7. Retrieval cache 预热

`services/cache_warmer.warm_retrieval_cache(db_path)` 遍历 active scenes 以固定 input_hash 调 build，把 cold 检索成本前移。适合作为 daily_maintenance 首步。

### D8. 大规模压测脚手架

`scripts/bench_large.py`：插入 N person（默认 10_000），冷/热检索延迟 p50/p95 报告。不强求 CI 跑满 10 万，规模可调。

### D9. 依赖锁定（轻量）

保持 `pyproject.toml` 的现有依赖约束；运行时新引入的都是 stdlib。本 ADR 显式记录"Phase 12 不引入任何新外部依赖"这一决策。

## 后果

### 正面

- 任何核心调用都可通过 `log_event` / `counter_inc` 产出可观测数据
- 配置与环境变量的优先级清晰
- 数据库 schema 漂移会在 bootstrap 期立即暴露
- 性能回归可用 `bench_large.py` 定量比较

### 负面 / 权衡

- 日志/metrics 目前是进程内；多实例部署需要 sink 到外部存储
- patch_batch 不是真正事务，仅顺序应用 + 停在错误
- 错误分级未迁移现有抛 ValueError 的代码，留给增量重构

### 后续

- Phase 13（未来）：日志/metrics sink 可插拔；迁移 ValueError → domain Error
- Phase 13（未来）：apply_patch_record 接受外部 conn，实现真正事务批处理
