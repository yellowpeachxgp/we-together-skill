---
adr: 0056
title: Phase 54 — 社区就绪（CONTRIBUTING + 对比文档 + mkdocs）
status: Accepted
date: 2026-04-19
---

# ADR 0056: Phase 54 — 社区就绪

## 状态
Accepted — 2026-04-19

## 背景
55 条 ADR 都写了，但**一份 CONTRIBUTING 都没有**。外部贡献者来到项目：
- 不知道从哪开始
- 不知道怎么与 Mem0 / Letta / LangMem 比较选型
- 找不到 Good First Issue
- 没有 GitHub 模板指引

B 支柱"真被消费"的最后一英里包括**社区就绪**，这一 phase 做完。

## 决策

### D1. 治理四件套
- `CONTRIBUTING.md`：开发流程 + 编码规约 + 不变式清单
- `CODE_OF_CONDUCT.md`：Contributor Covenant 2.1 改编
- `SECURITY.md`：漏洞报告流程 + 当前已知边界
- `GOVERNANCE.md`：三级维护者 + 决策流程 + release

### D2. 对比文档 3 份
- `vs_mem0.md` / `vs_letta.md` / `vs_langmem.md`
- 公开资料基础上的客观对比；鼓励 PR 修正
- **不贬低其他项目**，只列差异与各自适用场景

### D3. mkdocs 最小骨架
- `mkdocs.yml` 不依赖 material 主题（保持轻量）
- `docs/index.md` 作首页
- 主要 nav：getting-started / hosts / comparisons / tutorials / plugins / tick-scheduling
- 真构建部署留 v0.18（GitHub Pages 或自托管）

### D4. GitHub 模板
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/PULL_REQUEST_TEMPLATE.md`（含不变式 checklist）

### D5. Good First Issues
- `docs/good_first_issues.md` 列 20 条
- 难度分 🟢 15 分钟 / 🟡 1-2 小时 / 🔴 半天 / ⚫ 多天
- 每条都有具体文件路径 + 参考 ADR

### D6. 一份 Tutorial 起步
- `docs/tutorials/family_graph.md`：家庭图谱 15 分钟教程
- 其他 tutorial（读书会 / DevOps）留给社区贡献（是 Good First Issue）

## 版本锚点
- 新文件: CONTRIBUTING / CODE_OF_CONDUCT / SECURITY / GOVERNANCE / mkdocs.yml / docs/index.md / docs/good_first_issues.md / docs/tutorials/family_graph.md / docs/comparisons/{vs_mem0,vs_letta,vs_langmem}.md / .github/{ISSUE_TEMPLATE,PULL_REQUEST_TEMPLATE}
- 无新 migration
- 无新 service
- 无新不变式（保持 25 条）

## 非目标（v0.18）
- mkdocs 真构建 + GitHub Pages 部署
- mkdocs-material 主题美化
- 视频 tutorial
- Discord / 邮件列表
- 多语言 README
- Claude Skills marketplace 真提交材料（留 Phase 56）

## 拒绝的备选
- 空 CONTRIBUTING（只写"欢迎贡献"）：对外部没帮助
- 硬写死对比结论：每个项目都在演化；留 disclaimer + 欢迎 PR
- 强制 mkdocs-material：引依赖；vanilla mkdocs 先跑起来
