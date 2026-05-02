---
adr: 0071
title: Phase 70 — tenant id 校验与 cross-tenant 负向测试
status: Accepted
date: 2026-04-22
---

# ADR 0071: Phase 70 — tenant id 校验与 cross-tenant 负向测试

## 状态
Accepted — 2026-04-22

## 背景

在上一轮推进后，tenant 路由已经进入大量 CLI / server 入口，但还存在两个风险：

1. `tenant_id` 只是字符串拼路径，尚未限制非法输入，理论上存在路径逃逸或奇怪目录名。
2. 很多测试证明“tenant 能跑”，但对“default 与 tenant 不串库”的负向证明仍然不够系统。

如果继续只补 `--tenant-id` 参数，而不先把这层边界定住，后面只会把风险复制到更多脚本。

## 决策

### D1. `tenant_id` 必须先 normalize，再 resolve

新增 `normalize_tenant_id()`：

- `None` / `""` / 空白 → `default`
- `default` → 原路径
- 非 default tenant 必须匹配：
  - 只允许 `[A-Za-z0-9_-]`
  - 长度 `1..64`
  - 禁止 `/`、`\`、`.`、`..`、空格

### D2. `resolve_tenant_root()` / `resolve_tenant_db_path()` 统一走校验

所有脚本和服务不再自己拼 tenant 路径，统一依赖：

- `resolve_tenant_root()`
- `resolve_tenant_db_path()`

这样 tenant 输入规则只维护一份。

### D3. 脚本级拒绝非法 tenant

最小要求：

- 非法 `tenant_id` 时脚本必须失败退出
- stderr 中包含 `invalid tenant_id`

本期先通过 `bootstrap.py` 的 subprocess 测试把这条钉住。

### D4. 增强 cross-tenant 负向证明

新增测试重点不是“tenant alpha 能跑”，而是：

- tenant server 不能读到 default tenant 的数据
- default root 不能读到 alpha tenant 的数据
- tenant 路由后的 CLI 在 tenant root 上工作，同时 default root 仍保持空或缺失

## 版本锚点

- `src/we_together/services/tenant_router.py`
- `tests/services/test_federation_bus_tenant.py`
- `tests/services/test_phase_70_mw.py`

## 非目标

- token -> tenant 绑定
- world namespace metadata
- tenant-aware RBAC
- 跨 tenant 数据迁移

## 拒绝的备选

### 备选 A：允许任意字符串 tenant id

拒绝原因：路径安全边界过弱。

### 备选 B：等 Phase 71 再统一收口

拒绝原因：当前 tenant 接线已经很广，继续拖会让问题扩散。

## 下一步

1. 继续补 cross-tenant leakage negative tests。
2. 在剩余 CLI 接线前优先复用 tenant_router，而不是手工拼路径。
3. 后续若接 RBAC，再把 `tenant_id` 与 token scope 正式绑定。
