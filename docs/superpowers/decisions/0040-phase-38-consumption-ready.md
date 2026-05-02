---
adr: 0040
title: Phase 38 — 消费就绪（三路宿主 + 面板 + 上手文档）
status: Accepted
date: 2026-04-19
---

# ADR 0040: Phase 38 — 消费就绪

## 状态
Accepted — 2026-04-19

## 背景
v0.14 把 Skill 宿主的"能跑"做齐了（MCP 全协议 + OpenAI Assistants demo），但距离"真被消费"仍缺"**如何装 / 如何看 / 如何验 / 如何示范**"这 4 份实体文档 + 观测面板。B 支柱从 8 → 10 的最后一段是**让用户能 5 分钟内真跑起来**。

## 决策

### D1. Dashboard 裸 HTML + JSON + /metrics 合一
- `scripts/dashboard.py`：单文件 `HTTPServer`
- 路由：
  - `/` / `/index.html` → 静态 HTML（无 JS 框架，自含 fetch）
  - `/api/summary` → 图谱 counts JSON
  - `/api/tick` → 近期 tick snapshot 列表
  - `/metrics` → Prometheus 文本（复用 `observability.metrics`）
- 零外部依赖；默认 127.0.0.1:7780

### D2. e2e smoke 脚本
- `scripts/skill_host_smoke.py --root /tmp/foo`
- 4 步：bootstrap → seed_society_c → run_turn → dashboard_summary
- 输出 `{"ok": bool, "results": [...]}` 给 CI / 手工验证用

### D3. 三份宿主接入文档
- `docs/hosts/claude-desktop.md`：Settings → Developer → Edit Config 步骤
- `docs/hosts/claude-code.md`：`claude mcp add we-together -- ...`
- `docs/hosts/openai-assistants.md`：`demo_openai_assistant.py` 导 schema + tool call 回调
- 每份都包含：Install / Config / 验证 / 故障排查

### D4. Getting Started 5 分钟路径
- `docs/getting-started.md`：7 步从 `git clone` 到接入 Claude Code

### D5. Bug fix（附带收获）
审 dashboard 时发现 `time_simulator._make_snapshot_after_tick` 之前写入的列 `scene_id / patch_refs_json` 不在 `snapshots` 表里（是旧 schema 想象），Phase 34 因为有 try/except 吞掉错误所以测试绿但实际未写 snapshot。本 ADR 修：仅使用 `snapshots` 表真实列 `snapshot_id / summary / created_at`，让 `snapshot_id` 真正被写入。

## 版本锚点
- tests: +8 (test_phase_38_cr.py)
- 文件: `scripts/dashboard.py` / `scripts/skill_host_smoke.py` / `docs/getting-started.md` / `docs/hosts/{claude-desktop,claude-code,openai-assistants}.md`
- Bug fix: `services/time_simulator._make_snapshot_after_tick`

## 非目标（留 v0.16）
- 真 Claude Skills marketplace 上架（外部审批）
- Dashboard JS 框架（React/Vue）：当前纯 HTML 足够；加框架只为了 push 复杂性
- OpenAI Assistants streaming tool call（需 key 真跑）
- 用户遥测：不放服务器，保留本地

## 拒绝的备选
- FastAPI 做 dashboard：引入依赖；`http.server` 够用
- 捆绑 prometheus_client：重；手写 Prometheus 文本格式更轻
