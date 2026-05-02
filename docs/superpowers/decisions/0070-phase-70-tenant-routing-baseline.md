---
adr: 0070
title: Phase 70 — 多租户脚本路由基线
status: Accepted
date: 2026-04-19
---

# ADR 0070: Phase 70 — 多租户脚本路由基线

## 状态
Accepted — 2026-04-19

## 背景

项目很早就有 `tenant_router`，但它长期停留在“路径函数存在，脚本层未接线”的状态。结果是：

- `bootstrap.py` 仍默认只操作 `<root>/db/main.sqlite3`
- `seed_demo.py` 无法把 demo 社会灌进某个 tenant
- `federation_http_server.py` 只能服务 default root

这意味着 Phase 11 里关于多租户的声明还没有真正进入 CLI / server 的使用路径。

## 决策

### D1. 脚本层统一支持 `--tenant-id`

本阶段把 `tenant_router` 接到三个关键入口：

- `scripts/bootstrap.py`
- `scripts/seed_demo.py`
- `scripts/federation_http_server.py`

规则：

- `tenant_id=None|default` → 原路径，保持向后兼容
- `tenant_id=<name>` → `<root>/tenants/<tenant_id>/...`

### D2. 先做“路径隔离”而不是“权限隔离”

这阶段仍不做 RBAC / token -> tenant 的强绑定。

原因：

- 当前目标是把 tenant routing 从 paper state 拉进真实运行路径
- 权限隔离属于下一层能力，不能和最小接线一起耦合

### D3. 联邦 server 必须能直接服务 tenant root

`federation_http_server.py --tenant-id alpha` 应只暴露：

- `tenants/alpha/db/main.sqlite3` 里的 persons / memories

而不是 default tenant 的数据。

## 版本锚点

- 更新脚本：`bootstrap.py` / `seed_demo.py` / `federation_http_server.py`
- 新测试：`tests/services/test_phase_70_mw.py`
- 测试基线：与当前主线一起维持全绿

## 非目标

- tenant-aware retrieval package 全链路透传
- token -> tenant 绑定
- cross-world migration
- namespace-aware federation payload

## 拒绝的备选

### 备选 A：只改 `tenant_router` 文档，不改脚本

拒绝原因：继续停留在纸面多租户。

### 备选 B：一口气上完整多 world / 多租户权限体系

拒绝原因：范围过大，且不利于快速把已有 stub 激活。

## 下一步

1. 给更多 CLI 入口接 `--tenant-id`
2. 增加 cross-tenant leakage negative tests
3. 再把 federation / retrieval / RBAC 的 tenant contract 收到一起
