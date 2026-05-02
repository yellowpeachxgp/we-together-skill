---
adr: 0046
title: Phase 44 — Plugin / Extension 架构
status: Accepted
date: 2026-04-19
---

# ADR 0046: Phase 44 — Plugin / Extension 架构

## 状态
Accepted — 2026-04-19

## 背景
v0.15 之前每加 importer / provider / service 都要改核心代码或 fork 项目。vision "**可扩展**" 字面提及但未兑现。第三方无法在不动 we-together 的前提下增加能力。这是 B 支柱走向社区的隐藏门槛。

## 决策

### D1. 4 类扩展点
用 Python `entry_points` 规范：
- `we_together.importers` → Importer
- `we_together.services` → Service
- `we_together.providers` → Provider (provider_kind: llm/embedding/vision/audio)
- `we_together.hooks` → Hook (event_type: tick.before/tick.after/patch.applied 等)

### D2. plugin_registry
- `discover(reload)` 扫描 entry_points；错误隔离（一个失败不影响其他）
- `register(kind, plugin, source='manual')` 手动注册
- `list_by_kind(kind, include_disabled)` / `get_by_name(kind, name)` 查询
- `disable / enable / unregister` 运行时管控
- `status()` 面板级聚合（`by_kind` + `load_errors`）

### D3. 校验规则
每个 plugin 必须有：
- `name: str`
- `plugin_api_version: str`（当前 "1"）
- kind 特定：Provider 必须 `provider_kind`；Hook 必须 `event_type`

违反 → `PluginLoadError`，**不 raise 出 discover**（隔离）。

### D4. API Version
- `PLUGIN_API_VERSION = "1"`
- 破坏性变更 → "2"；向后兼容扩展属 additive
- plugin 声明版本 ≠ expected 拒绝加载

### D5. CLI + 文档 + 示例
- `scripts/plugins_list.py` 查看状态
- `docs/plugins/authoring.md` 开发指南
- `examples/plugin_example_minimal/` 可 pip install 的最小包

## 不变式（新，v0.16 第 23 条）
**#23**：扩展点必须通过 plugin registry 注册；核心 we-together 代码不得为特定 importer/provider/service 硬编。
> 违反则第三方无法在不 fork 的前提下扩展；可扩展性失效。

## 非目标（v0.17+）
- 真热重载（当前 reset + rediscover 够用）
- plugin 签名（基于哈希/签名证书）
- plugin marketplace
- 动态依赖解析（pip install at runtime）

## 版本锚点
- tests: +12 (test_phase_44_pl.py)
- 文件: `src/we_together/plugins/__init__.py` / `plugin_registry.py` / `scripts/plugins_list.py` / `docs/plugins/authoring.md` / `examples/plugin_example_minimal/`
- Schema 不变（纯 runtime 扩展）

## 拒绝的备选
- pluggy（pytest 用的）：引入依赖；stdlib entry_points 够用
- 动态 `importlib.import_module(str)`：灵活但不安全，entry_points 有 pip 解析层保护
- 只用手动 register：不能被外部 pip install 发现，违背"可扩展"目标
