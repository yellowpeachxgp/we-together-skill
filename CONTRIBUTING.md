# Contributing to we-together

欢迎参与 we-together——一个 Skill-first 的社会 + 世界图谱运行时。

## 快速起步

```bash
git clone <repo> we-together && cd we-together
python -m venv .venv && source .venv/bin/activate
pip install -e .
python scripts/bootstrap.py --root .
.venv/bin/python -m pytest -q   # 期望 628+ passed
```

参考 [`docs/getting-started.md`](docs/getting-started.md) 里的 5 分钟路径。

## 我能贡献什么？

### 代码贡献
- **Plugin**：新 importer / provider / service / hook（参见 [`docs/plugins/authoring.md`](docs/plugins/authoring.md)）
- **Importer**：新数据源适配（Slack / Discord / 飞书 / Notion / Signal）
- **Host adapter**：新 Skill 宿主（Coze / LangChain / 飞书机器人）
- **新不变式**：识别一条应该冻结的规则，提 ADR

### 非代码贡献
- **文档**：tutorial / 翻译 / 对比
- **benchmark**：在真环境下跑 `simulate_year` 归档报告
- **issue**：bug report / feature request / 使用案例分享
- **社区**：回答问题 / 讨论设计

## 开发流程

### 1. 找一个 issue
- 看 [Good First Issue](docs/good_first_issues.md)
- 或在 issues 区提一个先讨论

### 2. 分支命名
```
feat/xxx / fix/xxx / docs/xxx / refactor/xxx
```

### 3. 写代码
**必读：**
- [ADR 目录](docs/superpowers/decisions/)——55 条决策
- [当前不变式 25 条](docs/superpowers/decisions/0052-phase-44-50-synthesis.md)——违反这些会被 reject
- [Service Inventory](docs/superpowers/state/2026-04-19-service-inventory.md)——避免重复造轮子

### 4. 测试
```bash
.venv/bin/python -m pytest -q     # 全量
.venv/bin/python -m pytest tests/services/test_your.py -v   # 单测
```

**覆盖要求**：新代码 ≥ 90%。

### 5. 开 PR
- 填 PR template
- 确认通过 CI
- 至少一位 maintainer review

## 编码规约

- Python 3.11+
- 类型注解必须（at least on public API）
- 不引入硬依赖（新依赖走 optional extras）
- 不硬编 provider（走 plugin entry_points）
- 新 service 加入 Service Inventory
- 新 migration 必须在 ADR 里说明写路径与读路径

## 不变式遵守

违反**任何一条**不变式必须有明确 ADR 论证：
- #1-#18（Phase 1-32 累计）
- #19 SkillRuntime v1 schema 版本化
- #20 tick 写入可回滚
- #21 激活可 introspect
- #22 写入对称撤销
- #23 扩展点 plugin registry 注册
- #24 时间敏感读 graph_clock
- #25 跨图谱出口 PII mask
- #26 世界对象时间范围
- #27 Agent 自主可解释

## 沟通

- Issues: GitHub issues
- Discussions: GitHub Discussions
- Security: 参见 [SECURITY.md](SECURITY.md)

## 许可

贡献代码即视为接受 MIT 许可。
